from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
F=ROOT/"company/factory-asset/fixtures/governed-canary/FA-206-v1-acceptance-result.json"
R=ROOT/"company/factory-asset/receipts/FA-206-factory-asset-v1-acceptance.receipt.json"
G=ROOT/"company/factory-asset/task-graph-v1.json"

def test_fa206_acceptance_matrix_is_all_pass():
    d=json.loads(F.read_text())
    assert d["result"]=="PASS"
    assert set(d["acceptance_matrix"].values())=={"PASS"}
    assert d["founder_qc"]["decision"]=="APPROVE"
    assert d["truth_boundaries"]["submission_authorized"] is False
    assert d["truth_boundaries"]["publication_authorized"] is False
    assert d["truth_boundaries"]["provider_calls_performed"] is False

def test_fa206_rollback_rehearsal_preserves_immutable_sources_and_has_no_external_side_effect():
    d=json.loads(F.read_text());r=d["rollback_evidence"]
    assert r["result"]=="PASS" and r["mode"]=="NON_DESTRUCTIVE_IN_MEMORY_RECONSTRUCTION"
    assert r["target_revision"]==2
    assert r["rights_state"]=="REVIEW_REQUIRED" and r["package_state"]=="PACKAGE_BLOCKED"
    assert r["source_master_retained"] is True
    assert r["provider_original_retained"] is True
    assert r["canonical_master_retained"] is True
    assert r["external_side_effect_to_undo"] is False

def test_fa206_receipt_and_graph_close_v1_without_publication_authority():
    r=json.loads(R.read_text());g=json.loads(G.read_text());by={x["id"]:x for x in g["tasks"]}
    assert r["result"]=="PASS" and r["scope"]["marketplace_publication_in_scope"] is False
    assert by["FA-206"]["status"]=="DONE"
    assert by["FA-121"]["status"]=="IN_PROGRESS"
