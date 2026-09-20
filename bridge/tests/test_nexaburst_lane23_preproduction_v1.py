from pathlib import Path
import importlib.util
import json
import pytest

R=Path(__file__).resolve().parents[2]
N=R/'company/die-agents/hermes/production-runtime/nexaburst'
C=N/'bin/nexaburst-preproduction-compile.py'

def mod():
    spec=importlib.util.spec_from_file_location('nb_preprod',C)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_lane2_identity_is_expression_aware_and_not_authorized():
    m=mod()
    req=json.loads((N/'config/fixtures/lane2-psr-canary-request.json').read_text())
    out=m.compile_object_psr(req)
    assert out['semantic_asset_id'].endswith('PSR-L0')
    assert out['dispatch_authorized'] is False
    assert out['contract']['activation']=='PREPARED_NOT_AUTHORIZED'
    assert 'watercolor texture' in out['contract']['visual_requirement']['forbidden']

def test_lane2_lane_change_changes_semantic_identity():
    m=mod()
    req=json.loads((N/'config/fixtures/lane2-psr-canary-request.json').read_text())
    a=m.compile_object_psr(req)
    req['lane_id']='PSR-L1'
    b=m.compile_object_psr(req)
    assert a['semantic_asset_id']!=b['semantic_asset_id']
    assert a['contract_sha256']!=b['contract_sha256']

def test_human_scene_requires_complete_10d_contract():
    m=mod()
    req=json.loads((N/'config/fixtures/lane3-human-scene-canary-request.json').read_text())
    out=m.compile_human_scene(req)
    assert out['dispatch_authorized'] is False
    assert out['contract']['h03_dependency'] is False
    assert out['contract']['web_ai_cognition_dependency'] is False
    assert set(m.DIMENSIONS)==set(out['contract']['dimensions'])

def test_human_scene_rejects_missing_dimension():
    m=mod()
    req=json.loads((N/'config/fixtures/lane3-human-scene-canary-request.json').read_text())
    del req['dimensions']['problem']
    with pytest.raises(m.ContractError) as e:m.compile_human_scene(req)
    assert 'E_SCENE_DIMENSIONS_MISSING:problem' in str(e.value)

def test_family_lane_eligibility_is_enforced():
    m=mod()
    req=json.loads((N/'config/fixtures/lane3-human-scene-canary-request.json').read_text())
    req['family_id']='HF-FIN-LIFE'
    req['lane_id']='HC-L5'
    with pytest.raises(m.ContractError) as e:m.compile_human_scene(req)
    assert 'E_FAMILY_LANE_INELIGIBLE' in str(e.value)

def test_human_scene_identity_changes_when_lane_changes():
    m=mod()
    req=json.loads((N/'config/fixtures/lane3-human-scene-canary-request.json').read_text())
    a=m.compile_human_scene(req)
    req['lane_id']='HC-L0'
    b=m.compile_human_scene(req)
    assert a['semantic_asset_id']!=b['semantic_asset_id']

def test_activation_hold_forbids_live_runtime():
    hold=json.loads((N/'config/lane23-activation-hold.v1.json').read_text())
    assert hold['status']=='HOLD'
    assert hold['lane2']['live'] is False
    assert hold['lane3']['live'] is False
    assert 'no cron' in hold['invariants']
    assert 'no H03 dependency' in hold['invariants']

def test_human_registry_is_multi_family_multi_lane():
    fam=json.loads((N/'config/human-commercial-families.v1.json').read_text())
    lanes=json.loads((N/'config/human-scene-lanes.v1.json').read_text())
    assert len(fam['families'])>=8
    assert len(lanes['lanes'])>=10
    assert all(len(x['eligible_lanes'])>=3 for x in fam['families'])
