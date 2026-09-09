from __future__ import annotations

from typing import Any, Callable

SCHEMA = "die.h03.mission-batch-supervision.v1"
_ALLOWED_STATUS = {"PLANNED","RUNNING","BLOCKED","AWAITING_FOUNDER","COMPLETED","FAILED"}
_FORBIDDEN_KEYS = {"cookie","cookies","token","tokens","lease_token","review_token","access_token","refresh_token","authorization","oauth","session_key","session_bytes","credentials","credential","browser_profile_path","profile_path","user_data_dir","prompt","messages"}
_EVENT_TO_METHOD = {
    "BATCH_STARTED": "mission.task.checkpoint",
    "BATCH_CHECKPOINT": "mission.task.checkpoint",
    "BATCH_COMPLETED": "mission.task.complete",
    "BATCH_BLOCKED": "mission.task.block",
    "FOUNDER_GATE_REQUIRED": "mission.founder.request",
}


def _scan(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise ValueError(f"SUPERVISION_SECRET_OR_MICROJOB_PAYLOAD_FORBIDDEN:{path}.{key}")
            _scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _scan(child, f"{path}[{idx}]")


def validate_batch_state(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict) or state.get("schema_version") != SCHEMA or state.get("holding_id") != "H03":
        raise ValueError("SUPERVISION_SCHEMA_INVALID")
    for field in ("batch_id","mission_task_id"):
        if not isinstance(state.get(field), str) or not state[field].strip():
            raise ValueError(f"SUPERVISION_FIELD_REQUIRED:{field}")
    if state.get("status") not in _ALLOWED_STATUS:
        raise ValueError("SUPERVISION_STATUS_INVALID")
    progress = state.get("progress_percent")
    if not isinstance(progress, int) or not 0 <= progress <= 100:
        raise ValueError("SUPERVISION_PROGRESS_INVALID")
    products = state.get("product_ids")
    if not isinstance(products, list) or len(products) != len(set(products)) or any(not isinstance(x, str) or not x.strip() for x in products):
        raise ValueError("SUPERVISION_PRODUCT_IDS_INVALID")
    counts = state.get("stage_counts")
    if not isinstance(counts, dict) or any(not isinstance(k, str) or not isinstance(v, int) or v < 0 for k, v in counts.items()):
        raise ValueError("SUPERVISION_STAGE_COUNTS_INVALID")
    if not isinstance(state.get("microjob_count"), int) or state["microjob_count"] < 0:
        raise ValueError("SUPERVISION_MICROJOB_COUNT_INVALID")
    refs = state.get("artifact_refs")
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or any(not isinstance(x, str) or not x.strip() for x in refs):
        raise ValueError("SUPERVISION_ARTIFACT_REFS_INVALID")
    for optional in ("failure_summary","recovery_summary","founder_gate"):
        if state.get(optional) is not None and not isinstance(state[optional], dict):
            raise ValueError(f"SUPERVISION_{optional.upper()}_INVALID")
    _scan(state)
    return state


def project_supervision_payload(state: dict[str, Any]) -> dict[str, Any]:
    validate_batch_state(state)
    return {
        "holding_id": "H03",
        "batch_id": state["batch_id"],
        "status": state["status"],
        "progress_percent": state["progress_percent"],
        "product_count": len(state["product_ids"]),
        "product_ids": list(state["product_ids"]),
        "stage_counts": dict(state["stage_counts"]),
        "microjob_count": state["microjob_count"],
        "artifact_refs": list(state["artifact_refs"]),
        "failure_summary": state["failure_summary"],
        "recovery_summary": state["recovery_summary"],
        "founder_gate": state["founder_gate"],
    }


def build_mission_intent(*, event: str, state: dict[str, Any], summary: str) -> dict[str, Any]:
    validate_batch_state(state)
    if event not in _EVENT_TO_METHOD:
        raise ValueError("SUPERVISION_EVENT_INVALID")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("SUPERVISION_SUMMARY_REQUIRED")
    method = _EVENT_TO_METHOD[event]
    projected = project_supervision_payload(state)
    intent: dict[str, Any] = {
        "schema_version": "die.h03.mission-intent.v1",
        "mission_method": method,
        "mission_task_id": state["mission_task_id"],
        "summary": summary.strip(),
        "payload": projected,
        "auth_injected_at_invoke": True,
        "microjob_protocol_call": False,
    }
    if method == "mission.task.checkpoint":
        intent["progress"] = state["progress_percent"]
    elif method == "mission.task.complete":
        if state["status"] != "COMPLETED" or state["progress_percent"] != 100:
            raise ValueError("SUPERVISION_COMPLETE_STATE_INVALID")
        intent["result"] = projected
        intent["artifacts"] = list(state["artifact_refs"])
    elif method == "mission.task.block":
        if state["status"] not in {"BLOCKED","FAILED"}:
            raise ValueError("SUPERVISION_BLOCK_STATE_INVALID")
        failure = state.get("failure_summary") or {}
        intent["reason"] = str(failure.get("reason") or summary).strip()
        intent["retryable"] = bool(failure.get("retryable", False))
        intent["founder_required"] = bool(failure.get("founder_required", False))
    elif method == "mission.founder.request":
        if state["status"] != "AWAITING_FOUNDER" or not state.get("founder_gate"):
            raise ValueError("SUPERVISION_FOUNDER_GATE_STATE_INVALID")
        gate = state["founder_gate"]
        intent["kind"] = str(gate.get("kind") or "H03_FOUNDER_GATE")
        intent["title"] = str(gate.get("title") or f"H03 Founder gate: {state['batch_id']}")
        intent["body"] = str(gate.get("body") or summary)
    _scan(intent)
    return intent


def invoke_mission_intent(*, intent: dict[str, Any], principal_id: str, lease_token: str, transport: Callable[[str, dict[str, Any]], Any]) -> Any:
    if not isinstance(principal_id, str) or not principal_id.strip() or not isinstance(lease_token, str) or not lease_token:
        raise ValueError("SUPERVISION_EPHEMERAL_AUTH_REQUIRED")
    if not callable(transport):
        raise ValueError("SUPERVISION_TRANSPORT_REQUIRED")
    method = intent.get("mission_method")
    if method not in _EVENT_TO_METHOD.values():
        raise ValueError("SUPERVISION_MISSION_METHOD_INVALID")
    base = {
        "taskId": intent["mission_task_id"],
        "principalId": principal_id,
        "leaseToken": lease_token,
    }
    if method == "mission.task.checkpoint":
        base.update({"summary":intent["summary"],"progress":intent["progress"],"payload":intent["payload"]})
    elif method == "mission.task.complete":
        base.update({"summary":intent["summary"],"result":intent["result"],"artifacts":intent["artifacts"]})
    elif method == "mission.task.block":
        base.update({"reason":intent["reason"],"retryable":intent["retryable"],"founderRequired":intent["founder_required"]})
    elif method == "mission.founder.request":
        base.update({"kind":intent["kind"],"title":intent["title"],"body":intent["body"]})
    return transport(method, base)
