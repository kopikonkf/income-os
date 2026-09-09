from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

SCHEMA = "die.h03.economic-observation.v1"
_ALLOWED_TYPES = {"RESOURCE_USAGE", "FOUNDER_TIME", "COST_DIRECT_VARIABLE"}
_COMPANY_LIB = Path(__file__).resolve().parents[2] / "company-os" / "lib"
if str(_COMPANY_LIB) not in sys.path:
    sys.path.insert(0, str(_COMPANY_LIB))
import economic_admission  # type: ignore


def validate_observation(obs: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obs, dict) or obs.get("schema_version") != SCHEMA or obs.get("holding_id") != "H03":
        raise ValueError("H03_ECON_OBSERVATION_SCHEMA_INVALID")
    for field in ("observation_id","observed_at","economic_trace_id","parent_task_id","provenance_ref"):
        if not isinstance(obs.get(field), str) or not obs[field].strip():
            raise ValueError(f"H03_ECON_OBSERVATION_FIELD_REQUIRED:{field}")
    if obs.get("event_type") not in _ALLOWED_TYPES:
        raise ValueError("H03_ECON_OBSERVATION_TYPE_INVALID")
    if obs.get("measurement_state") not in {"OBSERVED","UNKNOWN"}:
        raise ValueError("H03_ECON_OBSERVATION_STATE_INVALID")
    refs = obs.get("evidence_refs")
    if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)) or obs["provenance_ref"] not in refs:
        raise ValueError("H03_ECON_OBSERVATION_EVIDENCE_INVALID")
    if obs["measurement_state"] == "UNKNOWN":
        if obs.get("payload") is not None:
            raise ValueError("H03_ECON_UNKNOWN_MUST_NOT_HAVE_VALUE")
    elif not isinstance(obs.get("payload"), dict):
        raise ValueError("H03_ECON_OBSERVED_PAYLOAD_REQUIRED")
    return obs


def _event_id(obs: dict[str, Any]) -> str:
    digest = hashlib.sha256((obs["observation_id"] + "|" + obs["economic_trace_id"]).encode("utf-8")).hexdigest()[:20].upper()
    return "ECON-EVT-H03_" + digest


def _authority() -> dict[str, bool]:
    return {"bank_integration":False,"payment_action":False,"spend_authorized":False,"capital_allocation_authorized":False,"credentials_embedded":False,"mutable_after_append":False}


def build_ledger_event(obs: dict[str, Any]) -> dict[str, Any]:
    validate_observation(obs)
    if obs["measurement_state"] != "OBSERVED":
        raise ValueError("H03_ECON_UNMEASURED_NOT_ADMISSIBLE")
    payload = obs["payload"]
    event = {
        "schema_version":"die.economic-ledger.event.v1",
        "event_id":_event_id(obs),
        "observed_at":obs["observed_at"],
        "event_type":obs["event_type"],
        "holding_id":"H03",
        "economic_trace_id":obs["economic_trace_id"],
        "parent_task_id":obs["parent_task_id"],
        "incident_id":None,
        "source_system":"H03_KNOWLEDGE_PRODUCT_FACTORY",
        "source_event_id":obs["observation_id"],
        "idempotency_key":"h03-shadow:" + obs["observation_id"],
        "provenance_ref":obs["provenance_ref"],
        "reversal_of_event_id":None,
        "authority_boundary":_authority(),
        "metadata":{"measurement_state":"OBSERVED"}
    }
    if obs["event_type"] == "RESOURCE_USAGE":
        event["resource_usage"] = payload
    elif obs["event_type"] == "FOUNDER_TIME":
        event["founder_time"] = payload
    elif obs["event_type"] == "COST_DIRECT_VARIABLE":
        event["money"] = payload
    return event


def prepare_shadow_admission(obs: dict[str, Any]) -> dict[str, Any]:
    event = build_ledger_event(obs)
    return economic_admission.prepare_admission(event, evidence_refs=list(obs["evidence_refs"]), holding_id="H03")
