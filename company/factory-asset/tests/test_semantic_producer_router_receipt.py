import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REC=R/'company/factory-asset/receipts/FA-133-semantic-producer-dispatch-router.receipt.json'
REG=R/'company/factory-asset/registries/producer-dispatch.v1.json'
def test_fa133_actual_acceptance_receipt_seals_expected_routes():
 r=json.loads(REC.read_text());assert r['result']=='PASS';p=r['positive_routes'];assert p['photo']['dispatch_adapter']=='FA104_PROVIDER_ROUTER';assert p['isolated_object']['dispatch_adapter']=='FA104_PROVIDER_ROUTER';assert p['pattern']['dispatch_adapter']=='PROCEDURAL_PATTERN_V0_1';assert p['animation']['dispatch_adapter']=='MOTION_ENGINE_V0_1';assert all(x['result']=='DISPATCH_READY' for x in p.values())
def test_fa133_actual_negative_controls_have_zero_false_success():
 r=json.loads(REC.read_text());n=r['negative_controls'];assert n['frozen_hash_mismatch']['code']=='FROZEN_BLUEPRINT_HASH_MISMATCH';assert n['producer_mismatch']['code']=='BLUEPRINT_PRODUCER_MISMATCH';assert n['native_vector_unaccepted']['code']=='PRODUCER_ENGINE_UNAVAILABLE';assert all(x['result']=='BLOCKED' for x in n.values());assert r['validation']['zero_false_success'] is True
def test_dispatch_registry_forbids_post_hoc_conversion_everywhere():
 d=json.loads(REG.read_text());assert d['schema']=='die.factory-asset.producer-dispatch-registry.v1';assert all(x['master_generation_mode']=='DIRECT_FROM_BLUEPRINT' and x['post_hoc_conversion_allowed'] is False for x in d['routes'])
def test_unaccepted_native_vector_routes_are_not_promoted():
 d=json.loads(REG.read_text());rows=[x for x in d['routes'] if x['producer_class']=='NATIVE_VECTOR'];assert rows and all(x['engine_state']=='UNAVAILABLE_NOT_ACCEPTED' for x in rows)
def test_fa133_has_zero_execution_or_marketplace_authority():
 r=json.loads(REC.read_text());assert r['authority']=={'provider_dispatch_performed':False,'native_render_performed':False,'credential_access':False,'marketplace_upload':False,'publication':False,'spend_usd':0}