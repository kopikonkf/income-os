from __future__ import annotations

from typing import Any

SCHEMA = "die.h03.demand-wtp-evidence.v1"
_SIGNAL_TYPES = {"REVEALED_SPEND","PAID_SUBSTITUTE","MARKETPLACE_SALE_PROXY","PURCHASE_INTENT_SEARCH","REPEATED_PAIN","ENGAGEMENT_ONLY"}
_LEVELS = {"UNKNOWN","LOW","MEDIUM","HIGH"}
_INTENT = {"UNKNOWN","WEAK","MEDIUM","STRONG"}


def derive_wtp_assessment(evidence: list[dict[str, Any]]) -> str:
    types = {e.get("signal_type") for e in evidence if isinstance(e, dict)}
    if "REVEALED_SPEND" in types:
        return "STRONG"
    if types & {"PAID_SUBSTITUTE","MARKETPLACE_SALE_PROXY"}:
        return "MEDIUM"
    if types & {"PURCHASE_INTENT_SEARCH","REPEATED_PAIN"}:
        return "WEAK"
    # Engagement by itself is not willingness-to-pay evidence.
    return "UNKNOWN"


def validate_demand_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict) or packet.get("schema_version") != SCHEMA or packet.get("holding_id") != "H03":
        raise ValueError("DEMAND_PACKET_SCHEMA_INVALID")
    for field in ("packet_id","problem_seed_id"):
        if not isinstance(packet.get(field), str) or not packet[field].strip():
            raise ValueError(f"DEMAND_PACKET_FIELD_REQUIRED:{field}")
    pain = packet.get("pain_observation")
    if not isinstance(pain, dict) or any(pain.get(k) not in _LEVELS for k in ("severity","frequency","urgency")):
        raise ValueError("DEMAND_PACKET_PAIN_INVALID")
    if packet.get("buyer_intent_state") not in _INTENT:
        raise ValueError("DEMAND_PACKET_BUYER_INTENT_INVALID")
    evidence = packet.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("DEMAND_PACKET_EVIDENCE_INVALID")
    seen: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict) or item.get("signal_type") not in _SIGNAL_TYPES or not item.get("evidence_id"):
            raise ValueError("DEMAND_PACKET_SIGNAL_INVALID")
        if item["evidence_id"] in seen:
            raise ValueError("DEMAND_PACKET_DUPLICATE_EVIDENCE_ID")
        seen.add(item["evidence_id"])
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs or len(refs) != len(set(refs)) or any(not isinstance(r, str) or not r.strip() for r in refs):
            raise ValueError("DEMAND_PACKET_SIGNAL_REFS_INVALID")
        money = item.get("money")
        if item["signal_type"] == "REVEALED_SPEND":
            if not isinstance(money, dict) or not isinstance(money.get("amount_minor"), int) or money["amount_minor"] < 0 or not isinstance(money.get("currency"), str):
                raise ValueError("DEMAND_PACKET_REVEALED_SPEND_MONEY_REQUIRED")
        elif money is not None:
            raise ValueError("DEMAND_PACKET_MONEY_ONLY_FOR_REVEALED_SPEND")
    derived = derive_wtp_assessment(evidence)
    if packet.get("wtp_assessment") != derived:
        raise ValueError(f"DEMAND_PACKET_WTP_MISMATCH:{derived}")
    if packet.get("truth_status") not in {"CANDIDATE","VALIDATED"}:
        raise ValueError("DEMAND_PACKET_TRUTH_STATUS_INVALID")
    return packet
