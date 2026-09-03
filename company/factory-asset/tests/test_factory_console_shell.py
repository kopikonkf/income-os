import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONSOLE = ROOT / 'company/factory-asset/console-prototype'
DATA = json.loads((CONSOLE / 'synthetic-data.json').read_text(encoding='utf-8'))


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_console_shell_files_exist_and_javascript_parses():
    for name in ('index.html','styles.css','app.js','synthetic-data.js','synthetic-data.json','README.md'):
        assert (CONSOLE / name).is_file()
    result = subprocess.run(['node', '--check', str(CONSOLE / 'app.js')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_console_has_exact_required_primary_navigation_and_panels():
    html = (CONSOLE / 'index.html').read_text(encoding='utf-8')
    nav = re.findall(r'data-view="([a-z]+)"', html)
    panels = re.findall(r'data-view-panel="([a-z]+)"', html)
    expected = ['blueprint','batch','queue','providers','output']
    assert nav == expected
    assert panels == expected


def test_fixture_is_synthetic_and_live_dispatch_is_disabled():
    assert DATA['environment'] == 'SYNTHETIC'
    assert DATA['liveDispatchEnabled'] is False
    assert DATA['batch']['dispatchAuthority'] == 'SIMULATED_ONLY'


def test_six_asset_types_and_semantic_packaging_counts_are_separate():
    assert [x['id'] for x in DATA['assetTypes']] == ['PHOTO','ISOLATED_OBJECT','ICON','OUTLINE','PATTERN','ANIMATION']
    assert DATA['batch']['semanticCount'] == DATA['batch']['quantity']
    assert DATA['batch']['packagingDerivativeCount'] > DATA['batch']['semanticCount']
    assert all(output['semanticCount'] == 1 for output in DATA['outputs'])
    assert all(len(output['derivatives']) >= 1 for output in DATA['outputs'])


def test_queue_fixture_spans_required_operational_states():
    states = {row['state'] for row in DATA['queue']}
    assert {'READY','RUNNING','RETRY_WAIT','SUCCEEDED','BLOCKED'} <= states


def test_provider_pool_contains_current_five_plus_optional_grok():
    providers = {p['id']: p for p in DATA['providers']}
    assert {'qwen','chatgpt','gemini','manus','duckai','grok'} == set(providers)
    assert all(providers[p]['eligibility'] == 'ELIGIBLE' for p in ('qwen','chatgpt','gemini','manus','duckai'))
    assert providers['grok']['eligibility'] == 'DEFERRED_OPTIONAL'
    assert 'never blocks' in providers['grok']['routing'].lower()


def test_synthetic_fixture_contains_no_credential_or_vendor_wire_keys():
    forbidden = {'cookie','cookies','session_token','access_token','refresh_token','password','credential','credentials','rpc_id','endpoint','raw_request_body','auth_body'}
    keys = {str(k).lower() for k in walk_keys(DATA)}
    assert not (keys & forbidden)


def test_shell_has_no_external_provider_or_browser_automation_api():
    js = (CONSOLE / 'app.js').read_text(encoding='utf-8')
    forbidden = ['XMLHttpRequest', 'WebSocket', 'EventSource', 'navigator.sendBeacon', 'axios', 'cdp', 'playwright', 'puppeteer', 'http://', 'https://']
    for marker in forbidden:
        assert marker not in js
    assert "postLocal('/api/compile'" in js
    assert "postLocal('/api/batch-intent'" in js
    assert 'Live Dispatch Locked' in js
    assert 'SIMULATED_ONLY' in js


def test_javascript_fixture_matches_json_fixture_exactly():
    js = (CONSOLE / 'synthetic-data.js').read_text(encoding='utf-8').strip()
    prefix = 'window.FactoryConsoleSyntheticData = '
    assert js.startswith(prefix) and js.endswith(';')
    embedded = json.loads(js[len(prefix):-1])
    assert embedded == DATA