import importlib.util,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('ddp',R/'company/factory-asset/lib/derivative_delivery_planner.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();FA131=json.loads((R/'company/factory-asset/receipts/FA-131-provider-original-intake.receipt.json').read_text());PHOTO=json.loads((R/'company/factory-asset/fixtures/shopping-bag-blueprint-v2/photo.json').read_text());PATTERN=json.loads((R/'company/factory-asset/fixtures/shopping-bag-blueprint-v2/pattern.json').read_text())
def provider_original(name): return next(x['receipt']['provider_original'] for x in FA131['acceptance']['fixtures'] if x['fixture']==name)
def facts(name,bp=PHOTO): return m.provider_master_facts(provider_original=provider_original(name),semantic_asset_id=bp['semantic_identity']['semantic_asset_id'],blueprint_id=bp['blueprint_id'])
def entry(plan,id): return next(x for x in plan['entries'] if x['derivative_id']==id)
def test_jpeg_provider_original_reuses_exact_bytes_for_adobe_jpeg_delivery():
 p=m.plan_derivatives(blueprint=PHOTO,master=facts('opaque.jpg'));j=entry(p,'ADOBE_JPEG');w=entry(p,'WEB_PREVIEW');assert j['action']=='REUSE_MASTER_BYTES';assert j['master_format']=='JPEG';assert j['compatibility_state']=='COMPATIBLE';assert j['alpha_policy']=='NOT_APPLICABLE';assert w['action']=='RASTER_DERIVATIVE';assert p['provider_original_bytes_mutated'] is False;assert p['semantic_asset_count']==1 and p['derivative_count']==2
def test_opaque_png_to_adobe_jpeg_requires_conversion_but_not_fake_transparency():
 p=m.plan_derivatives(blueprint=PHOTO,master=facts('opaque.png'));j=entry(p,'ADOBE_JPEG');w=entry(p,'WEB_PREVIEW');assert j['action']=='RASTER_DERIVATIVE';assert j['alpha_policy']=='NOT_APPLICABLE';assert j['transparent_output_claim'] is False;assert w['transparent_output_claim'] is False
def test_transparent_png_to_jpeg_requires_explicit_flatten_white_and_webp_preserves():
 p=m.plan_derivatives(blueprint=PHOTO,master=facts('alpha.png'));j=entry(p,'ADOBE_JPEG');w=entry(p,'WEB_PREVIEW');assert j['alpha_policy']=='FLATTEN_WHITE';assert j['transparent_output_claim'] is False;assert w['alpha_policy']=='PRESERVE';assert w['transparent_output_claim'] is True
def test_opaque_rgba_still_uses_explicit_jpeg_alpha_handling_without_transparent_claim():
 p=m.plan_derivatives(blueprint=PHOTO,master=facts('opaque-rgba.png'));j=entry(p,'ADOBE_JPEG');w=entry(p,'WEB_PREVIEW');assert j['alpha_policy']=='FLATTEN_WHITE';assert w['alpha_policy']=='PRESERVE';assert w['transparent_output_claim'] is False
def test_jpeg_to_png_preview_never_claims_transparency():
 b=json.loads(json.dumps(PHOTO));b['derivatives'][1]={'derivative_id':'PNG_PREVIEW','purpose':'PREVIEW','format':'PNG','semantic_identity_effect':'NONE'};p=m.plan_derivatives(blueprint=b,master=facts('opaque.jpg',b));x=entry(p,'PNG_PREVIEW');assert x['action']=='RASTER_DERIVATIVE';assert x['alpha_policy']=='NOT_APPLICABLE';assert x['transparent_output_claim'] is False
def test_unknown_marketplace_profile_blocks_package_instead_of_promoting_pass():
 b=json.loads(json.dumps(PHOTO));b['policy']['marketplace_profiles']=['DREAMSTIME'];b['policy']['compatibility_state']='COMPATIBILITY_UNKNOWN';p=m.plan_derivatives(blueprint=b,master=facts('opaque.jpg',b));j=entry(p,'ADOBE_JPEG');assert j['compatibility_state']=='COMPATIBILITY_UNKNOWN';assert j['package_blocked'] is True;assert p['package_blocked'] is True
def test_duplicate_delivery_variants_collapse_to_one_physical_plan_entry():
 b=json.loads(json.dumps(PHOTO));b['derivatives'].append({'derivative_id':'ADOBE_JPEG_DUP','purpose':'MARKETPLACE_DELIVERY','format':'JPEG','semantic_identity_effect':'NONE'});p=m.plan_derivatives(blueprint=b,master=facts('opaque.png',b));jpeg=[x for x in p['entries'] if x['format']=='JPEG' and x['purpose']=='MARKETPLACE_DELIVERY'];assert len(jpeg)==1;assert jpeg[0]['aliases']==['ADOBE_JPEG_DUP'];assert p['derivative_count']==2
def test_native_pattern_plans_eps_delivery_and_jpeg_preview_without_raster_masquerade():
 master=m.native_master_facts(semantic_asset_id=PATTERN['semantic_identity']['semantic_asset_id'],blueprint_id=PATTERN['blueprint_id'],sha256='a'*64,format='SVG');p=m.plan_derivatives(blueprint=PATTERN,master=master);eps=entry(p,'ADOBE_EPS');jpg=entry(p,'JPEG_PREVIEW');assert eps['action']=='NATIVE_VECTOR_EXPORT';assert eps['compatibility_state']=='COMPATIBLE';assert jpg['action']=='VECTOR_PREVIEW_RENDER';assert p['source_kind']=='NATIVE_MASTER';assert p['semantic_asset_count']==1
def test_planning_is_deterministic():
 master=facts('alpha.png');a=m.plan_derivatives(blueprint=PHOTO,master=master);b=m.plan_derivatives(blueprint=PHOTO,master=master);assert a==b and a['plan_sha256']==b['plan_sha256']