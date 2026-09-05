from pathlib import Path
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parents[3]
PROFILES = R / 'company/factory-asset/registries/provider-readiness-profiles.v1.json'
CLUSTERS = R / 'company/factory-asset/registries/web-ai-clusters.v1.json'
CORE = R / 'company/browser/linux/provider_readiness.mjs'


def test_profiles_cover_active_cluster_members_without_grok():
    p = json.loads(PROFILES.read_text())['providers']
    c = json.loads(CLUSTERS.read_text())['clusters'][0]
    active = {x['provider_id'] for x in c['providers'] if x['membership'] == 'ACTIVE'}
    assert active == {'chatgpt', 'qwen', 'gemini', 'manus', 'duckai'}
    assert active <= set(p)
    assert 'grok' not in p
    for x in c['providers']:
        if x['provider_id'] in active:
            assert x['readiness_profile'] == x['provider_id']
            assert x['evidence']


def test_readiness_core_has_no_secret_or_storage_reads():
    s = CORE.read_text().lower()
    for bad in ('context.cookies', 'storagestate', 'localstorage', 'sessionstorage', 'indexeddb', 'document.cookie', 'authorization'):
        assert bad not in s
    assert 'safe_url' in s
    assert 'credential_values_read: false' in s
    assert 'cookies_or_tokens_read: false' in s


def test_safe_url_strips_query_and_fragment_and_states_are_provider_specific():
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / 'h.mjs'
        script = f'''
import {{ sanitizeProviderStatusUrl, classifyProviderPage }} from {json.dumps(CORE.as_uri())};
import fs from 'node:fs/promises';
const profiles=JSON.parse(await fs.readFile({json.dumps(str(PROFILES))},'utf8')).providers;
const mk=(url,visible=[],body='')=>({{
  url:()=>url,
  locator:(selector)=>({{
    count:async()=>selector==='body'?1:(visible.includes(selector)?1:0),
    nth:()=>({{isVisible:async()=>true}}),
    innerText:async()=>selector==='body'?body:''
  }})
}});
const healthy=await classifyProviderPage({{page:mk('https://chat.qwen.ai/chat/123?token=secret#frag',['textarea']),providerId:'qwen',profile:profiles.qwen,observedAt:'2026-09-05T00:00:00Z'}});
const auth=await classifyProviderPage({{page:mk('https://gemini.google.com/app',['a:has-text("Sign in")']),providerId:'gemini',profile:profiles.gemini,observedAt:'2026-09-05T00:00:00Z'}});
const cp=await classifyProviderPage({{page:mk('https://manus.im/app',[],'Verify you are human'),providerId:'manus',profile:profiles.manus,observedAt:'2026-09-05T00:00:00Z'}});
console.log(JSON.stringify({{safe:sanitizeProviderStatusUrl('https://chat.qwen.ai/chat/123?token=secret#frag'),healthy,auth,cp}}));
'''
        h.write_text(script)
        r = subprocess.run(['node', str(h)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip())
        assert v['safe'] == 'https://chat.qwen.ai/chat/123'
        assert v['healthy']['state'] == 'HEALTHY'
        assert v['healthy']['reason_code'] == 'COMPOSER_READY'
        assert v['auth']['state'] == 'AUTH_REQUIRED'
        assert v['cp']['state'] == 'CHECKPOINT'
        assert 'secret' not in json.dumps(v)


def test_cluster_aggregation_keeps_siblings_alive():
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / 'h.mjs'
        h.write_text(f'''import {{aggregateClusterReadiness}} from {json.dumps(CORE.as_uri())};\nconst a=aggregateClusterReadiness([{{membership:'ACTIVE',state:'HEALTHY'}},{{membership:'ACTIVE',state:'CHECKPOINT'}},{{membership:'ACTIVE',state:'HEALTHY'}}]);\nconst b=aggregateClusterReadiness([{{membership:'ACTIVE',state:'HEALTHY'}},{{membership:'ACTIVE',state:'HEALTHY'}}]);\nconsole.log(JSON.stringify({{a,b}}));\n''')
        r = subprocess.run(['node', str(h)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip())
        assert v == {'a': 'DEGRADED', 'b': 'HEALTHY'}