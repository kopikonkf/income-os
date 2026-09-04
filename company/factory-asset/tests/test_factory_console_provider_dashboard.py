import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CONSOLE=ROOT/'company/factory-asset/console-prototype'

def load_server():
 spec=importlib.util.spec_from_file_location('console_c007_server',CONSOLE/'server.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def test_provider_dashboard_endpoint_state_is_core_backed_fixture_truth():
 m=load_server();d=m.provider_dashboard_state();assert d['schema']=='die.factory-asset.provider-dashboard.v1';assert d['evidence_mode']=='SYNTHETIC_OBSERVED_FIXTURE';assert d['guessed_quota_present'] is False;assert d['provider_dispatch_performed'] is False;assert d['selected_profile_id']=='qwen_a'
 rows={x['provider_id']:x for x in d['providers']};assert rows['gemini']['capacity']=='CONSTRAINED';assert rows['gemini']['health']=='DEGRADED';assert rows['grok']['eligibility']=='DEFERRED_OPTIONAL';assert 'POLICY_BLOCKED' in rows['grok']['routing_reason']

def test_provider_dashboard_http_roundtrip():
 m=load_server();httpd=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/providers',timeout=5) as response:d=json.loads(response.read())
  assert d['selected_profile_id']=='qwen_a';assert len(d['providers'])==6;assert d['provider_dispatch_performed'] is False
 finally:httpd.shutdown();httpd.server_close();thread.join(timeout=5)

def test_provider_dashboard_ui_uses_api_not_synthetic_provider_cards():
 js=(CONSOLE/'app.js').read_text(encoding='utf-8');assert "getLocal('/api/providers')" in js;assert 'source.providers.map' not in js;assert 'd.evidence_mode' in js;assert 'Guessed quota' in js;assert 'Provider dispatch' in js

def test_provider_dashboard_output_contains_no_secret_or_vendor_wire_material():
 m=load_server();text=json.dumps(m.provider_dashboard_state()).lower()
 for marker in ('password','session_token','access_token','refresh_token','cookie','rpc_id','cdp_url','browser_profile','raw_auth_body'):
  assert marker not in text

def test_optional_grok_does_not_block_selected_route():
 m=load_server();d=m.provider_dashboard_state();rows={x['provider_id']:x for x in d['providers']};assert rows['grok']['eligibility']=='DEFERRED_OPTIONAL';assert d['selected_profile_id'] is not None and d['selected_profile_id']!='grok_a'