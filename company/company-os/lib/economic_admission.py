from __future__ import annotations

from copy import deepcopy
from typing import Any

import economic_contracts

SCHEMA_VERSION = "die.economic-ledger.admission.v1"
WRITER_ID = "die-state-manager"
STATUS = "validated_not_committed"
AUTHORITY_FIELDS = {
    "canonical_commit_authorized",
    "live_ingestion_authorized",
    "spend_authorized",
    "payment_action",
    "capital_allocation_authorized",
    "credential_access",
    "external_submission",
}


class EconomicAdmissionError(ValueError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}:{message}" if message else code)
        self.code = code
        self.message = message


def _shadow_authority() -> dict[str, bool]:
    return {key: False for key in sorted(AUTHORITY_FIELDS)}


def _validate_evidence_refs(refs: Any, provenance_ref: str) -> list[str]:
    if not isinstance(refs, list) or not refs:
        raise EconomicAdmissionError("E_ECON_ADMISSION_EVIDENCE_REQUIRED")
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise EconomicAdmissionError("E_ECON_ADMISSION_EVIDENCE_INVALID")
    if len(refs) != len(set(refs)):
        raise EconomicAdmissionError("E_ECON_ADMISSION_EVIDENCE_DUPLICATE")
    if provenance_ref not in refs:
        raise EconomicAdmissionError("E_ECON_ADMISSION_PROVENANCE_NOT_EVIDENCED")
    return list(refs)


def prepare_admission(event: dict[str, Any], *, evidence_refs: list[str], holding_id: str) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EconomicAdmissionError("E_ECON_ADMISSION_EVENT_OBJECT_REQUIRED")
    normalized = economic_contracts.validate_ledger_event(deepcopy(event))
    if normalized.get("holding_id") != holding_id:
        raise EconomicAdmissionError("E_ECON_ADMISSION_HOLDING_MISMATCH")
    refs = _validate_evidence_refs(evidence_refs, normalized["provenance_ref"])
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "writer": WRITER_ID,
        "holding_id": holding_id,
        "event": normalized,
        "evidence_refs": refs,
        "authority_boundary": _shadow_authority(),
    }


def validate_admission(payload: Any) -> dict[str, Any]:
    required = {
        "schema_version", "status", "writer", "holding_id",
        "event", "evidence_refs", "authority_boundary",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise EconomicAdmissionError("E_ECON_ADMISSION_FIELDS")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise EconomicAdmissionError("E_ECON_ADMISSION_SCHEMA")
    if payload.get("status") != STATUS or payload.get("writer") != WRITER_ID:
        raise EconomicAdmissionError("E_ECON_ADMISSION_NOT_SHADOW")
    auth = payload.get("authority_boundary")
    if not isinstance(auth, dict) or set(auth) != AUTHORITY_FIELDS:
        raise EconomicAdmissionError("E_ECON_ADMISSION_AUTHORITY_FIELDS")
    if any(auth.get(key) is not False for key in AUTHORITY_FIELDS):
        raise EconomicAdmissionError("E_ECON_ADMISSION_AUTHORITY_WIDENING")
    event = economic_contracts.validate_ledger_event(deepcopy(payload.get("event")))
    if event.get("holding_id") != payload.get("holding_id"):
        raise EconomicAdmissionError("E_ECON_ADMISSION_HOLDING_MISMATCH")
    _validate_evidence_refs(payload.get("evidence_refs"), event["provenance_ref"])
    return payload
