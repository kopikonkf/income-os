import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('cr',R/'company/factory-asset/lib/cognition_router.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();PLAN=json.loads((R/'company/factory-asset/fixtures/asset-expression-plan/one.json').read_text());CASES=json.loads((R/'company/factory-asset/fixtures/cognition-router/cases.v1.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_cognition_routes(case):
 r=m.route_cognition(plan=PLAN,semantic_asset_id=case['semantic_asset_id'],blueprint_state=case['blueprint_state'],signals=case['signals']);assert r['outcome']==case['expected'];assert r['per_image_cognition_gate'] is False;assert r['worker_authority_granted'] is False;assert r['provider_authority_granted'] is False;assert r['submission_authority']=='FOUNDER_CONTROLLED'
def test_reuse_path_has_zero_division_and_zero_executive_calls():
 c=CASES[0];r=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert r['reuse_allowed'] is True;assert r['division01']['action']=='NONE';assert r['executive']['action']=='NONE';assert [x['actor'] for x in r['sequence']]==['HERMES']
def test_new_family_sequence_author_then_challenge_then_hermes_freeze():
 c=CASES[1];r=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert [x['actor'] for x in r['sequence']]==['DIVISION01','EXECUTIVE','HERMES'];assert r['division01']['action']=='AUTHOR';assert r['executive']['action']=='CHALLENGE'
def test_stale_or_incompatible_blueprint_never_reused():
 c=json.loads(json.dumps(CASES[0]));c['blueprint_state']['rights_assumptions_current']=False;r=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert r['reuse_allowed'] is False;assert r['division01']['action']=='REVISE';assert 'BLUEPRINT_INCOMPATIBLE_RIGHTS_ASSUMPTIONS_CURRENT' in r['division01']['reasons']
def test_bounded_semantic_question_routes_only_to_division01():
 c=json.loads(json.dumps(CASES[0]));c['signals']['bounded_semantic_question']=True;r=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert r['outcome']=='DIVISION01_REVISE';assert r['executive']['action']=='NONE'
def test_strategic_cannibalization_routes_executive_without_forcing_division_revision():
 c=json.loads(json.dumps(CASES[0]));c['signals']['portfolio_cannibalization_material']=True;r=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert r['outcome']=='EXECUTIVE_CHALLENGE_EXISTING_BLUEPRINT';assert r['division01']['action']=='NONE';assert r['executive']['action']=='CHALLENGE'
def test_existing_blueprint_requires_hash_pin():
 c=json.loads(json.dumps(CASES[0]));del c['blueprint_state']['blueprint_sha256']
 with pytest.raises(m.CognitionRoutingError) as e:m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals'])
 assert e.value.code=='BLUEPRINT_SHA256_REQUIRED'
def test_missing_blueprint_forbids_fake_hash():
 c=json.loads(json.dumps(CASES[1]));c['blueprint_state']['blueprint_sha256']='a'*64
 with pytest.raises(m.CognitionRoutingError) as e:m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals'])
 assert e.value.code=='BLUEPRINT_SHA256_FORBIDDEN'
def test_routing_is_deterministic():
 c=CASES[0];a=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);b=m.route_cognition(plan=PLAN,semantic_asset_id=c['semantic_asset_id'],blueprint_state=c['blueprint_state'],signals=c['signals']);assert a==b