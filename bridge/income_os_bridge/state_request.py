"""Validate and normalize semantic state requests without committing state."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from . import authority, config, snapshot

SCHEMA_VERSION = "die.state.request.v1"
REQUEST_ID = re.compile(r"^REQ-[A-Z0-9][A-Z0-9-]{2,63}$")
ACTION_OBJECT_TYPES = {
    "state.decision.submit": "DECISION",
}
REQUIRED_FIELDS = {
    "schema_version",
    "request_id",
    "principal_id",
    "scope",
    "action",
    "object_type",
    "object",
    "source_snapshot",
    "evidence_refs",
}
OPTIONAL_FIELDS = {"assumptions"}
RAW_ACCESS = re.compile(
    r"(?i)(?:^|[;\s])[A-Z]:[\\/]|\.\.[\\/]|"
    r"\b(?:sk-|gh[pous]_)[A-Za-z0-9_-]{8,}|"
    r"\b(?:api[_-]?key|password|secret|token)\b\s*[=:]\s*\S+"
)


class StateRequestError(ValueError):
    """A typed pre-commit state-contract rejection."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _raise_from_contract(exc: Exception) -> None:
    code = getattr(exc, "code", "E_REQUEST_INVALID")
    message = getattr(exc, "message", str(exc))
    raise StateRequestError(code, message) from exc


def validate_and_normalize(
    request: Any,
    *,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise StateRequestError("E_REQUEST_INVALID", "state request must be an object")

    unknown = set(request) - REQUIRED_FIELDS - OPTIONAL_FIELDS
    missing = REQUIRED_FIELDS - set(request)
    if unknown or missing:
        raise StateRequestError(
            "E_REQUEST_INVALID",
            "state request has missing or unknown fields",
        )
    if request.get("schema_version") != SCHEMA_VERSION:
        raise StateRequestError("E_REQUEST_INVALID", "unsupported request schema")

    request_bytes = len(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    if request_bytes > config.STATE_REQUEST_MAX_BYTES:
        raise StateRequestError(
            "E_REQUEST_TOO_LARGE",
            f"state request exceeds {config.STATE_REQUEST_MAX_BYTES} bytes",
        )

    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        raise StateRequestError("E_REQUEST_INVALID", "request_id format is invalid")

    principal_id = request.get("principal_id")
    scope = request.get("scope")
    action = request.get("action")
    if not all(isinstance(value, str) and value for value in (principal_id, scope, action)):
        raise StateRequestError(
            "E_REQUEST_INVALID",
            "principal_id, scope, and action must be non-empty strings",
        )

    expected_object_type = ACTION_OBJECT_TYPES.get(action)
    if expected_object_type is None:
        raise StateRequestError(
            "E_UNSUPPORTED_ACTION",
            f"state request action is not supported: {action!r}",
        )
    if request.get("object_type") != expected_object_type:
        raise StateRequestError(
            "E_REQUEST_INVALID",
            f"object_type must be {expected_object_type!r} for {action!r}",
        )
    if not isinstance(request.get("object"), dict) or not request["object"]:
        raise StateRequestError("E_REQUEST_INVALID", "object must be a non-empty object")
    object_text = json.dumps(request["object"], ensure_ascii=False, separators=(",", ":"))
    if len(object_text.encode("utf-8")) > config.STATE_OBJECT_MAX_BYTES:
        raise StateRequestError(
            "E_REQUEST_TOO_LARGE",
            f"semantic object exceeds {config.STATE_OBJECT_MAX_BYTES} bytes",
        )
    if RAW_ACCESS.search(object_text):
        raise StateRequestError(
            "E_NO_RAW_ACCESS",
            "semantic object contains a host path, traversal, or credential-shaped value",
        )

    assumptions = request.get("assumptions", [])
    if not isinstance(assumptions, list) or any(
        not isinstance(item, str) for item in assumptions
    ):
        raise StateRequestError("E_REQUEST_INVALID", "assumptions must be an array of strings")
    if any(RAW_ACCESS.search(item) for item in assumptions):
        raise StateRequestError(
            "E_NO_RAW_ACCESS",
            "assumptions contain a host path, traversal, or credential-shaped value",
        )

    try:
        granted = authority.authorize(
            principal_id,
            action,
            scope,
            registry_path,
        )
        source_snapshot = snapshot.assert_fresh(
            request["source_snapshot"],
            now=now,
        )
        evidence_refs = snapshot.validate_evidence_refs(request["evidence_refs"])
    except (authority.AuthorizationError, snapshot.SnapshotError) as exc:
        _raise_from_contract(exc)

    snapshot_principal = source_snapshot.get("principal", {})
    if snapshot_principal.get("principal_id") != principal_id:
        raise StateRequestError(
            "E_SNAPSHOT_PRINCIPAL_MISMATCH",
            "snapshot principal does not match request principal",
        )
    if snapshot_principal.get("scope") != scope:
        raise StateRequestError(
            "E_SNAPSHOT_SCOPE_MISMATCH",
            "snapshot scope does not match request scope",
        )

    submitted = now or dt.datetime.now(dt.timezone.utc)
    if submitted.tzinfo is None:
        submitted = submitted.replace(tzinfo=dt.timezone.utc)
    submitted_at = submitted.astimezone(dt.timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")

    return {
        "accepted": True,
        "commit_status": "validated_not_committed",
        "writer": "die-state-manager",
        "normalized": {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "principal_id": principal_id,
            "identity_id": granted["identity_id"],
            "scope": granted["scope"],
            "authority": {
                "action": granted["action"],
                "capability": granted["capability"],
                "source": granted["authority_source"],
            },
            "source_snapshot": {
                "snapshot_id": source_snapshot["snapshot_id"],
                "snapshot_version": source_snapshot["snapshot_version"],
                "events_next_seq": source_snapshot.get("source_cursor", {}).get(
                    "events_next_seq"
                ),
            },
            "object_type": expected_object_type,
            "object": request["object"],
            "evidence_refs": evidence_refs,
            "assumptions": assumptions,
            "submitted_at": submitted_at,
        },
    }
