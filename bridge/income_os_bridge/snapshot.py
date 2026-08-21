"""Typed, bounded and freshness-enforced context snapshots."""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
from typing import Any

from . import config

SCHEMA_VERSION = "die.context.snapshot.v1"
SIGNING_KEY_ENV = "DIE_SNAPSHOT_HMAC_KEY"
SIGNING_KEY_ID_ENV = "DIE_SNAPSHOT_HMAC_KEY_ID"
SIGNATURE_ALGORITHM = "HMAC-SHA256"
TRUST_ORDER = {"DEGRADED": 0, "ASSUMED": 1, "VERIFIED": 2}
TRUST_VALUES = set(TRUST_ORDER)
EVIDENCE_KEYS = {
    "evidence_id",
    "kind",
    "ref",
    "claim",
    "trust",
    "observed_at",
}


class SnapshotError(ValueError):
    """A typed context-contract failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _utc(value: dt.datetime | None = None) -> dt.datetime:
    value = value or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return _utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str):
        raise SnapshotError("E_SNAPSHOT_INVALID", f"{field} must be an ISO timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(
            "E_SNAPSHOT_INVALID",
            f"{field} must be an ISO timestamp",
        ) from exc
    return _utc(parsed)


def validate_evidence_refs(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise SnapshotError("E_EVIDENCE_INVALID", "evidence_refs must be an array")

    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SnapshotError(
                "E_EVIDENCE_INVALID",
                f"evidence_refs[{index}] must be an object",
            )
        unknown = set(row) - EVIDENCE_KEYS
        missing = EVIDENCE_KEYS - set(row)
        if unknown or missing:
            raise SnapshotError(
                "E_EVIDENCE_INVALID",
                f"evidence_refs[{index}] has missing/unknown fields",
            )
        for field in ("evidence_id", "kind", "ref", "claim", "observed_at"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise SnapshotError(
                    "E_EVIDENCE_INVALID",
                    f"evidence_refs[{index}].{field} must be a non-empty string",
                )
        if row["trust"] not in TRUST_VALUES:
            raise SnapshotError(
                "E_EVIDENCE_INVALID",
                f"evidence_refs[{index}].trust is invalid",
            )
        _parse_iso(row["observed_at"], f"evidence_refs[{index}].observed_at")
        normalized.append(dict(row))
    return normalized


def _typed_provenance(surfaces: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for surface_name, surface in surfaces.items():
        trust = surface.get("source_trust", "ASSUMED")
        if trust not in TRUST_VALUES:
            trust = "DEGRADED"
        observed_at = surface.get("as_of")
        _parse_iso(observed_at, f"{surface_name}.as_of")
        for source in surface.get("sources", []):
            if not isinstance(source, str) or not source:
                continue
            key = (surface_name, source)
            if key in seen:
                continue
            seen.add(key)
            source_type = source.split(":", 1)[0] if ":" in source else "semantic"
            rows.append(
                {
                    "type": source_type,
                    "ref": source,
                    "surface": surface_name,
                    "observed_at": observed_at,
                    "trust": trust,
                }
            )
    return rows


def _worst_trust(surfaces: dict[str, dict[str, Any]]) -> str:
    values = [
        surface.get("source_trust", "ASSUMED")
        for surface in surfaces.values()
    ]
    return min(values, key=lambda value: TRUST_ORDER.get(value, -1))


def _canonical_bytes(payload: dict[str, Any], *excluded: str) -> bytes:
    canonical_payload = {
        key: value for key, value in payload.items() if key not in set(excluded)
    }
    return json.dumps(
        canonical_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _expected_snapshot_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        _canonical_bytes(payload, "snapshot_id", "integrity")
    ).hexdigest()[:16].upper()
    return "SNAP-" + digest


def _resolve_signing_key(signing_key: str | bytes | None = None) -> bytes | None:
    value = signing_key if signing_key is not None else os.environ.get(SIGNING_KEY_ENV)
    if value is None:
        return None
    encoded = value if isinstance(value, bytes) else value.encode("utf-8")
    if len(encoded) < 32:
        raise SnapshotError(
            "E_SNAPSHOT_SIGNING_KEY",
            "snapshot signing key must contain at least 32 bytes",
        )
    return encoded


def _signature(payload: dict[str, Any], key: bytes) -> str:
    return hmac.new(
        key,
        _canonical_bytes(payload, "integrity"),
        hashlib.sha256,
    ).hexdigest()


def build(
    authority: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    evidence_refs: list[dict[str, Any]] | None = None,
    *,
    now: dt.datetime | None = None,
    ttl_s: int = config.CONTEXT_SNAPSHOT_TTL_S,
) -> dict[str, Any]:
    if not surfaces:
        raise SnapshotError("E_SNAPSHOT_INVALID", "at least one semantic surface is required")
    if not isinstance(ttl_s, int) or ttl_s <= 0:
        raise SnapshotError("E_SNAPSHOT_INVALID", "ttl_s must be a positive integer")

    created = _utc(now)
    expires = created + dt.timedelta(seconds=ttl_s)
    data = {
        name: json.loads(json.dumps(surface.get("data"), ensure_ascii=False))
        for name, surface in surfaces.items()
    }
    provenance = _typed_provenance(surfaces)
    evidence = validate_evidence_refs(evidence_refs or [])

    recent = data.get("recent_events")
    source_cursor = {
        "events_since_seq": recent.get("since_seq", 0) if isinstance(recent, dict) else 0,
        "events_next_seq": recent.get("next_seq", 0) if isinstance(recent, dict) else 0,
    }
    completeness_values = {
        surface.get("completeness", "complete") for surface in surfaces.values()
    }
    if "degraded" in completeness_values:
        completeness = "degraded"
    elif "truncated" in completeness_values:
        completeness = "truncated"
    else:
        completeness = "complete"
    notes: list[str] = []

    payload: dict[str, Any] = {
        "snapshot_id": "SNAP-" + ("0" * 16),
        "schema_version": SCHEMA_VERSION,
        "snapshot_version": 1,
        "principal": {
            "principal_id": authority["principal_id"],
            "identity_id": authority["identity_id"],
            "kind": authority.get("kind"),
            "scope": authority["scope"],
        },
        "authority": {
            "action": authority["action"],
            "capability": authority["capability"],
            "source": authority["authority_source"],
        },
        "freshness": {
            "created_at": _iso(created),
            "expires_at": _iso(expires),
            "ttl_s": ttl_s,
            "status": "fresh",
        },
        "source_cursor": source_cursor,
        "completeness": completeness,
        "source_trust": _worst_trust(surfaces),
        "provenance": provenance,
        "evidence_refs": evidence,
        "notes": notes,
        "data": data,
    }

    def encoded_size() -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    event_rows = (
        data.get("recent_events", {}).get("events")
        if isinstance(data.get("recent_events"), dict)
        else None
    )
    if isinstance(event_rows, list):
        while event_rows and encoded_size() > config.MAX_RESP_BYTES:
            event_rows.pop()
            payload["completeness"] = "truncated"
        if payload["completeness"] == "truncated":
            notes.append("recent_events trimmed to enforce semantic response-size limit")

    if encoded_size() > config.MAX_RESP_BYTES:
        raise SnapshotError(
            "E_SNAPSHOT_TOO_LARGE",
            f"snapshot exceeds {config.MAX_RESP_BYTES} bytes after bounded trimming",
        )

    payload["snapshot_id"] = _expected_snapshot_id(payload)
    signing_key = _resolve_signing_key()
    if signing_key is not None:
        payload["integrity"] = {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": os.environ.get(SIGNING_KEY_ID_ENV, "runtime-v1"),
            "signature": _signature(payload, signing_key),
        }
    if encoded_size() > config.MAX_RESP_BYTES:
        raise SnapshotError(
            "E_SNAPSHOT_TOO_LARGE",
            "snapshot identifier pushed payload above semantic response-size limit",
        )
    return payload


def assert_integrity(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise SnapshotError("E_SNAPSHOT_INVALID", "source_snapshot must be an object")
    supplied = snapshot.get("snapshot_id")
    if not isinstance(supplied, str):
        raise SnapshotError("E_SNAPSHOT_INVALID", "snapshot_id is required")
    expected = _expected_snapshot_id(snapshot)
    if not hmac.compare_digest(supplied, expected):
        raise SnapshotError(
            "E_SNAPSHOT_INTEGRITY",
            "snapshot content does not match its deterministic identifier",
        )
    return snapshot


def assert_trusted(
    snapshot: Any,
    *,
    signing_key: str | bytes | None = None,
    key_id: str | None = None,
) -> dict[str, Any]:
    assert_integrity(snapshot)
    proof = snapshot.get("integrity")
    if not isinstance(proof, dict) or set(proof) != {
        "algorithm",
        "key_id",
        "signature",
    }:
        raise SnapshotError(
            "E_SNAPSHOT_UNTRUSTED",
            "mutation requires a server-signed snapshot",
        )
    if proof.get("algorithm") != SIGNATURE_ALGORITHM:
        raise SnapshotError("E_SNAPSHOT_UNTRUSTED", "snapshot signature algorithm is invalid")

    resolved_key = _resolve_signing_key(signing_key)
    if resolved_key is None:
        raise SnapshotError(
            "E_SNAPSHOT_UNTRUSTED",
            "snapshot verification key is unavailable",
        )
    expected_key_id = key_id or os.environ.get(SIGNING_KEY_ID_ENV, "runtime-v1")
    if proof.get("key_id") != expected_key_id:
        raise SnapshotError("E_SNAPSHOT_UNTRUSTED", "snapshot signing key id is invalid")
    supplied = proof.get("signature")
    expected = _signature(snapshot, resolved_key)
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, expected):
        raise SnapshotError("E_SNAPSHOT_UNTRUSTED", "snapshot signature is invalid")
    return snapshot


def assert_fresh(
    snapshot: Any,
    *,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise SnapshotError("E_SNAPSHOT_INVALID", "source_snapshot must be an object")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotError("E_SNAPSHOT_INVALID", "unsupported snapshot schema")
    if snapshot.get("snapshot_version") != 1:
        raise SnapshotError("E_SNAPSHOT_INVALID", "unsupported snapshot version")
    assert_integrity(snapshot)

    freshness = snapshot.get("freshness")
    if not isinstance(freshness, dict):
        raise SnapshotError("E_SNAPSHOT_INVALID", "freshness object is required")
    created = _parse_iso(freshness.get("created_at"), "freshness.created_at")
    expires = _parse_iso(freshness.get("expires_at"), "freshness.expires_at")
    current = _utc(now)
    if expires <= created:
        raise SnapshotError("E_SNAPSHOT_INVALID", "snapshot expiry must follow creation")
    if current >= expires:
        raise SnapshotError(
            "E_STALE_SNAPSHOT",
            f"snapshot expired at {_iso(expires)}",
        )
    return snapshot
