from pathlib import Path
import importlib.util

R = Path(__file__).resolve().parents[3]
A = R / 'company/factory-asset/providers/duckai/adapter.py'
C = R / 'company/factory-asset/providers/duckai/linux/duckai_muxia_canary.mjs'
E = R / 'company/factory-asset/providers/duckai/linux/duckai_indexeddb_extract.py'


def load():
    s = importlib.util.spec_from_file_location('d', A)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_contract():
    m = load()
    c = m.capability()
    assert c['provider_id'] == 'duckai'
    assert c['transport_classes'] == ['BROWSER_CDP']
    assert c['browser_runtime_owner'] == 'MUXIA'
    assert c['profile_id'] == 'chatgpt-linux-a'


def test_image_mode_and_provider_specific_routes():
    s = load().browser_strategy()
    assert s['mode_activation'] == ['Tools', 'Create Image']
    assert s['primary_acquisition_route'] == 'INDEXEDDB_CHAT_IMAGES_BLOB'
    assert s['fallback_acquisition_route'] == 'PROVIDER_DATA_URI_DOM'
    assert s['indexeddb_object_store'] == 'chat-images'
    assert s['text_only_endpoint_eligible'] is False
    assert s['internal_chat_endpoint_is_success_contract'] is False


def test_adapter_no_endpoint_or_secrets():
    s = A.read_text().lower()
    for bad in ('duckchat/v1/chat', 'httpx', 'cookie=', 'token=', 'credentials/duckai', 'd:/assets'):
        assert bad not in s


def test_indexeddb_extractor_reads_only_chat_images_and_no_secret_store():
    s = E.read_text()
    assert "stores.get('chat-images')" in s
    assert 'blob_references' in s
    assert 'r.object_store_id=?' in s
    assert 'sync-credentials' not in s
    assert "'credential_values_read': False" in s
    assert "'cookies_or_tokens_read': False" in s


def test_indexeddb_extractor_has_size_time_and_dimension_gates():
    s = E.read_text()
    assert '--after-utc' in s
    assert 'len(raw) != declared' in s
    assert 'min(w, h) < 512' in s
    assert 'E_NO_ELIGIBLE_CHAT_IMAGE_BLOB' in s


def test_canary_still_excludes_anomaly_tiles_and_never_reads_secrets():
    s = C.read_text().lower()
    assert '/assets/anomaly/' in s
    assert 'context.cookies' not in s
    assert 'storagestate' not in s
    assert 'credential_values_read:false' in s
    assert 'cookies_or_tokens_read:false' in s