from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "company" / "muxia" / "receipts" / "oe007"
BUNDLE = BASE / "OE-007C-evidence-remediation.bundle.json"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_evidence_bundle_pins_all_four_lane_receipts() -> None:
    bundle = _load(BUNDLE)
    assert bundle["schema"] == "die.oe007c.evidence-remediation.bundle.v1"
    assert bundle["status"] == "READY_FOR_FRESH_WORTH_MAKING"
    assert {row["lane"] for row in bundle["evidence"]} == {"EVID-A", "EVID-B", "EVID-C", "EVID-D"}
    for row in bundle["evidence"]:
        path = ROOT / row["path"]
        assert path.is_file()
        assert row["status"] == "PASS"
        assert _sha(path) == row["sha256"]


def test_evid_a_does_not_claim_exact_candidate_transaction() -> None:
    data = _load(BASE / "evidence-remediation" / "EVID-A-buyer-demand.receipt.json")
    assert data["status"] == "PASS"
    assert data["conclusion"]["buyer_demand_status"] == "OBSERVED_CATEGORY_LEVEL"
    assert data["conclusion"]["payer_existence"] == "OBSERVED"
    assert data["conclusion"]["stock_asset_purchase_or_licensing_behavior"] == "OBSERVED"
    assert data["conclusion"]["candidate_specific_sale_or_download"] == "UNOBSERVED"


def test_evid_b_is_policy_fit_not_account_or_submission_acceptance() -> None:
    data = _load(BASE / "evidence-remediation" / "EVID-B-platform-fit.receipt.json")
    assert data["status"] == "PASS"
    assert len(data["routes"]) == 5
    assert all(row["status"] == "CONDITIONAL_ELIGIBLE" for row in data["routes"])
    conclusion = data["conclusion"]
    assert conclusion["cohort_policy_fit"] == "5_OF_5_CONDITIONALLY_ELIGIBLE_BY_PUBLIC_POLICY"
    assert conclusion["account_specific_eligibility"] == "NOT_CHECKED"
    assert conclusion["submission_acceptance"] == "NOT_CLAIMED"


def test_evid_c_observes_supply_but_does_not_invent_competition_gap() -> None:
    data = _load(BASE / "evidence-remediation" / "EVID-C-competition.receipt.json")
    assert data["status"] == "PASS"
    assert data["conclusion"]["supply_presence"] == "OBSERVED"
    assert data["conclusion"]["competition_presence"] == "OBSERVED"
    assert data["conclusion"]["competition_gap_status"] == "NOT_PROVEN"
    assert data["conclusion"]["cross_platform_count_normalization"] == "NOT_PERFORMED"


def test_evid_d_resolves_structural_family_without_inventing_family_id() -> None:
    data = _load(BASE / "evidence-remediation" / "EVID-D-portfolio-overlap.receipt.json")
    assert data["status"] == "PASS"
    assert data["family_lineage_basis"]["family_id_invented"] is False
    assert data["conclusion"]["sibling_count"] == 6
    assert data["conclusion"]["other_promoted_sibling_count"] == 0
    assert data["conclusion"]["existing_portfolio_cannibalization"] == "NOT_OBSERVED"
    assert data["conclusion"]["intra_family_semantic_overlap"] == "HIGH"


def test_bundle_preserves_synthetic_boundary_and_zero_authority() -> None:
    bundle = _load(BUNDLE)
    summary = bundle["epistemic_summary"]
    assert summary["old_synthetic_demand_score_must_not_be_relabelled_live"] is True
    assert summary["competition_gap"] == "NOT_PROVEN"
    assert summary["exact_candidate_transaction"] == "UNOBSERVED"
    for path in [
        BASE / "evidence-remediation" / "EVID-A-buyer-demand.receipt.json",
        BASE / "evidence-remediation" / "EVID-B-platform-fit.receipt.json",
        BASE / "evidence-remediation" / "EVID-C-competition.receipt.json",
        BASE / "evidence-remediation" / "EVID-D-portfolio-overlap.receipt.json",
    ]:
        authority = _load(path)["authority"]
        assert all(value is False for value in authority.values())
    assert all(value is False for value in bundle["authority"].values())


def test_graph_stays_blocked_until_fresh_cognition_review_advances() -> None:
    graph = _load(GRAPH)
    tasks = {row["id"]: row for row in graph["tasks"]}
    assert tasks["OE-007C"]["status"] == "BLOCKED"
    assert tasks["OE-007D"]["status"] == "BLOCKED"
    next_gate = _load(BUNDLE)["next_gate"]
    assert next_gate["division01_fresh_worth_making_required"] is True
    assert next_gate["executive_fresh_review_required"] is True
    assert next_gate["oe007d_release_requires_advancing_review"] is True
