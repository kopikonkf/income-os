from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
F=ROOT/"company/factory-asset/fixtures/scale/FA-121-final-acceptance-evidence.json"
R=ROOT/"company/factory-asset/receipts/FA-121-24h-provider-stability.receipt.json"
G=ROOT/"company/factory-asset/task-graph-v1.json"

def test_fa121_final_evaluator_passes_real_24h_and_safety_assertions():
 d=json.loads(F.read_text());e=d["final_evaluation"];assert d["result"]=="PASS";assert e["coverage"]["covers_24h"] is True;assert e["coverage"]["observed_duration_ms"]>=86400000;assert e["coverage"]["max_gap_ms"]<=900000;assert all(e["assertions"].values())

def test_fa121_load_is_bounded_and_skips_after_provider_cap_without_dispatch():
 d=json.loads(F.read_text());assert d["runtime_final"]["successful_generations"]==6;assert d["runtime_final"]["skipped_no_eligible_route"]==6;assert d["runtime_final"]["failure_events"]==0;assert len(d["artifacts"])==6;assert len({x["sha256"] for x in d["artifacts"]})==6

def test_fa121_receipt_and_graph_close_soak_and_unlock_dependencies():
 r=json.loads(R.read_text());g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]};assert r["status"]=="DONE" and r["result"]=="PASS" and r["full_fa121_acceptance"] is True;assert by["FA-121"]["status"]=="DONE";assert by["FA-122"]["status"] in {"READY","DONE"};assert by["FA-307"]["status"] in {"READY","IN_PROGRESS","DONE"}
 if by["FA-307"]["status"]!="READY":
  q=json.loads((ROOT/"company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json").read_text());assert q["task_id"]=="FA-307";assert q["status"]==by["FA-307"]["status"]

def test_fa121_final_truth_boundaries_remain_closed():
 d=json.loads(F.read_text())["truth_boundaries"];assert d["credential_values_read"] is False;assert d["cookies_or_tokens_read"] is False;assert d["spend_usd"]==0;assert d["submission_authorized"] is False;assert d["publication_authorized"] is False

