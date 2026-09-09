from pathlib import Path
import json

R=Path(__file__).resolve().parents[3]
REG=R/'company/factory-asset/registries/web-ai-clusters.v1.json'
FIX=R/'company/factory-asset/fixtures/multi-cluster/FA-305-cluster-b-readiness.json'
GRAPH=R/'company/factory-asset/task-graph-v1.json'
UNIT=R/'company/factory-asset/systemd/die-muxia-cluster-b.service'
QC=R/'company/factory-asset/contracts/founder-qc-delivery.v1.json'
ORCH=R/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py'

def test_cluster_b_is_canonical_with_only_observed_healthy_subset_schedulable():
 g=json.loads(REG.read_text());by={x['cluster_id']:x for x in g['clusters']}
 assert set(by)=={'cluster-a','cluster-b'}
 b=by['cluster-b'];assert b['profile_id']=='web-ai-cluster-b' and b['max_tabs']==8 and b['lifecycle_state'] in {'ACTIVE','ACTIVE_ATTACH_ONLY'}
 p={x['provider_id']:x for x in b['providers']}
 assert {k for k,v in p.items() if v['membership']=='ACTIVE'}=={'chatgpt','qwen','gemini','manus','duckai'}
 assert p['chatgpt']['membership']=='ACTIVE' and p['chatgpt']['cluster_b_readiness']=='HEALTHY' and p['chatgpt']['cluster_b_readiness_reason']=='COMPOSER_READY'
 assert p['grok']['membership']=='DEFERRED_OPTIONAL'

def test_fa305_readiness_fixture_preserves_secret_and_authority_boundaries():
 d=json.loads(FIX.read_text());assert d['auth_handoff']['state']=='AUTH_HANDOFF_CLOSED'
 assert d['broker_acceptance']['state']=='READY' and d['broker_acceptance']['second_owner_rejected'] is True
 assert d['active_provider_subset']==['qwen','gemini','manus','duckai']
 assert d['credential_values_read'] is False and d['cookies_or_tokens_read'] is False
 assert d['provider_generation_calls_performed']==0 and d['spend_usd']==0
 assert d['submission_authorized'] is False and d['publication_authorized'] is False

def test_cluster_b_systemd_unit_is_attach_only_loopback_broker():
 s=UNIT.read_text();assert 'User=kopiko' in s and '--cluster-id cluster-b' in s and '--control-port 39122' in s
 assert 'Requires=die-muxia-cluster-b-browser.service' in s and '--attach-cdp-port 39222' in s
 assert '/usr/bin/xvfb-run' not in s and '--headless' not in s and '/srv/die/company/factory-asset/registries/web-ai-clusters.v1.json' in s
 assert 'Restart=on-failure' in s

def test_vector_track_is_future_only_and_dependency_ordered():
 g=json.loads(GRAPH.read_text());by={x['id']:x for x in g['tasks']}
 ids=[f'FA-V00{i}' for i in range(1,8)]
 assert by['FA-V001']['status']=='DEFERRED'
 assert 'future work' in by['FA-V001']['defer_reason'].lower()
 for prev,cur in zip(ids,ids[1:]):
  assert by[cur]['status']=='BLOCKED' and prev in by[cur]['depends_on']
 assert by['FA-V003']['authority']=='FOUNDER_REQUIRED_FOR_LIVE_PROVIDER_CALL'

def test_founder_qc_delivery_contract_matches_runtime_alias_policy():
 c=json.loads(QC.read_text());r=c['review_surface']
 assert r['file_mode_octal']=='0640' and r['required_group']=='die-runtime' and r['world_readable'] is False
 s=ORCH.read_text();assert 'def make_founder_readable' in s and 'path.chmod(0o640)' in s


def test_fa305_done_unlocks_or_accepts_fa306_and_receipt_records_live_systemd_acceptance():
 g=json.loads(GRAPH.read_text());by={x['id']:x for x in g['tasks']}
 assert by['FA-305']['status']=='DONE' and by['FA-306']['status'] in {'READY','DONE'}
 if by['FA-306']['status']=='DONE':
  r306=json.loads((R/'company/factory-asset/receipts/FA-306-multi-cluster-scheduler.receipt.json').read_text())
  assert r306['task_id']=='FA-306' and r306['status']=='DONE' and r306['result']=='PASS'
 r=json.loads((R/'company/factory-asset/receipts/FA-305-cluster-b-provisioning.receipt.json').read_text())
 assert r['full_fa305_acceptance'] is True and r['result']=='PASS'
 live=r['live_systemd_acceptance'];assert live['enabled'] is True and live['active'] is True and live['state']=='READY'
 assert live['owner_pid_changed_after_restart'] is True and live['second_owner_rejected'] is True and live['active_leases_after_restart']==0
 assert live['provider_generation_calls_performed']==0 and live['submission_authorized'] is False and live['publication_authorized'] is False
