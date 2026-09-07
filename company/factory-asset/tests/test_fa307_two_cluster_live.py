from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_fa307_contract_is_exactly_two_broker_owned_calls_and_closed_authority():
 c=json.loads(C.read_text());assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2;assert c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="qwen";assert c["clusters"]["cluster-b"]["provider_id"]=="manus";assert c["attempt_number"]==3;assert c["prior_attempts"][0]["result"]=="FAIL_OUTPUT_TIMEOUT_GEMINI";assert c["prior_attempts"][1]["result"]=="FAIL_PRE_DISPATCH_MANUS_PLUS_QWEN_TIMEOUT";assert c["authority"]["spend_usd"]==0;assert c["authority"]["submission_authorized"] is False;assert c["authority"]["publication_authorized"] is False

def test_fa307_selftest_passes_without_live_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS";assert all(d["assertions"].values())

def test_fa307_runner_uses_existing_brokers_not_new_profile_owner():
 s=R.read_text();assert "connectLeasedClusterTab" in s and "acquireClusterTab" in s and "generateFa121ProviderImage" in s;assert "Promise.all" in s;assert "PlaywrightChromiumDriver" not in s;assert "launchPersistentContext" not in s;assert "--user-data-dir" not in s

def test_fa307_prep_is_in_progress_with_founder_live_authorization():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};r=json.loads(REC.read_text());assert by["FA-121"]["status"]=="DONE" and by["FA-306"]["status"]=="DONE";assert by["FA-307"]["status"]=="IN_PROGRESS";assert r["status"]=="IN_PROGRESS" and r["founder_authorization"]["observed_in_session"] is True


def test_fa307_attempt1_failure_is_preserved_and_attempt2_is_fresh():
 prior=ROOT/"company/factory-asset/fixtures/multi-cluster/FA-307-attempt-1-qwen-gemini-result.json"
 d=json.loads(prior.read_text());assert d["result"]=="FAIL";assert d["attempts"]["qwen"]["status"]=="SUCCEEDED";assert d["attempts"]["gemini"]["status"]=="FAILED";assert d["attempts"]["gemini"]["dispatch_committed"] is True;assert "E_BOUNDED_COMPLETION_TIMEOUT" in d["attempts"]["gemini"]["failure_code"]
 r=json.loads(REC.read_text());assert r["founder_authorization"]["attempt_number"]==3;assert r["planned_jobs"][1]["provider_id"]=="manus";assert r["planned_jobs"][0]["job_id"].startswith("FA307-R3-") and r["planned_jobs"][1]["job_id"].startswith("FA307-R3-")

def test_attempt2_runner_uses_manus_response_byte_extraction_via_cluster_b_broker():
 s=R.read_text();assert "generateManus" in s and "manuscdn.com" in s and "provider_id:'manus'" in s;assert "FA307-R3-MANUS-B-20260907" in s;assert "FA307-R3-QWEN-A-20260907" in s


def test_attempt3_manus_readiness_uses_proven_bounded_editor_wait_before_dispatch():
 s=R.read_text();assert "initialReadiness" in s;assert "EDITOR_READY_AFTER_BOUNDED_WAIT" in s;assert "editorDeadline=Date.now()+20000" in s;assert "E_PRE_DISPATCH_READINESS_${initialReadiness.state}" in s
 dispatch=s.index("rec.dispatch_started_at=now()",s.index("async function generateManus"));editor=s.index("EDITOR_READY_AFTER_BOUNDED_WAIT",s.index("async function generateManus"));assert editor < dispatch


def test_attempt2_failure_is_preserved_without_retry_and_attempt3_is_fresh():
 p=ROOT/"company/factory-asset/fixtures/multi-cluster/FA-307-attempt-2-qwen-manus-result.json";d=json.loads(p.read_text())
 assert d["result"]=="FAIL";assert d["attempts"]["manus"]["dispatch_committed"] is False;assert d["attempts"]["manus"]["failure_code"]=="E_PRE_DISPATCH_READINESS_DEGRADED";assert d["attempts"]["qwen"]["dispatch_committed"] is True;assert d["attempts"]["qwen"]["failure_code"]=="PROVIDER_TIMEOUT";assert d["post_dispatch_retry_performed"] is False
 r=json.loads(REC.read_text());assert r["founder_authorization"]["attempt_number"]==3;assert all(x["job_id"].startswith("FA307-R3-") for x in r["planned_jobs"])
