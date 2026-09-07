from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/"company/factory-asset/contracts/fa307-two-cluster-live.v1.json"
R=ROOT/"company/factory-asset/bin/run_fa307_two_cluster_live.mjs"
G=ROOT/"company/factory-asset/task-graph-v1.json"
REC=ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json"

def test_fa307_attempt4_contract_is_exact_two_closed_authority_calls():
 c=json.loads(C.read_text());assert c["attempt_number"]==4;assert c["authority"]["authorized_provider_calls"]==2;assert c["limits"]["max_provider_calls"]==2 and c["limits"]["max_pre_dispatch_retries"]==0;assert c["clusters"]["cluster-a"]["provider_id"]=="duckai";assert c["clusters"]["cluster-b"]["provider_id"]=="manus";assert c["authority"]["spend_usd"]==0 and c["authority"]["submission_authorized"] is False and c["authority"]["publication_authorized"] is False

def test_fa307_selftest_passes_without_live_provider_calls():
 r=subprocess.run(["node",str(R),"selftest"],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d["result"]=="PASS" and all(d["assertions"].values())

def test_attempt4_runner_is_broker_owned_and_parallel_without_profile_spawn():
 s=R.read_text();assert "connectLeasedClusterTab" in s and "acquireClusterTab" in s and "Promise.all" in s;assert "generateDuck" in s and "generateManus" in s;assert "PlaywrightChromiumDriver" not in s and "launchPersistentContext" not in s and "--user-data-dir" not in s

def test_attempt4_uses_duck_fa118_style_original_byte_extraction_and_manus_response_capture():
 s=R.read_text();assert "provider_image_response_body" in s and "Create Image" in s and "duckchat/v1/chat" in s and "E_HUMAN_CHALLENGE_REQUIRED" in s;assert "manuscdn.com" in s and "EDITOR_READY_AFTER_BOUNDED_WAIT" in s

def test_attempt4_current_plan_is_fresh_and_authorized():
 g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};r=json.loads(REC.read_text());assert by["FA-307"]["status"]=="IN_PROGRESS";assert r["founder_authorization"]["attempt_number"]==4;assert [x["provider_id"] for x in r["planned_jobs"]]==["duckai","manus"];assert all(x["job_id"].startswith("FA307-R4-") for x in r["planned_jobs"])

def test_attempts_1_to_3_are_preserved_and_never_retried_post_dispatch():
 files=["FA-307-attempt-1-qwen-gemini-result.json","FA-307-attempt-2-qwen-manus-result.json","FA-307-attempt-3-qwen-manus-result.json"]
 ds=[json.loads((ROOT/"company/factory-asset/fixtures/multi-cluster"/f).read_text()) for f in files];assert all(d["result"]=="FAIL" for d in ds);assert all(d["post_dispatch_retry_performed"] is False for d in ds);assert ds[2]["attempts"]["manus"]["status"]=="SUCCEEDED" and ds[2]["attempts"]["manus"]["artifact"]["sha256"]=="0e3195e675c789835126b675a0e75d2142f689482ed28f81696422c1483465de"

def test_duck_and_manus_dispatch_each_occurs_only_after_preflight():
 s=R.read_text();d=s.index("rec.dispatch_started_at=now()",s.index("async function generateDuck"));dt=s.index("Create Image",s.index("async function generateDuck"));m=s.index("rec.dispatch_started_at=now()",s.index("async function generateManus"));mt=s.index("EDITOR_READY_AFTER_BOUNDED_WAIT",s.index("async function generateManus"));assert dt<d and mt<m
