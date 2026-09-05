from pathlib import Path
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parents[3]
LEASES = R / 'company/browser/linux/cluster_tab_leases.mjs'
CLIENT = R / 'company/browser/linux/cluster_broker_client.mjs'
CORE = R / 'company/browser/linux/cluster_broker_core.mjs'


def test_lease_manager_enforces_max_eight_and_provider_limit():
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / 'h.mjs'
        script = f'''
import {{ ClusterTabLeaseManager }} from {json.dumps(LEASES.as_uri())};
class P {{ constructor(){{this.u="about:blank";this.closed=false;}} url(){{return this.u;}} isClosed(){{return this.closed;}} async goto(u){{this.u=u;}} async close(){{this.closed=true;}} }}
class C {{ constructor(){{this.ps=[new P()]}} pages(){{return this.ps.filter(p=>!p.closed)}} async newPage(){{const p=new P();this.ps.push(p);return p;}} }}
const c=new C(); const m=new ClusterTabLeaseManager({{context:c,maxTabs:8,defaultProviderLimit:1,defaultTtlMs:60000}});
const first=await m.acquire({{providerId:"p1",jobId:"j1"}});
let dup=""; try{{await m.acquire({{providerId:"p1",jobId:"j2"}})}}catch(e){{dup=String(e.message)}}
for(let i=2;i<=8;i++) await m.acquire({{providerId:`p${{i}}`,jobId:`j${{i}}`}});
let ninth=""; try{{await m.acquire({{providerId:"p9",jobId:"j9"}})}}catch(e){{ninth=String(e.message)}}
console.log(JSON.stringify({{active:m.snapshot().active_leases,open:m.snapshot().open_pages,dup,ninth,first}}));
'''
        h.write_text(script)
        r = subprocess.run(['node', str(h)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        assert v['active'] == 8 and v['open'] == 8
        assert 'E_PROVIDER_TAB_CAPACITY:p1' in v['dup']
        assert 'E_CLUSTER_TAB_CAPACITY' in v['ninth']
        assert v['first']['claim_url'].startswith('about:blank#die-lease=')


def test_provider_checkpoint_isolated_from_sibling_and_release_reuses_capacity():
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / 'h.mjs'
        script = f'''
import {{ ClusterTabLeaseManager }} from {json.dumps(LEASES.as_uri())};
class P {{ constructor(){{this.u="about:blank";this.closed=false;}} url(){{return this.u;}} isClosed(){{return this.closed;}} async goto(u){{this.u=u;}} async close(){{this.closed=true;}} }}
class C {{ constructor(){{this.ps=[new P()]}} pages(){{return this.ps.filter(p=>!p.closed)}} async newPage(){{const p=new P();this.ps.push(p);return p;}} }}
const c=new C(); const m=new ClusterTabLeaseManager({{context:c,maxTabs:8,providerLimits:{{chatgpt:1,qwen:1}},defaultProviderLimit:1}});
m.setProviderState("chatgpt","CHECKPOINT");
let blocked="";try{{await m.acquire({{providerId:"chatgpt",jobId:"cg1"}})}}catch(e){{blocked=String(e.message)}}
const q=await m.acquire({{providerId:"qwen",jobId:"q1"}});
const rel=await m.release(q.lease_id,"DONE");
const q2=await m.acquire({{providerId:"qwen",jobId:"q2"}});
console.log(JSON.stringify({{blocked,q:q.job_id,rel,q2:q2.job_id,snapshot:m.snapshot()}}));
'''
        h.write_text(script)
        r = subprocess.run(['node', str(h)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        assert 'E_PROVIDER_NOT_SCHEDULABLE:chatgpt:CHECKPOINT' in v['blocked']
        assert v['q'] == 'q1' and v['q2'] == 'q2' and v['rel']['released'] is True
        assert v['snapshot']['active_leases'] == 1


def test_expired_lease_is_reclaimed_and_page_closed():
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / 'h.mjs'
        script = f'''
import {{ ClusterTabLeaseManager }} from {json.dumps(LEASES.as_uri())};
let now=1000;
class P {{ constructor(){{this.u="about:blank";this.closed=false;}} url(){{return this.u;}} isClosed(){{return this.closed;}} async goto(u){{this.u=u;}} async close(){{this.closed=true;}} }}
class C {{ constructor(){{this.ps=[new P()]}} pages(){{return this.ps.filter(p=>!p.closed)}} async newPage(){{const p=new P();this.ps.push(p);return p;}} }}
const c=new C(); const m=new ClusterTabLeaseManager({{context:c,maxTabs:8,defaultProviderLimit:1,defaultTtlMs:1000,now:()=>now}});
const l=await m.acquire({{providerId:"gemini",jobId:"g1",ttlMs:1000}}); now=3000; const rec=await m.reclaimExpired();
console.log(JSON.stringify({{rec,s:m.snapshot(),allPages:c.ps.map(p=>({{closed:p.closed,url:p.url()}}))}}));
'''
        h.write_text(script)
        r = subprocess.run(['node', str(h)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        assert len(v['rec']) == 1 and v['rec'][0]['reason'] == 'TTL_EXPIRED'
        assert v['s']['active_leases'] == 0 and v['s']['open_pages'] == 0
        assert v['allPages'][0]['closed'] is True


def test_client_and_broker_expose_lease_api_without_profile_launch():
    cs = CLIENT.read_text().lower()
    bs = CORE.read_text()
    assert 'acquireclustertab' in cs and 'connectleasedclustertab' in cs
    for bad in ('spawn(', '--user-data-dir', 'launchpersistentcontext'):
        assert bad not in cs
    assert '/v1/leases/acquire' in bs
    assert '/v1/leases/reclaim' in bs
    assert 'setProviderState' in bs
    assert 'providers' in bs and 'state' in bs
