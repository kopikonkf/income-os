from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import profile_pool
import research_plan
import source_ingestion
import web_ai_capability

PACKET_SCHEMA = "die.h03.research-packet.v1"


def _decrement_slot(pool: dict[str, Any], route: dict[str, Any]) -> None:
    for shard in pool["shards"]:
        if shard["shard_id"] != route.get("profile_shard_id"):
            continue
        for provider in shard["providers"]:
            if provider["provider_id"] == route["provider_id"] and provider["available_slots"] > 0:
                provider["available_slots"] -= 1
                return
    raise RuntimeError("RESEARCH_ROUTE_SLOT_NOT_FOUND")


def build_research_dispatches(*, plan: dict[str, Any], registry: dict[str, Any], pool: dict[str, Any]) -> list[dict[str, Any]]:
    research_plan.validate_research_plan(plan)
    cards = research_plan.build_research_work_cards(plan)
    working_pool = copy.deepcopy(pool)
    dispatches: list[dict[str, Any]] = []
    questions = {q["question_id"]: q for q in plan["questions"]}
    prefix = f"H03-WC-RSCH-{plan['research_plan_id']}-"
    for card in cards:
        work_card_id = card["work_card_id"]
        if not work_card_id.startswith(prefix):
            raise ValueError("RESEARCH_WORK_CARD_PLAN_PREFIX_MISMATCH")
        qid = work_card_id[len(prefix):]
        if qid not in questions:
            raise ValueError(f"RESEARCH_WORK_CARD_QUESTION_UNKNOWN:{qid}")
        question = questions[qid]
        route = profile_pool.route_worker_from_pool(role=card["role"], registry=registry, pool=working_pool, required_capabilities=["web_research"])
        _decrement_slot(working_pool, route)
        req = {
            "schema_version": web_ai_capability.REQUEST_SCHEMA,
            "request_id": f"REQ-{card['work_card_id']}",
            "holding_id": "H03",
            "role": card["role"],
            "task_id": "H03-RSCH-002",
            "model_route": route["model_route"],
            "prompt": question["question"],
            "context": {
                "question_id": qid,
                "required_source_classes": question["required_source_classes"],
                "minimum_independent_sources": question["minimum_independent_sources"],
                "research_plan_id": plan["research_plan_id"]
            },
            "output_mode": "JSON"
        }
        web_ai_capability.validate_capability_request(req)
        dispatches.append({"work_card": card, "question": question, "route": route, "request": req})
    return dispatches


def ingest_worker_research_output(*, dispatch: dict[str, Any], worker_output: dict[str, Any]) -> dict[str, Any]:
    sources = worker_output.get("source_documents")
    findings = worker_output.get("findings")
    if not isinstance(sources, list) or not sources or not isinstance(findings, list):
        raise ValueError("RESEARCH_WORKER_OUTPUT_INVALID")
    snapshots: list[dict[str, Any]] = []
    source_map: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict) or any(not source.get(k) for k in ("source_id","source_uri","text")):
            raise ValueError("RESEARCH_SOURCE_DOCUMENT_INVALID")
        snap = source_ingestion.ingest_external_bytes(
            source_id=source["source_id"],
            source_uri=source["source_uri"],
            raw_bytes=source["text"].encode("utf-8"),
            media_type=source.get("media_type", "text/plain"),
            acquisition_method=source.get("acquisition_method", "WEB_TOOL_SNAPSHOT"),
            rights_state="UNKNOWN",
            rights_basis="pending governed source review",
            verbatim_reuse_allowed=False,
        )
        snapshots.append(snap)
        source_map[source["source_id"]] = snap
    normalized_findings: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("finding_id") or not finding.get("text"):
            raise ValueError("RESEARCH_FINDING_INVALID")
        source_ids = finding.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            raise ValueError("RESEARCH_FINDING_SOURCE_IDS_REQUIRED")
        evidence_refs: list[str] = []
        for sid in source_ids:
            if sid not in source_map:
                raise ValueError("RESEARCH_FINDING_UNKNOWN_SOURCE")
            for unit in source_map[sid]["evidence_units"]:
                evidence_refs.append(unit["evidence_id"])
        normalized_findings.append({"finding_id": finding["finding_id"], "text": finding["text"], "evidence_refs": evidence_refs})
    route = dispatch["route"]
    card = dispatch["work_card"]
    qid = dispatch["question"]["question_id"]
    return {
        "schema_version": PACKET_SCHEMA,
        "research_packet_id": f"H03-RP-{card['work_card_id']}",
        "holding_id": "H03",
        "work_card_id": card["work_card_id"],
        "question_id": qid,
        "provider_observation": {
            "provider_id": route["provider_id"],
            "model_route": route["model_route"],
            "profile_shard_id": route.get("profile_shard_id"),
            "transport_family": route.get("transport_family"),
        },
        "source_snapshots": snapshots,
        "findings": normalized_findings,
        "terminal_status": "SUCCEEDED",
        "truth_status": "UNVERIFIED_RESEARCH_PACKET",
    }
