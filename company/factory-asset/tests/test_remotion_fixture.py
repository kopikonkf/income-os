import json, shutil, subprocess
from pathlib import Path
import jsonschema, pytest

ROOT=Path(__file__).resolve().parents[3]
FIX=ROOT/'company/factory-asset/native-producers/remotion-fixture'
RECEIPT=ROOT/'company/factory-asset/receipts/FA-041-remotion-motion-producer-fixture.receipt.json'

def test_remotion_composition_contract_exactly_matches_fa040_fixture():
    plan=json.loads((ROOT/'company/factory-asset/fixtures/motion-composition/fixture-plan.v1.json').read_text())
    canonical=next(x['composition'] for x in plan['fixtures'] if x['name']=='shopping-bag-bounce-mp4')
    local=json.loads((FIX/'src/composition-contract.json').read_text())
    assert local==canonical
    assert local['semantic_mode']=='ANIMATION' and local['native_representation']=='TIMED_FRAMES'
    assert local['conversion_from_raster'] is False

def test_remotion_runtime_versions_are_exact_and_install_script_allowlist_is_narrow():
    pkg=json.loads((FIX/'package.json').read_text()); lock=json.loads((FIX/'package-lock.json').read_text())
    assert pkg['dependencies']=={'@remotion/bundler':'4.0.520','@remotion/cli':'4.0.520','@remotion/renderer':'4.0.520','react':'19.2.8','react-dom':'19.2.8','remotion':'4.0.520'}
    assert pkg['allowScripts']=={'esbuild@0.28.1':True}
    assert lock['packages']['']['dependencies']==pkg['dependencies']

def test_worker_pins_contract_render_flags_and_atomic_cleanup_boundary():
    src=(FIX/'render-worker.mjs').read_text()
    for marker in ('--codec=h264','--pixel-format=yuv420p','--image-format=png','--muted','--concurrency=1','browser', 'ensure', 'renameSync(temp, finalDir)', 'rmSync(temp, {recursive: true, force: true})'):
        assert marker in src
    assert 'OUTPUT_DIR_EXISTS' in src and 'INJECTED_FAILURE_BEFORE_RENDER' in src

def test_worker_failure_cleanup_self_test_runs_without_rendering():
    node=shutil.which('node')
    if not node: pytest.skip('node unavailable')
    p=subprocess.run([node,str(FIX/'render-worker.mjs'),'--self-test-cleanup'],capture_output=True,text=True,check=True,timeout=30)
    result=json.loads(p.stdout.strip())
    assert result=={'schema':'die.factory-asset.remotion-cleanup-self-test.v1','result':'PASS','injected_failure_observed':True,'temporary_entries_after_failure':0,'partial_final_output':False}

def test_fa041_actual_receipt_proves_real_mp4_contract_and_native_receipt():
    r=json.loads(RECEIPT.read_text()); ns=json.loads((ROOT/'company/factory-asset/schemas/native-producer.schema.json').read_text())
    assert r['result']=='PASS' and r['renderer_execution_performed'] is True
    assert r['contract_exact_match'] is True
    assert r['render']=={'composition_id':'ShoppingBagBounce','master_format':'MP4','codec':'h264','pixel_format':'yuv420p','width':1080,'height':1080,'fps':30,'frame_count':180,'duration_seconds':6.0,'audio_stream_count':0,'audio_policy':'NONE','preview_format':'PNG','preview_frame':90,'preview_dimensions':[1080,1080]}
    assert r['repeatability']['independent_render_master_sha_match'] is True
    assert r['repeatability']['independent_render_preview_sha_match'] is True
    assert r['repeatability']['binary_repeatability']=='PASS'
    assert r['cleanup']['success_temp_leftovers']==0 and r['cleanup']['failure_self_test']['result']=='PASS'
    jsonschema.Draft202012Validator(ns).validate(r['native_receipt'])
    assert r['native_receipt']['master']['conversion_from_raster'] is False

def test_fa041_has_no_live_provider_marketplace_or_production_license_claim():
    r=json.loads(RECEIPT.read_text()); src=(FIX/'render-worker.mjs').read_text().lower()
    assert r['authority']=={'provider_generation':False,'browser_profile_ownership':False,'credential_access':False,'marketplace_upload':False,'publication':False,'spend_usd':0}
    assert r['marketplace_compatibility']=='UNKNOWN_PENDING_FA-042'
    assert r['licensing_scope']['production_automation_license_asserted'] is False
    for marker in ('fetch(', 'requests.', 'session_token', 'cdp_url', 'marketplace upload'):
        assert marker not in src