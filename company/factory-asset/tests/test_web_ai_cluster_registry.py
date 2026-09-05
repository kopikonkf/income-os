import json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
REG=R/'company/factory-asset/registries/web-ai-clusters.v1.json'

def load(): return json.loads(REG.read_text())

def test_cluster_a_identity_and_single_owner_contract():
 g=load(); c=g['clusters'][0]
 assert c['cluster_id']=='cluster-a'
 assert c['profile_id']=='chatgpt-linux-a'
 assert c['profile_dir']=='/var/lib/muxia/profiles/chatgpt-linux-a/browser'
 assert c['runtime_owner']=='MUXIA'
 assert c['browser_owner_model']=='SINGLE_LONG_LIVED_CHROMIUM_PROCESS'
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
 assert 'VISIBLE_NO_CDP' in r['auth_handoff']
 assert 'BEFORE_BROKER_START' in r['auth_handoff']

def test_failure_isolation_and_lifecycle_states():
 g=load(); assert 'TAB_OR_PROVIDER_FAILURE_MUST_NOT_FAIL_HEALTHY_SIBLING_PROVIDERS'==g['rules']['provider_failure_isolation']
 assert 'DRAINING' in g['health_states']['cluster']
 assert 'CHECKPOINT' in g['health_states']['provider']
 assert 'IN_FLIGHT' in g['health_states']['tab']
