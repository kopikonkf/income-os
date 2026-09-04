from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image

class UpscaleRecoveryError(RuntimeError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def sha256_file(path:str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

NONRECOVERABLE_CODES={'RIGHTS_FAILED','RIGHTS_UNCLEAR','SAFETY_FAILED','SAFETY_UNCLEAR','WATERMARK_PRESENT','WATERMARK_UNCLEAR','INTEGRITY_HASH_MISMATCH','INTEGRITY_FILE_MISSING','INTEGRITY_RASTER_CORRUPT','LINEAGE_MISSING','LINEAGE_MISMATCH'}
RECOVERABLE_CODES={'TECHNICAL_DIMENSION_BELOW_MINIMUM','DETAIL_SOFTNESS','COMPRESSION_ARTIFACTS'}

def decide_upscale_recovery(*,master:dict[str,Any],route_requirement:dict[str,Any],technical_defects:list[str]|None=None,rights_state:str='PASS')->dict[str,Any]:
    if master.get('schema')!='die.factory-asset.master-facts.v1': raise UpscaleRecoveryError('MASTER_FACTS_SCHEMA_INVALID',str(master.get('schema')))
    if rights_state not in {'PASS','REVIEW_REQUIRED','BLOCK'}: raise UpscaleRecoveryError('RIGHTS_STATE_INVALID',rights_state)
    defects=sorted(set(technical_defects or []))
    if rights_state!='PASS':
        return {'schema':'die.factory-asset.upscale-recovery-decision.v1','state':'BLOCK_NONRECOVERABLE','reasons':[f'RIGHTS_STATE_{rights_state}'],'source_sha256':master['sha256'],'source_dimensions':[master.get('width_px'),master.get('height_px')],'target_dimensions':None,'recovery_allowed':False,'upscale_required':False}
    nonrecoverable=sorted(set(defects)&NONRECOVERABLE_CODES)
    unknown=sorted(set(defects)-NONRECOVERABLE_CODES-RECOVERABLE_CODES)
    if nonrecoverable or unknown:
        return {'schema':'die.factory-asset.upscale-recovery-decision.v1','state':'BLOCK_NONRECOVERABLE','reasons':[*(f'NONRECOVERABLE:{x}' for x in nonrecoverable),*(f'UNCLASSIFIED_DEFECT:{x}' for x in unknown)],'source_sha256':master['sha256'],'source_dimensions':[master.get('width_px'),master.get('height_px')],'target_dimensions':None,'recovery_allowed':False,'upscale_required':False}
    min_w=int(route_requirement.get('min_width_px',0));min_h=int(route_requirement.get('min_height_px',0))
    if min_w<=0 or min_h<=0: raise UpscaleRecoveryError('ROUTE_REQUIREMENT_INVALID','positive min dimensions required')
    w=master.get('width_px');h=master.get('height_px')
    if not isinstance(w,int) or not isinstance(h,int): raise UpscaleRecoveryError('RASTER_DIMENSIONS_REQUIRED',str((w,h)))
    below=w<min_w or h<min_h
    needs_recovery=bool(defects)
    if not below and not needs_recovery:
        return {'schema':'die.factory-asset.upscale-recovery-decision.v1','state':'NOOP_SUFFICIENT','reasons':['ROUTE_REQUIREMENTS_ALREADY_SATISFIED'],'source_sha256':master['sha256'],'source_dimensions':[w,h],'target_dimensions':[w,h],'recovery_allowed':False,'upscale_required':False}
    scale=max(min_w/w,min_h/h,1.0)
    target=[max(min_w,int(round(w*scale))),max(min_h,int(round(h*scale)))]
    state='UPSCALE_REQUIRED' if below else 'RECOVERY_REQUIRED'
    reasons=[]
    if below: reasons.append('DIMENSIONS_BELOW_ROUTE_MINIMUM')
    reasons.extend(f'RECOVERABLE:{x}' for x in defects)
    return {'schema':'die.factory-asset.upscale-recovery-decision.v1','state':state,'reasons':reasons,'source_sha256':master['sha256'],'source_dimensions':[w,h],'target_dimensions':target,'recovery_allowed':True,'upscale_required':below}

def reference_resize_engine(source:Path,dest:Path,*,target_dimensions:list[int],engine_config:dict[str,Any])->dict[str,Any]:
    # Acceptance-only deterministic CPU reference. Production RealESRGAN remains pluggable.
    with Image.open(source) as img:
        img.load(); out=img.resize(tuple(target_dimensions),Image.Resampling.LANCZOS)
        fmt=img.format or 'PNG'
        kwargs={}
        if fmt=='PNG': kwargs['compress_level']=9
        out.save(dest,format=fmt,**kwargs)
    return {'engine_id':'PILLOW_LANCZOS_REFERENCE','engine_version':'1.0','model_sha256':None,'production_engine':False}

def execute_upscale_recovery(*,source_path:str|Path,output_path:str|Path,decision:dict[str,Any],engine:Callable[...,dict[str,Any]]=reference_resize_engine,engine_config:dict[str,Any]|None=None)->dict[str,Any]:
    source=Path(source_path).resolve();output=Path(output_path).resolve();sidecar=Path(str(output)+'.upscale-receipt.json')
    if not source.is_file(): raise UpscaleRecoveryError('SOURCE_NOT_FOUND',str(source))
    source_sha=sha256_file(source)
    if source_sha!=decision.get('source_sha256'): raise UpscaleRecoveryError('SOURCE_HASH_MISMATCH',source_sha)
    source_before=source.read_bytes()
    if decision['state']=='BLOCK_NONRECOVERABLE': raise UpscaleRecoveryError('RECOVERY_FORBIDDEN',','.join(decision.get('reasons',[])))
    if decision['state']=='NOOP_SUFFICIENT':
        return {'schema':'die.factory-asset.upscale-recovery-receipt.v1','result':'NOOP','decision_state':'NOOP_SUFFICIENT','source_sha256':source_sha,'source_dimensions':decision['source_dimensions'],'final_sha256':source_sha,'final_dimensions':decision['source_dimensions'],'output_path':str(source),'source_unchanged':True,'idempotent_reuse':True,'engine':None,'partial_output':False}
    if decision['state'] not in {'UPSCALE_REQUIRED','RECOVERY_REQUIRED'}: raise UpscaleRecoveryError('DECISION_STATE_INVALID',str(decision.get('state')))
    config=dict(engine_config or {})
    engine_id=config.get('engine_id')
    if not isinstance(engine_id,str) or not engine_id.strip(): raise UpscaleRecoveryError('ENGINE_ID_REQUIRED','engine_config.engine_id')
    if config.get('production_engine') is True:
        model_sha=str(config.get('model_sha256') or '')
        if len(model_sha)!=64 or any(c not in '0123456789abcdef' for c in model_sha): raise UpscaleRecoveryError('PRODUCTION_MODEL_SHA256_REQUIRED',model_sha)
    key=_sha({'source_sha256':source_sha,'state':decision['state'],'target_dimensions':decision['target_dimensions'],'engine_config':config})
    if output.exists() and sidecar.exists():
        prior=json.loads(sidecar.read_text(encoding='utf-8'))
        if prior.get('idempotency_key')==key and prior.get('final_sha256')==sha256_file(output):
            return {**prior,'idempotent_reuse':True}
        raise UpscaleRecoveryError('OUTPUT_EXISTS_CONFLICT',str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temp_name=tempfile.mkstemp(prefix='.fa135-',suffix=output.suffix,dir=str(output.parent))
    os.close(fd)
    temp=Path(temp_name)
    try:
        temp.unlink(missing_ok=True)
        meta=engine(source,temp,target_dimensions=decision['target_dimensions'],engine_config=config)
        if str(meta.get('engine_id'))!=engine_id: raise UpscaleRecoveryError('ENGINE_ID_MISMATCH',str(meta.get('engine_id')))
        if config.get('production_engine') is True and meta.get('model_sha256')!=config.get('model_sha256'): raise UpscaleRecoveryError('MODEL_SHA256_MISMATCH',str(meta.get('model_sha256')))
        if not temp.is_file() or temp.stat().st_size<=0: raise UpscaleRecoveryError('ENGINE_OUTPUT_MISSING',str(temp))
        with Image.open(temp) as check:
            check.load();dims=list(check.size)
        if dims!=decision['target_dimensions']: raise UpscaleRecoveryError('OUTPUT_DIMENSION_MISMATCH',str(dims))
        final_sha=sha256_file(temp)
        if source.read_bytes()!=source_before or sha256_file(source)!=source_sha: raise UpscaleRecoveryError('SOURCE_MUTATED',str(source))
        if output.exists(): raise UpscaleRecoveryError('OUTPUT_RACE_CONFLICT',str(output))
        os.replace(temp,output)
        receipt={'schema':'die.factory-asset.upscale-recovery-receipt.v1','result':'PASS','decision_state':decision['state'],'source_sha256':source_sha,'source_dimensions':decision['source_dimensions'],'final_sha256':final_sha,'final_dimensions':dims,'output_path':str(output),'source_unchanged':True,'idempotency_key':key,'idempotent_reuse':False,'engine':meta,'partial_output':False}
        sidecar.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
        return receipt
    except Exception:
        temp.unlink(missing_ok=True)
        if output.exists() and not sidecar.exists(): output.unlink(missing_ok=True)
        if source.read_bytes()!=source_before: raise UpscaleRecoveryError('SOURCE_MUTATED_DURING_FAILURE',str(source))
        raise
    finally:
        temp.unlink(missing_ok=True)