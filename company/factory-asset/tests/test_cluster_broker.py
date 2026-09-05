from pathlib import Path
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parents[3]
CORE = R / 'company/browser/linux/cluster_broker_core.mjs'
CLIENT = R / 'company/browser/linux/cluster_broker_client.mjs'
LAUNCHER = R / 'company/muxia/scripts/linux/muxia-cluster-broker.mjs'


def test_worker_client_attaches_only_and_never_owns_profile():
    s = CLIENT.read_text().lower()
    assert 'connectovercdp' in s
    for bad in ('spawn(', '--user-data-dir', 'launchpersistentcontext', '.launch('):
        assert bad not in s


def test_broker_is_loopback_single_owner_and_max_eight():
    s = CORE.read_text()
    assert "controlHost !== '127.0.0.1'" in s
    assert 'E_CLUSTER_BROKER_ALREADY_OWNED' in s
    assert 'maxTabs > 8' in s
    assert 'driver.launch(this.profileDir)' in s
    assert 'credential_values_read: false' in s
    assert 'cookies_or_tokens_read: false' in s


def test_launcher_resolves_profile_from_registry_not_provider():
    s = LAUNCHER.read_text()
    assert 'registry.clusters.find' in s
    assert 'profileDir: cluster.profile_dir' in s
    assert "controlHost: '127.0.0.1'" in s
    assert 'chatgpt.com' not in s.lower()
    assert 'qwen.ai' not in s.lower()


def test_fake_driver_lifecycle_attach_and_exclusive_lock():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        harness = td / 'h.mjs'
        core_uri = CORE.as_uri()
        root = str(td).replace('\\', '/')
        script = f'''
import fs from "node:fs";
import {{ ClusterBrokerCore }} from {json.dumps(core_uri)};
const root={json.dumps(root)};
const fake={{launchCalls:0,stopCalls:0,async launch(profile){{this.launchCalls++;return {{pid:4242,userDataDir:profile,debugHost:"127.0.0.1",debugPort:39421,debugUrl:"http://127.0.0.1:39421",browser:{{}}}};}},async stop(){{this.stopCalls++;}}}};
const cfg={{clusterId:"fixture",profileId:"fixture-profile",profileDir:root+"/profile",stateFile:root+"/state.json",lockFile:root+"/broker.lock",driver:fake,maxTabs:8}};
const b=new ClusterBrokerCore(cfg);
const st=await b.start();
const attach=await (await fetch(`http://127.0.0.1:${{st.control_port}}/v1/attach`)).json();
let secondError="";
try {{ const fake2={{...fake}}; const b2=new ClusterBrokerCore({{...cfg,driver:fake2}}); await b2.start(); }} catch(e) {{ secondError=String(e.message||e); }}
await b.stop();
console.log(JSON.stringify({{launchCalls:fake.launchCalls,stopCalls:fake.stopCalls,attach,secondError,lockExists:fs.existsSync(cfg.lockFile),state:JSON.parse(fs.readFileSync(cfg.stateFile,"utf8"))}}));
'''
        harness.write_text(script)
        r = subprocess.run(['node', str(harness)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        assert v['launchCalls'] == 1 and v['stopCalls'] == 1
        assert v['attach']['schema'] == 'die.muxia.cluster-broker-attach.v1'
        assert v['attach']['debug_host'] == '127.0.0.1'
        assert 'profile_dir' not in v['attach']
        assert v['attach']['credential_values_read'] is False
        assert 'E_CLUSTER_BROKER_ALREADY_OWNED' in v['secondError']
        assert v['lockExists'] is False
        assert v['state']['state'] == 'OFFLINE'