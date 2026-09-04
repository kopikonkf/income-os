import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REC=R/'company/factory-asset/receipts/FA-135-upscale-recovery.receipt.json'
def test_fa135_noop_preserves_source_hash_and_dimensions():
 r=json.loads(REC.read_text());n=r['receipts']['noop'];assert n['result']=='NOOP';assert n['source_sha256']==n['final_sha256']==r['source']['sha256'];assert n['source_dimensions']==n['final_dimensions']==[12,8];assert n['source_unchanged'] is True
def test_fa135_upscale_and_rerun_are_lineage_safe():
 r=json.loads(REC.read_text());u=r['receipts']['upscale_first'];rr=r['receipts']['upscale_rerun'];assert u['result']=='PASS' and u['final_dimensions']==[24,16];assert rr['idempotent_reuse'] is True and rr['final_sha256']==u['final_sha256'];assert u['source_sha256']==r['source']['sha256']
def test_fa135_recovery_rights_and_failure_rules():
 r=json.loads(REC.read_text());assert r['decisions']['recovery']['state']=='RECOVERY_REQUIRED';assert r['decisions']['rights_block']['state']=='BLOCK_NONRECOVERABLE';assert r['failure_injection']['final_output_exists'] is False and r['failure_injection']['source_unchanged'] is True
def test_fa135_production_engine_not_falsely_certified():
 r=json.loads(REC.read_text());g=r['production_engine_guard'];assert g['unpinned_model_rejected']=='PRODUCTION_MODEL_SHA256_REQUIRED';assert g['realesrgan_production_certified'] is False;assert r['receipts']['upscale_first']['engine']['production_engine'] is False
def test_fa135_zero_publish_authority():
 r=json.loads(REC.read_text());assert r['authority']=={'provider_generation':False,'marketplace_upload':False,'publication':False,'spend_usd':0}