import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('spr',R/'company/factory-asset/lib/semantic_producer_router.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load()
PLAN=json.loads((R/'company/factory-asset/fixtures/asset-expression-plan/multiple.json').read_text())
def bp(name):return json.loads((R/f'company/factory-asset/fixtures/shopping-bag-blueprint-v2/{name}.json').read_text())
def route(name,semantic):
 b=bp(name);return m.route_frozen_expression(plan=PLAN,semantic_asset_id=semantic,blueprint=b,frozen_blueprint_sha256=m.canonical_sha256(b))
def test_photo_routes_to_provider_router_without_selecting_provider():
 r=route('photo','FASA-SHOPPING_BAG_PHOTO');assert r['result']=='DISPATCH_READY';assert r['semantic_mode']=='PHOTO';assert r['producer_class']=='RASTER_GENERATIVE';assert r['route_kind']=='PROVIDER_ROUTER';assert r['dispatch_adapter']=='FA104_PROVIDER_ROUTER';assert r['provider_selection_delegated'] is True;assert 'provider_id' not in r;assert r['post_hoc_conversion_allowed'] is False
def test_pattern_routes_to_accepted_native_pattern_engine():
 r=route('pattern','FASA-SHOPPING_BAG_PATTERN');assert r['route_kind']=='NATIVE_PRODUCER';assert r['dispatch_adapter']=='PROCEDURAL_PATTERN_V0_1';assert r['producer_class']=='PROCEDURAL_VECTOR';assert r['master_generation_mode']=='DIRECT_FROM_BLUEPRINT';assert r['post_hoc_conversion_allowed'] is False;assert 'receipt://FA-034' in r['evidence_refs']
def test_animation_routes_to_accepted_motion_engine():
 r=route('animation','FASA-SHOPPING_BAG_ANIMATION');assert r['route_kind']=='NATIVE_PRODUCER';assert r['dispatch_adapter']=='MOTION_ENGINE_V0_1';assert r['producer_class']=='MOTION_RENDERER';assert r['native_representation']=='TIMED_FRAMES';assert 'receipt://FA-043' in r['evidence_refs'];assert r['post_hoc_conversion_allowed'] is False
def test_frozen_blueprint_hash_mismatch_fails_before_dispatch():
 b=bp('photo')
 with pytest.raises(m.ProducerDispatchError) as e:m.route_frozen_expression(plan=PLAN,semantic_asset_id='FASA-SHOPPING_BAG_PHOTO',blueprint=b,frozen_blueprint_sha256='0'*64)
 assert e.value.code=='FROZEN_BLUEPRINT_HASH_MISMATCH'
def test_expression_and_blueprint_producer_mismatch_fails_closed():
 b=bp('pattern');b['producer_class']='NATIVE_VECTOR'
 with pytest.raises(m.ProducerDispatchError) as e:m.route_frozen_expression(plan=PLAN,semantic_asset_id='FASA-SHOPPING_BAG_PATTERN',blueprint=b,frozen_blueprint_sha256=m.canonical_sha256(b))
 assert e.value.code=='BLUEPRINT_PRODUCER_MISMATCH'
def test_expression_and_blueprint_mode_mismatch_fails_closed():
 b=bp('photo');b['asset_type']='ISOLATED_OBJECT'
 with pytest.raises(m.ProducerDispatchError) as e:m.route_frozen_expression(plan=PLAN,semantic_asset_id='FASA-SHOPPING_BAG_PHOTO',blueprint=b,frozen_blueprint_sha256=m.canonical_sha256(b))
 assert e.value.code=='BLUEPRINT_MODE_MISMATCH'
def test_unaccepted_native_vector_engine_is_recognized_but_not_dispatchable():
 plan=json.loads(json.dumps(PLAN));icon=bp('icon')
 # reuse evidence shape from photo but create an internally valid icon expression/evidence pair
 ev=plan['evidence'][0]; ev['evidence_id']='fixture-icon'; ev['support'].update({'buyer':'UI designer','commercial_use_case':'Use a shopping bag icon in retail navigation','product_expression':'Editable shopping bag navigation icon','semantic_mode':'ICON'}); ev['rationale']='A UI designer needs an editable shopping bag icon for retail navigation and interface composition.'
 plan['evidence']=[ev];plan['expressions']=[{'semantic_asset_id':'FASA-SHOPPING_BAG_ICON','buyer':'UI designer','commercial_use_case':'Use a shopping bag icon in retail navigation','product_expression':'Editable shopping bag navigation icon','semantic_mode':'ICON','producer_class':'NATIVE_VECTOR','candidate_marketplace_route':{'platform_id':'ADOBE_STOCK','listing_use':'Editable shopping bag navigation icon','state':'CANDIDATE_REQUIRES_POLICY_CHECK'},'evidence_refs':['fixture-icon'],'selection_rationale':'A UI designer needs an editable shopping bag icon for retail navigation and interface composition.'}]
 with pytest.raises(m.ProducerDispatchError) as e:m.route_frozen_expression(plan=plan,semantic_asset_id='FASA-SHOPPING_BAG_ICON',blueprint=icon,frozen_blueprint_sha256=m.canonical_sha256(icon))
 assert e.value.code=='PRODUCER_ENGINE_UNAVAILABLE'
def test_dispatch_key_is_deterministic_and_changes_with_frozen_blueprint():
 a=route('photo','FASA-SHOPPING_BAG_PHOTO');b=route('photo','FASA-SHOPPING_BAG_PHOTO');assert a['dispatch_key']==b['dispatch_key']
def test_registry_has_no_post_hoc_conversion_route():
 reg=m.load_registry();assert all(r['post_hoc_conversion_allowed'] is False and r['master_generation_mode']=='DIRECT_FROM_BLUEPRINT' for r in reg['routes'])