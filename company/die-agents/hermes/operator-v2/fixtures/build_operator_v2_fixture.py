from __future__ import annotations

import copy, hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'INTELLIGENCE_PREREQUISITE_REGISTRY_V1.json'
AS_OF='2026-08-30T07:00:00Z'
EXPIRES='2026-08-31T07:00:00Z'
COMPILED_HASH='a'*64

def sh(text:str)->str: return hashlib.sha256(text.encode()).hexdigest()

def registry()->dict[str,Any]: return json.loads(REGISTRY.read_text(encoding='utf-8'))

def receipt(stage:dict[str,Any], *, suffix:str='CURRENT')->dict[str,Any]:
    rtype=stage['receipt_type']; issuer=stage['allowed_issuer_ids'][0]
    claims=copy.deepcopy(stage.get('required_claims',{}))
    if rtype=='BLUEPRINT_COMPILE_HASH_LOCK': claims['exact_compiled_blueprint_sha256']=COMPILED_HASH
    if rtype=='FOUNDER_PRODUCTION_AUTHORIZATION':
        claims['authorized_compiled_blueprint_sha256']=COMPILED_HASH; claims['decision_id']='D-SYNTHETIC-PROD-AUTH-0001'
    return {'receipt_type':rtype,'artifact_id':rtype+'-'+suffix,'artifact_sha256':sh('artifact:'+rtype+':'+suffix),'issuer_id':issuer,'issuer_kind':stage['issuer_kind'],'artifact_schema':stage['artifact_schema'],'status':'VALID','recorded_at':'2026-08-30T06:00:00Z','expires_at':EXPIRES if stage.get('freshness_required') else None,'source_ref':'fixture://operator-v2/'+rtype.lower(),'validation':{'validator_id':'synthetic-validator-'+rtype.lower(),'status':'PASS','receipt_ref':'fixture://validation/'+rtype.lower(),'receipt_sha256':sh('validation:'+rtype+':'+suffix)},'claims':claims}

def snapshot_prefix(count:int, *, kanban_done:bool=True)->dict[str,Any]:
    stages=registry()['stages']
    return {'schema_version':'die.operator-v2.receipt-snapshot.v1','company_instance_id':'DIE-WINDOWS','mission_id':'M-001','subject_id':'M001-SYNTHETIC-BATCH-0001','as_of':AS_OF,'receipts':[receipt(s) for s in stages[:count]],'kanban_metadata':{'legacy_cards':[{'id':'T1','status':'done'},{'id':'T2','status':'done'}] if kanban_done else []}}

def full_snapshot()->dict[str,Any]: return snapshot_prefix(len(registry()['stages']))