from pathlib import Path
import json
import subprocess
import tempfile

R = Path(__file__).resolve().parents[3]
CORE = R / 'company/browser/linux/cluster_broker_core.mjs'
LAUNCHER = R / 'company/muxia/scripts/linux/muxia-cluster-broker.mjs'
REGISTRY = R / 'company/factory-asset/registries/web-ai-clusters.v1.json'


def test_owner_disconnect_marks_owner_failed_and_blocks_attach():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        harness = td / 'owner-failure.mjs'
        root = str(td).replace('\\', '/')
        script = f'''
import fs from "node:fs";
import {{ EventEmitter }} from "node:events";
import {{ ClusterBrokerCore }} from {json.dumps(CORE.as_uri())};
const root={json.dumps(root)};
const browser=new EventEmitter();
browser.connected=true;
browser.isConnected=()=>browser.connected;
const fake={{
  stopCalls:0,
  async launch(profile){{return {{pid:process.pid,userDataDir:profile,debugHost:"127.0.0.1",debugPort:39422,debugUrl:"http://127.0.0.1:39422",browser}};}},
  async stop(){{this.stopCalls++;}}
}};
const b=new ClusterBrokerCore({{clusterId:"fixture-owner",profileId:"fixture-profile",profileDir:root+"/profile",stateFile:root+"/state.json",lockFile:root+"/broker.lock",driver:fake,maxTabs:8,ownerHealthIntervalMs:100}});
const started=await b.start();
browser.connected=false;
browser.emit('disconnected');
const failure=await Promise.race([b.waitForOwnerFailure(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('OWNER_FAILURE_TIMEOUT')),1500))]);
let attachError='';try{{b.attachDescriptor();}}catch(e){{attachError=String(e.message||e);}}
const failedStatus=b.status();
await b.stop({{finalState:'OWNER_FAILED',reason:failure.reason}});
const persisted=JSON.parse(fs.readFileSync(root+"/state.json","utf8"));
console.log(JSON.stringify({{started:started.state,failure,failedStatus,attachError,persisted,stopCalls:fake.stopCalls}}));
'''
        harness.write_text(script, encoding='utf-8')
        r = subprocess.run(['node', str(harness)], capture_output=True, text=True, check=True, timeout=30)
        v = json.loads(r.stdout.strip().splitlines()[-1])
        assert v['started'] == 'READY'
        assert v['failure']['kind'] == 'OWNER_FAILED'
        assert v['failure']['reason'] == 'OWNER_BROWSER_DISCONNECTED'
        assert v['failedStatus']['state'] == 'OWNER_FAILED'
        assert 'E_CLUSTER_BROKER_NOT_READY:OWNER_FAILED' in v['attachError']
        assert v['persisted']['state'] == 'OWNER_FAILED'
        assert v['persisted']['stop_reason'] == 'OWNER_BROWSER_DISCONNECTED'
        assert v['stopCalls'] == 1


def test_launcher_restarts_on_owner_failure_and_registry_is_headful_by_default():
    launcher = LAUNCHER.read_text(encoding='utf-8')
    assert 'Promise.race([signal, broker.waitForOwnerFailure()])' in launcher
    assert "finalState: 'OWNER_FAILED'" in launcher
    assert 'E_CLUSTER_BROKER_OWNER_FAILED' in launcher
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    rules = registry['rules']
    assert rules['production_browser_mode_policy'].startswith('HEADFUL_OR_VIRTUAL_DISPLAY_DEFAULT')
    assert 'HEADLESS_REQUIRES_PROVIDER_SPECIFIC_ACCEPTANCE' in rules['production_browser_mode_policy']
    assert 'VISIBLE_BROWSER_WITH_CDP_OFF' in rules['interactive_auth_policy']
    assert rules['checkpoint_policy'].startswith('DO_NOT_BYPASS_PROVIDER_CHALLENGES')
    assert 'OWNER_DEATH_MUST_FAIL_CLOSED' in rules['owner_health_policy']


def test_headed_owner_lifecycle_receipt_is_done_pass():
    receipt = json.loads((R / 'company/factory-asset/receipts/FA-HOTFIX-cluster-headed-owner-lifecycle.receipt.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'DONE' and receipt['result'] == 'PASS'
    assert receipt['acceptance']['same_owner_across_chatgpt_and_qwen'] is True
    assert receipt['acceptance']['active_leases_after_sequence'] == 0
    assert receipt['acceptance']['open_pages_after_sequence'] == 1
    assert receipt['permanent_protocol']['production_browser_mode'] == 'HEADFUL_OR_VIRTUAL_DISPLAY_DEFAULT'
    assert receipt['authority_and_safety']['provider_generation_calls_performed'] == 0
    assert receipt['authority_and_safety']['checkpoint_or_captcha_bypass'] is False
