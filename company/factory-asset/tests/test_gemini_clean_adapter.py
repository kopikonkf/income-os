from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[3]
ADAPTER = ROOT / 'company/factory-asset/providers/gemini/adapter.py'
CANARY = ROOT / 'company/factory-asset/providers/gemini/linux/gemini_muxia_canary.mjs'


def load_adapter():
    spec = importlib.util.spec_from_file_location('gemini_adapter', ADAPTER)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_capability_is_muxia_browser_cdp_cluster_a():
    m=load_adapter(); c=m.capability(); assert c['provider_id']=='gemini'; assert c['transport_classes']==['BROWSER_CDP']; assert c['browser_runtime_owner']=='MUXIA'; assert c['profile_id']=='chatgpt-linux-a'


def test_strategy_is_windows_proven_download_control_only():
    m=load_adapter(); s=m.browser_strategy(); assert s['acquisition_route']=='PROVIDER_DOWNLOAD_CONTROL'; assert 'download' in s['download_selector'].lower(); assert s['credential_values_embedded'] is False; assert s['session_material_embedded'] is False


def test_adapter_contains_no_browser_or_secret_ownership():
    s=ADAPTER.read_text().lower()
    for bad in ('connect_over_cdp','connectovercdp','launchpersistentcontext','context.cookies','storage_state','cookie=','token=','d:/assets','credentials/gemini'):
        assert bad not in s


def test_canary_is_bounded_single_dispatch_and_cluster_a():
    s=CANARY.read_text(); assert "chatgpt-linux-a" in s; assert "browser_runtime_owner: 'MUXIA'" in s; assert s.count("composer.press('Enter')")==1; assert 'generationTimeoutMs = 180000' in s


def test_canary_never_reads_session_secret_material():
    s=CANARY.read_text().lower(); assert 'context.cookies' not in s; assert 'storagestate' not in s; assert 'credential_values_read: false' in s; assert 'cookies_or_tokens_read: false' in s; assert 'operator_actions_after_dispatch: 0' in s


def test_normalize_rejects_nonpass_and_secret_boundary_break():
    m=load_adapter()
    base={'provider_id':'gemini','transport_class':'BROWSER_CDP','status':'PASS','operator_actions_after_dispatch':0,'credential_values_read':False,'cookies_or_tokens_read':False,'output_extracted_by_automation':True,'prompt_submitted_by_automation':True,'sha256':'a'*64,'bytes':1,'mime':'image/png','local_path':'/x','original_byte_acquisition_method':'provider_browser_download_event'}
    assert m.normalize_canary_receipt(base)['kind']=='GENERATE_RESULT'
    bad=dict(base,status='FAILED')
    try: m.normalize_canary_receipt(bad); assert False
    except ValueError: pass
