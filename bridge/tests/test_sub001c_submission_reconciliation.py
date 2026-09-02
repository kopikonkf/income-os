from __future__ import annotations

import json
from pathlib import Path

from income_os_bridge.submission_reconciliation import build_idempotency_key, decide_submission_attempt

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-reconciliation.v1.schema.json"
DOC = ROOT / "docs" / "operations" / "SUBMISSION_IDEMPOTENCY_RETRY_RECONCILIATION_V1.md"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"

PKG = "a" * 64
ROUTE = "ROUTE-SUB001C01"


def _decide(**kwargs):
    defaults = dict(
        pinned_package_sha256=PKG,
        pinned_route_id=ROUTE,
        observed_package_sha256=PKG,
        observed_route_id=ROUTE,
        route_state="AUTHORIZED",
        current_attempt=0,
        proposed_attempt=1,
        external_observation="NOT_CHECKED",
    )
    defaults.update(kwargs)
    return decide_submission_attempt(**defaults)


def test_sub001c_idempotency_key_is_stable_for_exact_package_route() -> None:
    first = build_idempotency_key(package_sha256=PKG, route_id=ROUTE)
    second = build_idempotency_key(package_sha256=PKG, route_id=ROUTE)
    other = build_idempotency_key(package_sha256="b" * 64, route_id=ROUTE)
    assert first == second
    assert first != other
    assert len(first) == 64


def test_sub001c_first_authorized_attempt_is_eligible_but_not_authorized() -> None:
    result = _decide()
    assert result.decision == "ALLOW_ATTEMPT"
    assert result.attempt_eligible is True
    assert result.submission_action_authorized is False
    assert result.review_required is False


def test_sub001c_exact_attempt_replay_is_noop_duplicate() -> None:
    result = _decide(current_attempt=1, proposed_attempt=1)
    assert result.decision == "NOOP_DUPLICATE"
    assert result.attempt_eligible is False
    assert result.submission_action_authorized is False


def test_sub001c_package_or_route_scope_mismatch_fails_closed() -> None:
    package = _decide(observed_package_sha256="b" * 64)
    route = _decide(observed_route_id="ROUTE-OTHER001")
    assert package.decision == "BLOCK_SCOPE_MISMATCH"
    assert route.decision == "BLOCK_SCOPE_MISMATCH"


def test_sub001c_attempt_counter_gap_fails_closed() -> None:
    result = _decide(current_attempt=1, proposed_attempt=3)
    assert result.decision == "BLOCK_NON_SEQUENTIAL_ATTEMPT"
    assert result.attempt_eligible is False


def test_sub001c_retry_must_reconcile_external_state_before_action() -> None:
    for observation in ["NOT_CHECKED", "AMBIGUOUS", "UNREACHABLE"]:
        result = _decide(current_attempt=1, proposed_attempt=2, external_observation=observation)
        assert result.decision == "STOP_REVIEW"
        assert result.reconciliation_required is True
        assert result.review_required is True
        assert result.attempt_eligible is False


def test_sub001c_external_prior_submission_never_blindly_retries() -> None:
    for observation in ["FOUND_SUBMITTED", "FOUND_REVIEW_PENDING", "FOUND_APPROVED", "FOUND_REJECTED"]:
        result = _decide(current_attempt=1, proposed_attempt=2, external_observation=observation)
        assert result.decision == "RECONCILE_NO_SUBMIT"
        assert result.reconciliation_required is True
        assert result.attempt_eligible is False


def test_sub001c_retry_only_eligible_after_not_found_reconciliation() -> None:
    result = _decide(current_attempt=1, proposed_attempt=2, external_observation="NOT_FOUND")
    assert result.decision == "ALLOW_ATTEMPT"
    assert result.attempt_eligible is True
    assert result.reconciliation_required is True
    assert result.submission_action_authorized is False


def test_sub001c_inflight_or_terminal_internal_state_reconciles_without_submit() -> None:
    for state in ["SUBMITTED", "REVIEW_PENDING", "APPROVED", "REJECTED", "RECONCILED"]:
        result = _decide(route_state=state, current_attempt=1, proposed_attempt=2)
        assert result.decision == "RECONCILE_NO_SUBMIT"
        assert result.attempt_eligible is False
        assert result.reconciliation_required is True


def test_sub001c_prepared_route_cannot_attempt_submission() -> None:
    result = _decide(route_state="PREPARED")
    assert result.decision == "BLOCK_ROUTE_STATE"
    assert result.attempt_eligible is False


def test_sub001c_schema_and_doc_keep_authority_fail_closed() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["submission_action_authorized"] == {"const": False}
    assert "STOP_REVIEW" in schema["properties"]["decision"]["enum"]
    assert "RECONCILE_NO_SUBMIT" in schema["properties"]["decision"]["enum"]
    doc = DOC.read_text(encoding="utf-8")
    for marker in [
        "Every retry is reconciliation-first",
        "STOP_REVIEW",
        "RECONCILE_NO_SUBMIT",
        "submission_action_authorized = false",
        "Mechanical retry eligibility is not submission authority",
    ]:
        assert marker in doc


def test_sub001c_graph_is_pre_acceptance_until_validation_seal() -> None:
    tasks = {row["id"]: row for row in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["SUB-001A"]["status"] == "DONE"
    assert tasks["SUB-001B"]["status"] == "DONE"
    assert tasks["SUB-001C"]["status"] in {"READY", "DONE"}
    assert tasks["SUB-001D"]["status"] in {"BLOCKED", "READY"}
