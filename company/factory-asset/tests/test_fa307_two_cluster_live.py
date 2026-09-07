from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_attempt8_contract_exact_two_qwen_a_gemini_b_calls():
 c=json.loads(C.read_text());assert c["attempt_number"]==8;assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2 and c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="qwen" and c["clusters"]["cluster-b"]["provider_id"]=="gemini"

def test_selftest_passes_without_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS" and all(d["assertions"].values())

def test_attempt8_runner_fresh_parallel_and_broker_owned():
 s=R.read_text();assert "FA307-R8-QWEN-A-20260907" in s and "FA307-R8-GEMINI-B-20260907" in s;assert "generateFa121ProviderImage" in s and "generateGemini" in s and "Promise.all" in s;assert "PlaywrightChromiumDriver" not in s and "--user-data-dir" not in s

def test_gemini_download_stream_precedes_temp_file_fallbacks():
 s=R.read_text();start=s.index("async function acquireDownloadBytes");stream=s.index("createReadStream",start);path=s.index("d.path()",stream);save=s.index("d.saveAs",path);href=s.index("context.request.get(href",save);assert stream<path<save<href;assert "provider_browser_download_stream" in s

def test_attempt7_failure_preserved_and_qwen_success_proven():
 d=json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster/FA-307-attempt-7-qwen-gemini-result.json").read_text());assert d["result"]=="FAIL";assert d["attempts"]["qwen"]["status"]=="SUCCEEDED" and d["attempts"]["qwen"]["artifact"]["sha256"]=="017ef1229139c1a342cc6c0b797693fcbbe56235cf3d1221cc95900e5027c96f";assert "E_DOWNLOAD_FAILED" in d["attempts"]["gemini"]["failure_code"] and d["post_dispatch_retry_performed"] is False

def test_attempts_1_to_7_preserved_fail_closed():
 names=["FA-307-attempt-1-qwen-gemini-result.json","FA-307-attempt-2-qwen-manus-result.json","FA-307-attempt-3-qwen-manus-result.json","FA-307-attempt-4-duck-manus-result.json","FA-307-attempt-5-gemini-manus-result.json","FA-307-attempt-6-gemini-manus-result.json","FA-307-attempt-7-qwen-gemini-result.json"];ds=[json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster"/n).read_text()) for n in names];assert all(d["result"]=="FAIL" for d in ds) and all(d["post_dispatch_retry_performed"] is False for d in ds);assert ds[3]["human_challenge_bypassed"] is False

def test_current_attempt8_plan_authorized():
 r=json.loads(REC.read_text());g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};assert by["FA-307"]["status"]=="IN_PROGRESS" and r["founder_authorization"]["attempt_number"]==8;assert [x["provider_id"] for x in r["planned_jobs"]]==["qwen","gemini"] and all(x["job_id"].startswith("FA307-R8-") for x in r["planned_jobs"])
