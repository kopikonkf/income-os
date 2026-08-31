from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'die-agents'/'hermes'/'operator-v2'
FIXTURE=ENGINE/'fixtures'/'build_operator_v2_fixture.py'

def load(name: str, path: Path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

F=load('review_loop_fixture',FIXTURE)
V=load('review_loop_validator',ENGINE/'validate_receipt_snapshot.py')
P=load('review_loop_projector',ENGINE/'project_intelligence_stage.py')
R=load('review_loop_router',ENGINE/'route_followup.py')

DIV='die-lnx-division-001'
EXEC='die-lnx-executive-001'

def linux_snapshot(count: int):
    snap=F.snapshot_prefix(count,kanban_done=False)
    snap['company_instance_id']='DIE-LINUX'
    snap['as_of']='2026-08-31T12:00:00Z'
    for row in snap['receipts']:
        row['expires_at']='2099-01-01T00:00:00Z' if row['expires_at'] is not None else None
        if row['receipt_type'] in {'WORTH_MAKING_AUTHOR','BLUEPRINT_AUTHOR'}: row['issuer_id']=DIV
        if row['receipt_type'] in {'WORTH_MAKING_EXEC_REVIEW','BLUEPRINT_EXEC_REVIEW'}: row['issuer_id']=EXEC
    return snap

def receipt(snap, rtype: str):
    return next(x for x in snap['receipts'] if x['receipt_type']==rtype)

def test_no_veto_still_promotes_worth_making_to_blueprint_authoring() -> None:
    snap=linux_snapshot(4)
    validation=V.validate(snap)
    assert validation['status']=='PASS'
    assert validation['review_directives']=={}
    projection=P.project(snap)
    assert projection['intelligence_stage']=='BLUEPRINT_AUTHORING'
    assert projection['next_action_type']=='OP-REQUEST-DIVISION01-BLUEPRINT'
    assert projection['required_principal']==DIV

def test_worth_making_revise_is_governed_return_to_linux_division01() -> None:
    snap=linux_snapshot(4)
    review=receipt(snap,'WORTH_MAKING_EXEC_REVIEW')
    review['claims']['outcome']='REVISE'
    validation=V.validate(snap)
    assert validation['status']=='PASS'
    assert validation['review_directives']['WORTH_MAKING_EXEC_REVIEW']['outcome']=='REVISE'
    projection=P.project(snap)
    assert projection['registry_status']=='PASS'
    assert projection['intelligence_stage']=='WORTH_MAKING_REVISION'
    assert projection['next_required_receipt']=='WORTH_MAKING_AUTHOR'
    assert projection['next_action_type']=='OP-RETURN-DIVISION01-WORTH-MAKING'
    assert projection['required_principal']==DIV
    assert projection['production_authorized'] is False
    plan=R.plan(projection,None,now=snap['as_of'])
    assert plan['status']=='READY'
    assert plan['decision']=='DISPATCH'
    assert plan['action_request']['target_principal_id']==DIV
    assert plan['action_request']['actor_id']=='hermes-operator'
    assert plan['authority_validation']['status']=='ALLOW'

def test_worth_making_veto_pending_evidence_blocks_promotion_and_routes_collector() -> None:
    snap=linux_snapshot(4)
    receipt(snap,'WORTH_MAKING_EXEC_REVIEW')['claims']['outcome']='VETO_PENDING_EVIDENCE'
    projection=P.project(snap)
    assert projection['intelligence_stage']=='WORTH_MAKING_EVIDENCE_GAP'
    assert projection['next_action_type']=='OP-REQUEST-WORTH-MAKING-EVIDENCE'
    assert projection['required_principal']=='approved-signal-collector'
    assert projection['can_invoke_production_runner'] is False
    plan=R.plan(projection,None,now=snap['as_of'])
    assert plan['status']=='READY'
    assert plan['action_request']['target_principal_id']=='approved-signal-collector'

def test_blueprint_revise_returns_to_linux_division01_and_never_compiles() -> None:
    snap=linux_snapshot(6)
    receipt(snap,'BLUEPRINT_EXEC_REVIEW')['claims']['outcome']='REVISE'
    projection=P.project(snap)
    assert projection['intelligence_stage']=='BLUEPRINT_REVISION'
    assert projection['next_required_receipt']=='BLUEPRINT_AUTHOR'
    assert projection['next_action_type']=='OP-RETURN-DIVISION01-BLUEPRINT'
    assert projection['required_principal']==DIV
    assert projection['next_action_type']!='OP-CREATE-BLUEPRINT-COMPILE-CARD'
    plan=R.plan(projection,None,now=snap['as_of'])
    assert plan['status']=='READY'
    assert plan['action_request']['target_principal_id']==DIV

def test_revision_supersedes_old_lineage_then_requests_executive_again() -> None:
    snap=linux_snapshot(4)
    old_author=receipt(snap,'WORTH_MAKING_AUTHOR')
    old_review=receipt(snap,'WORTH_MAKING_EXEC_REVIEW')
    old_review['claims']['outcome']='REVISE'
    old_author['status']='SUPERSEDED'
    old_review['status']='SUPERSEDED'
    stage=next(x for x in F.registry()['stages'] if x['receipt_type']=='WORTH_MAKING_AUTHOR')
    revised=F.receipt(stage,suffix='REVISION-2')
    revised['issuer_id']=DIV
    revised['recorded_at']='2026-08-31T11:30:00Z'
    revised['expires_at']='2099-01-01T00:00:00Z'
    snap['receipts'].append(revised)
    projection=P.project(snap)
    assert projection['intelligence_stage']=='EXEC_WORTH_MAKING_REVIEW'
    assert projection['next_action_type']=='OP-REQUEST-EXECUTIVE-WORTH-MAKING-REVIEW'
    assert projection['required_principal']==EXEC
    assert 'WORTH_MAKING_AUTHOR' in projection['active_receipt_types']
    assert 'WORTH_MAKING_EXEC_REVIEW' not in projection['active_receipt_types']

def test_review_escalation_routes_founder_not_peer_principals() -> None:
    snap=linux_snapshot(4)
    receipt(snap,'WORTH_MAKING_EXEC_REVIEW')['claims']['outcome']='ESCALATE_FOUNDER'
    projection=P.project(snap)
    assert projection['intelligence_stage']=='EXEC_REVIEW_ESCALATION'
    assert projection['next_action_type']=='OP-NOTIFY-FOUNDER'
    assert projection['required_principal']=='founder'
    plan=R.plan(projection,None,now=snap['as_of'])
    assert plan['status']=='READY'
    assert plan['action_request']['target_principal_id']=='founder'
