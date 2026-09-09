from pathlib import Path
import importlib.util,json,subprocess,tempfile
R=Path(__file__).resolve().parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('p',R/'company/factory-asset/lib/profile_storage_capacity.py')
B=load('b',R/'company/factory-asset/lib/browser_capacity_model.py')
S=load('s',R/'company/factory-asset/lib/storage_retention_model.py')
A=load('a',R/'company/factory-asset/lib/archive_restore_contract.py')
C310=R/'company/factory-asset/contracts/fa310-management-ingress.v1.json';C311=R/'company/factory-asset/contracts/fa311-profile-storage.v1.json';C312=R/'company/factory-asset/contracts/fa312-browser-capacity.v1.json';C314=R/'company/factory-asset/contracts/fa314-storage-retention.v1.json'
RUNTIME=R/'company/die-agents/hermes/production-runtime/production_runtime_tick.py';WRAP=R/'company/muxia/scripts/linux/die-muxia-image-dispatch.py';DISPATCH=R/'company/factory-asset/bin/production_multi_cluster_dispatch.mjs';WORKER=R/'company/factory-asset/lib/console_broker_provider_worker.mjs'

def test_fa311_planning_and_cache_allowlist_preserve_session_state():
 c=json.loads(C311.read_text());e=P.planning_envelopes(profile_a_bytes=c['current_measurement']['cluster_a_bytes'],profile_b_bytes=c['current_measurement']['cluster_b_bytes'])
 assert round(e['conservative_current_max']['total_gib'],3)==101.723 and round(e['one_gib_per_profile']['total_gib'],3)==100.641 and round(e['two_gib_per_profile']['total_gib'],3)==200.641
 assert set(P.SAFE_CACHE_DIRS).isdisjoint(P.PROTECTED_NAMES)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'Default/Cache').mkdir(parents=True);(root/'Default/IndexedDB').mkdir();(root/'Default/Local Storage').mkdir();(root/'Default/Cache/a').write_text('cache');(root/'Default/IndexedDB/auth').write_text('keep');(root/'Default/Local Storage/session').write_text('keep')
  targets=P.cleanup_candidates(root);assert targets==[root/'Default/Cache'];[__import__('shutil').rmtree(x) for x in targets]
  assert (root/'Default/IndexedDB/auth').read_text()=='keep' and (root/'Default/Local Storage/session').read_text()=='keep'

def test_fa312_measured_owner_ceiling_is_eight_not_profile_count():
 c=json.loads(C312.read_text());x=B.owner_ceiling(total_ram_bytes=c['measurement']['total_ram_bytes'],combined_two_owner_peak_mib=c['measurement']['accepted_live_reference']['combined_two_cluster_peak_mib'])
 assert x['raw_ram_owner_limit']==9 and x['active_browser_owner_ceiling']==8 and x['remaining_headroom_gib']>3.5
 assert c['capacity_policy']['current_production_owner_target']==2 and c['sharding']['profile_count_is_not_concurrency'] is True

def test_fa314_p95_storage_and_restore_integrity():
 c=json.loads(C314.read_text());x=S.scenario(c['measurement']['workspace_total_bytes']['p95']);assert round(x['daily_gib'],3)==46.609 and round(x['period_tib'],3)==1.365
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);src=root/'src';src.mkdir();po=src/'source.png';am=src/'master.png';rc=src/'rights.json';po.write_bytes(b'provider-original');am.write_bytes(b'active-master');rc.write_text('{}')
  m=A.build_manifest(provider_original=po,active_master=am,receipts=[rc]);archive=root/'archive';A.archive_files(m,{p.name:p for p in [po,am,rc]},archive);dest=root/'restore';out=A.restore(m,archive,dest);assert len(out)==3 and all(A.sha(p)==next(r['sha256'] for r in m['objects'] if r['name']==p.name) for p in out)

def test_fa310_contract_is_rollback_first_and_keeps_browser_ports_off_tunnel():
 c=json.loads(C310.read_text());assert c['rollback']['automatic_local_timer_seconds']==180 and c['target_sshd']['password_authentication']=='yes' and c['target_sshd']['permit_root_login']=='no';assert c['tunnel_boundary']['expose_browser_or_cdp_through_cloudflare'] is False
 s=(R/'company/factory-asset/bin/apply_fa310_ssh_hardening.sh').read_text();assert 'systemd-run' in s and 'systemctl reload ssh' in s and 'sshd -t' in s;assert c['recovery_topology']['provider_password_is_breakglass_path'] is True and c['recovery_topology']['management_access_must_not_depend_on_windows_mcp'] is True

def test_fa313_production_runtime_removes_hard_pinned_handoff_without_rewriting_blueprint():
 s=RUNTIME.read_text();assert "prod.get('engine') not in {'MUXIA/chatgpt-linux-a','MUXIA/governed-multi-cluster'}" in s
 assert "'provider_id':'AUTO'" in s and "'profile_selector':'governed-multi-cluster'" in s and "'scheduler_contract':'FA-306'" in s
 assert "prod.get('master_prompt'" not in s # runtime does not rewrite master prompt
 w=WRAP.read_text();assert 'production_multi_cluster_dispatch.mjs' in w and '--profile' not in w and 'chatgpt-linux-a' not in w

def test_fa313_dispatch_uses_fa306_scheduler_live_capacity_and_actual_lineage():
 s=DISPATCH.read_text();assert 'MultiClusterScheduler' in s and 'generateConsoleProviderImage' in s
 for token in ('provider_states','active_leases','cluster_selection_counts','provider_circuits','cluster_circuits','E_RECONCILIATION_REQUIRED','dispatch_committed','provider_id:r.provider_id','cluster_id:r.cluster_id'):assert token in s
 assert "prompt=String(prod.master_prompt||'').trim()" in s and 'prompt,' in s
 w=WORKER.read_text();
 for provider in ('qwen','chatgpt','gemini','manus','duckai'):assert provider in w
 assert 'button[aria-label="Send"]' in w and 'provider_leased_strategies.mjs' in w

def test_fa306_scheduler_regression_still_passes_without_provider_calls():
 cp=subprocess.run(['node',str(R/'company/factory-asset/bin/run_fa306_multi_cluster_scheduler_synthetic.mjs')],capture_output=True,text=True,check=True,timeout=60);d=json.loads(cp.stdout);assert d['result']=='PASS' and d['provider_calls_performed'] is False and d['browser_processes_spawned']==0
