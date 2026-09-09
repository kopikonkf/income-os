from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import problem_seed
import demand_wtp

SCHEMA = "die.h03.worth-making-decision.v1"
_PRODUCTABILITY = {"UNKNOWN","LOW","MEDIUM","HIGH"}


def _validate_productability(value: dict[str, Any]) -> None:
    if not isinstance(value, dict) or value.get("state") not in _PRODUCTABILITY:
        raise ValueError("WORTH_MAKING_PRODUCTABILITY_INVALID")
    refs = value.get("evidence_refs")
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or any(not isinstance(r, str) or not r.strip() for r in refs):
        raise ValueError("WORTH_MAKING_PRODUCTABILITY_EVIDENCE_INVALID")
    if value["state"] == "UNKNOWN" and refs:
        raise ValueError("WORTH_MAKING_UNKNOWN_PRODUCTABILITY_HAS_EVIDENCE")
    if value["state"] != "UNKNOWN" and not refs:
        raise ValueError("WORTH_MAKING_PRODUCTABILITY_EVIDENCE_REQUIRED")


def evaluate_worth_making(*, decision_id: str, seed: dict[str, Any], demand_packet: dict[str, Any], productability: dict[str, Any]) -> dict[str, Any]:
    problem_seed.validate_problem_seed(seed)
    demand_wtp.validate_demand_packet(demand_packet)
    _validate_productability(productability)
    if demand_packet["problem_seed_id"] != seed["problem_seed_id"]:
        raise ValueError("WORTH_MAKING_SEED_DEMAND_MISMATCH")

    wtp = demand_packet["wtp_assessment"]
    intent = demand_packet["buyer_intent_state"]
    pain = demand_packet["pain_observation"]
    pstate = productability["state"]
    reasons: list[str] = []

    if pstate == "LOW":
        decision = "REJECT"
        reasons.append("LOW_PRODUCTABILITY")
    elif wtp in {"MEDIUM","STRONG"} and intent in {"MEDIUM","STRONG"} and pstate in {"MEDIUM","HIGH"}:
        decision = "MAKE"
        reasons.extend(["WTP_EVIDENCED","BUYER_INTENT_EVIDENCED","PRODUCTABILITY_EVIDENCED"])
    elif wtp == "WEAK" and intent == "WEAK" and pain.get("severity") == "LOW" and pain.get("frequency") == "LOW" and pain.get("urgency") == "LOW":
        decision = "REJECT"
        reasons.append("LOW_COMMERCIAL_PRESSURE")
    else:
        decision = "RESEARCH_MORE"
        if wtp == "UNKNOWN": reasons.append("WTP_UNKNOWN")
        elif wtp == "WEAK": reasons.append("WTP_WEAK")
        if intent == "UNKNOWN": reasons.append("BUYER_INTENT_UNKNOWN")
        elif intent == "WEAK": reasons.append("BUYER_INTENT_WEAK")
        if pstate == "UNKNOWN": reasons.append("PRODUCTABILITY_UNKNOWN")
        if not reasons: reasons.append("EVIDENCE_INSUFFICIENT_FOR_MAKE_OR_REJECT")

    evidence_refs: list[str] = []
    for item in demand_packet["evidence"]:
        for ref in item["evidence_refs"]:
            if ref not in evidence_refs:
                evidence_refs.append(ref)
    for ref in productability["evidence_refs"]:
        if ref not in evidence_refs:
            evidence_refs.append(ref)

    return {
        "schema_version": SCHEMA,
        "decision_id": decision_id,
        "holding_id": "H03",
        "problem_seed_id": seed["problem_seed_id"],
        "decision": decision,
        "reason_codes": reasons,
        "evidence_refs": evidence_refs,
        "productability_state": pstate
    }
