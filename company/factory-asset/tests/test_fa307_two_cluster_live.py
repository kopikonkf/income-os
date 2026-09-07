from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_attempt6_contract_is_exact_two_gemini_manus_calls():
 c=json.loads(C.read_text());assert c["attempt_number"]==6;assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2 and c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="gemini" and c["clusters"]["cluster-b"]["provider_id"]=="manus";assert c["authority"]["spend_usd"]==0 and c["authority"]["submission_authorized"] is False

def test_selftest_passes_without_live_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS" and all(d["assertions"].values())

def test_attempt6_runner_is_broker_owned_parallel_and_fresh():
 s=R.read_text();assert "connectLeasedClusterTab" in s and "acquireClusterTab" in s and "Promise.all" in s;assert "FA307-R6-GEMINI-A-20260907" in s and "FA307-R6-MANUS-B-20260907" in s;assert "PlaywrightChromiumDriver" not in s and "--user-data-dir" not in s

def test_gemini_hardening_uses_predispatch_image_baseline_and_dom_bytes_before_download_fallback():
 s=R.read_text();start=s.index("async function generateGemini");base=s.index("baselineImages",start);dispatch=s.index("rec.dispatch_started_at=now()",start);control=s.index("if(!control)throw new Error('E_BOUNDED_COMPLETION_TIMEOUT')",start);fresh=s.index("fresh-generated-dom-after-download-control",start);fallback=s.index("acquireDownloadBytes(page,context,control)",fresh);assert base<dispatch<control<fresh<fallback;assert "w>=512&&x.h>=512" in s or "x.w>=512&&x.h>=512" in s

def test_attempt5_failure_is_preserved_as_extractor_race_not_provider_retry():
 d=json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster/FA-307-attempt-5-gemini-manus-result.json").read_text());assert d["result"]=="FAIL";assert d["attempts"]["gemini"]["dispatch_committed"] is True;assert "E_DOWNLOAD_FAILED" in d["attempts"]["gemini"]["failure_code"] and "ENOENT" in d["attempts"]["gemini"]["failure_code"];assert d["attempts"]["manus"]["status"]=="SUCCEEDED";assert d["post_dispatch_retry_performed"] is False

def test_attempts_1_to_5_are_preserved_and_no_duck_challenge_bypass():
 names=["FA-307-attempt-1-qwen-gemini-result.json","FA-307-attempt-2-qwen-manus-result.json","FA-307-attempt-3-qwen-manus-result.json","FA-307-attempt-4-duck-manus-result.json","FA-307-attempt-5-gemini-manus-result.json"];ds=[json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster"/n).read_text()) for n in names];assert all(d["result"]=="FAIL" for d in ds) and all(d["post_dispatch_retry_performed"] is False for d in ds);assert ds[3]["human_challenge_bypassed"] is False

def test_current_attempt6_plan_is_authorized_and_fresh():
 r=json.loads(REC.read_text());g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};assert by["FA-307"]["status"]=="IN_PROGRESS" and r["founder_authorization"]["attempt_number"]==6;assert [x["provider_id"] for x in r["planned_jobs"]]==["gemini","manus"] and all(x["job_id"].startswith("FA307-R6-") for x in r["planned_jobs"])
