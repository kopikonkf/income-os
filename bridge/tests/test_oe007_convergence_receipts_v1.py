from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = ROOT / "company/muxia/receipts/oe007"
GRAPH = ROOT / "company/muxia-task-graph-v1.json"

def _tasks():
    return {x["id"]: x for x in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}

def test_oe007a_candidate_snapshot_is_live_canon_pinned_and_nonproduction():
    r=json.loads((RECEIPTS/"OE-007A-candidate-snapshot.receipt.json").read_text(encoding="utf-8"))
    assert r["status"]=="PASS"
    assert r["candidate_family"]["object"]=="shopping bag"
    assert r["candidate_family"]["human_context_id"]=="HCTX-SMALL-BUSINESS-PACKAGING-001"
    assert r["object_atlas"]["result_count"]==1
    assert r["object_atlas"]["results"][0]["status"]=="approved"
    assert r["object_atlas"]["source_db"]["mode"]=="READ_ONLY_POINT_IN_TIME_OR_AUTHORITATIVE_SNAPSHOT"
    assert r["authority_boundary"]["production_invoked"] is False

def test_oe007b_has_fresh_bounded_signals_complete_score_and_no_hidden_parent_fallback():
    r=json.loads((RECEIPTS/"OE-007B-signals-score-longtail.receipt.json").read_text(encoding="utf-8"))
    assert r["status"]=="PASS"
    assert r["signal_policy_mode"]=="APPROVED_BOUNDED_SYNTHETIC_ONLY"
    assert r["live_market_observation_claimed"] is False
    assert len(r["opportunity_signals"])==3
    assert all(x["evidence_label"]=="SYNTHETIC" for x in r["opportunity_signals"])
    assert all(x["cost_usd"]==0 for x in r["opportunity_signals"])
    assert r["demand_score"]["score_status"]=="COMPLETE"
    assert r["demand_score"]["final_score"] is not None
    assert r["phrase_score"]["parent_score_inherited"] is False
    assert all(r["acceptance"].values())

def test_graph_releases_only_oe007c_after_ab_closure():
    t=_tasks()
    assert t["OE-007A"]["status"]=="DONE"
    assert t["OE-007B"]["status"]=="DONE"
    assert t["OE-007C"]["status"]=="READY"
    assert t["OE-007D"]["status"]=="BLOCKED"
