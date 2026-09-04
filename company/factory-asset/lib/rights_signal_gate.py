from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
POLICY_PATH=ROOT/'company/factory-asset/registries/rights-signal-policy.v1.json'

class RightsSignalError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def sha256_file(path:str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def load_policy()->dict[str,Any]:return json.loads(POLICY_PATH.read_text(encoding='utf-8'))

def _norm(text:str)->str:return ' '.join(text.casefold().split())

def _validate_observation(obs:dict[str,Any],master_sha:str,policy:dict[str,Any])->dict[str,Any]:
    if obs.get('schema')!='die.factory-asset.rights-observation.v1':raise RightsSignalError('OBSERVATION_SCHEMA_INVALID',str(obs.get('schema')))
    if obs.get('master_sha256')!=master_sha:raise RightsSignalError('OBSERVATION_MASTER_HASH_MISMATCH',str(obs.get('master_sha256')))
    detectors=obs.get('detectors')
    if not isinstance(detectors,dict):raise RightsSignalError('DETECTORS_REQUIRED','object required')
    required=set(policy['required_detectors']);unknown=set(detectors)-required;missing=required-set(detectors)
    if unknown:raise RightsSignalError('DETECTOR_UNKNOWN',','.join(sorted(unknown)))
    if missing:raise RightsSignalError('DETECTOR_MISSING',','.join(sorted(missing)))
    return detectors

def evaluate_rights_signals(*,master_path:str|Path,expected_sha256:str,observation:dict[str,Any],policy:dict[str,Any]|None=None)->dict[str,Any]:
    p=Path(master_path).resolve()
    if not p.is_file():raise RightsSignalError('MASTER_NOT_FOUND',str(p))
    actual=sha256_file(p)
    if actual!=expected_sha256:raise RightsSignalError('MASTER_HASH_MISMATCH',actual)
    pol=policy or load_policy();d=_validate_observation(observation,actual,pol)
    blocking=[];review=[];evidence=[]
    complete_state=pol['detector_complete_state']
    for name in pol['required_detectors']:
        state=d[name].get('state')
        if state!=complete_state:
            review.append({'signal':'DETECTOR_INCOMPLETE','detector':name,'detail':str(state)})
    text=d['text'];strings=text.get('detected_strings',[])
    if not isinstance(strings,list) or any(not isinstance(x,str) for x in strings):raise RightsSignalError('TEXT_STRINGS_INVALID','list[str] required')
    normalized=[_norm(x) for x in strings if x.strip()]
    for term in pol['stock_watermark_terms']:
        t=_norm(term)
        if any(t in s for s in normalized):blocking.append({'signal':'WATERMARK_PRESENT','detector':'text','detail':term})
    confirmed=text.get('confirmed_trademark_terms',[]);candidates=text.get('trademark_candidates',[]);unresolved=text.get('unresolved_strings',[])
    for label in confirmed:blocking.append({'signal':'TRADEMARK_CONFIRMED','detector':'text','detail':str(label)})
    for label in candidates:review.append({'signal':'TRADEMARK_CANDIDATE','detector':'text','detail':str(label)})
    for label in unresolved:review.append({'signal':'TEXT_PRESENT_UNRESOLVED','detector':'text','detail':str(label)})
    logo=d['logo'];
    for item in logo.get('candidates',[]):
        if item.get('confirmed_brand') is True:blocking.append({'signal':'BRAND_LOGO_CONFIRMED','detector':'logo','detail':str(item.get('label','unknown'))})
        else:review.append({'signal':'LOGO_CANDIDATE','detector':'logo','detail':str(item.get('label','unknown'))})
    watermark=d['watermark']
    for item in watermark.get('candidates',[]):
        if item.get('confirmed') is True:blocking.append({'signal':'WATERMARK_PRESENT','detector':'watermark','detail':str(item.get('label','watermark'))})
        else:review.append({'signal':'WATERMARK_UNCLEAR','detector':'watermark','detail':str(item.get('label','candidate'))})
    safety=d['safety']
    for item in safety.get('flags',[]):
        disp=item.get('disposition')
        if disp=='BLOCK':blocking.append({'signal':'SAFETY_FAILED','detector':'safety','detail':str(item.get('code','unknown'))})
        elif disp=='REVIEW':review.append({'signal':'SAFETY_UNCLEAR','detector':'safety','detail':str(item.get('code','unknown'))})
        else:raise RightsSignalError('SAFETY_DISPOSITION_INVALID',str(disp))
    # Stable dedupe while preserving first evidence occurrence.
    def dedupe(rows):
        seen=set();out=[]
        for row in rows:
            key=(row['signal'],row['detector'],row['detail'])
            if key not in seen:seen.add(key);out.append(row)
        return out
    blocking=dedupe(blocking);review=dedupe(review)
    if blocking:route='BLOCK'
    elif review:route='REVIEW_REQUIRED'
    else:route='PASS'
    defect_map={'WATERMARK_PRESENT':'WATERMARK_PRESENT','TRADEMARK_CONFIRMED':'RIGHTS_FAILED','BRAND_LOGO_CONFIRMED':'RIGHTS_FAILED','SAFETY_FAILED':'SAFETY_FAILED','DETECTOR_INCOMPLETE':'RIGHTS_UNCLEAR','TEXT_PRESENT_UNRESOLVED':'RIGHTS_UNCLEAR','TRADEMARK_CANDIDATE':'RIGHTS_UNCLEAR','LOGO_CANDIDATE':'RIGHTS_UNCLEAR','WATERMARK_UNCLEAR':'WATERMARK_UNCLEAR','SAFETY_UNCLEAR':'SAFETY_UNCLEAR'}
    defects=[]
    for row in blocking+review:
        code=defect_map[row['signal']]
        if code not in defects:defects.append(code)
    return {
      'schema':'die.factory-asset.rights-signal-gate.v1','result':route,'master_sha256':actual,'master_path':str(p),'detector_states':{k:d[k].get('state') for k in pol['required_detectors']},
      'blocking_signals':blocking,'review_signals':review,'qa_defects':defects,'human_rights_clearance':False,'founder_qc_required':True,'submission_eligible':False,'submission_authority':'FOUNDER_CONTROLLED','signal_gate_pass':route=='PASS'
    }