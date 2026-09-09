import importlib.util,json,sys,threading,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];LIB=ROOT/'company/factory-asset/lib/console_production_acceptance.py';CONSOLE=ROOT/'company/factory-asset/console-prototype'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
def broker(_url):
 return {'state':'READY','tab_leases':{'schema':'die.muxia.cluster-tab-lease-snapshot.v1','active_leases':0,'open_pages':1,'max_tabs':8,'provider_states':{p:'HEALTHY' for p in ('chatgpt','qwen','gemini','manus','duckai')}}}
def test_production_acceptance_binds_real_fa124_truth_to_sanitized_pool():
 m=load('c013_accept',LIB);d=m.build_production_acceptance(ROOT,broker_fetch=broker,observed_at='2026-09-09T15:00:00Z')
 assert d['technical_result']=='PASS' and d['founder_validation_required'] is True
 assert d['production_model']['accepted_masters']==100 and d['production_model']['unique_sha256']==100 and d['production_model']['all_10_routes_certified'] is True
 assert d['live_pool']['healthy_routes']==10 and len(d['live_pool']['routes'])==10
 assert d['batch_queue']['fa_c011_result']=='PASS' and d['recovery']['fa_c012_result']=='PASS'
 assert d['recovery']['duplicate_dispatch_blocked'] is True and d['output_truth']['exact_duplicate_hashes']==0 and d['output_truth']['object_confirmed_near_duplicate_pairs']==0
 assert d['storage']['estimated_100_per_day_gib']==4.661 and d['storage']['estimated_30_day_gib']==139.826
 assert d['provider_dispatch_authority'] is False and d['publication_authority'] is False
 text=json.dumps(d).lower()
 for marker in ('password','session_token','access_token','refresh_token','private_key','cdp_url','browser_profile','raw_auth_body'):assert marker not in text
 assert d['truth_boundaries']['cookies_or_tokens_read'] is False

def test_console_http_exposes_production_acceptance_without_dispatch():
 s=load('c013_server',CONSOLE/'server.py');sample={'schema':'die.factory-asset.console-production-acceptance.v1','technical_result':'PASS','provider_dispatch_authority':False,'publication_authority':False,'founder_validation_required':True,'production_model':{},'live_pool':{'routes':[]}}
 s.production_acceptance_state=lambda:sample
 httpd=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/production-acceptance',timeout=5) as r:d=json.loads(r.read())
  assert d==sample
 finally:httpd.shutdown();httpd.server_close();t.join(timeout=5)

def test_gui_has_acceptance_surface_and_preserves_no_live_authority_boundary():
 html=(CONSOLE/'index.html').read_text();js=(CONSOLE/'app.js').read_text()
 assert 'data-view="acceptance"' in html and 'GOVERNED CONTROL PLANE' in html
 assert "getLocal('/api/production-acceptance')" in js and '100/day Production Acceptance' in js
 assert 'Provider dispatch from Console' in js and 'Marketplace publication' in js and 'Founder GUI validation' in js
