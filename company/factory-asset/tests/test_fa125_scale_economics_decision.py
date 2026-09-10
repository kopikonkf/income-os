import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/"docs/architecture/FACTORY_ASSET_SCALE_ECONOMICS_DECISION_V1.md"
REC=ROOT/"company/factory-asset/receipts/FA-125-scale-economics-decision.receipt.json"
GRAPH=ROOT/"company/factory-asset/task-graph-v1.json"

def test_fa125_packet_recommends_hold_without_self_ratifying_founder_decision():
    s=DOC.read_text(encoding="utf-8")
    assert "Architect recommendation: **HOLD**" in s
    assert "Founder ratification: **PENDING**" in s
    assert "FullyLoadedCostPerMarketplaceAcceptedAsset = UNKNOWN" in s
    assert "Factory marketplace acceptance" in s and "**HOLD**" in s
    assert "0 */3 * * *" in s and "scale_100_per_day=false" in s

def test_fa125_receipt_preserves_authority_and_unknown_economics():
    r=json.loads(REC.read_text(encoding="utf-8"))
    assert r["status"]=="WAITING_FOUNDER"
    assert r["architect_recommendation"]=="HOLD" and r["founder_decision"]=="PENDING"
    assert r["evidence"]["factory_marketplace_acceptance_rate"]=="UNKNOWN"
    assert r["evidence"]["factory_realized_licensing_revenue"]=="UNKNOWN"
    assert r["evidence"]["fully_loaded_cost_per_marketplace_accepted_asset"]=="UNKNOWN"
    a=r["authority"]
    assert a["continuous_100_per_day_authorized"] is False and a["fa126_500_per_day_unlocked"] is False
    assert a["production_schedule_changed"] is False and a["baseline_schedule"]=="0 */3 * * *"
    assert a["scale_100_per_day"] is False and a["new_spend_authorized"] is False
    assert a["marketplace_submission_authorized"] is False and a["publication_authorized"] is False

def test_fa125_graph_waits_for_founder_and_fa126_remains_deferred():
    g=json.loads(GRAPH.read_text(encoding="utf-8")); by={x["id"]:x for x in g["tasks"]}
    assert by["FA-125"]["status"]=="WAITING_FOUNDER"
    assert "recommends HOLD" in by["FA-125"]["result"]
    assert by["FA-126"]["status"]=="DEFERRED"
    assert "FA-125 recommends PROMOTE" in by["FA-126"]["resume_condition"]

def test_fa125_storage_numbers_are_planning_bounds_not_scale_authority():
    r=json.loads(REC.read_text(encoding="utf-8")); e=r["evidence"]
    assert e["p95_storage_gib_per_day_at_100"]==4.661
    assert e["p95_storage_gib_30_day_at_100"]==139.826
    assert e["live_free_disk_gib_observed"]==63.395
    assert e["unmanaged_local_storage_runway_days_at_p95_100_day"]==13.6
    assert r["authority"]["continuous_100_per_day_authorized"] is False
