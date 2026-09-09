from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import cognition_work_card
import web_ai_capability

MAP_SCHEMA = "die.h03.knowledge-map.v1"
CANDIDATE_SCHEMA = "die.h03.knowledge-package-candidate.v1"
_PACKET_SCHEMA = "die.h03.research-packet.v1"
_WTP_SIGNALS = {"REVEALED_SPEND","PAID_SUBSTITUTE","MARKETPLACE_SALE_PROXY","PURCHASE_INTENT_SEARCH","REPEATED_PAIN","ENGAGEMENT_ONLY","OTHER"}


def _validate_packets(packets: list[dict[str, Any]]) -> None:
    if not isinstance(packets, list) or not packets:
        raise ValueError("SYNTHESIS_RESEARCH_PACKETS_REQUIRED")
    ids: set[str] = set()
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("schema_version") != _PACKET_SCHEMA or packet.get("holding_id") != "H03":
            raise ValueError("SYNTHESIS_RESEARCH_PACKET_INVALID")
        pid = packet.get("research_packet_id")
        if not isinstance(pid, str) or not pid or pid in ids:
            raise ValueError("SYNTHESIS_RESEARCH_PACKET_ID_INVALID")
        ids.add(pid)
        if packet.get("truth_status") != "UNVERIFIED_RESEARCH_PACKET" or packet.get("terminal_status") != "SUCCEEDED":
            raise ValueError("SYNTHESIS_RESEARCH_PACKET_STATE_INVALID")


def _evidence_index(packets: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    evidence: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    for packet in packets:
        for source in packet.get("source_snapshots") or []:
            sid = source.get("source_id")
            if not sid:
                raise ValueError("SYNTHESIS_SOURCE_ID_REQUIRED")
            if sid in sources and sources[sid] != source:
                raise ValueError("SYNTHESIS_SOURCE_ID_COLLISION")
            sources[sid] = source
            for unit in source.get("evidence_units") or []:
                eid = unit.get("evidence_id")
                if not eid or not unit.get("text"):
                    raise ValueError("SYNTHESIS_EVIDENCE_UNIT_INVALID")
                if eid in evidence and evidence[eid] != unit:
                    raise ValueError("SYNTHESIS_EVIDENCE_ID_COLLISION")
                evidence[eid] = unit
    if not evidence:
        raise ValueError("SYNTHESIS_NO_EVIDENCE")
    return evidence, sources


def build_synthesis_work_card(*, knowledge_map_id: str, research_packet_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    if not research_packet_artifacts:
        raise ValueError("SYNTHESIS_ARTIFACTS_REQUIRED")
    card = {
        "schema_version": cognition_work_card.CARD_SCHEMA,
        "work_card_id": f"H03-WC-SYNTH-{knowledge_map_id}",
        "holding_id": "H03",
        "task_id": "H03-KF-003",
        "role": "SYNTHESIZER",
        "queue": "synthesis",
        "idempotency_key": f"h03-synthesis:{knowledge_map_id}",
        "input_artifacts": copy.deepcopy(research_packet_artifacts),
        "output_contract": {"artifact_kind":"knowledge_map","schema_version":MAP_SCHEMA},
        "capability_requirements": cognition_work_card.standard_web_ai_capabilities(),
        "terminal_policy": {"max_attempts":3,"retryable_failures":["RATE_LIMITED","PROVIDER_UNAVAILABLE","PROFILE_UNAVAILABLE","INVALID_OUTPUT"]}
    }
    return cognition_work_card.validate_work_card(card)


def build_synthesis_request(*, card: dict[str, Any], packets: list[dict[str, Any]], model_route: str) -> dict[str, Any]:
    cognition_work_card.validate_work_card(card)
    _validate_packets(packets)
    context_packets = []
    for packet in packets:
        context_packets.append({
            "research_packet_id": packet["research_packet_id"],
            "question_id": packet["question_id"],
            "findings": copy.deepcopy(packet.get("findings") or []),
            "source_ids": [s.get("source_id") for s in packet.get("source_snapshots") or []],
        })
    req = {
        "schema_version": web_ai_capability.REQUEST_SCHEMA,
        "request_id": f"REQ-{card['work_card_id']}",
        "holding_id": "H03",
        "role": "SYNTHESIZER",
        "task_id": "H03-KF-003",
        "model_route": model_route,
        "prompt": "Synthesize the research packets into supported findings, explicit contradictions, unresolved gaps, market/WTP findings, and candidate product claims. Every finding and claim must cite only supplied evidence_refs. Do not invent evidence or mark model output as canonical truth.",
        "context": {"research_packets": context_packets},
        "output_mode": "JSON"
    }
    web_ai_capability.validate_capability_request(req)
    return req


def _refs(value: Any, evidence: dict[str, Any], field: str, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum or len(value) != len(set(value)):
        raise ValueError(f"SYNTHESIS_EVIDENCE_REFS_INVALID:{field}")
    missing = [ref for ref in value if ref not in evidence]
    if missing:
        raise ValueError(f"SYNTHESIS_UNRESOLVED_EVIDENCE:{field}:{','.join(missing)}")
    return list(value)


def _promotion_state(*, sources: dict[str, dict[str, Any]], contradictions: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> str:
    if any(bool(g.get("critical")) for g in gaps):
        return "AWAITING_GAP_RESOLUTION"
    if any(c.get("resolution_state") == "UNRESOLVED" for c in contradictions):
        return "AWAITING_CONTRADICTION_RESOLUTION"
    for source in sources.values():
        review = source.get("review") or {}
        rights = source.get("rights_policy") or {}
        governed = review.get("status") == "ACCEPTED_FOR_KNOWLEDGE" and review.get("crawler_or_llm_authority") is False and rights.get("state") not in {None,"UNKNOWN"}
        if not governed:
            return "AWAITING_SOURCE_GOVERNANCE"
    return "ELIGIBLE_FOR_KNOWLEDGE_VALIDATION"


def normalize_synthesis_output(*, knowledge_map_id: str, candidate_id: str, packets: list[dict[str, Any]], model_output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_packets(packets)
    evidence, sources = _evidence_index(packets)
    if not isinstance(model_output, dict):
        raise ValueError("SYNTHESIS_MODEL_OUTPUT_OBJECT_REQUIRED")

    supported = []
    for item in model_output.get("supported_findings") or []:
        if not item.get("finding_id") or not item.get("text"):
            raise ValueError("SYNTHESIS_FINDING_INVALID")
        supported.append({"finding_id":item["finding_id"],"text":item["text"],"evidence_refs":_refs(item.get("evidence_refs"), evidence, f"finding:{item.get('finding_id')}")})

    contradictions = []
    for item in model_output.get("contradictions") or []:
        if not item.get("contradiction_id") or not item.get("statement") or item.get("resolution_state") not in {"UNRESOLVED","RESOLVED"}:
            raise ValueError("SYNTHESIS_CONTRADICTION_INVALID")
        contradictions.append({"contradiction_id":item["contradiction_id"],"statement":item["statement"],"evidence_refs":_refs(item.get("evidence_refs"), evidence, f"contradiction:{item.get('contradiction_id')}", minimum=2),"resolution_state":item["resolution_state"]})

    gaps = []
    for item in model_output.get("gaps") or []:
        if not item.get("gap_id") or not item.get("question") or not isinstance(item.get("critical"), bool):
            raise ValueError("SYNTHESIS_GAP_INVALID")
        gaps.append({"gap_id":item["gap_id"],"question":item["question"],"critical":item["critical"]})

    market_wtp = []
    for item in model_output.get("market_wtp_findings") or []:
        if not item.get("finding_id") or not item.get("text") or item.get("signal_type") not in _WTP_SIGNALS:
            raise ValueError("SYNTHESIS_MARKET_WTP_INVALID")
        market_wtp.append({"finding_id":item["finding_id"],"text":item["text"],"evidence_refs":_refs(item.get("evidence_refs"), evidence, f"market-wtp:{item.get('finding_id')}"),"signal_type":item["signal_type"]})

    claims = []
    seen_claims: set[str] = set()
    for item in model_output.get("claims") or []:
        cid = item.get("claim_id")
        if not cid or cid in seen_claims or not item.get("text"):
            raise ValueError("SYNTHESIS_CLAIM_INVALID")
        seen_claims.add(cid)
        claims.append({"claim_id":cid,"text":item["text"],"evidence_refs":_refs(item.get("evidence_refs"), evidence, f"claim:{cid}")})
    if not claims:
        raise ValueError("SYNTHESIS_CLAIMS_REQUIRED")

    knowledge_map = {
        "schema_version": MAP_SCHEMA,
        "knowledge_map_id": knowledge_map_id,
        "holding_id": "H03",
        "research_packet_ids": [p["research_packet_id"] for p in packets],
        "supported_findings": supported,
        "contradictions": contradictions,
        "gaps": gaps,
        "market_wtp_findings": market_wtp,
        "truth_status": "UNVERIFIED_SYNTHESIS"
    }
    candidate = {
        "schema_version": CANDIDATE_SCHEMA,
        "knowledge_package_candidate_id": candidate_id,
        "holding_id": "H03",
        "knowledge_map_id": knowledge_map_id,
        "claims": claims,
        "source_snapshot_refs": sorted(sources),
        "contradictions": copy.deepcopy(contradictions),
        "gaps": copy.deepcopy(gaps),
        "promotion_state": _promotion_state(sources=sources, contradictions=contradictions, gaps=gaps),
        "canonical_truth": False
    }
    return knowledge_map, candidate
