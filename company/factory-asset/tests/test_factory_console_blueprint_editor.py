import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONSOLE = ROOT / 'company/factory-asset/console-prototype'
FIXTURES = ROOT / 'company/factory-asset/fixtures/shopping-bag-blueprint-v2'


def load_module():
    path = CONSOLE / 'server.py'
    spec = importlib.util.spec_from_file_location('factory_console_server_test', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


server = load_module()


def load_bp(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', ['photo.json','isolated-object.json','icon.json','outline.json','pattern.json','animation.json'])
def test_all_six_asset_types_compile_through_canonical_backend(name):
    bp = load_bp(name)
    result = server.compile_blueprint_payload({'blueprint': bp, 'ui_constraints': {'style_preset':'S1','consistency_preset':'C1','background':'B1'}})
    assert result['result'] == 'PASS'
    assert result['plan']['asset_type'] == bp['asset_type']
    assert result['plan']['semantic_asset_id'] == bp['semantic_identity']['semantic_asset_id']
    assert result['dispatch_performed'] is False


def test_packaging_changes_do_not_mint_semantic_identity():
    base = load_bp('photo.json')
    one = server.compile_blueprint_payload({'blueprint': base, 'ui_constraints': {'style_preset':'A','consistency_preset':'C','background':'white'}})
    changed = copy.deepcopy(base)
    changed['master_spec']['width_px'] = 8192
    changed['master_spec']['height_px'] = 8192
    changed['derivatives'][1]['format'] = 'JPEG'
    two = server.compile_blueprint_payload({'blueprint': changed, 'ui_constraints': {'style_preset':'B','consistency_preset':'C2','background':'gray'}})
    assert one['semantic_fingerprint'] == two['semantic_fingerprint']
    assert one['plan']['semantic_asset_id'] == two['plan']['semantic_asset_id']
    assert one['packaging_fingerprint'] != two['packaging_fingerprint']


def test_cross_family_invalid_editor_choice_fails_canonical_compile():
    bp = load_bp('photo.json')
    bp['master_spec']['format'] = 'SVG'
    with pytest.raises(server.compiler.BlueprintCompileError) as exc:
        server.compile_blueprint_payload({'blueprint': bp, 'ui_constraints': {'style_preset':'S','consistency_preset':'C','background':'B'}})
    assert exc.value.code == 'BLUEPRINT_SCHEMA_INVALID'


def test_batch_intent_requires_compile_and_keeps_counts_separate():
    bp = load_bp('isolated-object.json')
    preview = server.compile_blueprint_payload({'blueprint': bp, 'ui_constraints': {'style_preset':'S','consistency_preset':'C','background':'transparent'}})
    intent = server.create_batch_intent({'compile_preview':preview,'quantity':25,'label':'isolated batch','ui_constraints':preview['ui_constraints']})
    assert intent['semantic_asset_count'] == 25
    assert intent['packaging_derivative_count'] == 50
    assert intent['dispatch_authority'] == 'SIMULATED_ONLY'
    assert intent['dispatch_performed'] is False


def test_batch_quantity_is_bounded():
    bp = load_bp('photo.json')
    preview = server.compile_blueprint_payload({'blueprint': bp, 'ui_constraints': {'style_preset':'S','consistency_preset':'C','background':'white'}})
    with pytest.raises(server.ConsoleRequestError) as exc:
        server.create_batch_intent({'compile_preview':preview,'quantity':1001,'label':'too many','ui_constraints':preview['ui_constraints']})
    assert exc.value.code == 'BATCH_QUANTITY_OUT_OF_RANGE'


def test_compile_bridge_rejects_vendor_or_extra_envelope_fields():
    bp = load_bp('photo.json')
    with pytest.raises(server.ConsoleRequestError) as exc:
        server.compile_blueprint_payload({'blueprint':bp,'ui_constraints':{},'provider_endpoint':'https://example.invalid'})
    assert exc.value.code == 'INVALID_COMPILE_ENVELOPE'


def test_server_is_loopback_only_by_contract():
    source = (CONSOLE / 'server.py').read_text(encoding='utf-8')
    assert '127.0.0.1' in source
    assert 'loopback-only' in source
    assert 'requests.' not in source
    assert 'urllib.request' not in source


def test_blueprint_templates_are_derived_for_all_six_modes():
    js = (CONSOLE / 'blueprint-templates.js').read_text(encoding='utf-8').strip()
    prefix = 'window.FactoryBlueprintTemplates = '
    assert js.startswith(prefix) and js.endswith(';')
    templates = json.loads(js[len(prefix):-1])
    assert set(templates) == {'PHOTO','ISOLATED_OBJECT','ICON','OUTLINE','PATTERN','ANIMATION'}
    for bp in templates.values():
        result = server.compile_blueprint_payload({'blueprint': bp, 'ui_constraints': {}})
        assert result['result'] == 'PASS'


def test_editor_exposes_compile_and_batch_controls():
    js = (CONSOLE / 'app.js').read_text(encoding='utf-8')
    html = (CONSOLE / 'index.html').read_text(encoding='utf-8')
    assert 'blueprint-templates.js' in html
    for marker in ('compile-blueprint','master-format','style-preset','create-batch-intent','batch-quantity'):
        assert marker in js

def test_loopback_http_compile_endpoint_reaches_canonical_compiler():
    import threading
    import urllib.request
    httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        bp = load_bp('icon.json')
        body = json.dumps({'blueprint': bp, 'ui_constraints': {'style_preset':'S','consistency_preset':'C','background':'B'}}).encode('utf-8')
        request = urllib.request.Request(
            f'http://127.0.0.1:{httpd.server_port}/api/compile',
            data=body,
            headers={'Content-Type':'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))
        assert payload['result'] == 'PASS'
        assert payload['plan']['asset_type'] == 'ICON'
        assert payload['plan']['producer']['class'] == 'NATIVE_VECTOR'
        assert payload['dispatch_performed'] is False
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)