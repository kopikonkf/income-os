from __future__ import annotations

from typing import Any

CARD_SCHEMA = "die.h03.cognition-work-card.v1"
RESULT_SCHEMA = "die.h03.cognition-worker-result.v1"
ROLES = {"SEED_CURATOR","MARKET_RESEARCHER","KNOWLEDGE_RESEARCHER","SYNTHESIZER","PRODUCT_ARCHITECT","PRODUCER","REVIEWER","GROWTH_PRODUCER"}
TERMINAL = {"SUCCEEDED","FAILED_RETRYABLE","FAILED_TERMINAL","CANCELLED"}
_FORBIDDEN = {"cookie","cookies","token","tokens","access_token","refresh_token","authorization","oauth","session_key","session_bytes","credentials","credential","browser_profile_path"}


def _scan(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _FORBIDDEN:
                raise ValueError(f"WORKER_SECRET_MATERIAL_FORBIDDEN:{path}.{k}")
            _scan(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan(item, f"{path}[{i}]")


def validate_work_card(card: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(card, dict) or card.get("schema_version") != CARD_SCHEMA or card.get("holding_id") != "H03":
        raise ValueError("WORK_CARD_SCHEMA_INVALID")
    for field in ("work_card_id","task_id","queue","idempotency_key"):
        if not isinstance(card.get(field), str) or not card[field].strip():
            raise ValueError(f"WORK_CARD_FIELD_REQUIRED:{field}")
    if len(card["idempotency_key"]) < 8:
        raise ValueError("WORK_CARD_IDEMPOTENCY_KEY_SHORT")
    if card.get("role") not in ROLES:
        raise ValueError("WORK_CARD_ROLE_INVALID")
    inputs = card.get("input_artifacts")
    if not isinstance(inputs, list):
        raise ValueError("WORK_CARD_INPUTS_INVALID")
    for item in inputs:
        if not isinstance(item, dict) or any(not item.get(k) for k in ("artifact_id","kind","ref")):
            raise ValueError("WORK_CARD_ARTIFACT_REF_INVALID")
    out = card.get("output_contract")
    if not isinstance(out, dict) or not out.get("artifact_kind") or not out.get("schema_version"):
        raise ValueError("WORK_CARD_OUTPUT_CONTRACT_INVALID")
    caps = card.get("capability_requirements")
    if not isinstance(caps, dict) or set(caps) != {"web_ai","mcp","shell","local_filesystem"} or any(not isinstance(v, bool) for v in caps.values()):
        raise ValueError("WORK_CARD_CAPABILITIES_INVALID")
    policy = card.get("terminal_policy")
    if not isinstance(policy, dict) or not isinstance(policy.get("max_attempts"), int) or policy["max_attempts"] < 1:
        raise ValueError("WORK_CARD_TERMINAL_POLICY_INVALID")
    _scan(card)
    return card


def validate_worker_result(card: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    validate_work_card(card)
    if not isinstance(result, dict) or result.get("schema_version") != RESULT_SCHEMA or result.get("work_card_id") != card["work_card_id"]:
        raise ValueError("WORKER_RESULT_SCHEMA_INVALID")
    attempt = result.get("attempt")
    if not isinstance(attempt, int) or not 1 <= attempt <= card["terminal_policy"]["max_attempts"]:
        raise ValueError("WORKER_RESULT_ATTEMPT_INVALID")
    if result.get("status") not in TERMINAL:
        raise ValueError("WORKER_RESULT_STATUS_INVALID")
    outputs = result.get("output_artifacts")
    if not isinstance(outputs, list):
        raise ValueError("WORKER_RESULT_OUTPUTS_INVALID")
    if result["status"] == "SUCCEEDED":
        if not outputs:
            raise ValueError("WORKER_RESULT_SUCCESS_REQUIRES_ARTIFACT")
        for item in outputs:
            if not isinstance(item, dict) or any(not item.get(k) for k in ("artifact_id","kind","ref")):
                raise ValueError("WORKER_RESULT_ARTIFACT_REF_INVALID")
            if item.get("kind") != card["output_contract"]["artifact_kind"]:
                raise ValueError("WORKER_RESULT_ARTIFACT_KIND_MISMATCH")
    elif outputs:
        raise ValueError("WORKER_RESULT_FAILURE_MUST_NOT_HANDOFF_OUTPUT")
    _scan(result)
    return result


def standard_web_ai_capabilities() -> dict[str, bool]:
    return {"web_ai": True, "mcp": False, "shell": False, "local_filesystem": False}
