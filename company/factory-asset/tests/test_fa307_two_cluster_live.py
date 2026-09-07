from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_attempt9_contract_exact_two_qwen_a_gemini_b_calls():
 c=json.loads(C.read_text());assert c["attempt_number"]==9;assert c["authority"]["authorized_provider_calls"]==2 and c["limits"]["max_provider_calls"]==2 and c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="qwen" and c["clusters"]["cluster-b"]["provider_id"]=="gemini"

def test_selftest_passes_without_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS" and all(d["assertions"].values())

def test_attempt9_network_capture_is_post_dispatch_and_gated_by_download_control():
 s=R.read_text();start=s.index("async function generateGemini");listener=s.index("page.on('response'",start);guard=s.index("if(!dispatchCommitted)return",listener);commit=s.index("dispatchCommitted=true",start);network_select=s.index("if(networkImages.length)",commit);control=s.index("if(!control)throw new Error('E_BOUNDED_COMPLETION_TIMEOUT')",commit);assert listener<guard<commit<control<network_select;assert "raw.length<100000" in s and "provider_generated_image_response_body_after_dispatch" in s

def test_attempt9_runner_is_fresh_broker_owned_parallel():
 s=R.read_text();assert "FA307-R9-QWEN-A-20260907" in s and "FA307-R9-GEMINI-B-20260907" in s;assert "generateFa121ProviderImage" in s and "Promise.all" in s;assert "PlaywrightChromiumDriver" not in s and "--user-data-dir" not in s

def test_attempt8_failure_preserved_no_retry():
 d=json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster/FA-307-attempt-8-qwen-gemini-result.json").read_text());assert d["result"]=="FAIL" and d["attempts"]["qwen"]["status"]=="SUCCEEDED";assert d["attempts"]["gemini"]["status"]=="FAILED" and d["post_dispatch_retry_performed"] is False

def test_attempts_1_to_8_preserved_fail_closed():
 names=["FA-307-attempt-1-qwen-gemini-result.json","FA-307-attempt-2-qwen-manus-result.json","FA-307-attempt-3-qwen-manus-result.json","FA-307-attempt-4-duck-manus-result.json","FA-307-attempt-5-gemini-manus-result.json","FA-307-attempt-6-gemini-manus-result.json","FA-307-attempt-7-qwen-gemini-result.json","FA-307-attempt-8-qwen-gemini-result.json"];ds=[json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster"/n).read_text()) for n in names];assert all(d["result"]=="FAIL" for d in ds) and all(d["post_dispatch_retry_performed"] is False for d in ds);assert ds[3]["human_challenge_bypassed"] is False

def test_current_attempt9_plan_authorized():
 r=json.loads(REC.read_text());g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};assert by["FA-307"]["status"]=="IN_PROGRESS" and r["founder_authorization"]["attempt_number"]==9;assert all(x["job_id"].startswith("FA307-R9-") for x in r["planned_jobs"])
