from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'division'/'division001'/'engines'/'worth-making'

def load(name,path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
B=load('oe004f_builder_test',ENGINE/'fixtures'/'build_governed_fixture.py')
V=load('oe004f_bundle_test',ENGINE/'validate_governed_bundle.py')
R=load('oe004f_runner_test',ENGINE/'run_governed_canary.py')
A=load('oe004f_attempt_test',ENGINE/'validate_attempt_lineage.py')


def test_oe004f_governed_case_matrix_passes_exact_expected_routes():
    out=R.run()
    assert out['status']=='PASS'
    assert {x['case_id']:(x['status'],x['decision']) for x in out['cases']} == {
      'PASS':('PASS','PROMOTABLE_TO_BLUEPRINT'),'REVISE':('PASS','RETURN_TO_DIVISION'),'VETO':('PASS','WAITING_EVIDENCE'),
      'STALE':('FAIL','INVALID'),'MISSING_PRINCIPAL':('FAIL','INVALID'),'FORGED_REVIEW':('FAIL','INVALID'),'KANBAN_ONLY':('FAIL','INVALID')}
    assert out['production_authority_granted'] is False
    assert out['live_cognition_performed'] is False


def test_oe004d_revision_attempt_n_plus_1_requires_new_division_artifact_and_same_chain():
    first=B.build(outcome='REVISE',attempt_number=1,artifact_suffix='A')
    assert V.validate_bundle(first)['decision']=='RETURN_TO_DIVISION'
    second=B.build(outcome='NO_VETO',attempt_number=2,previous_attempt=first['attempt'],artifact_suffix='B')
    result=V.validate_bundle(second)
    assert result['status']=='PASS'
    assert result['decision']=='PROMOTABLE_TO_BLUEPRINT'
    assert second['attempt']['chain_id']==first['attempt']['chain_id']
    assert second['attempt']['attempt_number']==2
    assert second['attempt']['division_artifact']['sha256'] != first['attempt']['division_artifact']['sha256']


def test_oe004d_same_division_hash_or_id_cannot_be_laundered_as_revision():
    first=B.build(outcome='REVISE',attempt_number=1,artifact_suffix='A')
    second=B.build(outcome='NO_VETO',attempt_number=2,previous_attempt=first['attempt'],artifact_suffix='A')
    errors=A.validate(second['attempt'],precheck=second['precheck'],division=second['division_artifact'],review=second['executive_review'],previous=first['attempt'])
    assert 'E_REVISION:division_hash_must_change' in errors
    assert 'E_REVISION:division_artifact_id_must_change' in errors
    assert V.validate_bundle(second)['decision']=='INVALID'


def test_oe004d_closed_no_veto_attempt_cannot_spawn_revision_attempt():
    first=B.build(outcome='NO_VETO',attempt_number=1,artifact_suffix='A')
    second=B.build(outcome='NO_VETO',attempt_number=2,previous_attempt=first['attempt'],artifact_suffix='B')
    errors=A.validate(second['attempt'],precheck=second['precheck'],division=second['division_artifact'],review=second['executive_review'],previous=first['attempt'])
    assert 'E_PREVIOUS:not_returnable' in errors


def test_oe004d_previous_attempt_hash_tamper_fails_closed():
    first=B.build(outcome='REVISE',attempt_number=1,artifact_suffix='A')
    second=B.build(outcome='NO_VETO',attempt_number=2,previous_attempt=first['attempt'],artifact_suffix='B')
    second['attempt']['previous_attempt']['sha256']='0'*64
    assert 'E_PREVIOUS:binding' in A.validate(second['attempt'],precheck=second['precheck'],division=second['division_artifact'],review=second['executive_review'],previous=first['attempt'])


def test_oe004e_precheck_source_replay_mismatch_invalidates_bundle():
    bundle=B.build()
    bundle['precheck_input']['buyer_hypothesis_seed']['buyer_label']='mutated buyer hypothesis after precheck'
    result=V.validate_bundle(bundle)
    assert result['status']=='FAIL' and result['decision']=='INVALID'
    assert any(x.startswith('E_PRECHECK_REPLAY:mismatch') for x in result['errors'])


def test_oe004e_repository_snapshot_mismatch_invalidates_bundle():
    bundle=B.build(); bundle['repository_sha']='a'*40
    result=V.validate_bundle(bundle)
    assert result['status']=='FAIL'
    assert 'E_REPOSITORY:division_sha_mismatch' in result['errors']
    assert 'E_REPOSITORY:executive_sha_mismatch' in result['errors']


def test_oe004e_research_or_defer_never_promotes_even_with_no_veto():
    research=V.validate_bundle(B.build(recommendation='RESEARCH'))
    defer=V.validate_bundle(B.build(recommendation='DEFER'))
    assert (research['status'],research['decision'])==('PASS','NOT_PROMOTABLE')
    assert (defer['status'],defer['decision'])==('PASS','NOT_PROMOTABLE')


def test_oe004e_escalation_routes_to_founder_without_granting_authority():
    result=V.validate_bundle(B.build(outcome='ESCALATE_FOUNDER'))
    assert (result['status'],result['decision'])==('PASS','ESCALATE_FOUNDER')
    assert result['production_authority_granted'] is False


def test_oe004f_stale_case_proves_current_freshness_not_historical_only():
    cases=json.loads((ENGINE/'fixtures'/'governed-canary-cases-v1.json').read_text())
    stale=next(x for x in cases['cases'] if x['id']=='STALE')
    assert stale['expected_decision']=='INVALID'
    bundle=B.build(); bundle['validated_at']='2026-08-31T12:40:00Z'
    result=V.validate_bundle(bundle)
    assert any('demand_score_stale' in x for x in result['errors'])
    assert any('review_stale' in x for x in result['errors'])


def test_oe004f_legacy_kanban_done_is_never_cognition_proof():
    bundle={'bundle_id':'WMBUNDLE-KANBAN-ONLY-0001','validated_at':'2026-08-29T12:40:00Z','repository_sha':'f'*40,'workflow_metadata':{'kanban_status':'done'}}
    result=V.validate_bundle(bundle)
    assert result['status']=='FAIL' and result['decision']=='INVALID'
    assert any(x.startswith('E_BUNDLE_MISSING:') for x in result['errors'])