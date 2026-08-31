#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
MAP=ROOT/'ACTION_AUTHORITY_MAP_V1.json'
SCHEMA=ROOT/'die.operator-v2.action-request.v1.schema.json'

class AuthorityError(RuntimeError): pass

def validate(request:dict[str,Any], *, projection:dict[str,Any]) -> dict[str,Any]:
    schema=json.loads(SCHEMA.read_text(encoding='utf-8')); amap=json.loads(MAP.read_text(encoding='utf-8')); errors=[]
    for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(request),key=lambda e:list(e.absolute_path)):
        errors.append('E_SCHEMA:'+e.message)
    if errors: return {'schema':'die.operator-v2.action-authority-validation.v1','status':'DENY','errors':errors,'authority':'UNKNOWN','effect':'NONE'}
    actions={x['action_type']:x for x in amap['actions']}
    action=actions.get(request['action_type'])
    if action is None: return {'schema':'die.operator-v2.action-authority-validation.v1','status':'DENY','errors':['E_ACTION_UNKNOWN'],'authority':'UNKNOWN','effect':'NONE'}
    authority=action['authority']
    if authority=='FORBIDDEN': errors.append('E_ACTION_FORBIDDEN')
    if request['actor_id'] not in action['allowed_actor_ids']: errors.append('E_ACTOR_NOT_ALLOWED')
    allowed=action['allowed_projection_stages']
    if '*' not in allowed and request['projection_stage'] not in allowed: errors.append('E_STAGE_NOT_ALLOWED')
    if request['projection_stage']!=projection.get('intelligence_stage'): errors.append('E_PROJECTION_STAGE_MISMATCH')
    active=set(projection.get('active_receipt_types',[])); supplied=set(request['evidence_receipt_types'])
    for rtype in action['requires_receipt_types']:
        if rtype not in active: errors.append('E_REQUIRED_RECEIPT_MISSING:'+rtype)
        if rtype not in supplied: errors.append('E_REQUIRED_RECEIPT_NOT_PINNED:'+rtype)
    if request['action_type']=='OP-INVOKE-M001-RUNNER':
        if projection.get('intelligence_stage')!='READY_FOR_PRODUCTION': errors.append('E_RUNNER_NOT_READY')
        if projection.get('production_authorized') is not True: errors.append('E_RUNNER_AUTHORIZATION_MISSING')
    if request['action_type']=='OP-DRAFT-U1-REQUEST' and projection.get('next_required_receipt')!='FOUNDER_PRODUCTION_AUTHORIZATION': errors.append('E_U1_NOT_DUE')
    if request['action_type'].startswith(('OP-REQUEST-DIVISION01','OP-REQUEST-EXECUTIVE','OP-RETURN-DIVISION01')) and request.get('target_principal_id')!=projection.get('required_principal'): errors.append('E_TARGET_PRINCIPAL')
    if request['action_type']=='OP-REQUEST-WORTH-MAKING-EVIDENCE' and request.get('target_principal_id')!='approved-signal-collector': errors.append('E_TARGET_PRINCIPAL')
    if authority=='FOUNDER_REQUIRED' and request['actor_id']!='founder': errors.append('E_FOUNDER_REQUIRED')
    return {'schema':'die.operator-v2.action-authority-validation.v1','status':'ALLOW' if not errors else 'DENY','errors':sorted(set(errors)),'authority':authority,'effect':action['effect'],'runtime_model_may_override_authority':False}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('request'); ap.add_argument('--projection',required=True); a=ap.parse_args(); req=json.loads(Path(a.request).read_text()); proj=json.loads(Path(a.projection).read_text()); out=validate(req,projection=proj); print(json.dumps(out,indent=2)); return 0 if out['status']=='ALLOW' else 2
if __name__=='__main__': raise SystemExit(main())