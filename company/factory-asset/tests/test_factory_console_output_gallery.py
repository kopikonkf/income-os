import importlib.util,json,sys,threading,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CONSOLE=ROOT/'company/factory-asset/console-prototype'
FIX=ROOT/'company/factory-asset/fixtures/output-gallery/fa029-actual-canary.v1.json'

def load_server():
 spec=importlib.util.spec_from_file_location('console_c008',CONSOLE/'server.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def test_output_fixture_preserves_semantic_vs_derivative_truth():
 d=json.loads(FIX.read_text());assert d['evidence_mode']=='ACTUAL_FA029_CANARY';assert d['semantic_asset_count']==5;assert d['derivative_count']==20;assert sum(x['semantic_count'] for x in d['assets'])==5;assert sum(len(x['derivatives']) for x in d['assets'])==20
 for a in d['assets']:
  assert a['master']['immutable'] is True;assert a['master']['canonical_truth'] is False;assert a['master']['ingestion_state']=='STAGED_NOT_CANONICAL';assert len(a['master']['sha256'])==64
  assert len(a['derivatives'])==4
  for x in a['derivatives']:
   assert x['qa_state']=='PASS';assert x['compatibility_state']=='COMPATIBLE';assert x['semantic_identity_effect']=='NONE';assert len(x['sha256'])==64;assert x['recipe_id']

def test_output_gallery_endpoint_uses_actual_canary_fixture():
 m=load_server();d=m.output_gallery_state();assert d['semantic_asset_count']==5 and d['derivative_count']==20;assert d['canonical_truth'] is False

def test_output_gallery_http_roundtrip():
 m=load_server();httpd=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler);t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/outputs',timeout=5) as r:d=json.loads(r.read())
  assert d['schema']=='die.factory-asset.output-gallery.v1';assert len(d['assets'])==5
 finally:httpd.shutdown();httpd.server_close();t.join(timeout=5)

def test_output_ui_uses_api_not_old_synthetic_cards():
 js=(CONSOLE/'app.js').read_text();assert "getLocal('/api/outputs')" in js;assert 'source.outputs.map' not in js;assert 'state_manager_status' in js;assert 'semantic_asset_count' in js;assert 'derivative_count' in js;assert 'Lineage' in js

def test_output_fixture_has_no_upload_or_publication_authority():
 d=json.loads(FIX.read_text());assert d['publication_action']=='NONE';assert d['upload_action']=='NONE'

def test_duplicate_suppression_evidence_is_visible_and_real():
 d=json.loads(FIX.read_text());probe=d['duplicate_suppression_probe'];assert probe['manifest_entry_count']==2;assert probe['unique_file_count']==1