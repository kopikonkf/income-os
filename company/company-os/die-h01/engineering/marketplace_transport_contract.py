"""H01-136 local-only marketplace transport and durable receipt contract.

This module deliberately has no provider, browser, network, credential, or
submission integration.  It validates an H01-134 package manifest or an
H01-135 submission-ready entry, persists a deterministic local receipt, and
records synthetic observations against that receipt.
"""

from __future__ import annotations

import datetime as _datetime
import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "die.h01.marketplace-transport-receipt.v1"
CONTRACT_VERSION = "1.0.0"
MAX_RETRIES = 2
MAX_ATTEMPTS = MAX_RETRIES + 1
BACKOFF_SECONDS = (120, 480)

STATES = (
    "PREPARED",
    "DISPATCHING",
    "REMOTE_ACCEPTED",
    "MODERATION_PENDING",
    "ACCEPTED",
    "REJECTED",
    "RETRYABLE_FAILED",
    "TERMINAL_FAILED",
)

TERMINAL_STATES = frozenset({"ACCEPTED", "REJECTED", "TERMINAL_FAILED"})

TRANSITIONS = {
    "PREPARED": frozenset({"DISPATCHING", "TERMINAL_FAILED"}),
    "DISPATCHING": frozenset({"REMOTE_ACCEPTED", "RETRYABLE_FAILED", "TERMINAL_FAILED"}),
    "REMOTE_ACCEPTED": frozenset({"MODERATION_PENDING"}),
    "MODERATION_PENDING": frozenset({"ACCEPTED", "REJECTED"}),
    "RETRYABLE_FAILED": frozenset({"DISPATCHING", "TERMINAL_FAILED"}),
    "ACCEPTED": frozenset(),
    "REJECTED": frozenset(),
    "TERMINAL_FAILED": frozenset(),
}

DISPATCH_OUTCOMES = {
    "REMOTE_ACCEPTED": {
        "retryable": False,
        "classification": "NONE",
        "failure_code": None,
    },
    "TIMEOUT": {
        "retryable": True,
        "classification": "TRANSIENT_TIMEOUT",
        "failure_code": "DISPATCH_TIMEOUT",
    },
    "RATE_LIMITED": {
        "retryable": True,
        "classification": "RATE_LIMITED",
        "failure_code": "DISPATCH_RATE_LIMITED",
    },
    "TEMPORARY_UNAVAILABLE": {
        "retryable": True,
        "classification": "TEMPORARY_UNAVAILABLE",
        "failure_code": "DISPATCH_TEMPORARY_UNAVAILABLE",
    },
    "REMOTE_5XX": {
        "retryable": True,
        "classification": "REMOTE_5XX",
        "failure_code": "DISPATCH_REMOTE_5XX",
    },
    "INVALID_PACKAGE": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "INVALID_PACKAGE",
    },
    "INELIGIBLE_PACKAGE": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "INELIGIBLE_PACKAGE",
    },
    "POLICY_REJECTED": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "PROVIDER_POLICY_REJECTED",
    },
    "RIGHTS_REJECTED": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "RIGHTS_REJECTED",
    },
    "AUTHORITY_REQUIRED": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "FOUNDER_AUTHORITY_REQUIRED",
    },
    "REMOTE_DUPLICATE": {
        "retryable": False,
        "classification": "NO_RETRY",
        "failure_code": "REMOTE_DUPLICATE",
    },
}

FEEDBACK_CODES = frozenset(
    {
        "CONTENT_POLICY",
        "METADATA_INVALID",
        "RIGHTS_UNCLEAR",
        "QUALITY_REVIEW",
        "DUPLICATE_CONTENT",
        "ACCOUNT_POLICY",
        "PROVIDER_POLICY",
        "UNKNOWN_REJECTION",
    }
)
FEEDBACK_LEARNING_TARGETS = {
    "CONTENT_POLICY": "PACKAGE_POLICY",
    "METADATA_INVALID": "METADATA",
    "RIGHTS_UNCLEAR": "RIGHTS",
    "QUALITY_REVIEW": "QUALITY",
    "DUPLICATE_CONTENT": "DISTINCTNESS",
    "ACCOUNT_POLICY": "ACCOUNT",
    "PROVIDER_POLICY": "MARKETPLACE_POLICY",
    "UNKNOWN_REJECTION": "HUMAN_REVIEW",
}

_ACTION_KEYS = (
    "login_action",
    "upload_action",
    "submission_action",
    "publication_action",
    "spend_action",
)
_FORBIDDEN_SOURCE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "password",
        "refresh_token",
        "session_bytes",
        "session_token",
        "token",
    }
)
_HEX64 = set("0123456789abcdef")
_MARKETPLACE_RE = re.compile(r"^[A-Z][A-Z0-9_-]{1,63}$")
_SEMANTIC_ASSET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class TransportContractError(ValueError):
    """Base error with a stable machine-readable code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class DuplicateSubmissionError(TransportContractError):
    pass


class ReceiptStoreError(TransportContractError):
    pass


class InvalidTransitionError(TransportContractError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _require_sha256(value: Any, detail: str) -> str:
    if not _is_sha256(value):
        raise TransportContractError("HASH_INVALID", detail)
    return str(value)


def _timestamp(value: Any, detail: str) -> str:
    if not isinstance(value, str) or not value:
        raise TransportContractError("TIMESTAMP_REQUIRED", detail)
    if not _RFC3339_RE.fullmatch(value):
        raise TransportContractError("TIMESTAMP_INVALID", detail)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = _datetime.datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise TransportContractError("TIMESTAMP_INVALID", detail) from exc
    if parsed.tzinfo is None:
        raise TransportContractError("TIMESTAMP_TIMEZONE_REQUIRED", detail)
    return value


def _bounded_optional_text(value: Any, detail: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > max_length:
        raise TransportContractError("TEXT_INVALID", detail)
    return value


def _timestamp_value(value: str) -> _datetime.datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return _datetime.datetime.fromisoformat(candidate)


def _timestamp_plus(value: str, seconds: int) -> str:
    parsed = _timestamp_value(value) + _datetime.timedelta(seconds=seconds)
    return parsed.astimezone(_datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _require_not_before(receipt: Mapping[str, Any], observed_at: str) -> None:
    updated_at = receipt.get("updated_at")
    if not isinstance(updated_at, str):
        raise ReceiptStoreError("RECEIPT_TIMESTAMP_INVALID", str(receipt.get("receipt_id")))
    try:
        previous = _timestamp_value(_timestamp(updated_at, "receipt.updated_at"))
    except TransportContractError as exc:
        raise ReceiptStoreError("RECEIPT_TIMESTAMP_INVALID", str(receipt.get("receipt_id"))) from exc
    if _timestamp_value(observed_at) < previous:
        raise InvalidTransitionError("TIMESTAMP_REGRESSION", f"{observed_at} < {updated_at}")


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            found.add(str(key).casefold())
            found.update(_walk_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_walk_keys(nested))
    return found


def _check_action_lock(source: Mapping[str, Any]) -> None:
    for key in _ACTION_KEYS:
        if source.get(key, "NONE") != "NONE":
            raise TransportContractError("EXTERNAL_ACTION_NOT_ALLOWED", key)
    for key in ("action", "external_action"):
        if source.get(key, "NONE") != "NONE":
            raise TransportContractError("EXTERNAL_ACTION_NOT_ALLOWED", key)
    actions = source.get("actions")
    if isinstance(actions, Mapping) and any(value != "NONE" for value in actions.values()):
        raise TransportContractError("EXTERNAL_ACTION_NOT_ALLOWED", "actions")


def _eligibility_from_manifest(source: Mapping[str, Any]) -> None:
    if source.get("submission_eligible") is not True:
        raise TransportContractError("INELIGIBLE_PACKAGE", "submission_eligible is not true")
    compatibility = source.get("compatibility")
    if not isinstance(compatibility, Mapping) or not (
        compatibility.get("status") == "COMPATIBLE"
        or compatibility.get("result") == "PASS"
    ):
        raise TransportContractError("INELIGIBLE_PACKAGE", "compatibility is not PASS")
    rights = source.get("rights_signal")
    if not isinstance(rights, Mapping) or rights.get("result") != "PASS":
        raise TransportContractError("INELIGIBLE_PACKAGE", "rights signal is not PASS")
    if source.get("founder_qc") != "PASS":
        raise TransportContractError("INELIGIBLE_PACKAGE", "Founder QC is not PASS")


def _eligibility_from_entry(source: Mapping[str, Any]) -> None:
    eligibility = source.get("eligibility")
    if not isinstance(eligibility, Mapping):
        raise TransportContractError("INELIGIBLE_PACKAGE", "eligibility object missing")
    if eligibility.get("submission_eligible") is not True:
        raise TransportContractError("INELIGIBLE_PACKAGE", "entry is not eligible")
    if eligibility.get("compatibility") != "PASS":
        raise TransportContractError("INELIGIBLE_PACKAGE", "compatibility is not PASS")
    if eligibility.get("rights") != "PASS":
        raise TransportContractError("INELIGIBLE_PACKAGE", "rights is not PASS")
    if eligibility.get("founder_qc") != "PASS":
        raise TransportContractError("INELIGIBLE_PACKAGE", "Founder QC is not PASS")


def _identity_fields(source: Mapping[str, Any]) -> tuple[str, str, str, str | None, list[dict[str, Any]], str]:
    schema = source.get("schema")
    if schema == "die.h01.marketplace-delivery-package.v1":
        source_kind = "H01_134_MANIFEST"
        _eligibility_from_manifest(source)
        marketplace = source.get("marketplace")
        semantic_asset_id = source.get("semantic_asset_id")
        artifacts = source.get("artifacts")
        sidecar = source.get("sidecar_metadata") or {}
        source_manifest_sha = source.get("manifest_file_sha256")
    elif schema == "die.h01.submission-ready-entry.v1":
        source_kind = "H01_135_ENTRY"
        _eligibility_from_entry(source)
        marketplace = source.get("marketplace")
        semantic_asset_id = source.get("semantic_asset_id")
        artifacts = source.get("files")
        sidecar = {}
        source_manifest_sha = source.get("source_manifest_sha256")
    else:
        raise TransportContractError("SOURCE_SCHEMA_UNSUPPORTED", str(schema))

    if not isinstance(marketplace, str) or not _MARKETPLACE_RE.fullmatch(marketplace):
        raise TransportContractError("SOURCE_IDENTITY_INVALID", "marketplace")
    if not isinstance(semantic_asset_id, str) or not _SEMANTIC_ASSET_ID_RE.fullmatch(semantic_asset_id):
        raise TransportContractError("SOURCE_IDENTITY_INVALID", "semantic_asset_id")
    if not isinstance(artifacts, list) or not artifacts:
        raise TransportContractError("PACKAGE_FILES_MISSING", "files/artifacts")

    normalized: list[dict[str, Any]] = []
    names: set[str] = set()
    for row in artifacts:
        if not isinstance(row, Mapping):
            raise TransportContractError("PACKAGE_FILE_INVALID", "file row is not an object")
        name = row.get("target") if schema == "die.h01.marketplace-delivery-package.v1" else row.get("path")
        if (
            not isinstance(name, str)
            or not name
            or len(name) > 4096
            or name in names
            or name.startswith("/")
            or "\\" in name
            or ".." in Path(name).parts
        ):
            raise TransportContractError("PACKAGE_FILE_INVALID", str(name))
        digest = _require_sha256(row.get("sha256"), f"file hash: {name}")
        byte_count = row.get("bytes")
        if byte_count is not None and (
            not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0
        ):
            raise TransportContractError("PACKAGE_FILE_INVALID", f"file bytes: {name}")
        names.add(name)
        normalized.append({"path": name, "sha256": digest, "bytes": byte_count})

    # H01-134's sidecar is part of the H01-135 projection and therefore part
    # of the same content identity even though the source field is different.
    if schema == "die.h01.marketplace-delivery-package.v1" and sidecar:
        sidecar_path = sidecar.get("path", "files/metadata.json")
        sidecar_name = "metadata.json" if str(sidecar_path).endswith("metadata.json") else str(sidecar_path)
        if (
            not sidecar_name
            or len(sidecar_name) > 4096
            or sidecar_name.startswith("/")
            or "\\" in sidecar_name
            or ".." in Path(sidecar_name).parts
        ):
            raise TransportContractError("PACKAGE_FILE_INVALID", sidecar_name)
        sidecar_sha = _require_sha256(sidecar.get("sha256"), "sidecar hash")
        sidecar_bytes = sidecar.get("bytes")
        if sidecar_bytes is not None and (
            not isinstance(sidecar_bytes, int)
            or isinstance(sidecar_bytes, bool)
            or sidecar_bytes < 0
        ):
            raise TransportContractError("PACKAGE_FILE_INVALID", f"file bytes: {sidecar_name}")
        existing_sidecar = next((row for row in normalized if row["path"] == sidecar_name), None)
        if existing_sidecar is not None and existing_sidecar["sha256"] != sidecar_sha:
            raise TransportContractError("PACKAGE_FILE_HASH_CONFLICT", sidecar_name)
        if existing_sidecar is None:
            normalized.append({"path": sidecar_name, "sha256": sidecar_sha, "bytes": sidecar_bytes})
            names.add(sidecar_name)

    normalized.sort(key=lambda row: row["path"])
    if source_manifest_sha is not None:
        source_manifest_sha = _require_sha256(source_manifest_sha, "source manifest hash")
    elif schema == "die.h01.submission-ready-entry.v1":
        raise TransportContractError("HASH_INVALID", "source manifest hash")
    package_digest = sha256_json(
        {
            "marketplace": marketplace,
            "semantic_asset_id": semantic_asset_id,
            "files": normalized,
        }
    )
    return source_kind, marketplace, semantic_asset_id, source_manifest_sha, normalized, package_digest


def normalize_source(source: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise TransportContractError("SOURCE_OBJECT_REQUIRED", "source")
    forbidden = _walk_keys(source) & _FORBIDDEN_SOURCE_KEYS
    if forbidden:
        raise TransportContractError("SECRET_FIELD_FORBIDDEN", sorted(forbidden)[0])
    _check_action_lock(source)
    source_kind, marketplace, semantic_asset_id, source_manifest_sha, files, package_digest = _identity_fields(source)
    return {
        "source_kind": source_kind,
        "marketplace": marketplace,
        "semantic_asset_id": semantic_asset_id,
        "package_digest": package_digest,
        "source_manifest_sha256": source_manifest_sha,
        "files": files,
    }


def idempotency_key(*, marketplace: str, semantic_asset_id: str, package_digest: str) -> str:
    return sha256_json(
        {
            "contract": SCHEMA,
            "marketplace": marketplace,
            "semantic_asset_id": semantic_asset_id,
            "package_digest": package_digest,
        }
    )


def duplicate_scope_key(*, marketplace: str, semantic_asset_id: str) -> str:
    return sha256_json(
        {
            "contract": SCHEMA,
            "marketplace": marketplace,
            "semantic_asset_id": semantic_asset_id,
        }
    )


def classify_dispatch_outcome(outcome: str) -> dict[str, Any]:
    if outcome not in DISPATCH_OUTCOMES:
        raise TransportContractError("OUTCOME_UNSUPPORTED", outcome)
    return dict(DISPATCH_OUTCOMES[outcome])


def _serialize(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


class ReceiptStore:
    """Small local receipt store; no remote or external action is available."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _exclusive(self):
        lock_path = self.root / ".receipt-store.lock"
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _path(self, receipt_id: str) -> Path:
        if not receipt_id.startswith("H01-136-") or "/" in receipt_id or "\\" in receipt_id:
            raise ReceiptStoreError("RECEIPT_ID_INVALID", receipt_id)
        return self.root / f"{receipt_id}.json"

    def load(self, receipt_id: str) -> dict[str, Any]:
        path = self._path(receipt_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ReceiptStoreError("RECEIPT_NOT_FOUND", receipt_id) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ReceiptStoreError("RECEIPT_READ_FAILED", receipt_id) from exc
        if not isinstance(value, dict):
            raise ReceiptStoreError("RECEIPT_OBJECT_REQUIRED", receipt_id)
        return value

    def find_by(self, *, key: str, value: str) -> dict[str, Any] | None:
        for path in sorted(self.root.glob("H01-136-*.json")):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ReceiptStoreError("RECEIPT_READ_FAILED", str(path)) from exc
            if not isinstance(row, dict):
                raise ReceiptStoreError("RECEIPT_OBJECT_REQUIRED", str(path))
            if row.get(key) == value:
                return row
        return None

    def create_prepared_once(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        with self._exclusive():
            idem = str(receipt.get("idempotency_key", ""))
            scope = str(receipt.get("duplicate_scope_key", ""))
            existing = self.find_by(key="idempotency_key", value=idem)
            if existing is not None:
                return existing
            scoped = self.find_by(key="duplicate_scope_key", value=scope)
            if scoped is not None:
                source = receipt.get("source") or {}
                raise DuplicateSubmissionError(
                    "DUPLICATE_SCOPE_CONFLICT",
                    f"{source.get('marketplace')}/{source.get('semantic_asset_id')} already has receipt {scoped.get('receipt_id')}",
                )
            return self.write(receipt)

    def write(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        receipt_id = str(receipt.get("receipt_id", ""))
        path = self._path(receipt_id)
        data = _serialize(receipt)
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ReceiptStoreError("RECEIPT_COLLISION", receipt_id) from exc
            if not isinstance(existing, dict) or existing.get("idempotency_key") != receipt.get("idempotency_key"):
                raise ReceiptStoreError("RECEIPT_COLLISION", receipt_id)

        fd, temporary = tempfile.mkstemp(prefix=f".{receipt_id}.", suffix=".tmp", dir=self.root)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return dict(receipt)


class LocalTransportContract:
    """Prepare receipts and record only synthetic observations."""

    def __init__(self, store: ReceiptStore):
        self.store = store

    def prepare(self, source: Mapping[str, Any], *, prepared_at: str) -> dict[str, Any]:
        prepared_at = _timestamp(prepared_at, "prepared_at")
        normalized = normalize_source(source)
        idem = idempotency_key(
            marketplace=normalized["marketplace"],
            semantic_asset_id=normalized["semantic_asset_id"],
            package_digest=normalized["package_digest"],
        )
        scope = duplicate_scope_key(
            marketplace=normalized["marketplace"],
            semantic_asset_id=normalized["semantic_asset_id"],
        )
        receipt: dict[str, Any] = {
            "schema": SCHEMA,
            "contract_version": CONTRACT_VERSION,
            "receipt_id": f"H01-136-{idem[:32]}",
            "idempotency_key": idem,
            "duplicate_scope_key": scope,
            "source": normalized,
            "state": "PREPARED",
            "state_history": [
                {"from": None, "to": "PREPARED", "at": prepared_at, "reason": "LOCAL_PACKAGE_VALIDATED"}
            ],
            "attempt_count": 0,
            "retry": {
                "classification": "NOT_ATTEMPTED",
                "retryable": False,
                "retry_count": 0,
                "max_retries": MAX_RETRIES,
                "backoff_seconds": list(BACKOFF_SECONDS),
                "next_retry_at": None,
            },
            "remote": {
                "remote_reference": None,
                "remote_reference_kind": "OPAQUE",
                "remote_status": None,
                "received_at": None,
            },
            "moderation": {
                "status": "NOT_STARTED",
                "moderation_reference": None,
                "feedback": [],
                "observed_at": None,
            },
            "failure": None,
            "authority": {
                "gate": "FOUNDER_APPROVAL_REQUIRED_BEFORE_EXTERNAL_ACTION",
                "founder_authorized": False,
                "submission_authorized": False,
                "publication_authorized": False,
                "external_action_performed": False,
                "credential_accessed": False,
            },
            "actions": {
                "login": "NONE",
                "upload": "NONE",
                "submission": "NONE",
                "publication": "NONE",
                "spend": "NONE",
            },
            "prepared_at": prepared_at,
            "updated_at": prepared_at,
        }
        return self.store.create_prepared_once(receipt)

    def _load(self, receipt_id: str) -> dict[str, Any]:
        return self.store.load(receipt_id)

    def _save_transition(self, receipt: dict[str, Any], state: str, at: str, reason: str) -> None:
        current = str(receipt.get("state"))
        if state not in STATES or state not in TRANSITIONS.get(current, frozenset()):
            raise InvalidTransitionError("TRANSITION_INVALID", f"{current} -> {state}")
        receipt["state_history"].append({"from": current, "to": state, "at": at, "reason": reason})
        receipt["state"] = state
        receipt["updated_at"] = at
        self.store.write(receipt)

    def record_synthetic_dispatch(
        self,
        receipt_id: str,
        *,
        outcome: str,
        observed_at: str,
        remote_reference: str | None = None,
        remote_status: str | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        with self.store._exclusive():
            return self._record_synthetic_dispatch(
                receipt_id,
                outcome=outcome,
                observed_at=observed_at,
                remote_reference=remote_reference,
                remote_status=remote_status,
                detail=detail,
            )

    def _record_synthetic_dispatch(
        self,
        receipt_id: str,
        *,
        outcome: str,
        observed_at: str,
        remote_reference: str | None = None,
        remote_status: str | None = None,
        detail: str | None = None,
    ) -> dict[str, Any]:
        observed_at = _timestamp(observed_at, "observed_at")
        detail = _bounded_optional_text(detail, "detail", max_length=2000)
        receipt = self._load(receipt_id)
        _require_not_before(receipt, observed_at)
        classification = classify_dispatch_outcome(outcome)
        current = str(receipt.get("state"))

        if remote_reference is not None and (not isinstance(remote_reference, str) or not remote_reference or len(remote_reference) > 512):
            raise TransportContractError("OPAQUE_REMOTE_REFERENCE_INVALID", "remote_reference")
        if remote_status is not None and (not isinstance(remote_status, str) or len(remote_status) > 120):
            raise TransportContractError("REMOTE_STATUS_INVALID", "remote_status")

        if current in TERMINAL_STATES:
            raise InvalidTransitionError("TERMINAL_RECEIPT_IMMUTABLE", receipt_id)
        if current == "RETRYABLE_FAILED":
            next_retry_at = receipt.get("retry", {}).get("next_retry_at")
            if isinstance(next_retry_at, str) and _timestamp_value(observed_at) < _timestamp_value(next_retry_at):
                raise InvalidTransitionError("BACKOFF_NOT_ELAPSED", next_retry_at)
            receipt["attempt_count"] = int(receipt.get("attempt_count", 0)) + 1
            self._save_transition(receipt, "DISPATCHING", observed_at, "RETRY_ATTEMPT_STARTED")
        elif current == "PREPARED":
            receipt["attempt_count"] = 1
            self._save_transition(receipt, "DISPATCHING", observed_at, "SYNTHETIC_DISPATCH_STARTED")
        elif current != "DISPATCHING":
            raise InvalidTransitionError("DISPATCH_STATE_REQUIRED", current)

        if int(receipt["attempt_count"]) > MAX_ATTEMPTS:
            raise InvalidTransitionError("ATTEMPT_LIMIT_EXCEEDED", receipt_id)

        if remote_reference is not None:
            receipt["remote"]["remote_reference"] = remote_reference
        receipt["remote"]["remote_status"] = remote_status
        receipt["remote"]["received_at"] = observed_at if outcome == "REMOTE_ACCEPTED" else receipt["remote"].get("received_at")

        if classification["retryable"]:
            retry_count = int(receipt["attempt_count"])
            retry = receipt["retry"]
            retry["retry_count"] = min(retry_count, MAX_RETRIES)
            retry["classification"] = classification["classification"]
            retry["retryable"] = retry_count < MAX_ATTEMPTS
            retry["next_retry_at"] = _timestamp_plus(observed_at, BACKOFF_SECONDS[retry_count - 1]) if retry_count < MAX_ATTEMPTS else None
            if retry_count < MAX_ATTEMPTS:
                receipt["failure"] = {"code": classification["failure_code"], "detail": detail}
                self._save_transition(receipt, "RETRYABLE_FAILED", observed_at, classification["failure_code"])
            else:
                retry["classification"] = "RETRIES_EXHAUSTED"
                receipt["failure"] = {"code": "RETRIES_EXHAUSTED", "detail": detail}
                self._save_transition(receipt, "TERMINAL_FAILED", observed_at, "RETRIES_EXHAUSTED")
        elif outcome == "REMOTE_ACCEPTED":
            receipt["retry"] = {
                "classification": "NONE",
                "retryable": False,
                "retry_count": int(receipt["retry"].get("retry_count", 0)),
                "max_retries": MAX_RETRIES,
                "backoff_seconds": list(BACKOFF_SECONDS),
                "next_retry_at": None,
            }
            receipt["failure"] = None
            self._save_transition(receipt, "REMOTE_ACCEPTED", observed_at, "SYNTHETIC_REMOTE_ACCEPTED")
        else:
            receipt["retry"] = {
                "classification": "NO_RETRY",
                "retryable": False,
                "retry_count": int(receipt["retry"].get("retry_count", 0)),
                "max_retries": MAX_RETRIES,
                "backoff_seconds": list(BACKOFF_SECONDS),
                "next_retry_at": None,
            }
            receipt["failure"] = {"code": classification["failure_code"], "detail": detail}
            self._save_transition(receipt, "TERMINAL_FAILED", observed_at, classification["failure_code"])
        return receipt

    def record_synthetic_moderation(
        self,
        receipt_id: str,
        *,
        status: str,
        observed_at: str,
        moderation_reference: str | None = None,
        feedback: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self.store._exclusive():
            return self._record_synthetic_moderation(
                receipt_id,
                status=status,
                observed_at=observed_at,
                moderation_reference=moderation_reference,
                feedback=feedback,
            )

    def _record_synthetic_moderation(
        self,
        receipt_id: str,
        *,
        status: str,
        observed_at: str,
        moderation_reference: str | None = None,
        feedback: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        observed_at = _timestamp(observed_at, "observed_at")
        receipt = self._load(receipt_id)
        _require_not_before(receipt, observed_at)
        current = str(receipt.get("state"))
        if status not in {"PENDING", "ACCEPTED", "REJECTED"}:
            raise TransportContractError("MODERATION_STATUS_UNSUPPORTED", status)
        if moderation_reference is not None and (not isinstance(moderation_reference, str) or not moderation_reference or len(moderation_reference) > 512):
            raise TransportContractError("OPAQUE_MODERATION_REFERENCE_INVALID", "moderation_reference")
        rows = []
        for item in feedback or []:
            if not isinstance(item, Mapping) or item.get("code") not in FEEDBACK_CODES:
                raise TransportContractError("FEEDBACK_CODE_UNSUPPORTED", str(item))
            detail = _bounded_optional_text(item.get("detail"), "feedback detail", max_length=2000)
            rows.append(
                {
                    "code": item["code"],
                    "detail": detail,
                    "learning_target": FEEDBACK_LEARNING_TARGETS[item["code"]],
                }
            )
        if status == "REJECTED" and not rows:
            raise TransportContractError("REJECTION_FEEDBACK_REQUIRED", "feedback")

        if current in TERMINAL_STATES:
            raise InvalidTransitionError("TERMINAL_RECEIPT_IMMUTABLE", receipt_id)
        if current == "REMOTE_ACCEPTED":
            self._save_transition(receipt, "MODERATION_PENDING", observed_at, "SYNTHETIC_MODERATION_OBSERVED")
        elif current != "MODERATION_PENDING":
            raise InvalidTransitionError("MODERATION_STATE_REQUIRED", current)

        receipt["moderation"] = {
            "status": status,
            "moderation_reference": moderation_reference,
            "feedback": rows,
            "observed_at": observed_at,
        }
        if status == "PENDING":
            receipt["updated_at"] = observed_at
            self.store.write(receipt)
        else:
            self._save_transition(receipt, status, observed_at, f"SYNTHETIC_MODERATION_{status}")
        return receipt


__all__ = [
    "BACKOFF_SECONDS",
    "DISPATCH_OUTCOMES",
    "FEEDBACK_CODES",
    "FEEDBACK_LEARNING_TARGETS",
    "LocalTransportContract",
    "ReceiptStore",
    "ReceiptStoreError",
    "TransportContractError",
    "DuplicateSubmissionError",
    "InvalidTransitionError",
    "classify_dispatch_outcome",
    "duplicate_scope_key",
    "idempotency_key",
    "normalize_source",
    "sha256_json",
]
