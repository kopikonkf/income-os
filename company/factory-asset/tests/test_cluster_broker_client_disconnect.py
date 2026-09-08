from pathlib import Path
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "company/browser/linux/cluster_broker_client.mjs"


def test_cdp_client_disconnect_closes_transport_not_broker_browser():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        fake = td / "fake-playwright.mjs"
        fake.write_text(
            """
export const state={connectionClose:0,browserClose:0};
const browser={
  _connection:{close(){state.connectionClose+=1;}},
  async close(){state.browserClose+=1;},
};
export const chromium={async connectOverCDP(){return browser;}};
""",
            encoding="utf-8",
        )
        harness = td / "h.mjs"
        harness.write_text(
            f"""
import http from 'node:http';
import {{ connectClusterBrowser }} from {json.dumps(CLIENT.as_uri())};
import {{ state }} from {json.dumps(fake.as_uri())};
const server=http.createServer((req,res)=>{{
  res.statusCode=200;res.setHeader('content-type','application/json');
  res.end(JSON.stringify({{
    schema:'die.muxia.cluster-broker-attach.v1',cluster_id:'fixture',profile_id:'fixture-profile',
    debug_host:'127.0.0.1',debug_port:49999,debug_url:'http://127.0.0.1:49999',browser_owner_pid:4242,
    max_tabs:8,broker_state:'READY',credential_values_read:false,cookies_or_tokens_read:false
  }}));
}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const port=server.address().port;
const connected=await connectClusterBrowser({{controlBaseUrl:`http://127.0.0.1:${{port}}/`,playwrightEntry:{json.dumps(str(fake))},timeoutMs:3000}});
await connected.disconnect();
await connected.disconnect();
await new Promise(r=>server.close(r));
console.log(JSON.stringify(state));
""",
            encoding="utf-8",
        )
        result = subprocess.run(["node", str(harness)], capture_output=True, text=True, check=True, timeout=30)
        value = json.loads(result.stdout.strip())
        assert value == {"connectionClose": 1, "browserClose": 0}


def test_client_source_never_browser_closes_broker_owned_cdp_session():
    text = CLIENT.read_text(encoding="utf-8")
    assert "browser?._connection" in text
    assert "connection.close()" in text
    assert "browser.close({ reason: 'DIE_CDP_CLIENT_DISCONNECT' })" not in text
    assert "E_CLUSTER_BROKER_CDP_CLIENT_DISCONNECT_UNSUPPORTED" in text
