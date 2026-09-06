from __future__ import annotations
import hashlib, json, os, tempfile
from pathlib import Path
from typing import Any

SCHEMA='die.factory-asset.canonical-asset-registry.v1'
WRITER='DIE_STATE_MANAGER'

class FactoryStateManagerError(RuntimeError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def _sha(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def _valid_sha(v:Any)->bool:return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
def _atomic(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.state-manager-',suffix='.json',dir=str(path.parent));os.close(fd);tmp=Path(name)
    try:
        payload=json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n'
        with tmp.open('w',encoding='utf-8',newline='\n') as f:f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)

def empty_registry()->dict[str,Any]:
    return {'schema':SCHEMA,'revision':0,'canonical_writer':WRITER,'assets':[],'physical_masters':[],'history':[]}

def load_registry(path:str|Path)->dict[str,Any]:
    p=Path(path)
    if not p.exists():return empty_registry()
    d=json.loads(p.read_text(encoding='utf-8'))
    if d.get('schema')!=SCHEMA or d.get('canonical_writer')!=WRITER or not isinstance(d.get('assets'),list) or not isinstance(d.get('physical_masters'),list):raise FactoryStateManagerError('REGISTRY_SCHEMA_INVALID',str(p))
    return d

def _validate_proposal(p:dict[str,Any])->None:
    if p.get('schema')!='die.factory-asset.master-ingestion-proposal.v1' or p.get('action')!='FACTORY_MASTER_INGEST':raise FactoryStateManagerError('PROPOSAL_SCHEMA_INVALID',str(p.get('schema')))
    if p.get('physical_writer_required')!=WRITER:raise FactoryStateManagerError('WRITER_BOUNDARY_INVALID',str(p.get('physical_writer_required')))
    for k in ('semantic_asset_id','blueprint_id','master_sha256','staged_blob_path','attempt_receipt_path'):
        if not p.get(k):raise FactoryStateManagerError('PROPOSAL_INCOMPLETE',k)
    if not _valid_sha(p['master_sha256']):raise FactoryStateManagerError('MASTER_SHA_INVALID',str(p['master_sha256']))

def _validate_evidence(proposal:dict[str,Any],e:dict[str,Any])->None:
    if e.get('schema')!='die.factory-asset.asset-registry-commit-evidence.v1':raise FactoryStateManagerError('EVIDENCE_SCHEMA_INVALID',str(e.get('schema')))
    for k in ('semantic_asset_id','blueprint_id','master','derivatives','package_compatibility','capacity','orchestration'):
        if k not in e:raise FactoryStateManagerError('EVIDENCE_INCOMPLETE',k)
    if e['semantic_asset_id']!=proposal['semantic_asset_id'] or e['blueprint_id']!=proposal['blueprint_id']:raise FactoryStateManagerError('IDENTITY_MISMATCH','semantic/blueprint')
    m=e['master']
    if m.get('sha256')!=proposal['master_sha256'] or not _valid_sha(m.get('sha256')):raise FactoryStateManagerError('MASTER_HASH_MISMATCH',str(m.get('sha256')))
    if m.get('technical_qa')!='PASS':raise FactoryStateManagerError('MASTER_QA_NOT_PASS',str(m.get('technical_qa')))
    rows=e['derivatives']
    if not isinstance(rows,list) or not rows:raise FactoryStateManagerError('DERIVATIVES_REQUIRED','empty')
    seen=set()
    for r in rows:
        did=r.get('derivative_id')
        if not did or did in seen:raise FactoryStateManagerError('DERIVATIVE_ID_INVALID',str(did))
        seen.add(did)
        if not _valid_sha(r.get('sha256')) or r.get('technical_qa')!='PASS' or r.get('semantic_identity_effect')!='NONE':raise FactoryStateManagerError('DERIVATIVE_EVIDENCE_INVALID',str(did))
    pc=e['package_compatibility']
    if pc.get('state')!='TECHNICALLY_COMPATIBLE_METADATA_RIGHTS_PENDING' or pc.get('marketplace')!='ADOBE_STOCK':raise FactoryStateManagerError('PACKAGE_COMPATIBILITY_INVALID',str(pc))
    cap=e['capacity']
    if cap.get('kind')!='PROVIDER' or cap.get('provider_id')!='chatgpt' or cap.get('cluster_id')!='cluster-a' or cap.get('state')!='OBSERVED_SUCCESS' or cap.get('capacity_state_at_observation')!='AVAILABLE' or cap.get('evidence_type')!='OBSERVED_SUCCESS_NOT_QUOTA_GUESS' or cap.get('routing_eligible_now') is not False:raise FactoryStateManagerError('CAPACITY_EVIDENCE_INVALID',str(cap))
    orch=e['orchestration']
    if orch.get('state')!='TECHNICAL_QA_PASS' or orch.get('next_task')!='FA-204':raise FactoryStateManagerError('ORCHESTRATION_STATE_INVALID',str(orch))
    auth=e.get('authority') or {}
    if auth.get('submission_authorized') is not False or auth.get('publication_authorized') is not False or auth.get('marketplace_upload') is not False:raise FactoryStateManagerError('AUTHORITY_ESCALATION','submission/publication')

def commit_asset(*,registry_path:str|Path,proposal:dict[str,Any],evidence:dict[str,Any],writer_id:str)->dict[str,Any]:
    if writer_id!=WRITER:raise FactoryStateManagerError('WRITER_ID_FORBIDDEN',writer_id)
    _validate_proposal(proposal);_validate_evidence(proposal,evidence)
    path=Path(registry_path);d=load_registry(path)
    record={'semantic_asset_id':proposal['semantic_asset_id'],'blueprint_id':proposal['blueprint_id'],'master_sha256':proposal['master_sha256'],'canonical_truth':True,'state':'TECHNICAL_QA_PASS','rights_state':'REVIEW_REQUIRED','package_state':'METADATA_RIGHTS_PENDING','derivatives':evidence['derivatives'],'package_compatibility':evidence['package_compatibility'],'capacity':evidence['capacity'],'orchestration':evidence['orchestration'],'authority':evidence['authority'],'source_proposal_sha256':_sha(proposal),'evidence_sha256':_sha(evidence),'committed_by':WRITER}
    record_sha=_sha(record)
    same=[x for x in d['assets'] if x.get('semantic_asset_id')==proposal['semantic_asset_id']]
    if same:
        old=same[0]
        if old.get('record_sha256')==record_sha:return {'schema':'die.factory-asset.state-manager-commit.v1','result':'IDEMPOTENT_REUSE','canonical_truth':True,'semantic_asset_id':proposal['semantic_asset_id'],'master_sha256':proposal['master_sha256'],'record_sha256':record_sha,'revision':d['revision'],'duplicate_suppressed':True,'committed_by':WRITER}
        raise FactoryStateManagerError('SEMANTIC_ASSET_CONFLICT',proposal['semantic_asset_id'])
    physical=next((x for x in d['physical_masters'] if x.get('sha256')==proposal['master_sha256']),None)
    physical_reused=physical is not None
    if physical is None:
        physical={'sha256':proposal['master_sha256'],'staged_blob_path':proposal['staged_blob_path'],'first_semantic_asset_id':proposal['semantic_asset_id']};d['physical_masters'].append(physical)
    record['record_sha256']=record_sha
    d['assets'].append(record);d['assets'].sort(key=lambda x:x['semantic_asset_id']);d['physical_masters'].sort(key=lambda x:x['sha256']);d['revision']+=1
    event={'kind':'ASSET_COMMIT','revision':d['revision'],'semantic_asset_id':proposal['semantic_asset_id'],'master_sha256':proposal['master_sha256'],'record_sha256':record['record_sha256'],'physical_master_reused':physical_reused,'writer':WRITER};event['event_sha256']=_sha(event);d['history'].append(event)
    _atomic(path,d)
    return {'schema':'die.factory-asset.state-manager-commit.v1','result':'COMMITTED','canonical_truth':True,'semantic_asset_id':proposal['semantic_asset_id'],'master_sha256':proposal['master_sha256'],'record_sha256':record['record_sha256'],'revision':d['revision'],'duplicate_suppressed':physical_reused,'committed_by':WRITER}