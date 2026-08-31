#!/usr/bin/env python3
from __future__ import annotations

import argparse, importlib.util, json
from pathlib import Path
from typing import Any
import jsonschema

ROOT=Path(__file__).resolve().parent
REGISTRY=ROOT/'INTELLIGENCE_PREREQUISITE_REGISTRY_V1.json'
AUTHORITY_MAP=ROOT/'ACTION_AUTHORITY_MAP_V1.json'
PROJECTION_SCHEMA=ROOT/'die.operator-v2.intelligence-projection.v1.schema.json'
RECEIPT_VALIDATOR=ROOT/'validate_receipt_snapshot.py'
INSTANCE_MODULE=ROOT/'company_instance.py'

class ProjectionError(RuntimeError): pass

def _load_receipt_validator():
    spec=importlib.util.spec_from_file_location('oe006c_receipt_validator',RECEIPT_VALIDATOR)
    if spec is None or spec.loader is None: raise ProjectionError('E_RECEIPT_VALIDATOR_LOAD')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

RECEIPTS=_load_receipt_validator()

def _load_instance_module():
    spec=importlib.util.spec_from_file_location('operator_v2_projection_instance',INSTANCE_MODULE)
    if spec is None or spec.loader is None: raise ProjectionError('E_INSTANCE_MODULE_LOAD')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

INSTANCE=_load_instance_module()

def _action_authority(action_type:str)->str:
    amap=json.loads(AUTHORITY_MAP.read_text(encoding='utf-8'))
    for row in amap['actions']:
        if row['action_type']==action_type: return row['authority']
    raise ProjectionError('E_ACTION_NOT_MAPPED:'+action_type)

def project(snapshot:dict[str,Any])->dict[str,Any]:
    registry=json.loads(REGISTRY.read_text(encoding='utf-8'))
    instance_id=INSTANCE.resolve_instance_id(snapshot)
    validation=RECEIPTS.validate(snapshot)
    active=list(validation.get('active_receipts',{}).keys())
    active_set=set(active)
    missing=validation.get('missing_receipt_types',[])
    if validation['status']!='PASS':
        out={'schema_version':'die.operator-v2.intelligence-projection.v1','company_instance_id':snapshot.get('company_instance_id'),'mission_id':snapshot.get('mission_id','M-001'),'subject_id':snapshot.get('subject_id','UNKNOWN'),'as_of':snapshot.get('as_of','1970-01-01T00:00:00Z'),'registry_status':'FAIL','intelligence_stage':'BLOCKED_INVALID_RECEIPTS','next_required_receipt':None,'next_action_type':'OP-BLOCK-CARD','required_principal':'hermes-operator','action_authority':_action_authority('OP-BLOCK-CARD'),'active_receipt_types':sorted(active),'missing_receipt_types':missing,'chain_gap_detected':False,'out_of_order_receipt_types':[],'production_authorized':False,'can_invoke_production_runner':False,'kanban_cognition_proof_used':False,'errors':validation['errors'],'warnings':validation['warnings']}
    else:
        ordered=registry['stages']
        directives=validation.get('review_directives',{})
        directive=None
        for rtype in ('WORTH_MAKING_EXEC_REVIEW','BLUEPRINT_EXEC_REVIEW'):
            if rtype in directives:
                directive={'receipt_type':rtype, **directives[rtype]}
                break
        first_missing=next((s for s in ordered if s['receipt_type'] not in active_set),None)
        if directive is not None:
            rtype=directive['receipt_type']; outcome=directive['outcome']
            if rtype=='WORTH_MAKING_EXEC_REVIEW' and outcome=='REVISE':
                stage='WORTH_MAKING_REVISION'; next_required='WORTH_MAKING_AUTHOR'; next_action='OP-RETURN-DIVISION01-WORTH-MAKING'; required_principal=INSTANCE.principal_for(instance_id,'division01')
            elif rtype=='WORTH_MAKING_EXEC_REVIEW' and outcome=='VETO_PENDING_EVIDENCE':
                stage='WORTH_MAKING_EVIDENCE_GAP'; next_required='OPPORTUNITY_SIGNALS'; next_action='OP-REQUEST-WORTH-MAKING-EVIDENCE'; required_principal='approved-signal-collector'
            elif rtype=='BLUEPRINT_EXEC_REVIEW' and outcome=='REVISE':
                stage='BLUEPRINT_REVISION'; next_required='BLUEPRINT_AUTHOR'; next_action='OP-RETURN-DIVISION01-BLUEPRINT'; required_principal=INSTANCE.principal_for(instance_id,'division01')
            elif rtype=='BLUEPRINT_EXEC_REVIEW' and outcome=='VETO_PENDING_EVIDENCE':
                stage='BLUEPRINT_EVIDENCE_GAP'; next_required='BLUEPRINT_AUTHOR'; next_action='OP-RETURN-DIVISION01-BLUEPRINT-EVIDENCE'; required_principal=INSTANCE.principal_for(instance_id,'division01')
            else:
                stage='EXEC_REVIEW_ESCALATION'; next_required=None; next_action='OP-NOTIFY-FOUNDER'; required_principal='founder'
            production_authorized=False; can_run=False; out_of_order=[]; gap=False
        elif first_missing is None:
            stage='READY_FOR_PRODUCTION'; next_required=None; next_action='OP-INVOKE-M001-RUNNER'; required_principal='hermes-operator'; production_authorized=True; can_run=True; out_of_order=[]; gap=False
        else:
            stage=first_missing['stage_id']; next_required=first_missing['receipt_type']; next_action=first_missing['next_action_if_missing']; required_principal=INSTANCE.principal_for(instance_id,first_missing['semantic_role']) if first_missing.get('semantic_role') else first_missing['required_principal']; production_authorized=False; can_run=False
            missing_order=first_missing['order']; out_of_order=[s['receipt_type'] for s in ordered if s['order']>missing_order and s['receipt_type'] in active_set]
            gap=bool(out_of_order)
        out={'schema_version':'die.operator-v2.intelligence-projection.v1','company_instance_id':instance_id,'mission_id':snapshot['mission_id'],'subject_id':snapshot['subject_id'],'as_of':snapshot['as_of'],'registry_status':'PASS','intelligence_stage':stage,'next_required_receipt':next_required,'next_action_type':next_action,'required_principal':required_principal,'action_authority':_action_authority(next_action),'active_receipt_types':sorted(active),'missing_receipt_types':missing,'chain_gap_detected':gap,'out_of_order_receipt_types':out_of_order,'production_authorized':production_authorized,'can_invoke_production_runner':can_run,'kanban_cognition_proof_used':False,'errors':validation['errors'],'warnings':validation['warnings']}
        if directive is not None: out['review_directive']=directive
    schema=json.loads(PROJECTION_SCHEMA.read_text(encoding='utf-8'))
    errs=sorted(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(out),key=lambda e:list(e.absolute_path))
    if errs: raise ProjectionError('E_PROJECTION_SCHEMA:'+errs[0].message)
    return out

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('snapshot'); a=ap.parse_args(); d=json.loads(Path(a.snapshot).read_text(encoding='utf-8')); out=project(d); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0 if out['registry_status']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())