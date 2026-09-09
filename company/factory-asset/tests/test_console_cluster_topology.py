import importlib.util,json,sys,threading,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];LIB=ROOT/'company/factory-asset/lib/console_cluster_topology.py';CONSOLE=ROOT/'company/factory-asset/console-prototype'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def fake_fetch(url):
 cid='cluster-a' if ':39121/' in url else 'cluster-b'
 return {'schema':'die.muxia.cluster-broker-state.v1','cluster_id':cid,'profile_id':'p','profile_dir':'/secret/profile','state':'READY','browser_owner_pid':1234 if cid=='cluster-a' else 5678,'browser_owner_model':'EXTERNAL_PERSISTENT_CHROME_CDP_ATTACH_ONLY','debug_host':'127.0.0.1','debug_port':39221,'control_host':'127.0.0.1','control_port':39121,'credential_values_read':False,'cookies_or_tokens_read':False,'tab_leases':{'max_tabs':8,'active_leases':1 if cid=='cluster-a' else 0,'open_pages':2 if cid=='cluster-a' else 1,'provider_states':{'chatgpt':'HEALTHY','qwen':'HEALTHY','gemini':'AUTH_REQUIRED' if cid=='cluster-a' else 'HEALTHY','manus':'HEALTHY','duckai':'DEGRADED'},'leases':([{'lease_id':'SECRET-LEASE','provider_id':'qwen','job_id':'PROD1','state':'IN_FLIGHT','claim_url':'about:blank#secret','acquired_at':'2026-09-09T18:00:00Z','expires_at':'2026-09-09T18:05:00Z','provider_limit':1}] if cid=='cluster-a' else [])}}

def test_topology_sanitizes_cluster_owner_tabs_jobs_and_auth_state():
 m=load('c015_topology',LIB);d=m.build_cluster_topology(ROOT,fetch_json=fake_fetch,observed_at='2026-09-09T18:00:00Z');assert d['provider_calls_performed'] is False and d['browser_owner_actions_performed'] is False and d['production_cadence_changed'] is False and d['scale_100_per_day_authorized'] is False
 assert len(d['clusters'])==2;a=d['clusters'][0];assert a['health']=='HEALTHY' and a['profile_owner']['lock_state']=='OWNED' and a['profile_owner']['owner_pid']==1234;assert a['tab_occupancy']['max_tabs']==8 and a['tab_occupancy']['open_pages']==2 and a['tab_occupancy']['active_leases']==1 and a['tab_occupancy']['free_tab_slots']==6
 q=next(x for x in a['provider_sessions'] if x['provider_id']=='qwen');assert q['capacity']=='BUSY' and q['active_jobs'][0]['job_id']=='PROD1'
 g=next(x for x in a['provider_sessions'] if x['provider_id']=='gemini');assert g['readiness']=='AUTH_REQUIRED' and g['capacity']=='UNAVAILABLE' and g['human_action_required'] is True and g['safe_reason']=='HUMAN_AUTH_REPAIR_REQUIRED'
 text=json.dumps(d).lower()
 for forbidden in ('profile_dir','debug_port','control_port','claim_url','lease_id','cookie','credential','token','oauth','private_key'):assert forbidden not in text

def test_unreachable_cluster_fails_closed_without_secret_detail():
 m=load('c015_topology_down',LIB)
 def down(_):raise TimeoutError('contains secret URL')
 d=m.build_cluster_topology(ROOT,fetch_json=down,observed_at='x');assert all(c['health']=='OFFLINE' and c['reachable'] is False for c in d['clusters']);assert all(p['readiness']=='UNKNOWN' for c in d['clusters'] for p in c['provider_sessions'] if p['membership']=='ACTIVE');assert 'contains secret' not in json.dumps(d)

def test_live_topology_endpoint_is_read_only_and_sanitized():
 s=load('c015_server',CONSOLE/'server.py');sample={'schema':'die.factory-asset.console-cluster-topology.v1','provider_calls_performed':False,'browser_owner_actions_performed':False,'clusters':[]};s.cluster_topology_state=lambda:sample
 httpd=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{httpd.server_port}/api/cluster-topology',timeout=5) as r:d=json.loads(r.read())
  assert d==sample
 finally:httpd.shutdown();httpd.server_close();t.join(timeout=5)

def test_console_has_cluster_route_and_operator_surface():
 html=(CONSOLE/'index.html').read_text();js=(CONSOLE/'app.js').read_text();assert 'data-view="clusters"' in html and 'view-clusters' in html;assert "getLocal('/api/cluster-topology')" in js;assert 'Cluster Topology / Tab Occupancy' in js and 'Profile owner' in js and 'generation slots' in js and 'HUMAN_AUTH_REPAIR_REQUIRED' not in js
