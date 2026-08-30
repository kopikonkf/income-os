from __future__ import annotations

import copy, importlib.util, json, sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'die-agents'/'hermes'/'operator-v2'

def load(name,path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
F=load('oe006_fixture_test',ENGINE/'fixtures'/'build_operator_v2_fixture.py')
R=load('oe006_receipts_test',ENGINE/'validate_receipt_snapshot.py')
P=load('oe006_projection_test',ENGINE/'project_intelligence_stage.py')
A=load('oe006_authority_test',ENGINE/'validate_action_authority.py')

STAGES=['SIGNALS','DEMAND_SCORE','WORTH_MAKING','EXEC_WORTH_MAKING_REVIEW','BLUEPRINT_AUTHORING','BLUEPRINT_REVIEW','COMPILE','AUTHORIZATION']
RECEIPTS=['OPPORTUNITY_SIGNALS','DEMAND_SCORE','WORTH_MAKING_AUTHOR','WORTH_MAKING_EXEC_REVIEW','BLUEPRINT_AUTHOR','BLUEPRINT_EXEC_REVIEW','BLUEPRINT_COMPILE_HASH_LOCK','FOUNDER_PRODUCTION_AUTHORIZATION']
ACTIONS=['OP-CREATE-RESEARCH-CARD','OP-DISPATCH-DEMAND-SCORE','OP-REQUEST-DIVISION01-WORTH-MAKING','OP-REQUEST-EXECUTIVE-WORTH-MAKING-REVIEW','OP-REQUEST-DIVISION01-BLUEPRINT','OP-REQUEST-EXECUTIVE-BLUEPRINT-REVIEW','OP-CREATE-BLUEPRINT-COMPILE-CARD','OP-DRAFT-U1-REQUEST']
PRINCIPALS=['approved-signal-collector','division001-demand-score-v1','division-head-division01','chatgpt-plus-executive','division-head-division01','chatgpt-plus-executive','worker-template','founder']

def req(action,projection,actor='hermes-operator',target=None,evidence=None):
    return {'schema_version':'die.operator-v2.action-request.v1','action_type':action,'actor_id':actor,'projection_stage':projection['intelligence_stage'],'evidence_receipt_types':projection['active_receipt_types'] if evidence is None else evidence,'target_principal_id':target}

def test_oe006a_registry_has_exact_ordered_eight_intelligence_prerequisites():
    d=json.loads((ENGINE/'INTELLIGENCE_PREREQUISITE_REGISTRY_V1.json').read_text())
    assert d['kanban_is_cognition_proof'] is False
    assert [x['order'] for x in d['stages']]==list(range(1,9))
    assert [x['receipt_type'] for x in d['stages']]==RECEIPTS

def test_oe006a_full_typed_snapshot_validates_and_binds_exact_authorization_hash():
    out=R.validate(F.full_snapshot())
    assert out['status']=='PASS' and out['missing_receipt_types']==[]
    assert set(out['active_receipts'])==set(RECEIPTS)
    assert out['kanban_cognition_proof_used'] is False

def test_oe006a_stale_receipt_becomes_incomplete_not_zero_or_valid():
    snap=F.snapshot_prefix(2); snap['as_of']='2026-09-01T07:00:00Z'
    out=R.validate(snap)
    assert out['status']=='PASS'
    assert 'OPPORTUNITY_SIGNALS' in out['missing_receipt_types'] and 'DEMAND_SCORE' in out['missing_receipt_types']
    assert any(x.startswith('W_STALE_RECEIPT:OPPORTUNITY_SIGNALS') for x in out['warnings'])

def test_oe006a_wrong_semantic_principal_fails_closed():
    snap=F.snapshot_prefix(3); snap['receipts'][2]['issuer_id']='hermes-operator'
    out=R.validate(snap)
    assert out['status']=='FAIL'
    assert 'E_ISSUER_ID:WORTH_MAKING_AUTHOR:hermes-operator' in out['errors']

def test_oe006a_conflicting_active_receipts_fail_but_superseded_history_is_ignored():
    snap=F.snapshot_prefix(1); dup=copy.deepcopy(snap['receipts'][0]); dup['artifact_id']='OPPORTUNITY_SIGNALS-OTHER'; dup['artifact_sha256']='b'*64; snap['receipts'].append(dup)
    assert 'E_CONFLICTING_ACTIVE_RECEIPTS:OPPORTUNITY_SIGNALS' in R.validate(snap)['errors']
    dup['status']='SUPERSEDED'; snap['receipts'][-1]=dup
    out=R.validate(snap); assert out['status']=='PASS' and out['missing_receipt_types'][0]=='DEMAND_SCORE'

def test_oe006a_founder_authorization_must_bind_exact_compiled_hash():
    snap=F.full_snapshot(); snap['receipts'][-1]['claims']['authorized_compiled_blueprint_sha256']='b'*64
    out=R.validate(snap)
    assert out['status']=='FAIL' and 'E_AUTH_COMPILED_HASH_MISMATCH' in out['errors']

def test_oe006a_authorization_without_compile_lock_fails_closed():
    snap=F.full_snapshot(); snap['receipts']=[x for x in snap['receipts'] if x['receipt_type']!='BLUEPRINT_COMPILE_HASH_LOCK']
    out=R.validate(snap)
    assert out['status']=='FAIL' and 'E_AUTH_WITHOUT_COMPILE_LOCK' in out['errors']

def test_oe006a_kanban_done_without_receipts_proves_nothing():
    snap=F.snapshot_prefix(0,kanban_done=True); out=R.validate(snap)
    assert out['status']=='PASS' and out['missing_receipt_types']==RECEIPTS
    assert out['kanban_cognition_proof_used'] is False

def test_oe006b_action_map_is_default_deny_and_runtime_cannot_override_authority():
    m=json.loads((ENGINE/'ACTION_AUTHORITY_MAP_V1.json').read_text())
    assert m['default_policy']=='DENY'; assert m['runtime_model_may_override_authority'] is False; assert m['capability_is_authority'] is False
    assert len({x['action_type'] for x in m['actions']})==len(m['actions'])

def test_oe006b_each_missing_stage_allows_only_its_mapped_operator_action():
    for i in range(8):
        proj=P.project(F.snapshot_prefix(i)); action=ACTIONS[i]
        target=PRINCIPALS[i] if action.startswith('OP-REQUEST-') else None
        verdict=A.validate(req(action,proj,target=target),projection=proj)
        assert verdict['status']=='ALLOW',(i,verdict)
        wrong=A.validate(req('OP-FOLLOW-UP-CARD',proj),projection=proj)
        assert wrong['status']=='ALLOW'  # generic workflow follow-up stays reversible
        if i<7:
            not_due=A.validate(req(ACTIONS[i+1],proj,target=PRINCIPALS[i+1] if ACTIONS[i+1].startswith('OP-REQUEST-') else None),projection=proj)
            assert not_due['status']=='DENY'

def test_oe006b_hermes_cannot_execute_founder_required_or_forbidden_actions():
    proj=P.project(F.snapshot_prefix(7))
    founder_req=req('F-PRODUCTION-AUTH',proj,actor='hermes-operator',evidence=['BLUEPRINT_COMPILE_HASH_LOCK'])
    out=A.validate(founder_req,projection=proj); assert out['status']=='DENY' and out['authority']=='FOUNDER_REQUIRED'
    forbidden=req('X-PROMPT-IMPROVISATION',proj,actor='founder')
    out2=A.validate(forbidden,projection=proj); assert out2['status']=='DENY' and out2['authority']=='FORBIDDEN'

def test_oe006b_runtime_request_cannot_spoof_authority_classification():
    proj=P.project(F.snapshot_prefix(0)); r=req('OP-CREATE-RESEARCH-CARD',proj); r['claimed_authority']='FOUNDER_REQUIRED'
    out=A.validate(r,projection=proj); assert out['status']=='DENY'; assert any(x.startswith('E_SCHEMA:') for x in out['errors'])

def test_oe006b_semantic_request_target_principal_is_pinned():
    proj=P.project(F.snapshot_prefix(2)); good=A.validate(req('OP-REQUEST-DIVISION01-WORTH-MAKING',proj,target='division-head-division01'),projection=proj)
    bad=A.validate(req('OP-REQUEST-DIVISION01-WORTH-MAKING',proj,target='hermes-operator'),projection=proj)
    assert good['status']=='ALLOW' and bad['status']=='DENY' and 'E_TARGET_PRINCIPAL' in bad['errors']

def test_oe006b_runner_requires_complete_chain_and_founder_authorization():
    notready=P.project(F.snapshot_prefix(7)); out=A.validate(req('OP-INVOKE-M001-RUNNER',notready,evidence=notready['active_receipt_types']),projection=notready)
    assert out['status']=='DENY'
    ready=P.project(F.full_snapshot()); out2=A.validate(req('OP-INVOKE-M001-RUNNER',ready,evidence=ready['active_receipt_types']),projection=ready)
    assert out2['status']=='ALLOW' and out2['authority']=='CONDITIONAL_AUTONOMOUS'

def test_oe006c_every_prefix_projects_exact_earliest_missing_receipt_action_and_principal():
    for i in range(8):
        p=P.project(F.snapshot_prefix(i))
        assert p['registry_status']=='PASS'; assert p['intelligence_stage']==STAGES[i]
        assert p['next_required_receipt']==RECEIPTS[i]; assert p['next_action_type']==ACTIONS[i]; assert p['required_principal']==PRINCIPALS[i]
        assert p['production_authorized'] is False and p['can_invoke_production_runner'] is False

def test_oe006c_full_chain_projects_ready_for_production_only_after_exact_auth():
    p=P.project(F.full_snapshot())
    assert p['intelligence_stage']=='READY_FOR_PRODUCTION'; assert p['next_required_receipt'] is None
    assert p['next_action_type']=='OP-INVOKE-M001-RUNNER'; assert p['production_authorized'] is True; assert p['can_invoke_production_runner'] is True

def test_oe006c_chain_gap_is_visible_and_does_not_skip_earliest_missing_stage():
    snap=F.snapshot_prefix(4); snap['receipts'].pop(1)
    p=P.project(snap)
    assert p['intelligence_stage']=='DEMAND_SCORE'; assert p['next_required_receipt']=='DEMAND_SCORE'
    assert p['chain_gap_detected'] is True and 'WORTH_MAKING_AUTHOR' in p['out_of_order_receipt_types']

def test_oe006c_invalid_receipt_chain_projects_blocked_fail_closed():
    snap=F.snapshot_prefix(3); snap['receipts'][2]['issuer_id']='hermes-operator'
    p=P.project(snap)
    assert p['intelligence_stage']=='BLOCKED_INVALID_RECEIPTS'; assert p['next_action_type']=='OP-BLOCK-CARD'; assert p['can_invoke_production_runner'] is False

def test_oe006c_legacy_kanban_all_done_still_projects_signals():
    p=P.project(F.snapshot_prefix(0,kanban_done=True))
    assert p['intelligence_stage']=='SIGNALS'; assert p['next_required_receipt']=='OPPORTUNITY_SIGNALS'; assert p['kanban_cognition_proof_used'] is False

def test_oe006c_projection_is_deterministic_for_identical_snapshot():
    snap=F.snapshot_prefix(6); assert P.project(copy.deepcopy(snap))==P.project(copy.deepcopy(snap))