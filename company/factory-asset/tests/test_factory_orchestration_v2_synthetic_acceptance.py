import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-140-factory-orchestration-v2-synthetic-acceptance.receipt.json'
def test_fa140_all_acceptance_flags_pass_except_explicit_nonclaim():
 r=json.loads(REC.read_text());assert r['result']=='PASS';a=r['acceptance'];assert a['binary_metadata_injection_claimed'] is False;assert all(v=='PASS' for k,v in a.items() if k!='binary_metadata_injection_claimed')
def test_fa140_raster_png_and_jpeg_reach_founder_gate_with_human_names():
 r=json.loads(REC.read_text());
 for case in ('png','jpeg'):
  x=r['raster_provider_original'][case];assert x['state']=='WAITING_FOUNDER_QC';assert x['listing_filename'].startswith('shopping-bag-isolated-object__');assert x['listing_filename']!='asset.png';assert {'PRODUCTION_STARTED','ARTIFACT_CREATED','QA_QC_UPDATE','WAITING_FOUNDER_QC'}.issubset(set(x['telegram_kinds']))
def test_fa140_native_pattern_and_motion_routes_are_accepted_without_posthoc_conversion():
 r=json.loads(REC.read_text());p=r['native_pattern'];assert p['route']['dispatch_adapter']=='PROCEDURAL_PATTERN_V0_1' and p['route']['post_hoc_conversion_allowed'] is False and p['embedded_raster'] is False and p['eps_certified'] is False;m=r['motion'];assert m['route']['dispatch_adapter']=='MOTION_ENGINE_V0_1' and m['route']['post_hoc_conversion_allowed'] is False;assert len(m['real_accepted_mp4_reference']['sha256'])==64
def test_fa140_cognition_and_retry_paths():
 r=json.loads(REC.read_text());assert r['cognition']['reuse']['outcome']=='REUSE_FIXED_BLUEPRINT';assert r['cognition']['new_family_escalation']['outcome']=='DIVISION01_AUTHOR_THEN_EXECUTIVE_CHALLENGE';assert r['crash_retry']['history_kinds']==['CREATE','ADVANCE','FAILURE','RESUME'] and r['crash_retry']['final_status']=='ACTIVE'
def test_fa140_zero_live_provider_and_publish_authority():
 r=json.loads(REC.read_text());assert r['authority']=={'network_calls':0,'live_provider_calls':0,'marketplace_upload':False,'publication':False,'founder_qc_completed':False,'human_rights_clearance':False,'spend_usd':0}