from pathlib import Path
import hashlib
import importlib.util
import json
import sys

R=Path(__file__).resolve().parents[3]
F=R/'company/factory-asset/fixtures/governed-canary'
REC=R/'company/factory-asset/receipts/FA-202-governed-production.receipt.json'
RUNNER=R/'company/factory-asset/bin/run_fa202_governed_production.py'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;assert spec and spec.loader;spec.loader.exec_module(m);return m


def test_frozen_blueprint_and_deterministic_prompt_are_exact():
    live=json.loads((F/'FA-202-live-result.json').read_text())
    bp=json.loads((F/'FA-201-shopping-bag-blueprint-v2.json').read_text())
    plan=json.loads((F/'FA-200-shopping-bag-expression-plan.json').read_text())
    mod=load('fa202_runner_test',RUNNER)
    assert live['frozen_blueprint_sha256']=='d66654c5031f5c36aebfeb348124f9fedd17685c9362fdf6b8dbd39cd0a2e31c'
    prompt=mod.deterministic_prompt(plan,bp)
    assert hashlib.sha256(prompt.encode()).hexdigest()==live['prompt_sha256']=='30890313f7cf29cabbaa327c503343c847837dcd8ef9aadd8e2904387a555992'
    for x in ('no text','no logos','no trademarks','no brands','no watermark'):
        assert x in prompt.lower()


def test_exactly_one_live_provider_generation_and_secret_boundaries():
    r=json.loads(REC.read_text());m=json.loads((F/'FA-202-muxia-dispatch-receipt.json').read_text())
    assert r['provider_dispatch']['generation_call_count']==1
    assert r['provider_dispatch']['rerun_generation_call_count']==0
    assert m['status']=='SUCCEEDED'
    assert m['prompt_submitted_by_automation'] is True and m['output_extracted_by_automation'] is True
    assert m['credential_values_read'] is False and m['cookies_or_tokens_read'] is False
    assert m['submission_authorized'] is False and m['publication_authorized'] is False
    assert r['truth_boundaries']['qwen_session_api_live_executor_claimed'] is False


def test_provider_original_to_realesrgan_to_4096_master_lineage():
    r=json.loads(REC.read_text());u=json.loads((F/'FA-202-realesrgan-x4-receipt.json').read_text());n=json.loads((F/'FA-202-master-normalization.json').read_text())
    assert r['provider_original']['sha256']=='f3aa28b40885e9a4a684a3836704aeab26f41aa4dc6c34ebc25e8e944f0959f7'
    assert r['provider_original']['media']['width_px']==1254 and r['provider_original']['media']['height_px']==1254
    assert r['provider_original']['immutable_after_postprocess'] is True
    assert u['status']=='PASS' and u['action']=='UPSCALE_X4'
    assert u['model']['sha256']=='8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292'
    assert n['output_dimensions']==[4096,4096]
    assert n['output_sha256']==r['master']['sha256']=='5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06'
    assert r['master']['canonical_truth'] is False and r['master']['state_manager_commit_required'] is True


def test_all_three_derivatives_are_4096_qa_pass_and_same_semantic_asset():
    r=json.loads(REC.read_text())
    expected={'ADOBE_JPEG':'JPEG','PNG_PREVIEW':'PNG','WEBP_PREVIEW':'WEBP'}
    assert r['frozen_semantics']['semantic_asset_count']==1
    assert r['frozen_semantics']['packaging_variant_count']==3
    for key,fmt in expected.items():
        d=r['derivatives'][key]
        assert d['format']==fmt and d['dimensions']==[4096,4096]
        assert d['semantic_identity_effect']=='NONE'
        assert d['qa_result']=='PASS' and d['magic_mime_match'] is True and d['decode_reopen'] is True


def test_rerun_is_byte_for_byte_idempotent_and_zero_provider_call():
    p=json.loads((F/'FA-202-idempotency-proof.json').read_text())
    assert p['bytes_unchanged'] is True and p['muxia_receipt_same_generation'] is True
    assert p['rerun_provider_call_performed'] is False
    assert p['rerun_master_reused'] is True and p['rerun_upscale_reused'] is True and p['rerun_active_stage_reused'] is True
    assert all(p['rerun_derivatives_reused'].values())
    for rel,before in p['before'].items():
        if rel=='muxia_receipt': continue
        assert p['after'][rel]==before


def test_fixture_hashes_and_authority_truth_boundaries_are_pinned():
    r=json.loads(REC.read_text())
    for meta in r['fixtures'].values():
        assert sha(R/meta['ref'])==meta['sha256']
    t=r['truth_boundaries']
    assert t['visual_semantic_content_classifier_run'] is False
    assert t['rights_runtime_state']=='REVIEW_REQUIRED'
    assert t['founder_qc_complete'] is False and t['marketplace_acceptance'] is False
    assert t['canonical_truth'] is False and t['submission_authorized'] is False and t['publication_authorized'] is False
    assert t['marketplace_upload'] is False and t['spend_usd']==0