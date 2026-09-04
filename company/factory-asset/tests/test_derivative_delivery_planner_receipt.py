import json
from pathlib import Path
R=Path(__file__).resolve().parents[3];REC=R/'company/factory-asset/receipts/FA-132-derivative-delivery-planner.receipt.json'
def test_fa132_acceptance_receipt_seals_provider_format_cases():
 r=json.loads(REC.read_text());assert r['result']=='PASS';a=r['acceptance'];assert all(v=='PASS' or v is False for v in a.values());assert a['provider_original_bytes_mutated'] is False
def test_fa132_receipt_keeps_semantic_count_one_across_all_cases():
 r=json.loads(REC.read_text());plans=list(r['provider_original_cases'].values())+[r['unknown_profile_case'],r['native_vector_case']];assert all(p['semantic_asset_count']==1 and p['packaging_variants_create_new_semantic_asset'] is False for p in plans)
def test_unknown_profile_is_blocking_not_promoted():
 r=json.loads(REC.read_text());p=r['unknown_profile_case'];assert p['package_blocked'] is True;assert any(e['compatibility_state']=='COMPATIBILITY_UNKNOWN' for e in p['entries'] if e['purpose']=='MARKETPLACE_DELIVERY')
def test_fa132_has_zero_execution_authority():
 r=json.loads(REC.read_text());assert r['authority']=={'derivative_execution_performed':False,'provider_dispatch_performed':False,'marketplace_upload':False,'publication':False,'spend_usd':0}