"""Stateless P6 Decision Gateway for normalized semantic decision requests."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Callable

from . import authority, config, snapshot, state_request

RESULT_SCHEMA = "die.decision.gateway.result.v1"
GATEWAY_ID = "die-decision-gateway"
WRITER_ID = "die-state-manager"
NEXT_OWNER = "hermes-operator"

WRAPPER_FIELDS = {"accepted", "commit_status", "writer", "normalized"}
NORMALIZED_FIELDS = {
    "schema_version",
    "request_id",
    "principal_id",
    "identity_id",
    "scope",
    "authority",
    "source_snapshot",
    "object_type",
    "object",
    "evidence_refs",
    "assumptions",
    "submitted_at",
}
AUTHORITY_FIELDS = {"action", "capability", "source"}
DECISION_REQUIRED = {"decision_class", "choice", "reason"}
DECISION_CLASS = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")

Writer = Callable[[dict[str, Any]], dict[str, Any]]


class DecisionGatewayError(ValueError):
    """Typed rejection safe to return through the Decision Gateway."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _utc(value: dt.datetime | None = None) -> dt.datetime:
    value = value or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _parse_iso(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            f"{field} must be an ISO timestamp",
        )
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            f"{field} must be an ISO timestamp",
        ) from exc
    return _utc(parsed)


def rejected_result(
    code: str,
    message: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA,
        "gateway": GATEWAY_ID,
        "request_id": request_id,
        "status": "rejected",
        "writer": WRITER_ID,
        "canonical_mutation": False,
        "error": {"code": code, "message": message},
        "commit": None,
        "route": None,
    }


def _request_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    normalized = payload.get("normalized")
    if not isinstance(normalized, dict):
        return None
    value = normalized.get("request_id")
    return value if isinstance(value, str) else None


def validate_normalized(
    payload: Any,
    *,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fail closed and return a revalidated, commit-ready normalized request."""

    if not isinstance(payload, dict) or set(payload) != WRAPPER_FIELDS:
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "gateway accepts only the exact normalized validation wrapper",
        )
    if (
        payload.get("accepted") is not True
        or payload.get("commit_status") != "validated_not_committed"
        or payload.get("writer") != WRITER_ID
    ):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "request is not an accepted uncommitted State Manager request",
        )

    normalized = payload.get("normalized")
    if not isinstance(normalized, dict) or set(normalized) != NORMALIZED_FIELDS:
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "normalized request has missing or unknown fields",
        )
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > config.STATE_REQUEST_MAX_BYTES:
        raise DecisionGatewayError(
            "E_REQUEST_TOO_LARGE",
            f"normalized request exceeds {config.STATE_REQUEST_MAX_BYTES} bytes",
        )

    if normalized.get("schema_version") != state_request.SCHEMA_VERSION:
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "unsupported normalized request schema",
        )
    request_id = normalized.get("request_id")
    if not isinstance(request_id, str) or not state_request.REQUEST_ID.fullmatch(
        request_id
    ):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "normalized request_id format is invalid",
        )

    principal_id = normalized.get("principal_id")
    identity_id = normalized.get("identity_id")
    scope = normalized.get("scope")
    if not all(
        isinstance(value, str) and value
        for value in (principal_id, identity_id, scope)
    ):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "principal_id, identity_id, and scope must be non-empty strings",
        )

    granted = authority.authorize(
        principal_id,
        "state.decision.submit",
        scope,
        registry_path,
    )
    supplied_authority = normalized.get("authority")
    expected_authority = {
        "action": granted["action"],
        "capability": granted["capability"],
        "source": granted["authority_source"],
    }
    if (
        identity_id != granted["identity_id"]
        or not isinstance(supplied_authority, dict)
        or set(supplied_authority) != AUTHORITY_FIELDS
        or supplied_authority != expected_authority
    ):
        raise DecisionGatewayError(
            "E_GATEWAY_AUTHORITY_MISMATCH",
            "normalized authority does not match the Company Brain registry",
        )

    source = snapshot.assert_trusted(normalized.get("source_snapshot"))
    snapshot.assert_fresh(source, now=now)
    source_principal = source.get("principal")
    if not isinstance(source_principal, dict):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "snapshot principal envelope is missing",
        )
    if source_principal.get("principal_id") != principal_id:
        raise DecisionGatewayError(
            "E_SNAPSHOT_PRINCIPAL_MISMATCH",
            "snapshot principal does not match normalized request principal",
        )
    if source_principal.get("scope") != scope:
        raise DecisionGatewayError(
            "E_SNAPSHOT_SCOPE_MISMATCH",
            "snapshot scope does not match normalized request scope",
        )

    if normalized.get("object_type") != "DECISION":
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "Decision Gateway v1 accepts only DECISION objects",
        )
    obj = normalized.get("object")
    if not isinstance(obj, dict) or not DECISION_REQUIRED.issubset(obj):
        raise DecisionGatewayError(
            "E_DECISION_INVALID",
            "decision requires decision_class, choice, and reason",
        )
    decision_class = obj.get("decision_class")
    choice = obj.get("choice")
    reason = obj.get("reason")
    if (
        not isinstance(decision_class, str)
        or not DECISION_CLASS.fullmatch(decision_class)
        or not isinstance(choice, str)
        or not choice.strip()
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise DecisionGatewayError(
            "E_DECISION_INVALID",
            "decision_class, choice, and reason are invalid",
        )
    alternatives = obj.get("alternatives_rejected", [])
    if not isinstance(alternatives, list) or any(
        not isinstance(item, str) or not item.strip() for item in alternatives
    ):
        raise DecisionGatewayError(
            "E_DECISION_INVALID",
            "alternatives_rejected must be an array of non-empty strings",
        )

    object_text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if len(object_text.encode("utf-8")) > config.STATE_OBJECT_MAX_BYTES:
        raise DecisionGatewayError(
            "E_REQUEST_TOO_LARGE",
            f"decision object exceeds {config.STATE_OBJECT_MAX_BYTES} bytes",
        )
    if state_request.RAW_ACCESS.search(object_text):
        raise DecisionGatewayError(
            "E_NO_RAW_ACCESS",
            "decision contains a host path, traversal, or credential-shaped value",
        )

    evidence_refs = snapshot.validate_evidence_refs(normalized.get("evidence_refs"))
    source_evidence = {
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in snapshot.validate_evidence_refs(source.get("evidence_refs"))
    }
    if any(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        not in source_evidence
        for row in evidence_refs
    ):
        raise DecisionGatewayError(
            "E_EVIDENCE_INVALID",
            "decision evidence must be present in the verified source snapshot",
        )
    assumptions = normalized.get("assumptions")
    if not isinstance(assumptions, list) or any(
        not isinstance(item, str) for item in assumptions
    ):
        raise DecisionGatewayError(
            "E_GATEWAY_INPUT_INVALID",
            "assumptions must be an array of strings",
        )
    if any(state_request.RAW_ACCESS.search(item) for item in assumptions):
        raise DecisionGatewayError(
            "E_NO_RAW_ACCESS",
            "assumptions contain a host path, traversal, or credential-shaped value",
        )
    _parse_iso(normalized.get("submitted_at"), "submitted_at")

    clean = json.loads(json.dumps(normalized, ensure_ascii=False))
    clean["authority"] = expected_authority
    clean["source_snapshot"] = json.loads(json.dumps(source, ensure_ascii=False))
    clean["object"]["decision_class"] = decision_class.lower()
    clean["object"]["choice"] = choice.strip()
    clean["object"]["reason"] = reason.strip()
    clean["object"]["alternatives_rejected"] = alternatives
    clean["evidence_refs"] = evidence_refs
    clean["assumptions"] = assumptions
    return clean


def process(
    payload: Any,
    *,
    writer: Writer | None,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate, commit through the sole writer, and return a route result."""

    request_id = _request_id(payload)
    try:
        normalized = validate_normalized(
            payload,
            now=now,
            registry_path=registry_path,
        )
    except (
        DecisionGatewayError,
        authority.AuthorizationError,
        snapshot.SnapshotError,
    ) as exc:
        return rejected_result(
            getattr(exc, "code", "E_GATEWAY_INPUT_INVALID"),
            getattr(exc, "message", str(exc)),
            request_id,
        )
    except Exception:
        return rejected_result(
            "E_GATEWAY_DEGRADED",
            "gateway validation failed closed",
            request_id,
        )

    if writer is None:
        return rejected_result(
            "E_STATE_WRITER_UNAVAILABLE",
            "DIE State Manager writer is unavailable",
            normalized["request_id"],
        )
    try:
        outcome = writer(normalized)
    except Exception:
        return rejected_result(
            "E_STATE_WRITER_FAILED",
            "DIE State Manager failed to commit the decision",
            normalized["request_id"],
        )

    if not isinstance(outcome, dict) or set(outcome) != {"record", "replayed"}:
        return rejected_result(
            "E_STATE_WRITER_RESULT_INVALID",
            "DIE State Manager returned an invalid commit result",
            normalized["request_id"],
        )
    record = outcome.get("record")
    replayed = outcome.get("replayed")
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("decision_id"), str)
        or not isinstance(record.get("ts"), str)
        or record.get("request_id") != normalized["request_id"]
        or not isinstance(replayed, bool)
    ):
        return rejected_result(
            "E_STATE_WRITER_RESULT_INVALID",
            "DIE State Manager commit receipt is incomplete",
            normalized["request_id"],
        )

    return {
        "schema_version": RESULT_SCHEMA,
        "gateway": GATEWAY_ID,
        "request_id": normalized["request_id"],
        "status": "committed",
        "writer": WRITER_ID,
        "canonical_mutation": not replayed,
        "error": None,
        "commit": {
            "object_type": "DECISION",
            "record_id": record["decision_id"],
            "committed_at": record["ts"],
            "replayed": replayed,
        },
        "route": {
            "next_owner": NEXT_OWNER,
            "status": "ready_for_operational_acceptance",
        },
    }
