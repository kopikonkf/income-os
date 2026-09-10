from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'company/factory-asset'
CONTRACT_PATH=BASE/'contracts/founder-display-observability.v1.json'
CLUSTER_PATH=BASE/'registries/web-ai-clusters.v1.json'

class FounderObservabilityError(ValueError):
    def __init__(self,code:str,message:str): super().__init__(f'{code}: {message}'); self.code=code

def load_json(path:Path)->dict[str,Any]: return json.loads(path.read_text(encoding='utf-8'))

def validate_contract(contract:dict[str,Any]|None=None,clusters:dict[str,Any]|None=None)->dict[str,Any]:
    contract=contract or load_json(CONTRACT_PATH); clusters=clusters or load_json(CLUSTER_PATH)
    if contract.get('schema')!='die.factory-asset.founder-display-observability.v1': raise FounderObservabilityError('SCHEMA_INVALID','contract')
    sec=contract['security']
    if sec['public_listener_allowed'] or sec['credential_extraction_allowed'] or sec['cookie_token_export_allowed']: raise FounderObservabilityError('SECURITY_BOUNDARY_INVALID','public/secret access')
    if sec['default_access']!='READ_ONLY' or sec['interactive_repair']!='FORBIDDEN_UNTIL_FA-325': raise FounderObservabilityError('INTERACTION_POLICY_INVALID','contract')
    by={c['cluster_id']:c for c in clusters['clusters']}
    seen=set()
    for row in contract['clusters']:
        cid=row['cluster_id']; seen.add(cid)
        if cid not in by: raise FounderObservabilityError('CLUSTER_UNKNOWN',cid)
        src=by[cid]
        if row['production_display']!=src['browser_virtual_display'] or row['display_socket']!=f":{src['browser_virtual_display']}": raise FounderObservabilityError('DISPLAY_DRIFT',cid)
        if row['browser_owner_service']!=src['browser_lifecycle_service'] or row['broker_service']!=src['broker_service']: raise FounderObservabilityError('SERVICE_DRIFT',cid)
        if row['cdp']!={'host':'127.0.0.1','port':src['browser_debug_port'],'founder_direct_exposure':False}: raise FounderObservabilityError('CDP_BOUNDARY_DRIFT',cid)
        if row['broker']!={'host':'127.0.0.1','port':src['broker_control_port'],'founder_direct_exposure':False}: raise FounderObservabilityError('BROKER_BOUNDARY_DRIFT',cid)
        v=row['vnc_plan']
        if v['state']!='NOT_DEPLOYED' or v['bind_host']!='127.0.0.1' or v['mode']!='READ_ONLY' or v['transport']!='SSH_LOCAL_FORWARD': raise FounderObservabilityError('VNC_PLAN_UNSAFE',cid)
    if seen!=set(by): raise FounderObservabilityError('CLUSTER_COVERAGE_DRIFT',str(sorted(set(by)-seen)))
    return contract

def sanitize_status(raw:dict[str,Any], *, cluster_id:str)->dict[str,Any]:
    contract=validate_contract()
    allowed=set(contract['status_fields_allowed'])
    forbidden=set(contract['status_fields_forbidden'])
    if any(k in raw for k in forbidden): raise FounderObservabilityError('FORBIDDEN_STATUS_FIELD','secret-bearing input')
    out={k:raw[k] for k in allowed if k in raw}
    out['cluster_id']=cluster_id
    return dict(sorted(out.items()))
