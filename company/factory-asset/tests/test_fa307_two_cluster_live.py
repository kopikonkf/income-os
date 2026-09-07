from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_fa307_contract_is_exactly_two_broker_owned_calls_and_closed_authority():
 c=json.loads(C.read_text());assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2;assert c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="qwen";assert c["clusters"]["cluster-b"]["provider_id"]=="gemini";assert c["authority"]["spend_usd"]==0;assert c["authority"]["submission_authorized"] is False;assert c["authority"]["publication_authorized"] is False

def test_fa307_selftest_passes_without_live_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS";assert all(d["assertions"].values())

def test_fa307_runner_uses_existing_brokers_not_new_profile_owner():
 s=R.read_text();assert "connectLeasedClusterTab" in s and "acquireClusterTab" in s and "generateFa121ProviderImage" in s;assert "Promise.all" in s;assert "PlaywrightChromiumDriver" not in s;assert "launchPersistentContext" not in s;assert "--user-data-dir" not in s

def test_fa307_prep_is_in_progress_with_founder_live_authorization():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};r=json.loads(REC.read_text());assert by["FA-121"]["status"]=="DONE" and by["FA-306"]["status"]=="DONE";assert by["FA-307"]["status"]=="IN_PROGRESS";assert r["status"]=="IN_PROGRESS" and r["founder_authorization"]["observed_in_session"] is True
