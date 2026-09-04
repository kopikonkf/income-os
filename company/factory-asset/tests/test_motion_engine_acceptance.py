import json, subprocess, shutil
from pathlib import Path
import jsonschema
R=Path(__file__).resolve().parents[3]
REC=R/'company/factory-asset/receipts/FA-043-motion-engine-v0.1-acceptance.receipt.json'
FIX=R/'company/factory-asset/native-producers/remotion-fixture'
def test_fa043_acceptance_matrix_and_zero_false_success():
 r=json.loads(REC.read_text());assert r['result']=='PASS';assert r['zero_false_success'] is True;assert set(r['acceptance'].values())=={'PASS','PASS_FAIL_CLOSED'};assert r['determinism']['retry_success_master_sha_match'] and r['determinism']['retry_success_preview_sha_match'];assert r['retry_output_motion_qa']['result']=='PASS'
def test_fa043_resource_bounds_are_explicit_and_single_concurrency():
 r=json.loads(REC.read_text());assert r['resource_bounds']=={'maxWidth':3840,'maxHeight':2160,'maxFrameCount':3600,'maxDurationSeconds':60,'maxFps':60,'concurrency':1,'commandTimeoutMs':300000}
def test_fa043_cancel_receipt_is_native_schema_and_nonpartial():
 r=json.loads(REC.read_text());ns=json.loads((R/'company/factory-asset/schemas/native-producer.schema.json').read_text());jsonschema.Draft202012Validator(ns).validate(r['cancellation']['native_receipt']);assert r['cancellation']['native_receipt']['result']=='CANCELLED';assert r['cancellation']['partial_final_output'] is False
def test_fa043_compatibility_is_fail_closed():
 r=json.loads(REC.read_text());assert r['compatibility']['ADOBE_STOCK']['state']=='COMPATIBLE';assert r['compatibility']['DREAMSTIME']['state']=='UNKNOWN';assert r['compatibility']['VECTEEZY']['state']=='UNKNOWN';assert r['compatibility']['MOTIONELEMENTS']['state']=='UNKNOWN'
def test_fa043_worker_declares_cancel_retry_bounds():
 src=(FIX/'render-worker.mjs').read_text();
 for marker in ('RESOURCE_BOUNDS','--self-test-cancel','--self-test-retry','commandTimeoutMs','concurrency:1','CANCELLED'):
  assert marker in src