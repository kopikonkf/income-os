from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

STATES=[
 'ARTIFACT_CREATED','MASTER_VALIDATED','UPSCALE_DECIDED','DERIVATIVES_READY','TECHNICAL_QA_PASS',
 'RIGHTS_SIGNAL_PASS_OR_REVIEW','METADATA_READY','PACKAGE_READY','WAITING_FOUNDER_QC'
]

class PostproductionStateError(RuntimeError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()

def _valid_sha(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

def _atomic_write(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.fa138-',suffix='.json',dir=str(path.parent));os.close(fd);tmp=Path(name)
    try:
        payload=json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n'
        with tmp.open('w',encoding='utf-8',newline='\n') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally: tmp.unlink(missing_ok=True)

def load_state(path:str|Path)->dict[str,Any]:
    p=Path(path)
    if not p.is_file(): raise PostproductionStateError('STATE_NOT_FOUND',str(p))
    try: d=json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc: raise PostproductionStateError('STATE_CORRUPT',str(exc)) from exc
    if d.get('schema')!='die.factory-asset.postproduction-state.v1' or d.get('state') not in STATES: raise PostproductionStateError('STATE_SCHEMA_INVALID',str(d.get('schema')))
    return d

def create_state(path:str|Path,*,job_id:str,semantic_asset_id:str,blueprint_id:str,source_master_sha256:str)->dict[str,Any]:
    p=Path(path)
    if not _valid_sha(source_master_sha256): raise PostproductionStateError('SOURCE_MASTER_SHA256_INVALID',str(source_master_sha256))
    identity={'job_id':job_id,'semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,'source_master_sha256':source_master_sha256}
    if p.exists():
        d=load_state(p)
        for k,v in identity.items():
            if d.get(k)!=v: raise PostproductionStateError('STATE_IDENTITY_CONFLICT',k)
        return d
    d={'schema':'die.factory-asset.postproduction-state.v1',**identity,'active_master_sha256':source_master_sha256,'state':'ARTIFACT_CREATED','status':'ACTIVE','revision':0,'rights_disposition':None,'derivatives':[],'metadata_sha256':None,'package_plan_sha256':None,'last_failure':None,'history':[{'kind':'CREATE','event_id':'CREATE','from':None,'to':'ARTIFACT_CREATED','revision':0,'evidence_sha256':_sha(identity),'evidence':identity}]}
    _atomic_write(p,d);return d

def _existing_event(d:dict[str,Any],event_id:str,target:str,evidence_sha:str)->dict[str,Any]|None:
    for row in d['history']:
        if row.get('event_id')==event_id:
            if row.get('to')==target and row.get('evidence_sha256')==evidence_sha: return d
            raise PostproductionStateError('EVENT_ID_CONFLICT',event_id)
    return None

def _require_revision(d:dict[str,Any],expected_revision:int)->None:
    if d['revision']!=expected_revision: raise PostproductionStateError('STALE_REVISION',f"expected {expected_revision}, actual {d['revision']}")

def _derivative_map(rows:list[dict[str,Any]])->dict[str,str]:
    out={}
    for row in rows:
        did=str(row.get('derivative_id',''));sha=str(row.get('sha256',''))
        if not did or not _valid_sha(sha): raise PostproductionStateError('DERIVATIVE_EVIDENCE_INVALID',did)
        if did in out: raise PostproductionStateError('DUPLICATE_DERIVATIVE_ID',did)
        out[did]=sha
    return out

def _validate_transition(d:dict[str,Any],target:str,e:dict[str,Any])->dict[str,Any]:
    changes={}
    active=d['active_master_sha256']
    if target=='MASTER_VALIDATED':
        if e.get('result')!='PASS' or e.get('master_sha256')!=active: raise PostproductionStateError('MASTER_VALIDATION_INVALID',str(e.get('master_sha256')))
    elif target=='UPSCALE_DECIDED':
        if e.get('result') not in {'NOOP','PASS'} or e.get('source_sha256')!=active or e.get('source_unchanged') is not True: raise PostproductionStateError('UPSCALE_EVIDENCE_INVALID',str(e.get('result')))
        final=e.get('final_sha256')
        if not _valid_sha(final): raise PostproductionStateError('UPSCALE_FINAL_SHA256_INVALID',str(final))
        changes['active_master_sha256']=final
    elif target=='DERIVATIVES_READY':
        if e.get('master_sha256')!=active: raise PostproductionStateError('DERIVATIVE_MASTER_HASH_MISMATCH',str(e.get('master_sha256')))
        rows=e.get('derivatives')
        if not isinstance(rows,list) or not rows: raise PostproductionStateError('DERIVATIVES_REQUIRED','empty')
        for row in rows:
            if row.get('master_sha256')!=active: raise PostproductionStateError('DERIVATIVE_MASTER_HASH_MISMATCH',str(row.get('derivative_id')))
        changes['derivatives']=[{'derivative_id':k,'sha256':v} for k,v in sorted(_derivative_map(rows).items())]
    elif target=='TECHNICAL_QA_PASS':
        if e.get('result')!='PASS': raise PostproductionStateError('TECHNICAL_QA_NOT_PASS',str(e.get('result')))
        expected=_derivative_map(d['derivatives']);actual={}
        for row in e.get('derivatives',[]):
            if row.get('result')!='PASS': raise PostproductionStateError('DERIVATIVE_QA_NOT_PASS',str(row.get('derivative_id')))
            actual[str(row.get('derivative_id'))]=str(row.get('sha256'))
        if actual!=expected: raise PostproductionStateError('TECHNICAL_QA_HASH_SET_MISMATCH',str(actual))
    elif target=='RIGHTS_SIGNAL_PASS_OR_REVIEW':
        disposition=e.get('result')
        if disposition not in {'PASS','REVIEW_REQUIRED'}: raise PostproductionStateError('RIGHTS_SIGNAL_NOT_ADVANCEABLE',str(disposition))
        if e.get('master_sha256')!=active: raise PostproductionStateError('RIGHTS_MASTER_HASH_MISMATCH',str(e.get('master_sha256')))
        changes['rights_disposition']=disposition
    elif target=='METADATA_READY':
        if e.get('master_sha256')!=active or not _valid_sha(e.get('metadata_sha256')): raise PostproductionStateError('METADATA_EVIDENCE_INVALID',str(e.get('master_sha256')))
        expected=_derivative_map(d['derivatives']);actual=_derivative_map(e.get('derivative_hashes',[]))
        if actual!=expected: raise PostproductionStateError('METADATA_DERIVATIVE_HASH_MISMATCH',str(actual))
        changes['metadata_sha256']=e['metadata_sha256']
    elif target=='PACKAGE_READY':
        if d.get('rights_disposition')!='PASS': raise PostproductionStateError('RIGHTS_REVIEW_UNRESOLVED',str(d.get('rights_disposition')))
        if e.get('result')!='PACKAGE_READY' or e.get('master_sha256')!=active: raise PostproductionStateError('PACKAGE_READINESS_INVALID',str(e.get('result')))
        plan=e.get('package_plan') or {}
        if plan.get('master_sha256')!=active or plan.get('metadata_sha256')!=d.get('metadata_sha256'): raise PostproductionStateError('PACKAGE_LINEAGE_MISMATCH','master/metadata')
        expected=_derivative_map(d['derivatives']);actual=_derivative_map(plan.get('deliverables',[]))
        if actual!=expected: raise PostproductionStateError('PACKAGE_DERIVATIVE_HASH_MISMATCH',str(actual))
        psha=plan.get('package_plan_sha256')
        if not _valid_sha(psha): raise PostproductionStateError('PACKAGE_PLAN_SHA256_INVALID',str(psha))
        changes['package_plan_sha256']=psha
    elif target=='WAITING_FOUNDER_QC':
        if e.get('founder_qc_required') is not True or e.get('human_rights_clearance') is not False: raise PostproductionStateError('FOUNDER_QC_EVIDENCE_INVALID','Founder gate invariants')
        if e.get('package_plan_sha256')!=d.get('package_plan_sha256'): raise PostproductionStateError('FOUNDER_QC_PACKAGE_HASH_MISMATCH',str(e.get('package_plan_sha256')))
        changes['status']='PARKED_HUMAN_GATE'
    else: raise PostproductionStateError('TARGET_STATE_INVALID',target)
    return changes

def advance(path:str|Path,*,target_state:str,evidence:dict[str,Any],event_id:str,expected_revision:int)->dict[str,Any]:
    p=Path(path);d=load_state(p);evidence_sha=_sha(evidence)
    prior=_existing_event(d,event_id,target_state,evidence_sha)
    if prior is not None: return prior
    _require_revision(d,expected_revision)
    if d['status']=='BLOCKED': raise PostproductionStateError('STATE_BLOCKED_BY_FAILURE',str(d.get('last_failure')))
    if d['status']=='PARKED_HUMAN_GATE': raise PostproductionStateError('STATE_ALREADY_PARKED',d['state'])
    try: expected=STATES[STATES.index(d['state'])+1]
    except IndexError: raise PostproductionStateError('STATE_TERMINAL',d['state'])
    if target_state!=expected: raise PostproductionStateError('STATE_TRANSITION_INVALID',f"{d['state']}->{target_state}, expected {expected}")
    changes=_validate_transition(d,target_state,evidence)
    new=json.loads(json.dumps(d));new.update(changes);new['state']=target_state;new['revision']=d['revision']+1
    new['history'].append({'kind':'ADVANCE','event_id':event_id,'from':d['state'],'to':target_state,'revision':new['revision'],'evidence_sha256':evidence_sha,'evidence':evidence})
    _atomic_write(p,new);return new

def record_failure(path:str|Path,*,code:str,retryable:bool,stage:str,evidence:dict[str,Any],event_id:str,expected_revision:int)->dict[str,Any]:
    p=Path(path);d=load_state(p);payload={'code':code,'retryable':retryable,'stage':stage,'evidence':evidence};esha=_sha(payload)
    prior=_existing_event(d,event_id,d['state'],esha)
    if prior is not None:return prior
    _require_revision(d,expected_revision)
    if d['status']=='PARKED_HUMAN_GATE': raise PostproductionStateError('STATE_ALREADY_PARKED',d['state'])
    if not code or stage not in STATES: raise PostproductionStateError('FAILURE_INPUT_INVALID',f'{code}:{stage}')
    new=json.loads(json.dumps(d));new['revision']=d['revision']+1;new['status']='BLOCKED';new['last_failure']={'code':code,'retryable':bool(retryable),'stage':stage,'evidence_sha256':_sha(evidence)}
    new['history'].append({'kind':'FAILURE','event_id':event_id,'from':d['state'],'to':d['state'],'revision':new['revision'],'evidence_sha256':esha,'evidence':payload})
    _atomic_write(p,new);return new

def resume_retry(path:str|Path,*,event_id:str,expected_revision:int)->dict[str,Any]:
    p=Path(path);d=load_state(p);e={'failure':d.get('last_failure')};esha=_sha(e)
    prior=_existing_event(d,event_id,d['state'],esha)
    if prior is not None:return prior
    _require_revision(d,expected_revision)
    failure=d.get('last_failure')
    if d.get('status')!='BLOCKED' or not failure: raise PostproductionStateError('NO_BLOCKED_FAILURE','resume')
    if failure.get('retryable') is not True: raise PostproductionStateError('FAILURE_NOT_RETRYABLE',failure.get('code',''))
    new=json.loads(json.dumps(d));new['revision']=d['revision']+1;new['status']='ACTIVE';new['last_failure']=None
    new['history'].append({'kind':'RESUME','event_id':event_id,'from':d['state'],'to':d['state'],'revision':new['revision'],'evidence_sha256':esha,'evidence':e})
    _atomic_write(p,new);return new

def resolve_rights_review(path:str|Path,*,evidence:dict[str,Any],event_id:str,expected_revision:int)->dict[str,Any]:
    p=Path(path);d=load_state(p);esha=_sha(evidence)
    prior=_existing_event(d,event_id,d['state'],esha)
    if prior is not None:return prior
    _require_revision(d,expected_revision)
    if STATES.index(d['state'])<STATES.index('RIGHTS_SIGNAL_PASS_OR_REVIEW') or d.get('rights_disposition')!='REVIEW_REQUIRED': raise PostproductionStateError('RIGHTS_REVIEW_NOT_PENDING',str(d.get('rights_disposition')))
    if evidence.get('result')!='PASS' or evidence.get('master_sha256')!=d['active_master_sha256']: raise PostproductionStateError('RIGHTS_RESOLUTION_INVALID',str(evidence.get('result')))
    new=json.loads(json.dumps(d));new['revision']=d['revision']+1;new['rights_disposition']='PASS'
    new['history'].append({'kind':'RIGHTS_RESOLUTION','event_id':event_id,'from':d['state'],'to':d['state'],'revision':new['revision'],'evidence_sha256':esha,'evidence':evidence})
    _atomic_write(p,new);return new