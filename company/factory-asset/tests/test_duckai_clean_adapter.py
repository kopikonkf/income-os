from pathlib import Path
import importlib.util
R=Path(__file__).resolve().parents[3];A=R/'company/factory-asset/providers/duckai/adapter.py';C=R/'company/factory-asset/providers/duckai/linux/duckai_muxia_canary.mjs'
def load():
 s=importlib.util.spec_from_file_location('d',A);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_contract():
 m=load();c=m.capability();assert c['provider_id']=='duckai' and c['transport_classes']==['BROWSER_CDP'] and c['browser_runtime_owner']=='MUXIA' and c['profile_id']=='chatgpt-linux-a'
def test_image_mode_and_route_only():
 s=load().browser_strategy();assert s['mode_activation']==['Tools','Create Image'];assert s['submit_label']=='Create';assert s['acquisition_route']=='PROVIDER_DATA_URI_DOM';assert s['text_only_endpoint_eligible'] is False
def test_adapter_no_text_endpoint_or_secrets():
 s=A.read_text().lower();
 for bad in ('duckchat/v1/chat','httpx','cookie=','token=','credentials/duckai','d:/assets'):assert bad not in s
def test_canary_one_create_dispatch_and_data_uri_only():
 s=C.read_text();assert s.count("createButton.click()") == 1;assert "src.startsWith('data:image/')" in s;assert 'Date.now()+180000' in s
def test_secret_boundary():
 s=C.read_text().lower();assert 'context.cookies' not in s and 'storagestate' not in s and 'credential_values_read:false' in s and 'cookies_or_tokens_read:false' in s and 'operator_actions_after_dispatch:0' in s

def test_human_challenge_is_typed_and_anomaly_tiles_are_excluded():
    s=C.read_text()
    assert "E_HUMAN_CHALLENGE_REQUIRED" in s
    assert "response.status()===418" in s
    assert "pathname.startsWith('/assets/anomaly/')" in s
    assert "Math.min(...dims)<512" in s
