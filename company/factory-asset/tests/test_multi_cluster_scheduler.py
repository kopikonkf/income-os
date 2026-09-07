from pathlib import Path
import json, subprocess
R=Path(__file__).resolve().parents[3]
CORE=R/'company/browser/linux/multi_cluster_scheduler.mjs'
RUN=R/'company/factory-asset/bin/run_fa306_multi_cluster_scheduler_synthetic.mjs'
CONTRACT=R/'company/factory-asset/contracts/multi-cluster-scheduler.v1.json'
RESULT=R/'company/factory-asset/fixtures/multi-cluster/FA-306-multi-cluster-scheduler-result.json'
TOPO=R/'company/factory-asset/fixtures/multi-cluster/FA-306-live-topology-snapshot.json'
GRAPH=R/'company/factory-asset/task-graph-v1.json'

def run_acceptance():
 r=subprocess.run(['node',str(RUN)],capture_output=True,text=True,check=True,timeout=60);return json.loads(r.stdout)

def test_fa306_synthetic_acceptance_passes_all_matrix():
 d=run_acceptance();assert d['result']=='PASS';assert all(d['assertions'].values());assert d['provider_calls_performed'] is False;assert d['browser_processes_spawned']==0;assert d['live_broker_leases_acquired']==0

def test_fairness_and_cross_cluster_queue_lease_are_deterministic():
 d=run_acceptance()['evidence'];assert d['fairness']['picks']==['cluster-a','cluster-b','cluster-a','cluster-b'];q=d['queue_lease_isolation'];assert q['first']['queue_lease']['lease_id']==q['replay']['queue_lease']['lease_id'];assert q['conflict']['code']=='E_JOB_QUEUE_LEASE_CONFLICT'

def test_provider_and_cluster_circuits_and_retry_budget():
 d=run_acceptance()['evidence'];assert d['provider_cluster_circuit']['circuits']['provider_cluster']['gemini@cluster-a']['state']=='OPEN';assert d['cluster_circuit']['after']['clusters']['cluster-a']['state']=='CLOSED';assert d['retry_budget']['limit']['code']=='E_RETRY_LIMIT'

def test_exactly_once_commit_and_post_dispatch_retry_block():
 d=run_acceptance()['evidence']['exactly_once_commit'];assert d['replay']['commit_id']==d['commit']['commit_id'];assert d['replay']['idempotent_replay'] is True;assert d['duplicate']['code']=='E_DUPLICATE_GENERATION_COMMIT';assert d['jobDuplicate']['code']=='E_JOB_ALREADY_COMMITTED';assert d['retryAfter']['code']=='E_RETRY_AFTER_DISPATCH_COMMIT'

def test_contract_preserves_per_cluster_tab_lease_and_authority_boundaries():
 c=json.loads(CONTRACT.read_text());assert c['queue_leases']['cross_cluster_exclusive'] is True;assert c['queue_leases']['provider_tab_lease_still_required_for_browser_routes'] is True;assert c['retry']['max_retries']==2;assert c['authority']['provider_generation_calls'] is False;assert c['authority']['browser_owner_actions'] is False;assert c['authority']['secret_reads'] is False

def test_scheduler_is_pure_control_plane_no_browser_or_network_surface():
 s=CORE.read_text().lower();
 for bad in ('child_process','spawn(','exec(','playwright','connectovercdp','launchpersistentcontext','--user-data-dir','fetch(','axios','context.cookies','storagestate','localstorage','sessionstorage','indexeddb','document.cookie','authorization'):
  assert bad not in s
 assert 'clusterawareproviderrouter' in s and 'browser_owner_action' in s

def test_live_topology_snapshot_has_two_ready_brokers_without_lease_mutation():
 d=json.loads(TOPO.read_text());by={x['cluster_id']:x for x in d['clusters']};assert set(by)=={'cluster-a','cluster-b'};assert all(x['state']=='READY' and x['max_tabs']==8 and x['active_leases']==0 for x in by.values());assert all(x['control_host']=='127.0.0.1' and x['debug_host']=='127.0.0.1' for x in by.values());assert d['live_lease_mutation_performed'] is False and d['provider_calls_performed'] is False
