from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
PROFILE_PATH=ROOT/'company/factory-asset/registries/marketplace-delivery-profiles.v1.json'

def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod
blueprint_compiler=_load('fa132_blueprint_compiler',ROOT/'company/factory-asset/lib/blueprint_compiler.py')

class DerivativePlanningError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def load_profiles()->dict[str,Any]: return json.loads(PROFILE_PATH.read_text(encoding='utf-8'))

def provider_master_facts(*,provider_original:dict[str,Any],semantic_asset_id:str,blueprint_id:str)->dict[str,Any]:
    if provider_original.get('schema')!='die.factory-asset.provider-original.v1': raise DerivativePlanningError('PROVIDER_ORIGINAL_SCHEMA_INVALID',str(provider_original.get('schema')))
    media=provider_original.get('media') or {}
    if not media.get('decode_verified') or not provider_original.get('sha256'): raise DerivativePlanningError('PROVIDER_ORIGINAL_UNVERIFIED','decode/hash required')
    return {
      'schema':'die.factory-asset.master-facts.v1','source_kind':'PROVIDER_ORIGINAL','provider_id':provider_original.get('provider_id'),'semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,
      'sha256':provider_original['sha256'],'format':media['format'],'width_px':media['width_px'],'height_px':media['height_px'],
      'has_alpha_channel':bool(media.get('has_alpha_channel')),'has_transparency_metadata':bool(media.get('has_transparency_metadata')),'has_transparency':bool(media.get('has_transparency')),
      'provider_original_lineage':{'source_filename':provider_original.get('source_filename'),'byte_preservation':provider_original.get('byte_preservation'),'transformation':provider_original.get('transformation')},
    }

def native_master_facts(*,semantic_asset_id:str,blueprint_id:str,sha256:str,format:str)->dict[str,Any]:
    if len(sha256)!=64 or any(c not in '0123456789abcdef' for c in sha256): raise DerivativePlanningError('MASTER_SHA256_INVALID',sha256)
    if format not in {'SVG','EPS','MP4','MOV'}: raise DerivativePlanningError('NATIVE_MASTER_FORMAT_UNSUPPORTED',format)
    return {'schema':'die.factory-asset.master-facts.v1','source_kind':'NATIVE_MASTER','provider_id':None,'semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,'sha256':sha256,'format':format,'width_px':None,'height_px':None,'has_alpha_channel':False,'has_transparency_metadata':False,'has_transparency':False,'provider_original_lineage':None}

def _canonical_profile_formats(profile:dict[str,Any],family:str)->set[str]:
    delivery=profile.get('delivery',{})
    keys={'RASTER':['raster','raster_photo'],'VECTOR':['vector','vector_source','vector_bundle'],'MOTION':['video']}[family]
    out=set()
    for key in keys:
        for raw in delivery.get(key,[]):
            text=str(raw).upper().replace('JPG','JPEG')
            for fmt in ('JPEG','PNG','WEBP','TIFF','PDF','SVG','EPS','AI','MP4','MOV'):
                if fmt in text: out.add(fmt)
    return out

def _family(blueprint:dict[str,Any])->str:
    rep=blueprint['native_representation']
    return {'RASTER_PIXELS':'RASTER','VECTOR_PATHS':'VECTOR','TIMED_FRAMES':'MOTION'}[rep]

def _alpha_policy(master:dict[str,Any],output_format:str)->str:
    alpha_present=bool(master.get('has_alpha_channel') or master.get('has_transparency_metadata'))
    if output_format in {'JPEG','PDF'}: return 'FLATTEN_WHITE' if alpha_present else 'NOT_APPLICABLE'
    if output_format in {'PNG','WEBP','TIFF'}: return 'PRESERVE' if alpha_present else 'NOT_APPLICABLE'
    return 'NOT_APPLICABLE'

def _action(master:dict[str,Any],output_format:str,alpha_policy:str,family:str)->str:
    if master['format']==output_format and alpha_policy in {'NOT_APPLICABLE','PRESERVE'}: return 'REUSE_MASTER_BYTES'
    if family=='RASTER':
        if output_format in {'JPEG','PNG','WEBP','TIFF'}: return 'RASTER_DERIVATIVE'
        if output_format=='PDF': return 'PDF_PREVIEW_PACKAGE'
        raise DerivativePlanningError('RASTER_OUTPUT_UNSUPPORTED',output_format)
    if family=='VECTOR':
        if output_format in {'SVG','EPS'}: return 'NATIVE_VECTOR_EXPORT'
        if output_format in {'PNG','JPEG','WEBP','PDF'}: return 'VECTOR_PREVIEW_RENDER'
        raise DerivativePlanningError('VECTOR_OUTPUT_UNSUPPORTED',output_format)
    if family=='MOTION':
        if output_format in {'MP4','MOV'}: return 'MOTION_TRANSCODE_OR_REUSE'
        if output_format in {'PNG','JPEG','WEBP'}: return 'MOTION_STILL_PREVIEW'
        raise DerivativePlanningError('MOTION_OUTPUT_UNSUPPORTED',output_format)
    raise DerivativePlanningError('FAMILY_UNSUPPORTED',family)

def plan_derivatives(*,blueprint:dict[str,Any],master:dict[str,Any],profiles:dict[str,Any]|None=None)->dict[str,Any]:
    try: blueprint_compiler.validate_blueprint(blueprint)
    except Exception as exc: raise DerivativePlanningError('BLUEPRINT_INVALID',f'{getattr(exc,"code","UNKNOWN")}:{exc}') from exc
    if master.get('schema')!='die.factory-asset.master-facts.v1': raise DerivativePlanningError('MASTER_FACTS_SCHEMA_INVALID',str(master.get('schema')))
    if master.get('semantic_asset_id')!=blueprint['semantic_identity']['semantic_asset_id']: raise DerivativePlanningError('MASTER_SEMANTIC_ID_MISMATCH',str(master.get('semantic_asset_id')))
    if master.get('blueprint_id')!=blueprint['blueprint_id']: raise DerivativePlanningError('MASTER_BLUEPRINT_ID_MISMATCH',str(master.get('blueprint_id')))
    fam=_family(blueprint); registry=profiles or load_profiles(); profile_by={p['platform_id']:p for p in registry['profiles']}
    requested_profiles=list(blueprint['policy']['marketplace_profiles'])
    entries=[]; seen={}
    for derivative in blueprint['derivatives']:
        fmt=derivative['format']; purpose=derivative['purpose']; alpha=_alpha_policy(master,fmt); action=_action(master,fmt,alpha,fam)
        compatibility='INTERNAL'; reasons=[]; package_blocked=False
        delivery_profiles=[]
        if purpose=='MARKETPLACE_DELIVERY':
            for platform in requested_profiles:
                profile=profile_by.get(platform)
                if profile is None: raise DerivativePlanningError('MARKETPLACE_PROFILE_UNKNOWN',platform)
                delivery_profiles.append(platform)
                if profile.get('profile_state')!='EVIDENCE_PINNED':
                    compatibility='COMPATIBILITY_UNKNOWN';package_blocked=True;reasons.append(f'{platform}:PROFILE_{profile.get("profile_state")}')
                    continue
                allowed=_canonical_profile_formats(profile,fam)
                if fmt not in allowed:
                    compatibility='INCOMPATIBLE';package_blocked=True;reasons.append(f'{platform}:FORMAT_NOT_PINNED:{fmt}')
                elif compatibility not in {'INCOMPATIBLE','COMPATIBILITY_UNKNOWN'}:
                    compatibility='COMPATIBLE';reasons.append(f'{platform}:PINNED_FORMAT_MATCH:{fmt}')
        transparent_claim=fmt in {'PNG','WEBP','TIFF'} and bool(master.get('has_transparency')) and alpha=='PRESERVE'
        signature=(purpose,fmt,tuple(sorted(delivery_profiles)),alpha,action,compatibility)
        if signature in seen:
            seen[signature]['aliases'].append(derivative['derivative_id']);continue
        row={
          'derivative_id':derivative['derivative_id'],'aliases':[],'purpose':purpose,'format':fmt,'action':action,'alpha_policy':alpha,'transparent_output_claim':transparent_claim,
          'semantic_asset_id':master['semantic_asset_id'],'semantic_identity_effect':'NONE','master_sha256':master['sha256'],'master_format':master['format'],'source_kind':master['source_kind'],'provider_id':master.get('provider_id'),
          'marketplace_profiles':sorted(delivery_profiles),'compatibility_state':compatibility,'compatibility_reasons':reasons,'package_blocked':package_blocked,
        }
        row['plan_key']=_sha({k:row[k] for k in ('purpose','format','action','alpha_policy','semantic_asset_id','master_sha256','marketplace_profiles','compatibility_state')})
        entries.append(row);seen[signature]=row
    blocked=any(x['package_blocked'] for x in entries if x['purpose']=='MARKETPLACE_DELIVERY')
    return {
      'schema':'die.factory-asset.derivative-delivery-plan.v1','result':'PLANNED','blueprint_id':blueprint['blueprint_id'],'semantic_asset_id':master['semantic_asset_id'],'semantic_asset_count':1,'master_sha256':master['sha256'],'master_format':master['format'],'source_kind':master['source_kind'],'provider_original_lineage':master.get('provider_original_lineage'),
      'derivative_count':len(entries),'entries':entries,'package_blocked':blocked,'submission_authority':'FOUNDER_CONTROLLED','provider_original_bytes_mutated':False,'packaging_variants_create_new_semantic_asset':False,
      'plan_sha256':_sha(entries),
    }