import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REG=R/'company/factory-asset/registries/web-ai-clusters.v1.json'


def load(): return json.loads(REG.read_text())


def test_cluster_a_identity_and_job_scoped_owner_contract():
 g=load(); c=g['clusters'][0]
 assert c['cluster_id']=='cluster-a'
 assert c['profile_id']=='chatgpt-linux-a'
 assert c['profile_dir']=='/var/lib/muxia/profiles/chatgpt-linux-a/browser'
 assert c['runtime_owner']=='FA338_JOB_SCOPED_MUXIA_BROKER_BROWSER_RUNTIME'
 assert c['browser_owner_model']=='JOB_SCOPED_HEADFUL_BROWSER_CDP'
 assert c['lifecycle_state']=='COLD_WHEN_IDLE'
 assert c['max_tabs']==8


def test_active_provider_membership_and_qwen_transport_preference():
 c=load()['clusters'][0]; by={p['provider_id']:p for p in c['providers']}
 assert {k for k,v in by.items() if v['membership']=='ACTIVE'}=={'chatgpt','qwen','gemini','manus','duckai'}
 assert by['qwen']['preferred_transport']=='SESSION_API'
 assert by['qwen']['browser_fallback']=='BROWSER_CDP'
 assert by['grok']['membership']=='DEFERRED_OPTIONAL'


def test_secret_and_auth_handoff_boundaries():
 g=load(); r=g['rules']
 assert r['profile_secret_copy_allowed'] is False
 assert r['credential_cookie_token_export_allowed'] is False
 assert 'FOUNDER' in r['auth_handoff'] and 'CDP OFF' in r['auth_handoff']
 assert 'SAME PERSISTENT PROFILE' in r['auth_handoff']
 assert 'LOOPBACK' in r['browser_lifecycle_policy'] or 'CDP' in r['browser_lifecycle_policy']


def test_failure_isolation_and_lifecycle_states():
 g=load(); assert 'TAB_OR_PROVIDER_FAILURE_MUST_NOT_FAIL_HEALTHY_SIBLING_PROVIDERS'==g['rules']['provider_failure_isolation']
 assert 'DRAINING' in g['health_states']['cluster']
 assert 'CHECKPOINT' in g['health_states']['provider']
 assert 'IN_FLIGHT' in g['health_states']['tab']
 assert 'COLD -> SPAWN_HEADFUL -> WORK -> DURABLE_TERMINAL -> CLOSE -> COLD' in g['rules']['browser_lifecycle_policy']


def test_cluster_a_initial_browser_concurrency_policy_is_preserved_inside_job_runtime():
 c=load()['clusters'][0]
 assert c['max_tabs']==8
 assert c['max_active_browser_generations']==5
 assert c['reserved_recovery_tabs']==3
 assert c['lease_default_ttl_seconds']==300
 assert c['provider_tab_limits']=={'chatgpt':1,'qwen':1,'gemini':1,'manus':1,'duckai':1,'claude':1}


def test_claude_is_registered_preauth_but_not_active():
 g=load()
 for c in g['clusters']:
  by={p['provider_id']:p for p in c['providers']}
  assert by['claude']['membership']=='AUTH_REQUIRED'
  assert by['claude']['preferred_transport']=='BROWSER_CDP'
  assert by['claude']['readiness_profile']=='claude'
  assert c['provider_tab_limits']['claude']==1
