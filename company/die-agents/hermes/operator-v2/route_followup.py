#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUTHORITY_VALIDATOR = ROOT / "validate_action_authority.py"
FOLLOW_UP_AFTER_SECONDS = 30 * 60
MAX_FOLLOW_UPS = 3


def _load_authority():
    spec = importlib.util.spec_from_file_location("oe006f_authority", AUTHORITY_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("E_AUTHORITY_VALIDATOR_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTHORITY = _load_authority()


def _parse_iso(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dedupe_key(projection: dict[str, Any]) -> str:
    raw = "|".join([
        str(projection.get("mission_id")), str(projection.get("subject_id")),
        str(projection.get("intelligence_stage")), str(projection.get("next_required_receipt")),
        str(projection.get("next_action_type")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _target_for(projection: dict[str, Any]) -> str | None:
    action = projection.get("next_action_type")
    if action == "OP-CREATE-RESEARCH-CARD": return "approved-signal-collector"
    if action == "OP-DISPATCH-DEMAND-SCORE": return "division001-demand-score-v1"
    if action in {"OP-REQUEST-DIVISION01-WORTH-MAKING", "OP-REQUEST-DIVISION01-BLUEPRINT"}: return "division-head-division01"
    if action in {"OP-REQUEST-EXECUTIVE-WORTH-MAKING-REVIEW", "OP-REQUEST-EXECUTIVE-BLUEPRINT-REVIEW"}: return "chatgpt-plus-executive"
    if action == "OP-CREATE-BLUEPRINT-COMPILE-CARD": return "worker-template"
    if action == "OP-DRAFT-U1-REQUEST": return "founder"
    if action == "OP-INVOKE-M001-RUNNER": return "worker-template"
    return None


def _request(action: str, projection: dict[str, Any], *, target: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "die.operator-v2.action-request.v1",
        "action_type": action,
        "actor_id": "hermes-operator",
        "projection_stage": projection["intelligence_stage"],
        "evidence_receipt_types": projection.get("active_receipt_types", []),
        "target_principal_id": target,
    }


def empty_state() -> dict[str, Any]:
    return {"schema": "die.operator-v2.routing-state.v1", "intents": {}}


def plan(projection: dict[str, Any], state: dict[str, Any] | None = None, *, now: str | None = None) -> dict[str, Any]:
    state = copy.deepcopy(state or empty_state())
    if state.get("schema") != "die.operator-v2.routing-state.v1" or not isinstance(state.get("intents"), dict):
        raise ValueError("E_ROUTING_STATE")
    now_dt = _parse_iso(now or projection["as_of"])
    key = _dedupe_key(projection)
    original_action = projection["next_action_type"]
    original_target = _target_for(projection)
    prior = state["intents"].get(key)
    decision = "DISPATCH"
    action = original_action
    target = original_target
    stall_age_seconds = 0
    follow_up_count = int(prior.get("follow_up_count", 0)) if isinstance(prior, dict) else 0
    if prior and prior.get("status") == "OPEN":
        last = _parse_iso(prior["last_action_at"])
        stall_age_seconds = max(0, int((now_dt - last).total_seconds()))
        if stall_age_seconds < FOLLOW_UP_AFTER_SECONDS:
            decision = "NO_OP_DUPLICATE"
            action = "OP-OBSERVE-STATE"
            target = None
        elif follow_up_count < MAX_FOLLOW_UPS:
            decision = "FOLLOW_UP"
            action = "OP-FOLLOW-UP-CARD"
            target = None
        else:
            decision = "BLOCK_STALLED"
            action = "OP-BLOCK-CARD"
            target = None
    req = _request(action, projection, target=target)
    verdict = AUTHORITY.validate(req, projection=projection)
    if verdict["status"] != "ALLOW":
        return {
            "schema": "die.operator-v2.routing-plan.v1", "status": "BLOCKED_AUTHORITY", "decision": "BLOCK_AUTHORITY",
            "mission_id": projection["mission_id"], "subject_id": projection["subject_id"], "as_of": _iso(now_dt),
            "dedupe_key": key, "projection_stage": projection["intelligence_stage"], "next_required_receipt": projection.get("next_required_receipt"),
            "requested_action_type": original_action, "requested_target_principal_id": original_target,
            "action_request": req, "authority_validation": verdict, "stall_age_seconds": stall_age_seconds,
            "follow_up_count": follow_up_count, "semantic_content_authored": False, "production_authority_granted": False,
        }
    return {
        "schema": "die.operator-v2.routing-plan.v1", "status": "READY", "decision": decision,
        "mission_id": projection["mission_id"], "subject_id": projection["subject_id"], "as_of": _iso(now_dt),
        "dedupe_key": key, "projection_stage": projection["intelligence_stage"], "next_required_receipt": projection.get("next_required_receipt"),
        "requested_action_type": original_action, "requested_target_principal_id": original_target,
        "action_request": req, "authority_validation": verdict, "stall_age_seconds": stall_age_seconds,
        "follow_up_count": follow_up_count, "semantic_content_authored": False, "production_authority_granted": False,
    }


def record(state: dict[str, Any] | None, routing_plan: dict[str, Any], *, outcome: str, at: str) -> dict[str, Any]:
    if outcome not in {"DISPATCHED", "COMPLETED", "FAILED", "BLOCKED"}:
        raise ValueError("E_OUTCOME")
    state = copy.deepcopy(state or empty_state())
    key = routing_plan["dedupe_key"]
    old = state["intents"].get(key, {})
    followups = int(old.get("follow_up_count", 0))
    if routing_plan.get("decision") == "FOLLOW_UP" and outcome == "DISPATCHED":
        followups += 1
    status = "OPEN" if outcome == "DISPATCHED" else outcome
    state["intents"][key] = {
        "status": status,
        "requested_action_type": routing_plan["requested_action_type"],
        "requested_target_principal_id": routing_plan.get("requested_target_principal_id"),
        "last_action_at": at,
        "follow_up_count": followups,
    }
    return state


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    pp = sub.add_parser("plan"); pp.add_argument("projection"); pp.add_argument("--state"); pp.add_argument("--now")
    pr = sub.add_parser("record"); pr.add_argument("routing_plan"); pr.add_argument("--state"); pr.add_argument("--outcome", required=True); pr.add_argument("--at", required=True)
    a = ap.parse_args()
    if a.command == "plan":
        projection = json.loads(Path(a.projection).read_text(encoding="utf-8")); state = json.loads(Path(a.state).read_text(encoding="utf-8")) if a.state else None
        out = plan(projection, state, now=a.now)
    else:
        routing_plan = json.loads(Path(a.routing_plan).read_text(encoding="utf-8")); state = json.loads(Path(a.state).read_text(encoding="utf-8")) if a.state else None
        out = record(state, routing_plan, outcome=a.outcome, at=a.at)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())