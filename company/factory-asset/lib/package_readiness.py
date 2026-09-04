from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

class PackageReadinessError(ValueError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()

def _clean(text:str)->str:
    return ' '.join(str(text).split()).strip()

def _keywords(blueprint:dict[str,Any])->list[str]:
    sem=blueprint['semantic_identity']
    sources=[sem['subject'],sem['commercial_use_case'],blueprint['asset_type'].replace('_',' ')]
    words=[];seen=set()
    for source in sources:
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*",source.casefold()):
            if len(token)<2 or token in {'and','for','the','with','into','from','this','that'}: continue
            if token not in seen: seen.add(token);words.append(token)
    return words[:49]


def _slug(text:str)->str:
    value=re.sub(r'[^a-z0-9]+','-',str(text).casefold()).strip('-')
    return value[:72] or 'asset'

def _listing_filename(blueprint:dict[str,Any],master_sha256:str,bindings:list[dict[str,Any]])->str:
    delivery=next((x for x in bindings if x['purpose']=='MARKETPLACE_DELIVERY'),bindings[0])
    ext={'JPEG':'jpg','PNG':'png','WEBP':'webp','TIFF':'tiff','PDF':'pdf','SVG':'svg','EPS':'eps','MP4':'mp4','MOV':'mov'}.get(delivery['format'],delivery['format'].lower())
    subject=_slug(blueprint['semantic_identity']['subject']); mode=_slug(blueprint['asset_type'])
    return f'{subject}-{mode}__{master_sha256[:8]}.{ext}'

def build_metadata(*,blueprint:dict[str,Any],master_sha256:str,derivative_hashes:list[dict[str,Any]],provenance:dict[str,Any])->dict[str,Any]:
    if len(master_sha256)!=64 or any(c not in '0123456789abcdef' for c in master_sha256): raise PackageReadinessError('MASTER_SHA256_INVALID',master_sha256)
    if not derivative_hashes: raise PackageReadinessError('DERIVATIVE_HASHES_REQUIRED','empty')
    for row in derivative_hashes:
        if len(str(row.get('sha256','')))!=64: raise PackageReadinessError('DERIVATIVE_SHA256_INVALID',str(row.get('derivative_id')))
    source_class=provenance.get('source_class')
    if source_class not in {'GENERATIVE_AI','PROCEDURAL_NATIVE','MOTION_NATIVE','HUMAN_AUTHORED'}: raise PackageReadinessError('PROVENANCE_SOURCE_CLASS_INVALID',str(source_class))
    ai_generated=provenance.get('ai_generated')
    if type(ai_generated) is not bool: raise PackageReadinessError('AI_GENERATED_BOOLEAN_REQUIRED',str(ai_generated))
    if source_class=='GENERATIVE_AI' and ai_generated is not True: raise PackageReadinessError('AI_DISCLOSURE_CONTRADICTION',source_class)
    disclosure=provenance.get('ai_disclosure')
    if ai_generated:
        if disclosure!='GENERATIVE_AI': raise PackageReadinessError('AI_DISCLOSURE_REQUIRED',str(disclosure))
    elif disclosure!='NOT_AI_GENERATED': raise PackageReadinessError('AI_DISCLOSURE_REQUIRED',str(disclosure))
    sem=blueprint['semantic_identity'];subject=_clean(sem['subject']);use=_clean(sem['commercial_use_case'])
    title=_clean(provenance.get('title_override') or f"{subject.title()} - {blueprint['asset_type'].replace('_',' ').title()}")
    description=_clean(provenance.get('description_override') or f"{subject.capitalize()} created for {use}.")
    keywords=_keywords(blueprint)
    if not title or not description or len(keywords)<3: raise PackageReadinessError('METADATA_INCOMPLETE','title/description/keywords')
    bindings=sorted([{'derivative_id':str(x['derivative_id']),'format':str(x['format']),'purpose':str(x['purpose']),'sha256':str(x['sha256'])} for x in derivative_hashes],key=lambda x:x['derivative_id'])
    listing_filename=_listing_filename(blueprint,master_sha256,bindings)
    payload={'schema':'die.factory-asset.metadata-bundle.v1','blueprint_id':blueprint['blueprint_id'],'semantic_asset_id':sem['semantic_asset_id'],'master_sha256':master_sha256,'title':title,'description':description,'keywords':keywords,'ai_generated':ai_generated,'ai_disclosure':disclosure,'source_class':source_class,'derivative_hashes':bindings,'listing_filename':listing_filename,'submission_fields':{'title':title,'description':description,'keywords':keywords,'ai_disclosure':disclosure,'filename':listing_filename},'binary_metadata_injected':False,'metadata_delivery':'SIDECAR_AND_SUBMISSION_FIELDS','submission_authority':'FOUNDER_CONTROLLED'}
    payload['metadata_sha256']=_sha(payload)
    return payload

def evaluate_package_readiness(*,blueprint:dict[str,Any],derivative_plan:dict[str,Any],rights_signal:dict[str,Any],derivative_evidence:list[dict[str,Any]],provenance:dict[str,Any],master_technical_qa:dict[str,Any]) -> dict[str,Any]:
    blockers=[]
    master_sha=derivative_plan.get('master_sha256')
    if derivative_plan.get('semantic_asset_id')!=blueprint['semantic_identity']['semantic_asset_id']: blockers.append('SEMANTIC_ID_MISMATCH')
    if derivative_plan.get('blueprint_id')!=blueprint['blueprint_id']: blockers.append('BLUEPRINT_ID_MISMATCH')
    if derivative_plan.get('package_blocked') is True: blockers.append('DERIVATIVE_PLAN_BLOCKED')
    if master_technical_qa.get('result')!='PASS' or master_technical_qa.get('master_sha256')!=master_sha: blockers.append('MASTER_TECHNICAL_QA_NOT_PASS')
    if rights_signal.get('master_sha256')!=master_sha: blockers.append('RIGHTS_MASTER_HASH_MISMATCH')
    if rights_signal.get('result')=='REVIEW_REQUIRED': blockers.append('RIGHTS_REVIEW_REQUIRED')
    elif rights_signal.get('result')=='BLOCK': blockers.append('RIGHTS_BLOCK')
    elif rights_signal.get('result')!='PASS': blockers.append('RIGHTS_SIGNAL_INVALID')
    evidence_by={str(x.get('derivative_id')):x for x in derivative_evidence}
    if len(evidence_by)!=len(derivative_evidence): blockers.append('DUPLICATE_DERIVATIVE_EVIDENCE')
    binding_rows=[]
    for planned in derivative_plan.get('entries',[]):
        did=planned['derivative_id'];ev=evidence_by.get(did)
        if ev is None:
            blockers.append(f'DERIVATIVE_MISSING:{did}');continue
        if ev.get('master_sha256')!=master_sha: blockers.append(f'DERIVATIVE_MASTER_HASH_MISMATCH:{did}')
        if ev.get('format')!=planned['format'] or ev.get('purpose')!=planned['purpose']: blockers.append(f'DERIVATIVE_PLAN_MISMATCH:{did}')
        if ev.get('qa_result')!='PASS': blockers.append(f'DERIVATIVE_QA_NOT_PASS:{did}')
        if ev.get('sha256_verified') is not True: blockers.append(f'DERIVATIVE_HASH_NOT_VERIFIED:{did}')
        if ev.get('qa_sha256')!=ev.get('sha256'): blockers.append(f'DERIVATIVE_QA_HASH_MISMATCH:{did}')
        if len(str(ev.get('sha256','')))!=64: blockers.append(f'DERIVATIVE_HASH_INVALID:{did}')
        if planned['purpose']=='MARKETPLACE_DELIVERY' and planned.get('compatibility_state')!='COMPATIBLE': blockers.append(f'DERIVATIVE_INCOMPATIBLE:{did}')
        binding_rows.append({'derivative_id':did,'format':ev.get('format'),'purpose':ev.get('purpose'),'sha256':ev.get('sha256')})
    extra=sorted(set(evidence_by)-{x['derivative_id'] for x in derivative_plan.get('entries',[])})
    if extra: blockers.append('UNPLANNED_DERIVATIVE_EVIDENCE:'+','.join(extra))
    metadata=None
    try:
        metadata=build_metadata(blueprint=blueprint,master_sha256=master_sha,derivative_hashes=binding_rows,provenance=provenance)
    except PackageReadinessError as exc: blockers.append(exc.code)
    blockers=sorted(set(blockers))
    state='PACKAGE_READY' if not blockers else 'PACKAGE_BLOCKED'
    package_plan=None
    if state=='PACKAGE_READY':
        package_plan={'schema':'die.factory-asset.hash-bound-package-plan.v1','semantic_asset_id':blueprint['semantic_identity']['semantic_asset_id'],'blueprint_id':blueprint['blueprint_id'],'master_sha256':master_sha,'metadata_sha256':metadata['metadata_sha256'],'rights_signal_result':rights_signal['result'],'deliverables':sorted(binding_rows,key=lambda x:x['derivative_id']),'publication_action':'NONE','upload_action':'NONE','submission_authority':'FOUNDER_CONTROLLED'}
        package_plan['package_plan_sha256']=_sha(package_plan)
    return {'schema':'die.factory-asset.package-readiness.v1','result':state,'semantic_asset_id':blueprint['semantic_identity']['semantic_asset_id'],'blueprint_id':blueprint['blueprint_id'],'master_sha256':master_sha,'metadata':metadata,'package_plan':package_plan,'blockers':blockers,'founder_qc_required':True,'human_rights_clearance':False,'submission_authority':'FOUNDER_CONTROLLED'}