from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "company/factory-asset/fixtures/scale/FA-122-final-acceptance-evidence.json"
RECEIPT = ROOT / "company/factory-asset/receipts/FA-122-20-50-masters-day.receipt.json"
GRAPH = ROOT / "company/factory-asset/task-graph-v1.json"


def test_fa122_final_evidence_proves_20_unique_qa_masters_without_volume_inflation():
    e = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert e["result"] == "PASS"
    assert e["live_result"]["dispatch_commits"] == 20
    assert e["live_result"]["successful_provider_artifacts"] == 20
    assert e["live_result"]["unique_artifact_sha256"] == 20
    assert e["technical_qa_and_distinctness"]["qa_passed_masters"] == 20
    assert e["technical_qa_and_distinctness"]["exact_duplicate_hash_count"] == 0
    assert e["technical_qa_and_distinctness"]["near_duplicate_pair_count"] == 0
    assert e["authority_and_safety"]["packaging_derivatives_counted_as_unique_masters"] is False
    assert all(e["assertions"].values())


def test_fa122_chatgpt_challenge_is_failed_closed_without_bypass_and_qwen_truth_is_preserved():
    e = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    c = e["chatgpt_incident_and_routing_truth"]
    assert c["observed_on_cluster_a"] == "CHECKPOINT"
    assert c["observed_on_cluster_b"] == "CHECKPOINT"
    assert c["reason_code"] == "PROTECTION_CHALLENGE"
    assert c["challenge_bypass_attempted"] is False
    assert c["routing_behavior"] == "FAIL_CLOSED_TO_HEALTHY_SIBLING_QWEN"
    assert c["qwen_actual_transport"] == "BROWSER_CDP"
    assert c["qwen_primary_transport_contract"] == "SESSION_API"
    assert c["qwen_session_api_live_executor_claimed"] is False
    assert e["live_result"]["provider_counts"] == {"qwen": 20, "chatgpt": 0}


def test_fa122_resource_and_authority_bounds_stay_closed():
    e = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    r = e["resource_observations"]
    a = e["authority_and_safety"]
    assert r["max_combined_browser_tree_rss_mb_observed"] <= r["rss_hard_cap_mb"]
    assert r["max_active_leases"] == {"cluster-a": 1, "cluster-b": 1}
    assert r["zero_lease_leak_after_completion"] is True
    assert r["profile_metadata_identity_preserved"] is True
    assert a["credential_values_read"] is False
    assert a["cookies_or_tokens_read"] is False
    assert a["spend_usd"] == 0
    assert a["account_actions"] == 0
    assert a["marketplace_actions"] == 0
    assert a["submission_authorized"] is False
    assert a["publication_authorized"] is False


def test_fa122_receipt_and_graph_close_task_and_unlock_fa123():
    r = json.loads(RECEIPT.read_text(encoding="utf-8"))
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    by = {row["id"]: row for row in g["tasks"]}
    assert r["status"] == "DONE" and r["result"] == "PASS"
    assert by["FA-122"]["status"] == "DONE"
    assert by["FA-123"]["status"] == "READY"
    assert by["FA-124"]["status"] == "BLOCKED"
