from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import cognition_work_card

SCHEMA = "die.h03.orchestrator-queue-state.v1"
_ALLOWED = {
    "QUEUED": {"DISPATCHED","CANCELLED"},
    "DISPATCHED": {"RUNNING","FAILED_RETRYABLE","FAILED_TERMINAL","CANCELLED"},
    "RUNNING": {"SUCCEEDED","FAILED_RETRYABLE","FAILED_TERMINAL","CANCELLED"},
    "FAILED_RETRYABLE": {"QUEUED","FAILED_TERMINAL","CANCELLED"},
    "SUCCEEDED": set(),
    "FAILED_TERMINAL": set(),
    "CANCELLED": set(),
}


def create_state(batch_id: str) -> dict[str, Any]:
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("QUEUE_BATCH_ID_REQUIRED")
    return {"schema_version":SCHEMA,"holding_id":"H03","batch_id":batch_id,"jobs":{},"fan_in_groups":[]}


def enqueue(state: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    cognition_work_card.validate_work_card(card)
    jobs = state["jobs"]
    for existing in jobs.values():
        if existing["idempotency_key"] == card["idempotency_key"]:
            return state
    jobs[card["work_card_id"]] = {
        "queue": card["queue"],
        "role": card["role"],
        "state": "QUEUED",
        "attempt": 0,
        "idempotency_key": card["idempotency_key"],
        "input_artifacts": copy.deepcopy(card["input_artifacts"]),
        "output_artifacts": [],
    }
    return state


def transition(state: dict[str, Any], work_card_id: str, target: str) -> dict[str, Any]:
    job = state["jobs"].get(work_card_id)
    if not job:
        raise ValueError("QUEUE_JOB_NOT_FOUND")
    current = job["state"]
    if target not in _ALLOWED.get(current, set()):
        raise ValueError(f"QUEUE_TRANSITION_INVALID:{current}->{target}")
    job["state"] = target
    if target == "RUNNING":
        job["attempt"] += 1
    return state


def apply_result(state: dict[str, Any], card: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    cognition_work_card.validate_worker_result(card, result)
    job = state["jobs"].get(card["work_card_id"])
    if not job:
        raise ValueError("QUEUE_JOB_NOT_FOUND")
    if job["state"] not in {"DISPATCHED","RUNNING"}:
        raise ValueError("QUEUE_RESULT_STATE_INVALID")
    job["state"] = result["status"]
    job["attempt"] = max(job["attempt"], result["attempt"])
    job["output_artifacts"] = copy.deepcopy(result["output_artifacts"])
    return state


def add_fan_in_group(state: dict[str, Any], *, group_id: str, child_work_card_ids: list[str], target_work_card_id: str, max_children: int = 16) -> dict[str, Any]:
    if not child_work_card_ids or len(child_work_card_ids) > max_children:
        raise ValueError("QUEUE_FANOUT_BOUND_EXCEEDED")
    if len(child_work_card_ids) != len(set(child_work_card_ids)):
        raise ValueError("QUEUE_FANOUT_DUPLICATE_CHILD")
    if any(cid not in state["jobs"] for cid in child_work_card_ids):
        raise ValueError("QUEUE_FANOUT_CHILD_NOT_FOUND")
    if any(g["group_id"] == group_id for g in state["fan_in_groups"]):
        raise ValueError("QUEUE_FANIN_GROUP_DUPLICATE")
    state["fan_in_groups"].append({"group_id":group_id,"child_work_card_ids":list(child_work_card_ids),"target_work_card_id":target_work_card_id,"max_children":max_children})
    return state


def fan_in_status(state: dict[str, Any], group_id: str) -> str:
    group = next((g for g in state["fan_in_groups"] if g["group_id"] == group_id), None)
    if not group:
        raise ValueError("QUEUE_FANIN_GROUP_NOT_FOUND")
    states = [state["jobs"][cid]["state"] for cid in group["child_work_card_ids"]]
    if any(s in {"FAILED_TERMINAL","CANCELLED"} for s in states):
        return "BLOCKED_FAILURE"
    if all(s == "SUCCEEDED" for s in states):
        return "READY"
    return "WAITING"


def collect_fan_in_artifacts(state: dict[str, Any], group_id: str) -> list[dict[str, Any]]:
    if fan_in_status(state, group_id) != "READY":
        raise ValueError("QUEUE_FANIN_NOT_READY")
    group = next(g for g in state["fan_in_groups"] if g["group_id"] == group_id)
    out: list[dict[str, Any]] = []
    for cid in group["child_work_card_ids"]:
        out.extend(copy.deepcopy(state["jobs"][cid]["output_artifacts"]))
    return out
