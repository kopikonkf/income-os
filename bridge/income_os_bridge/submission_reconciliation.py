from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

Decision = Literal[
    "ALLOW_ATTEMPT",
    "NOOP_DUPLICATE",
    "RECONCILE_NO_SUBMIT",
    "STOP_REVIEW",
    "BLOCK_SCOPE_MISMATCH",
    "BLOCK_NON_SEQUENTIAL_ATTEMPT",
    "BLOCK_ROUTE_STATE",
]

ExternalObservation = Literal[
    "NOT_CHECKED",
    "NOT_FOUND",
    "FOUND_SUBMITTED",
    "FOUND_REVIEW_PENDING",
    "FOUND_APPROVED",
    "FOUND_REJECTED",
    "AMBIGUOUS",
    "UNREACHABLE",
]

_ALLOWED_ROUTE_STATES = {
    "PREPARED",
    "AUTHORIZED",
    "SUBMITTED",
    "REVIEW_PENDING",
    "APPROVED",
    "REJECTED",
    "RECONCILED",
}
_EXTERNAL_FINAL_OR_IN_FLIGHT = {
    "FOUND_SUBMITTED",
    "FOUND_REVIEW_PENDING",
    "FOUND_APPROVED",
    "FOUND_REJECTED",
}


@dataclass(frozen=True)
class SubmissionDecision:
    decision: Decision
    idempotency_key: str
    current_attempt: int
    proposed_attempt: int
    external_observation: ExternalObservation
    attempt_eligible: bool
    reconciliation_required: bool
    review_required: bool
    submission_action_authorized: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "idempotency_key": self.idempotency_key,
            "current_attempt": self.current_attempt,
            "proposed_attempt": self.proposed_attempt,
            "external_observation": self.external_observation,
            "attempt_eligible": self.attempt_eligible,
            "reconciliation_required": self.reconciliation_required,
            "review_required": self.review_required,
            "submission_action_authorized": self.submission_action_authorized,
            "reason": self.reason,
        }


def build_idempotency_key(*, package_sha256: str, route_id: str) -> str:
    """Stable package/route identity; retries intentionally keep the same key."""
    material = f"die.asset.submission-route.v1\n{package_sha256}\n{route_id}\n".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def decide_submission_attempt(
    *,
    pinned_package_sha256: str,
    pinned_route_id: str,
    observed_package_sha256: str,
    observed_route_id: str,
    route_state: str,
    current_attempt: int,
    proposed_attempt: int,
    external_observation: ExternalObservation = "NOT_CHECKED",
) -> SubmissionDecision:
    """Pure fail-closed decision core. It never performs or authorizes submission."""
    key = build_idempotency_key(package_sha256=pinned_package_sha256, route_id=pinned_route_id)

    def result(
        decision: Decision,
        *,
        attempt_eligible: bool = False,
        reconciliation_required: bool = False,
        review_required: bool = False,
        reason: str,
    ) -> SubmissionDecision:
        return SubmissionDecision(
            decision=decision,
            idempotency_key=key,
            current_attempt=current_attempt,
            proposed_attempt=proposed_attempt,
            external_observation=external_observation,
            attempt_eligible=attempt_eligible,
            reconciliation_required=reconciliation_required,
            review_required=review_required,
            reason=reason,
        )

    if route_state not in _ALLOWED_ROUTE_STATES or current_attempt < 0 or proposed_attempt < 1:
        return result("BLOCK_ROUTE_STATE", reason="invalid route state or attempt counter")

    if observed_package_sha256 != pinned_package_sha256 or observed_route_id != pinned_route_id:
        return result("BLOCK_SCOPE_MISMATCH", reason="package/route differs from immutable pinned scope")

    if proposed_attempt <= current_attempt:
        return result("NOOP_DUPLICATE", reason="same package/route attempt already recorded")

    if proposed_attempt != current_attempt + 1:
        return result("BLOCK_NON_SEQUENTIAL_ATTEMPT", reason="attempt counter must advance by exactly one")

    if route_state in {"SUBMITTED", "REVIEW_PENDING", "APPROVED", "REJECTED", "RECONCILED"}:
        return result(
            "RECONCILE_NO_SUBMIT",
            reconciliation_required=True,
            reason="route already has external/in-flight state; reconcile instead of repeating action",
        )

    if route_state != "AUTHORIZED":
        return result("BLOCK_ROUTE_STATE", reason="submission attempt requires an AUTHORIZED route")

    is_retry = current_attempt > 0
    if not is_retry:
        return result(
            "ALLOW_ATTEMPT",
            attempt_eligible=True,
            reason="first attempt is mechanically eligible; separate Founder authority remains required",
        )

    if external_observation in {"NOT_CHECKED", "AMBIGUOUS", "UNREACHABLE"}:
        return result(
            "STOP_REVIEW",
            reconciliation_required=True,
            review_required=True,
            reason="retry outcome is unknown; external state must be reconciled before any repeat",
        )

    if external_observation in _EXTERNAL_FINAL_OR_IN_FLIGHT:
        return result(
            "RECONCILE_NO_SUBMIT",
            reconciliation_required=True,
            reason="external state proves prior action/outcome; record reconciliation without resubmission",
        )

    if external_observation == "NOT_FOUND":
        return result(
            "ALLOW_ATTEMPT",
            attempt_eligible=True,
            reconciliation_required=True,
            reason="external reconciliation found no prior submission; retry is mechanically eligible",
        )

    return result("STOP_REVIEW", reconciliation_required=True, review_required=True, reason="unclassified retry state")
