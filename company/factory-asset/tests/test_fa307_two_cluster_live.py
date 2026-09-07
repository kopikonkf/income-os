from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_attempt5_contract_exact_two_gemini_manus_calls_closed_authority():
 c=json.loads(C.read_text());assert c["attempt_number"]==5;assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2 and c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="gemini" and c["clusters"]["cluster-b"]["provider_id"]=="manus";assert c["authority"]["spend_usd"]==0 and c["authority"]["submission_authorized"] is False and c["authority"]["publication_authorized"] is False

def test_selftest_passes_without_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS" and all(d["assertions"].values())

def test_runner_is_broker_owned_parallel_gemini_manus():
 s=R.read_text();assert "connectLeasedClusterTab" in s and "acquireClusterTab" in s and "Promise.all" in s;assert "generateGemini" in s and "generateManus" in s;assert "PlaywrightChromiumDriver" not in s and "launchPersistentContext" not in s and "--user-data-dir" not in s

def test_gemini_uses_fa114_download_control_original_bytes_and_manus_response_bytes():
 s=R.read_text();assert "provider_browser_download_event" in s and "provider_download_href_browser_context" in s and "gemini.google.com/app" in s;assert "manuscdn.com" in s and "EDITOR_READY_AFTER_BOUNDED_WAIT" in s

def test_current_plan_is_fresh_attempt5_and_founder_authorized():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};r=json.loads(REC.read_text());assert by["FA-307"]["status"]=="IN_PROGRESS";assert r["founder_authorization"]["attempt_number"]==5;assert [x["provider_id"] for x in r["planned_jobs"]]==["gemini","manus"];assert all(x["job_id"].startswith("FA307-R5-") for x in r["planned_jobs"]);assert r["preflight_selection"]["gemini_cluster_a"]=="HEALTHY_COMPOSER_READY"

def test_attempts_1_to_4_are_terminal_preserved_no_post_dispatch_retry_or_challenge_bypass():
 names=["FA-307-attempt-1-qwen-gemini-result.json","FA-307-attempt-2-qwen-manus-result.json","FA-307-attempt-3-qwen-manus-result.json","FA-307-attempt-4-duck-manus-result.json"];ds=[json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster"/n).read_text()) for n in names];assert all(d["result"]=="FAIL" for d in ds);assert all(d["post_dispatch_retry_performed"] is False for d in ds);assert ds[3]["human_challenge_bypassed"] is False and ds[3]["attempts"]["duckai"]["failure_code"]=="E_HUMAN_CHALLENGE_REQUIRED";assert ds[2]["attempts"]["manus"]["status"]=="SUCCEEDED" and ds[3]["attempts"]["manus"]["status"]=="SUCCEEDED"

def test_both_dispatches_are_after_provider_specific_preflight():
 s=R.read_text();g=s.index("rec.dispatch_started_at=now()",s.index("async function generateGemini"));gr=s.index("readiness.state!=='HEALTHY'",s.index("async function generateGemini"));m=s.index("rec.dispatch_started_at=now()",s.index("async function generateManus"));mr=s.index("EDITOR_READY_AFTER_BOUNDED_WAIT",s.index("async function generateManus"));assert gr<g and mr<m
