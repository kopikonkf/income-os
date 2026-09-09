from __future__ import annotations

from typing import Any

SCHEMA = "die.h03.worker-resilience-policy.v1"
_FAILURES = {
    "AUTH_REQUIRED": {"class":"AUTH","retryable":True,"circuit_break":True},
    "RATE_LIMITED": {"class":"RATE_LIMIT","retryable":True,"circuit_break":True},
    "PROVIDER_UNAVAILABLE": {"class":"PROVIDER","retryable":True,"circuit_break":True},
    "PROFILE_UNAVAILABLE": {"class":"PROFILE","retryable":True,"circuit_break":True},
    "TIMEOUT": {"class":"RUNTIME","retryable":True,"circuit_break":False},
    "INVALID_OUTPUT": {"class":"OUTPUT","retryable":True,"circuit_break":False},
    "POLICY_REJECTED": {"class":"POLICY","retryable":False,"circuit_break":False},
}


def default_policy(queue_limit: int = 100) -> dict[str, Any]:
    return {"schema_version":SCHEMA,"holding_id":"H03","queue_limit":queue_limit,"failure_classes":_FAILURES}


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict) or policy.get("schema_version") != SCHEMA or policy.get("holding_id") != "H03":
        raise ValueError("RESILIENCE_POLICY_SCHEMA_INVALID")
    if not isinstance(policy.get("queue_limit"), int) or policy["queue_limit"] < 1:
        raise ValueError("RESILIENCE_QUEUE_LIMIT_INVALID")
    if policy.get("failure_classes") != _FAILURES:
        raise ValueError("RESILIENCE_FAILURE_CLASSES_INVALID")
    return policy


def backpressure_action(*, queue_depth: int, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    if queue_depth < 0:
        raise ValueError("RESILIENCE_QUEUE_DEPTH_INVALID")
    if queue_depth >= policy["queue_limit"]:
        return {"action":"PAUSE_NEW_DISPATCH","backpressure":True,"queue_depth":queue_depth,"queue_limit":policy["queue_limit"]}
    return {"action":"ACCEPT_DISPATCH","backpressure":False,"queue_depth":queue_depth,"queue_limit":policy["queue_limit"]}


def decide_failure(*, failure_code: str, attempt: int, max_attempts: int, alternative_slots: int, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    if failure_code not in _FAILURES:
        return {"action":"FAIL_TERMINAL","failure_class":"UNKNOWN","circuit_break":False,"retryable":False}
    if not isinstance(attempt, int) or not isinstance(max_attempts, int) or attempt < 1 or max_attempts < 1 or alternative_slots < 0:
        raise ValueError("RESILIENCE_ATTEMPT_INPUT_INVALID")
    meta = _FAILURES[failure_code]
    if not meta["retryable"] or attempt >= max_attempts:
        return {"action":"FAIL_TERMINAL","failure_class":meta["class"],"circuit_break":meta["circuit_break"],"retryable":False}
    if alternative_slots > 0:
        return {"action":"FALLBACK_ALTERNATE_WORKER","failure_class":meta["class"],"circuit_break":meta["circuit_break"],"retryable":True}
    if failure_code == "AUTH_REQUIRED":
        return {"action":"WAIT_CAPABILITY_RECOVERY","failure_class":meta["class"],"circuit_break":True,"retryable":True}
    return {"action":"RETRY_LATER","failure_class":meta["class"],"circuit_break":meta["circuit_break"],"retryable":True}
