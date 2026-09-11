from __future__ import annotations

import copy
import hashlib
import json
import shutil
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import artifact_courier
import cognition_work_card
import demand_wtp
import h03_factory
import knowledge_synthesis
import live_source_verifier
import problem_discovery
import problem_seed
import product_packager
import product_planner
import product_release_gate
import research_plan
import review_engine
import semantic_producer
import worth_making
from live_work_card_runner import LiveWorkCardRunner, MissionControlH03Client

RUN_SCHEMA = "die.h03.live-organism-run.v1"
RUN_ID = "LIVE-ORG-001"
TASK_ID = "H03-LIVE-ORG-001"
EXECUTION_MODE = "LIVE_WEB_AI"
OPPORTUNITY_QUESTION = (
    "What recurring human problems in high-income English-speaking markets show observable friction, "
    "search behavior, existing solutions, and plausible willingness to pay for a structured digital solution?"
)

_ALLOWED_SIGNAL_HINTS = {
    "PAID_SUBSTITUTE", "MARKETPLACE_SALE_PROXY", "PURCHASE_INTENT_SEARCH",
    "REPEATED_PAIN", "ENGAGEMENT_ONLY", "PRODUCTABILITY",
}
_ALLOWED_DEMAND_SIGNALS = {
    "PAID_SUBSTITUTE", "MARKETPLACE_SALE_PROXY", "PURCHASE_INTENT_SEARCH",
    "REPEATED_PAIN", "ENGAGEMENT_ONLY",
}
_LEVELS = {"UNKNOWN", "LOW", "MEDIUM", "HIGH"}
_INTENT = {"UNKNOWN", "WEAK", "MEDIUM", "STRONG"}


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _safe_text(value: Any, field: str, minimum: int = 1, maximum: int = 4000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"LIVE_ORG_TEXT_REQUIRED:{field}")
    text = " ".join(value.split())
    if len(text) < minimum or len(text) > maximum:
        raise ValueError(f"LIVE_ORG_TEXT_LENGTH:{field}")
    return text


def _make_card(
    *,
    work_card_id: str,
    role: str,
    queue: str,
    inputs: list[dict[str, Any]],
    artifact_kind: str,
    output_schema: str,
    max_attempts: int = 3,
) -> dict[str, Any]:
    card = {
        "schema_version": cognition_work_card.CARD_SCHEMA,
        "work_card_id": work_card_id,
        "holding_id": "H03",
        "task_id": TASK_ID,
        "role": role,
        "queue": queue,
        "idempotency_key": f"h03-live-org-001:{work_card_id.lower()}",
        "input_artifacts": copy.deepcopy(inputs),
        "output_contract": {"artifact_kind": artifact_kind, "schema_version": output_schema},
        "capability_requirements": cognition_work_card.standard_web_ai_capabilities(),
        "terminal_policy": {
            "max_attempts": max_attempts,
            "retryable_failures": [
                "RATE_LIMITED", "PROVIDER_UNAVAILABLE", "PROFILE_UNAVAILABLE",
                "INVALID_OUTPUT", "OUTPUT_SCHEMA_INVALID",
            ],
        },
    }
    return cognition_work_card.validate_work_card(card)


def _emit_local(
    client: MissionControlH03Client,
    *,
    stage_id: str,
    queue: str,
    state: str,
    artifact: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    event: dict[str, Any] = {
        "schema_version": "die.h03.runtime-event.v1",
        "holding_id": "H03",
        "run_id": RUN_ID,
        "work_card_id": f"H03-LOCAL-{stage_id}",
        "task_id": TASK_ID,
        "role": "LOCAL_ENGINE",
        "queue": queue,
        "state": state,
    }
    if artifact is not None:
        event["artifact"] = artifact
        if state == "SUCCEEDED":
            event["output_artifacts"] = [artifact]
    if error:
        event["error"] = error[:1200]
    try:
        client.emit(event)
    except Exception:
        pass


def _ensure_local_artifact(
    *,
    courier: artifact_courier.ArtifactCourier,
    client: MissionControlH03Client,
    artifact_id: str,
    kind: str,
    declared_schema: str,
    stage_id: str,
    queue: str,
    builder: Callable[[], Any],
) -> tuple[dict[str, Any], Any, bool]:
    existing = courier.existing_ref(run_id=RUN_ID, artifact_id=artifact_id, kind=kind)
    if existing is not None:
        return existing, courier.resolve(existing), False
    _emit_local(client, stage_id=stage_id, queue=queue, state="RUNNING")
    try:
        payload = builder()
        ref = courier.commit_payload(
            run_id=RUN_ID,
            artifact_id=artifact_id,
            kind=kind,
            declared_schema=declared_schema,
            producer_work_card_id=f"H03-LOCAL-{stage_id}",
            payload=payload,
        )
        _emit_local(client, stage_id=stage_id, queue=queue, state="ARTIFACT_COMMITTED", artifact=ref)
        _emit_local(client, stage_id=stage_id, queue=queue, state="SUCCEEDED", artifact=ref)
        return ref, payload, True
    except Exception as exc:
        _emit_local(client, stage_id=stage_id, queue=queue, state="FAILED_TERMINAL", error=f"{type(exc).__name__}:{exc}")
        raise


def _validate_seed_curator_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
        raise ValueError("LIVE_SEED_CANDIDATES_REQUIRED")
    candidates = payload["candidates"]
    if not 6 <= len(candidates) <= 12:
        raise ValueError("LIVE_SEED_CANDIDATE_COUNT_INVALID")
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in candidates:
        if not isinstance(raw, dict):
            raise ValueError("LIVE_SEED_CANDIDATE_INVALID")
        candidate = copy.deepcopy(raw)
        candidate["schema_version"] = problem_seed.SCHEMA
        candidate["holding_id"] = "H03"
        candidate["source_refs"] = []
        pain = candidate.get("pain")
        if not isinstance(pain, dict):
            raise ValueError("LIVE_SEED_PAIN_REQUIRED")
        for key in ("severity_state", "frequency_state", "urgency_state"):
            pain[key] = "UNKNOWN"
        candidate = problem_discovery.normalize_discovered_seed(candidate)
        pid = candidate["problem_seed_id"]
        if pid in ids:
            raise ValueError("LIVE_SEED_ID_DUPLICATE")
        ids.add(pid)
        normalized.append(candidate)
    return {"candidates": normalized}


def _validate_scout_payload(payload: Any, *, seed_ids: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("candidate_sources"), list):
        raise ValueError("LIVE_MARKET_SCOUT_INVALID")
    groups = payload["candidate_sources"]
    if not 1 <= len(groups) <= 5:
        raise ValueError("LIVE_MARKET_SCOUT_GROUP_COUNT")
    seen_candidates: set[str] = set()
    total = 0
    clean_groups: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("LIVE_MARKET_SCOUT_GROUP_INVALID")
        pid = str(group.get("problem_seed_id") or "")
        if pid not in seed_ids or pid in seen_candidates:
            raise ValueError("LIVE_MARKET_SCOUT_SEED_INVALID")
        seen_candidates.add(pid)
        requests = group.get("source_requests")
        if not isinstance(requests, list) or not 2 <= len(requests) <= 6:
            raise ValueError("LIVE_MARKET_SCOUT_SOURCE_COUNT")
        clean_requests: list[dict[str, Any]] = []
        for req in requests:
            if not isinstance(req, dict):
                raise ValueError("LIVE_MARKET_SCOUT_SOURCE_INVALID")
            url = str(req.get("url") or "").strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("LIVE_MARKET_SCOUT_URL_INVALID")
            source_class = str(req.get("source_class") or "")
            if source_class not in live_source_verifier._ALLOWED_SOURCE_CLASSES:
                raise ValueError("LIVE_MARKET_SCOUT_CLASS_INVALID")
            signal_hint = str(req.get("signal_hint") or "")
            if signal_hint not in _ALLOWED_SIGNAL_HINTS:
                raise ValueError("LIVE_MARKET_SCOUT_SIGNAL_INVALID")
            terms = req.get("relevance_terms")
            if not isinstance(terms, list) or not 1 <= len(terms) <= 6:
                raise ValueError("LIVE_MARKET_SCOUT_TERMS_INVALID")
            clean_requests.append({
                "url": url,
                "source_class": source_class,
                "signal_hint": signal_hint,
                "relevance_terms": [_safe_text(t, "relevance_term", 2, 80) for t in terms],
            })
            total += 1
        clean_groups.append({"problem_seed_id": pid, "source_requests": clean_requests})
    if total > 20:
        raise ValueError("LIVE_MARKET_SCOUT_TOTAL_EXCEEDED")
    return {"candidate_sources": clean_groups}


def _flatten_market_source_requests(
    scout: dict[str, Any],
    *,
    prefix: str = "LIVE001-MKT",
    exclude_urls: set[str] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    excluded = set(exclude_urls or set())
    counter = 0
    for group in scout["candidate_sources"]:
        for req in group["source_requests"]:
            url = req["url"]
            if url in excluded:
                continue
            counter += 1
            out.append({
                "source_id": f"{prefix}-S{counter:03d}",
                "url": url,
                "source_class": req["source_class"],
                "signal_hint": req["signal_hint"],
                "relevance_terms": req["relevance_terms"],
                "candidate_id": group["problem_seed_id"],
            })
    return out


def _source_index(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["source_id"]: s for s in bundle.get("verified_sources") or []}


def _source_text(source: dict[str, Any]) -> str:
    return " ".join(str(unit.get("text", "")) for unit in source.get("evidence_units") or [])


def _source_host(source: dict[str, Any]) -> str:
    try:
        return (urlparse(str(source.get("source_uri") or "")).hostname or "").lower()
    except Exception:
        return ""


def _source_has_paid_marker(source: dict[str, Any]) -> bool:
    text = _source_text(source).lower()
    return bool(re.search(r"(?:[$£€]\s?\d|\bprice\b|\bpricing\b|\bplans?\b|\bsubscription\b|\bbilling\b|\bmonthly\b|\bannual\b|\byearly\b|\bper month\b|\bper year\b|\bcheckout\b)", text))


def _source_has_marketplace_proxy_marker(source: dict[str, Any]) -> bool:
    text = _source_text(source).lower()
    return bool(re.search(r"\b(?:reviews?|ratings?|sold|sales|downloads?|customers?|purchases?|orders?)\b", text))


def _market_candidate_coverage(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    for source in bundle.get("verified_sources") or []:
        candidate_id = str(source.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        row = coverage.setdefault(candidate_id, {"source_ids": [], "hosts": set(), "paid_source_ids": []})
        row["source_ids"].append(source["source_id"])
        host = _source_host(source)
        if host:
            row["hosts"].add(host)
        if source.get("signal_hint") == "PAID_SUBSTITUTE" and _source_has_paid_marker(source):
            row["paid_source_ids"].append(source["source_id"])
        if (
            source.get("signal_hint") == "MARKETPLACE_SALE_PROXY"
            and source.get("source_class") == "MARKETPLACE_LISTING"
            and _source_has_marketplace_proxy_marker(source)
        ):
            row["paid_source_ids"].append(source["source_id"])
    out: dict[str, dict[str, Any]] = {}
    for candidate_id, row in coverage.items():
        out[candidate_id] = {
            "source_ids": list(dict.fromkeys(row["source_ids"])),
            "host_count": len(row["hosts"]),
            "paid_source_ids": list(dict.fromkeys(row["paid_source_ids"])),
        }
    return out


def _market_ready_candidate_ids(bundle: dict[str, Any]) -> set[str]:
    return {
        candidate_id
        for candidate_id, row in _market_candidate_coverage(bundle).items()
        if len(row["source_ids"]) >= 2 and row["host_count"] >= 2 and bool(row["paid_source_ids"])
    }


def _bundle_urls(bundle: dict[str, Any]) -> set[str]:
    urls = {str(source.get("source_uri") or "") for source in bundle.get("verified_sources") or []}
    urls.update(str(item.get("url") or "") for item in bundle.get("failures") or [])
    return {url for url in urls if url}


def _merge_source_bundles(*bundles: dict[str, Any]) -> dict[str, Any]:
    if not bundles:
        raise ValueError("LIVE_SOURCE_BUNDLE_MERGE_REQUIRED")
    verified_by_url: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    requested = 0
    for bundle in bundles:
        if bundle.get("schema_version") != live_source_verifier.BUNDLE_SCHEMA:
            raise ValueError("LIVE_SOURCE_BUNDLE_MERGE_SCHEMA")
        requested += int(bundle.get("requested_count") or 0)
        for source in bundle.get("verified_sources") or []:
            verified_by_url.setdefault(str(source.get("source_uri") or source.get("source_id")), copy.deepcopy(source))
        failures.extend(copy.deepcopy(bundle.get("failures") or []))
    verified = list(verified_by_url.values())
    return {
        "schema_version": live_source_verifier.BUNDLE_SCHEMA,
        "holding_id": "H03",
        "run_id": RUN_ID,
        "verified_sources": verified,
        "failures": failures,
        "verified_count": len(verified),
        "requested_count": requested,
        "truth_status": "VERIFIED_PUBLIC_REFERENCE_SNAPSHOTS",
    }


def _independent_source_count(bundle: dict[str, Any]) -> int:
    return len({_source_host(source) for source in bundle.get("verified_sources") or [] if _source_host(source)})


def _validate_market_evaluation(payload: Any, *, seed_ids: set[str], source_bundle: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LIVE_MARKET_EVAL_INVALID")
    selected = payload.get("selected_problem_seed_id")
    if selected is None:
        reason = _safe_text(payload.get("no_make_reason"), "no_make_reason", 10, 1000)
        return {"selected_problem_seed_id": None, "no_make_reason": reason}
    if selected not in seed_ids:
        raise ValueError("LIVE_MARKET_EVAL_SEED_UNKNOWN")
    sources = _source_index(source_bundle)
    eligible_source_ids = {sid for sid, s in sources.items() if s.get("candidate_id") == selected}
    if selected not in _market_ready_candidate_ids(source_bundle):
        raise ValueError("LIVE_MARKET_EVAL_VERIFIED_SOURCE_COVERAGE_LOW")

    pain = payload.get("pain_observation")
    if not isinstance(pain, dict) or any(pain.get(k) not in _LEVELS for k in ("severity", "frequency", "urgency")):
        raise ValueError("LIVE_MARKET_EVAL_PAIN_INVALID")
    intent = payload.get("buyer_intent_state")
    if intent not in _INTENT:
        raise ValueError("LIVE_MARKET_EVAL_INTENT_INVALID")
    productability = payload.get("productability_state")
    if productability not in {"MEDIUM", "HIGH"}:
        raise ValueError("LIVE_MARKET_EVAL_PRODUCTABILITY_INSUFFICIENT")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not 2 <= len(evidence) <= 8:
        raise ValueError("LIVE_MARKET_EVAL_EVIDENCE_COUNT")
    clean_evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("LIVE_MARKET_EVAL_EVIDENCE_INVALID")
        eid = _safe_text(item.get("evidence_id"), "market_evidence_id", 2, 80)
        if eid in seen:
            raise ValueError("LIVE_MARKET_EVAL_EVIDENCE_DUPLICATE")
        seen.add(eid)
        signal = str(item.get("signal_type") or "")
        if signal not in _ALLOWED_DEMAND_SIGNALS:
            raise ValueError("LIVE_MARKET_EVAL_SIGNAL_INVALID")
        source_ids = item.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or not set(source_ids).issubset(eligible_source_ids):
            raise ValueError("LIVE_MARKET_EVAL_SOURCE_REF_INVALID")
        if signal == "PAID_SUBSTITUTE" and not any(_source_has_paid_marker(sources[sid]) for sid in source_ids):
            raise ValueError("LIVE_MARKET_EVAL_PAID_SIGNAL_UNVERIFIED")
        if signal == "MARKETPLACE_SALE_PROXY" and not any(
            sources[sid].get("source_class") == "MARKETPLACE_LISTING" and _source_has_marketplace_proxy_marker(sources[sid])
            for sid in source_ids
        ):
            raise ValueError("LIVE_MARKET_EVAL_MARKETPLACE_PROXY_UNVERIFIED")
        clean_evidence.append({
            "evidence_id": eid,
            "signal_type": signal,
            "source_ids": list(dict.fromkeys(source_ids)),
            "rationale": _safe_text(item.get("rationale"), "market_evidence_rationale", 8, 1000),
        })
    if not any(e["signal_type"] in {"PAID_SUBSTITUTE", "MARKETPLACE_SALE_PROXY"} for e in clean_evidence):
        raise ValueError("LIVE_MARKET_EVAL_WTP_SIGNAL_REQUIRED")

    productability_source_ids = payload.get("productability_source_ids")
    if not isinstance(productability_source_ids, list) or not productability_source_ids or not set(productability_source_ids).issubset(eligible_source_ids):
        raise ValueError("LIVE_MARKET_EVAL_PRODUCTABILITY_REFS_INVALID")
    reasons = payload.get("selection_reasons")
    if not isinstance(reasons, list) or not reasons:
        raise ValueError("LIVE_MARKET_EVAL_REASONS_REQUIRED")
    return {
        "selected_problem_seed_id": selected,
        "pain_observation": {k: pain[k] for k in ("severity", "frequency", "urgency")},
        "buyer_intent_state": intent,
        "productability_state": productability,
        "productability_source_ids": list(dict.fromkeys(productability_source_ids)),
        "evidence": clean_evidence,
        "selection_reasons": [_safe_text(x, "selection_reason", 5, 600) for x in reasons[:8]],
    }


def _expand_source_evidence(source_ids: list[str], source_map: dict[str, dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for sid in source_ids:
        source = source_map[sid]
        for unit in source.get("evidence_units") or []:
            eid = unit.get("evidence_id")
            if eid and eid not in refs:
                refs.append(eid)
    if not refs:
        raise ValueError("LIVE_SOURCE_EVIDENCE_EMPTY")
    return refs


def build_demand_and_worth(
    *,
    seed: dict[str, Any],
    market_evaluation: dict[str, Any],
    source_bundle: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    problem_seed.validate_problem_seed(seed)
    source_map = _source_index(source_bundle)
    evidence: list[dict[str, Any]] = []
    for item in market_evaluation["evidence"]:
        evidence.append({
            "evidence_id": item["evidence_id"],
            "signal_type": item["signal_type"],
            "evidence_refs": _expand_source_evidence(item["source_ids"], source_map),
            "money": None,
        })
    demand_packet = {
        "schema_version": demand_wtp.SCHEMA,
        "packet_id": "H03-DMD-LIVE001-001",
        "holding_id": "H03",
        "problem_seed_id": seed["problem_seed_id"],
        "pain_observation": copy.deepcopy(market_evaluation["pain_observation"]),
        "buyer_intent_state": market_evaluation["buyer_intent_state"],
        "evidence": evidence,
        "wtp_assessment": demand_wtp.derive_wtp_assessment(evidence),
        "truth_status": "CANDIDATE",
    }
    demand_wtp.validate_demand_packet(demand_packet)
    productability = {
        "state": market_evaluation["productability_state"],
        "evidence_refs": _expand_source_evidence(market_evaluation["productability_source_ids"], source_map),
    }
    worth = worth_making.evaluate_worth_making(
        decision_id="H03-WM-LIVE001-001",
        seed=seed,
        demand_packet=demand_packet,
        productability=productability,
    )
    return demand_packet, worth


def build_live_research_plan(*, seed: dict[str, Any], worth: dict[str, Any]) -> dict[str, Any]:
    if worth.get("decision") != "MAKE":
        raise ValueError("LIVE_RESEARCH_PLAN_REQUIRES_MAKE")
    pain = seed["pain"]["statement"]
    job = seed["job_to_be_done"]
    outcome = seed["desired_outcome"]
    plan = {
        "schema_version": research_plan.SCHEMA,
        "research_plan_id": "H03-RPLAN-LIVE001-001",
        "holding_id": "H03",
        "problem_seed_id": seed["problem_seed_id"],
        "worth_making_decision_id": worth["decision_id"],
        "questions": [
            {
                "question_id": "RQ-PAIN",
                "question": f"What recurring real-world friction, failed attempts, and practical constraints do people report when trying to {job}, especially around: {pain}?",
                "lane": "COMMUNITY_PAIN",
                "critical": True,
                "required_source_classes": ["COMMUNITY_DISCUSSION", "CUSTOMER_REVIEW", "SPECIALIST_PUBLICATION"],
                "minimum_independent_sources": 2,
            },
            {
                "question_id": "RQ-SOLUTIONS",
                "question": f"What existing paid or structured solutions address this job, what do they actually provide, and what gaps remain for someone seeking this outcome: {outcome}?",
                "lane": "COMPETITOR_SOLUTIONS",
                "critical": True,
                "required_source_classes": ["COMPETITOR_PRODUCT", "MARKETPLACE_LISTING", "SPECIALIST_PUBLICATION"],
                "minimum_independent_sources": 2,
            },
            {
                "question_id": "RQ-PRACTICE",
                "question": f"What evidence-supported practical workflow, decision rules, checks, and common mistakes can safely help a person achieve this outcome: {outcome}?",
                "lane": "GENERAL_KNOWLEDGE",
                "critical": True,
                "required_source_classes": ["SPECIALIST_PUBLICATION", "OFFICIAL_PRIMARY", "ACADEMIC_PAPER"],
                "minimum_independent_sources": 2,
            },
        ],
        "budget": {"max_research_jobs": 4, "max_sources": 12},
        "stop_policy": {
            "minimum_source_classes": 2,
            "diminishing_returns_window_packets": 2,
            "minimum_new_supported_findings_in_window": 2,
        },
        "truth_status": "PLAN",
    }
    return research_plan.validate_research_plan(plan)


def _validate_research_scout(payload: Any, *, question: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("source_requests"), list):
        raise ValueError("LIVE_RESEARCH_SCOUT_INVALID")
    requests = payload["source_requests"]
    if not 2 <= len(requests) <= 4:
        raise ValueError("LIVE_RESEARCH_SCOUT_COUNT")
    allowed = set(question["required_source_classes"])
    clean: list[dict[str, Any]] = []
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("LIVE_RESEARCH_SOURCE_INVALID")
        url = str(req.get("url") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("LIVE_RESEARCH_URL_INVALID")
        source_class = str(req.get("source_class") or "")
        if source_class not in allowed:
            raise ValueError("LIVE_RESEARCH_CLASS_OUTSIDE_PLAN")
        terms = req.get("relevance_terms")
        if not isinstance(terms, list) or not 1 <= len(terms) <= 6:
            raise ValueError("LIVE_RESEARCH_TERMS_INVALID")
        clean.append({
            "url": url,
            "source_class": source_class,
            "relevance_terms": [_safe_text(x, "research_term", 2, 80) for x in terms],
            "signal_hint": "PRODUCTABILITY",
        })
    return {"source_requests": clean}


def _validate_research_analysis(payload: Any, *, source_ids: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise ValueError("LIVE_RESEARCH_ANALYSIS_INVALID")
    findings = payload["findings"]
    if not 2 <= len(findings) <= 7:
        raise ValueError("LIVE_RESEARCH_FINDING_COUNT")
    seen: set[str] = set()
    clean: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("LIVE_RESEARCH_FINDING_INVALID")
        fid = _safe_text(item.get("finding_id"), "research_finding_id", 2, 80)
        if fid in seen:
            raise ValueError("LIVE_RESEARCH_FINDING_DUPLICATE")
        seen.add(fid)
        refs = item.get("source_ids")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(source_ids):
            raise ValueError("LIVE_RESEARCH_FINDING_SOURCE_INVALID")
        clean.append({
            "finding_id": fid,
            "text": _safe_text(item.get("text"), "research_finding_text", 20, 1800),
            "source_ids": list(dict.fromkeys(refs)),
        })
    return {"findings": clean}


def _build_research_packet(
    *,
    question: dict[str, Any],
    analyst_card: dict[str, Any],
    analyst_result: dict[str, Any],
    source_bundle: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    source_map = _source_index(source_bundle)
    findings: list[dict[str, Any]] = []
    for item in analysis["findings"]:
        findings.append({
            "finding_id": item["finding_id"],
            "text": item["text"],
            "evidence_refs": _expand_source_evidence(item["source_ids"], source_map),
        })
    obs = analyst_result.get("worker_observation") or {}
    return {
        "schema_version": "die.h03.research-packet.v1",
        "research_packet_id": f"H03-RP-LIVE001-{question['question_id']}",
        "holding_id": "H03",
        "work_card_id": analyst_card["work_card_id"],
        "question_id": question["question_id"],
        "provider_observation": {
            "provider_id": obs.get("provider_id"),
            "model_route": obs.get("effective_model"),
            "effective_mode": obs.get("effective_mode"),
            "profile_shard_id": "H03-KNOWLEDGE-A",
            "transport_family": "BROWSER_CDP",
            "execution_mode": EXECUTION_MODE,
        },
        "source_snapshots": copy.deepcopy(source_bundle["verified_sources"]),
        "findings": findings,
        "terminal_status": "SUCCEEDED",
        "truth_status": "UNVERIFIED_RESEARCH_PACKET",
    }


def build_composite_source_packet(packets: list[dict[str, Any]]) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for packet in packets:
        for source in packet.get("source_snapshots") or []:
            sid = source.get("source_id")
            if not sid:
                raise ValueError("LIVE_COMPOSITE_SOURCE_ID_REQUIRED")
            if sid in sources and sources[sid] != source:
                raise ValueError("LIVE_COMPOSITE_SOURCE_COLLISION")
            sources[sid] = source
            review = source.get("review") or {}
            rights = source.get("rights_policy") or {}
            if review.get("status") != "ACCEPTED_FOR_KNOWLEDGE" or review.get("crawler_or_llm_authority") is not False:
                raise ValueError("LIVE_COMPOSITE_SOURCE_UNGOVERNED")
            if rights.get("state") != "REVIEWED_REFERENCE_ONLY" or rights.get("verbatim_reuse_allowed") is not False:
                raise ValueError("LIVE_COMPOSITE_RIGHTS_INVALID")
            for unit in source.get("evidence_units") or []:
                eid = unit.get("evidence_id")
                if not eid or not unit.get("text"):
                    raise ValueError("LIVE_COMPOSITE_EVIDENCE_INVALID")
                if eid in evidence and evidence[eid] != unit:
                    raise ValueError("LIVE_COMPOSITE_EVIDENCE_COLLISION")
                evidence[eid] = unit
    if not sources or not evidence:
        raise ValueError("LIVE_COMPOSITE_EMPTY")
    source_summary = [
        {"source_id": sid, "source_uri": src.get("source_uri"), "raw_sha256": src.get("raw_sha256")}
        for sid, src in sorted(sources.items())
    ]
    raw_digest = hashlib.sha256(json.dumps(source_summary, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    joined = "\n".join(evidence[eid]["text"] for eid in sorted(evidence))
    normalized_digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return {
        "source_id": "H03-LIVE001-GOVERNED-SOURCE-BUNDLE",
        "source_uri": "artifact://h03/LIVE-ORG-001/governed-source-bundle",
        "rights_status": "GOVERNED_EXTERNAL",
        "raw_sha256": raw_digest,
        "normalized_text_sha256": normalized_digest,
        "acquisition_method": "COMPOSITE_GOVERNED_REFERENCE",
        "rights_policy": {
            "state": "REVIEWED_REFERENCE_ONLY",
            "basis": "Composite of individually fetched and governed public reference-only source snapshots.",
            "verbatim_reuse_allowed": False,
        },
        "review": {
            "status": "ACCEPTED_FOR_KNOWLEDGE",
            "reviewer_kind": "GOVERNED_RULESET",
            "reviewer_id": "H03-LIVE-COMPOSITE-SOURCE-GATE-V1",
            "decision_basis": "Every underlying source passed H03 live public-source verification and reference-only rights gate.",
            "crawler_or_llm_authority": False,
        },
        "canonical_truth": False,
        "source_count": len(sources),
        "source_ids": sorted(sources),
        "evidence_units": [copy.deepcopy(evidence[eid]) for eid in sorted(evidence)],
    }


def _validate_product_architect_payload(payload: Any, *, seed: dict[str, Any], knowledge_package: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LIVE_PRODUCT_ARCHITECT_INVALID")
    title = _safe_text(payload.get("title"), "product_title", 8, 100)
    subtitle = _safe_text(payload.get("subtitle", "Practical evidence-grounded toolkit"), "product_subtitle", 3, 180)
    claim_ids = {c["claim_id"] for c in knowledge_package["claims"]}
    section_plan = payload.get("section_plan")
    if not isinstance(section_plan, list) or not 3 <= len(section_plan) <= 7:
        raise ValueError("LIVE_PRODUCT_SECTION_COUNT")
    clean_sections: list[dict[str, Any]] = []
    coverage: set[str] = set()
    for section in section_plan:
        if not isinstance(section, dict):
            raise ValueError("LIVE_PRODUCT_SECTION_INVALID")
        ids = section.get("claim_ids")
        if not isinstance(ids, list) or not ids or not set(ids).issubset(claim_ids):
            raise ValueError("LIVE_PRODUCT_SECTION_CLAIMS_INVALID")
        coverage.update(ids)
        clean_sections.append({
            "heading": _safe_text(section.get("heading"), "section_heading", 4, 140),
            "claim_ids": list(dict.fromkeys(ids)),
        })
    if coverage != claim_ids:
        raise ValueError("LIVE_PRODUCT_CLAIM_COVERAGE_INCOMPLETE")
    profile = {
        "schema_version": product_planner.PROFILE_SCHEMA,
        "planning_profile_id": "H03-PPLAN-LIVE001-001",
        "holding_id": "H03",
        "problem_seed_id": seed["problem_seed_id"],
        "knowledge_package_id": knowledge_package["knowledge_package_id"],
        "desired_outcome": seed["desired_outcome"],
        "delivery_shape": payload.get("delivery_shape"),
        "recurrence": payload.get("recurrence"),
        "decision_complexity": payload.get("decision_complexity"),
        "explanation_depth": payload.get("explanation_depth"),
        "input_capture": payload.get("input_capture"),
        "lookup_frequency": payload.get("lookup_frequency"),
        "evidence_density": payload.get("evidence_density"),
        "reusable_structure": payload.get("reusable_structure"),
        "section_plan": clean_sections,
    }
    product_planner.validate_planning_profile(profile, available_claim_ids=claim_ids)
    return {"title": title, "subtitle": subtitle, "profile": profile}


def _producer_dispatch_stub(
    *,
    card: dict[str, Any],
    blueprint: dict[str, Any],
    section_index: int,
    provider_id: str,
    effective_model: str | None,
) -> dict[str, Any]:
    section = blueprint["sections"][section_index]
    sid = f"SEC-{section_index+1:03d}"
    return {
        "work_card": card,
        "route": {
            "provider_id": provider_id,
            "model_route": effective_model,
            "profile_shard_id": "H03-KNOWLEDGE-A",
            "transport_family": "BROWSER_CDP",
        },
        "request": {"context": {"product_id": blueprint["product_id"]}},
        "section_id": sid,
        "section_heading": section["heading"],
        "claim_ids": list(section["claim_ids"]),
    }


def _validate_producer_payload(
    payload: Any,
    *,
    card: dict[str, Any],
    blueprint: dict[str, Any],
    knowledge_package: dict[str, Any],
    section_index: int,
) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("blocks"), list):
        raise ValueError("LIVE_PRODUCER_OUTPUT_INVALID")
    if not 2 <= len(payload["blocks"]) <= 7:
        raise ValueError("LIVE_PRODUCER_BLOCK_COUNT")
    for block in payload["blocks"]:
        if not isinstance(block, dict) or len(" ".join(str(block.get("text", "")).split())) < 35:
            raise ValueError("LIVE_PRODUCER_BLOCK_TOO_THIN")
    semantic_producer.normalize_producer_output(
        dispatch=_producer_dispatch_stub(
            card=card,
            blueprint=blueprint,
            section_index=section_index,
            provider_id="VALIDATOR",
            effective_model="VALIDATOR",
        ),
        knowledge_package=knowledge_package,
        model_output=payload,
    )
    return payload


def _validate_review_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("LIVE_REVIEW_OUTPUT_INVALID")
    decision = payload.get("decision")
    if decision not in {"PASS", "REVISE", "REJECT"}:
        raise ValueError("LIVE_REVIEW_DECISION_INVALID")
    confidence = payload.get("evidence_confidence")
    if confidence not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("LIVE_REVIEW_CONFIDENCE_INVALID")
    reasons = payload.get("decision_reasons")
    if not isinstance(reasons, list) or len(reasons) < 2:
        raise ValueError("LIVE_REVIEW_REASONS_REQUIRED")
    risks = payload.get("risk_flags") or []
    rights = payload.get("rights_flags") or []
    if not isinstance(risks, list) or not isinstance(rights, list):
        raise ValueError("LIVE_REVIEW_FLAGS_INVALID")
    return {
        "decision": decision,
        "evidence_confidence": confidence,
        "risk_flags": [_safe_text(x, "risk_flag", 2, 500) for x in risks[:12]],
        "rights_flags": [_safe_text(x, "rights_flag", 2, 500) for x in rights[:12]],
        "decision_reasons": [_safe_text(x, "review_reason", 5, 1200) for x in reasons[:12]],
    }


def _copy_founder_qc_package(
    *,
    founder_qc_root: Path,
    output_root: Path,
    product_id: str,
    artifacts: dict[str, Any],
) -> Path:
    src = output_root / product_id
    dst = founder_qc_root / product_id
    dst.mkdir(parents=True, exist_ok=True)
    for path in src.iterdir():
        if path.is_file():
            shutil.copy2(path, dst / path.name)
    for name, payload in artifacts.items():
        _json_write(dst / f"{name}.json", payload)
    return dst


def run_live_org(
    *,
    artifact_root: Path,
    output_root: Path,
    founder_qc_root: Path,
    mc_endpoint: str = "http://127.0.0.1:8891",
    source_verifier: Callable[..., dict[str, Any]] = live_source_verifier.verify_source_bundle,
    courier: artifact_courier.ArtifactCourier | None = None,
    client: Any | None = None,
    worker: Any | None = None,
) -> dict[str, Any]:
    courier = courier or artifact_courier.ArtifactCourier(artifact_root)
    client = client or MissionControlH03Client(endpoint=mc_endpoint, timeout_seconds=420.0)
    worker = worker or LiveWorkCardRunner(courier, client, max_input_chars=95_000)

    brief_ref, brief, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-OPPORTUNITY-BRIEF", kind="opportunity_brief",
        declared_schema="die.h03.live-opportunity-brief.v1", stage_id="A00-BRIEF", queue="opportunity-brief",
        builder=lambda: {
            "schema_version": "die.h03.live-opportunity-brief.v1",
            "holding_id": "H03",
            "question": OPPORTUNITY_QUESTION,
            "market_scope": ["United States", "Canada", "United Kingdom", "Australia", "New Zealand"],
            "candidate_target": 8,
            "constraints": {
                "structured_digital_solution": True,
                "recurring_or_repeatable_problem_preferred": True,
                "observable_friction_required_for_promotion": True,
                "high_stakes_medical_legal_financial_advice_excluded": True,
                "regulated_or_illicit_product_categories_excluded": True,
                "no_publication": True,
                "no_spend": True,
            },
        },
    )

    seed_card = _make_card(
        work_card_id="H03-WC-LIVE001-A-CURATE", role="SEED_CURATOR", queue="A-seed-curation",
        inputs=[brief_ref], artifact_kind="seed_curator_output",
        output_schema="die.h03.live-seed-curator-output.v1", max_attempts=3,
    )
    seed_result = worker.run(
        run_id=RUN_ID, card=seed_card, timeout_seconds=300,
        instruction=(
            "Generate 8 distinct recurring human-problem candidates for the supplied high-income English-speaking market brief. "
            "Return exactly JSON {\"candidates\":[...]}. Each candidate must contain problem_seed_id, persona {actor, qualifier}, "
            "context, trigger, job_to_be_done, pain {statement}, and desired_outcome. Do not claim demand, WTP, severity, frequency, "
            "urgency, or source evidence at this curation stage. Favor practical low-risk problems that can be addressed by a structured "
            "guide, checklist, workbook, playbook, reference sheet, worksheet, template, or bounded report. Avoid generic topics."
        ),
        payload_validator=_validate_seed_curator_payload,
    )
    seed_candidates = courier.resolve(seed_result["output_artifacts"][0])
    seed_batch_ref, seed_batch, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-PROBLEM-SEED-BATCH", kind="problem_seed_batch",
        declared_schema=problem_discovery.BATCH_SCHEMA, stage_id="A10-SEED-BATCH", queue="A-seed-normalize",
        builder=lambda: problem_discovery.build_problem_seed_batch(
            batch_id="LIVE001",
            source_signal_refs=[brief_ref["ref"]],
            candidates=seed_candidates["candidates"],
        ),
    )
    if len(seed_batch["candidates"]) < 5:
        raise RuntimeError("LIVE_ORG_INSUFFICIENT_DEDUPED_SEEDS")

    seed_ids = {s["problem_seed_id"] for s in seed_batch["candidates"]}
    market_scout_card = _make_card(
        work_card_id="H03-WC-LIVE001-B-MARKET-SCOUT", role="MARKET_RESEARCHER", queue="B-market-source-scout",
        inputs=[seed_batch_ref], artifact_kind="market_source_scout",
        output_schema="die.h03.live-market-source-scout.v1", max_attempts=3,
    )
    market_scout_result = worker.run(
        run_id=RUN_ID, card=market_scout_card, timeout_seconds=420,
        instruction=(
            "Use web/search research to shortlist up to 4 supplied problem seeds with the strongest observable commercial friction. "
            "Return exactly JSON {\"candidate_sources\":[{\"problem_seed_id\":...,\"source_requests\":[...]}]}. Each source request "
            "must contain url, source_class, signal_hint, relevance_terms. source_class must be one of OFFICIAL_PRIMARY, "
            "SPECIALIST_PUBLICATION, MARKETPLACE_LISTING, CUSTOMER_REVIEW, COMMUNITY_DISCUSSION, SEARCH_DEMAND, COMPETITOR_PRODUCT. "
            "signal_hint must be PAID_SUBSTITUTE, MARKETPLACE_SALE_PROXY, PURCHASE_INTENT_SEARCH, REPEATED_PAIN, ENGAGEMENT_ONLY, "
            "or PRODUCTABILITY. Prefer direct public HTML pages accessible without login/paywall, not search-result pages. Do not invent URLs. "
            "For each candidate try to include a paid substitute/competitor source and a pain/authority source. Source text is NOT evidence yet; "
            "the local verifier will fetch the URLs independently."
        ),
        payload_validator=lambda p: _validate_scout_payload(p, seed_ids=seed_ids),
    )
    market_scout = courier.resolve(market_scout_result["output_artifacts"][0])

    market_sources_ref, market_sources, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-MARKET-VERIFIED-SOURCES", kind="verified_source_bundle",
        declared_schema=live_source_verifier.BUNDLE_SCHEMA, stage_id="B10-MARKET-VERIFY", queue="B-market-source-verify",
        builder=lambda: source_verifier(
            run_id=RUN_ID,
            source_requests=_flatten_market_source_requests(market_scout),
            max_sources=14,
        ),
    )
    market_ready_ids = _market_ready_candidate_ids(market_sources)
    if not market_ready_ids:
        recovery_card = _make_card(
            work_card_id="H03-WC-LIVE001-B2-MARKET-RECOVERY", role="MARKET_RESEARCHER", queue="B2-market-source-recovery",
            inputs=[seed_batch_ref, market_scout_result["output_artifacts"][0], market_sources_ref],
            artifact_kind="market_source_scout",
            output_schema="die.h03.live-market-source-scout.v1", max_attempts=3,
        )
        recovery_result = worker.run(
            run_id=RUN_ID, card=recovery_card, timeout_seconds=600, preferred_provider="copilot",
            instruction=(
                "Recover the market-source shortlist after the local verifier rejected or could not fetch enough earlier URLs. "
                "Use web/search to propose replacement DIRECT public HTML pages for up to 4 supplied problem seeds. The input includes the "
                "original scout output and a verified-source bundle containing both accepted sources and failed attempted URLs. Do NOT repeat "
                "any attempted URL. Return exactly JSON {\"candidate_sources\":[{\"problem_seed_id\":...,\"source_requests\":[...]}]}. "
                "Each request must contain url, source_class, signal_hint, relevance_terms. Prioritize sources likely to be fetchable without "
                "login/paywall/JavaScript-only rendering. For each candidate, seek two independent hosts: one source that visibly demonstrates a "
                "paid substitute or marketplace demand signal (pricing/plans/reviews/sales where actually observable), and one authority/pain source "
                "that substantiates recurring friction or productability. Prefer official vendor pricing/product pages, government/recognized authority "
                "guidance, and substantive specialist publications. Do not invent URLs or facts; local code will fetch, hash, relevance-check, and "
                "govern every page before it becomes evidence."
            ),
            payload_validator=lambda p: _validate_scout_payload(p, seed_ids=seed_ids),
        )
        recovery_scout = courier.resolve(recovery_result["output_artifacts"][0])
        attempted_urls = _bundle_urls(market_sources)
        recovery_requests = _flatten_market_source_requests(
            recovery_scout, prefix="LIVE001-MKT-R2", exclude_urls=attempted_urls
        )
        if not recovery_requests:
            raise RuntimeError("LIVE_ORG_MARKET_RECOVERY_R2_NO_NEW_URLS")
        recovery_sources_ref, recovery_sources, _ = _ensure_local_artifact(
            courier=courier, client=client,
            artifact_id="LIVE001-MARKET-RECOVERY-R2-SOURCES", kind="verified_source_bundle",
            declared_schema=live_source_verifier.BUNDLE_SCHEMA, stage_id="B20-MARKET-RECOVERY-VERIFY",
            queue="B2-market-source-recovery-verify",
            builder=lambda: source_verifier(
                run_id=RUN_ID, source_requests=recovery_requests, max_sources=14
            ),
        )
        market_sources_ref, market_sources, _ = _ensure_local_artifact(
            courier=courier, client=client,
            artifact_id="LIVE001-MARKET-VERIFIED-SOURCES-R2", kind="verified_source_bundle",
            declared_schema=live_source_verifier.BUNDLE_SCHEMA, stage_id="B30-MARKET-RECOVERY-MERGE",
            queue="B2-market-source-recovery-merge",
            builder=lambda: _merge_source_bundles(market_sources, recovery_sources),
        )
        market_ready_ids = _market_ready_candidate_ids(market_sources)

    if not market_ready_ids:
        coverage = _market_candidate_coverage(market_sources)
        raise RuntimeError(
            "LIVE_ORG_MARKET_RECOVERY_R2_EXHAUSTED:"
            f"verified={market_sources['verified_count']}:independent_hosts={_independent_source_count(market_sources)}:"
            f"coverage={json.dumps(coverage, sort_keys=True)}"
        )

    market_eval_card = _make_card(
        work_card_id="H03-WC-LIVE001-C-MARKET-EVAL", role="MARKET_RESEARCHER", queue="C-demand-wtp-evaluation",
        inputs=[seed_batch_ref, market_sources_ref], artifact_kind="market_evaluation",
        output_schema="die.h03.live-market-evaluation.v1", max_attempts=3,
    )
    market_eval_result = worker.run(
        run_id=RUN_ID, card=market_eval_card, timeout_seconds=420,
        instruction=(
            "Evaluate the supplied problem seeds using ONLY the locally verified source snapshots. Select one candidate only if evidence "
            "supports a plausible MAKE gate. Return JSON with selected_problem_seed_id; pain_observation {severity,frequency,urgency}; "
            "buyer_intent_state; productability_state; productability_source_ids; evidence; selection_reasons. Each evidence item must contain "
            "evidence_id, signal_type, source_ids, rationale. signal_type may be PAID_SUBSTITUTE, MARKETPLACE_SALE_PROXY, "
            "PURCHASE_INTENT_SEARCH, REPEATED_PAIN, or ENGAGEMENT_ONLY. Do not use REVEALED_SPEND unless an actual transaction record was "
            "supplied (none is supplied here). Reference source_id values exactly as present in the verified bundle. Select a candidate only when "
            "it has at least two verified sources, at least one paid-substitute/marketplace signal, and MEDIUM/HIGH productability. If no candidate "
            "honestly meets that bar, return {\"selected_problem_seed_id\":null,\"no_make_reason\":\"...\"}."
        ),
        payload_validator=lambda p: _validate_market_evaluation(p, seed_ids=seed_ids, source_bundle=market_sources),
    )
    market_eval = courier.resolve(market_eval_result["output_artifacts"][0])
    if market_eval.get("selected_problem_seed_id") is None:
        raise RuntimeError("LIVE_ORG_NO_MAKE_CANDIDATE:" + market_eval["no_make_reason"])
    selected_seed = next(s for s in seed_batch["candidates"] if s["problem_seed_id"] == market_eval["selected_problem_seed_id"])

    demand_ref, demand_packet, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-DEMAND-WTP", kind="demand_wtp_packet",
        declared_schema=demand_wtp.SCHEMA, stage_id="C10-DEMAND", queue="C-demand-wtp-normalize",
        builder=lambda: build_demand_and_worth(seed=selected_seed, market_evaluation=market_eval, source_bundle=market_sources)[0],
    )
    worth_ref, worth, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-WORTH-MAKING", kind="worth_making_decision",
        declared_schema=worth_making.SCHEMA, stage_id="C20-WORTH", queue="C-worth-making",
        builder=lambda: build_demand_and_worth(seed=selected_seed, market_evaluation=market_eval, source_bundle=market_sources)[1],
    )
    if worth["decision"] != "MAKE":
        raise RuntimeError(f"LIVE_ORG_WORTH_MAKING_STOP:{worth['decision']}:{','.join(worth['reason_codes'])}")

    selected_seed_ref, _, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-SELECTED-PROBLEM-SEED", kind="problem_seed",
        declared_schema=problem_seed.SCHEMA, stage_id="C30-SELECTED-SEED", queue="C-selected-seed",
        builder=lambda: selected_seed,
    )
    plan_ref, plan, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-RESEARCH-PLAN", kind="research_plan",
        declared_schema=research_plan.SCHEMA, stage_id="D00-PLAN", queue="D-research-plan",
        builder=lambda: build_live_research_plan(seed=selected_seed, worth=worth),
    )

    research_packets: list[dict[str, Any]] = []
    research_packet_refs: list[dict[str, Any]] = []
    for q_index, question in enumerate(plan["questions"], start=1):
        role = "MARKET_RESEARCHER" if question["lane"] in {"MARKET_WTP", "COMMUNITY_PAIN", "COMPETITOR_SOLUTIONS"} else "KNOWLEDGE_RESEARCHER"
        scout_card = _make_card(
            work_card_id=f"H03-WC-LIVE001-D{q_index}-SCOUT", role=role, queue=f"D{q_index}-research-scout-{question['question_id'].lower()}",
            inputs=[selected_seed_ref, demand_ref, plan_ref], artifact_kind="research_source_scout",
            output_schema="die.h03.live-research-source-scout.v1", max_attempts=3,
        )
        scout_result = worker.run(
            run_id=RUN_ID, card=scout_card, timeout_seconds=420,
            instruction=(
                f"Research question {question['question_id']}: {question['question']} Use web/search capability to identify 2-4 independent "
                f"public sources. Return exactly JSON {{\"source_requests\":[...]}}. Every source request must contain url, source_class, "
                f"relevance_terms. source_class MUST be one of: {', '.join(question['required_source_classes'])}. Prefer direct public pages "
                "with substantive text and no login/paywall. Do not invent URLs and do not return source text as evidence; local code will fetch "
                "and hash the pages independently."
            ),
            payload_validator=lambda p, q=question: _validate_research_scout(p, question=q),
        )
        scout_payload = courier.resolve(scout_result["output_artifacts"][0])
        reqs = []
        for i, req in enumerate(scout_payload["source_requests"], start=1):
            reqs.append({
                "source_id": f"LIVE001-{question['question_id']}-S{i:02d}",
                "url": req["url"],
                "source_class": req["source_class"],
                "relevance_terms": req["relevance_terms"],
                "signal_hint": "PRODUCTABILITY",
                "candidate_id": selected_seed["problem_seed_id"],
            })
        bundle_ref, bundle, _ = _ensure_local_artifact(
            courier=courier, client=client,
            artifact_id=f"LIVE001-{question['question_id']}-VERIFIED-SOURCES", kind="verified_source_bundle",
            declared_schema=live_source_verifier.BUNDLE_SCHEMA, stage_id=f"D{q_index}5-VERIFY", queue=f"D{q_index}-research-source-verify",
            builder=lambda requests=reqs: source_verifier(run_id=RUN_ID, source_requests=requests, max_sources=4),
        )
        if bundle["verified_count"] < question["minimum_independent_sources"]:
            raise RuntimeError(f"LIVE_ORG_RESEARCH_SOURCE_COVERAGE:{question['question_id']}:{bundle['verified_count']}")
        source_ids = set(_source_index(bundle))
        analyst_card = _make_card(
            work_card_id=f"H03-WC-LIVE001-E{q_index}-ANALYZE", role=role, queue=f"E{q_index}-research-analysis-{question['question_id'].lower()}",
            inputs=[selected_seed_ref, plan_ref, bundle_ref], artifact_kind="research_analysis",
            output_schema="die.h03.live-research-analysis.v1", max_attempts=3,
        )
        analyst_result = worker.run(
            run_id=RUN_ID, card=analyst_card, timeout_seconds=420,
            instruction=(
                f"Answer research question {question['question_id']} using ONLY the verified source snapshots in the input. Return exactly JSON "
                "{\"findings\":[{\"finding_id\":\"...\",\"text\":\"...\",\"source_ids\":[\"...\"]}]}. Produce 2-6 specific useful "
                "findings. Every finding must reference actual source_id values from the verified bundle. Preserve uncertainty and disagreements; "
                "do not invent evidence, statistics, prices, or facts not present in the supplied source text."
            ),
            payload_validator=lambda p, ids=source_ids: _validate_research_analysis(p, source_ids=ids),
        )
        analysis = courier.resolve(analyst_result["output_artifacts"][0])
        packet = _build_research_packet(
            question=question, analyst_card=analyst_card, analyst_result=analyst_result,
            source_bundle=bundle, analysis=analysis,
        )
        packet_ref, packet, _ = _ensure_local_artifact(
            courier=courier, client=client,
            artifact_id=f"LIVE001-RP-{question['question_id']}", kind="research_packet",
            declared_schema="die.h03.research-packet.v1", stage_id=f"E{q_index}5-PACKET", queue=f"E{q_index}-research-packet",
            builder=lambda value=packet: value,
        )
        research_packets.append(packet)
        research_packet_refs.append(packet_ref)

    classes_seen = sorted({s.get("source_class") for p in research_packets for s in p.get("source_snapshots") or [] if s.get("source_class")})
    stop = research_plan.evaluate_stop(plan, {
        "completed_jobs": len(research_packets),
        "source_count": len({s["source_id"] for p in research_packets for s in p.get("source_snapshots") or []}),
        "covered_question_ids": [p["question_id"] for p in research_packets],
        "source_classes_seen": classes_seen,
        "unresolved_critical_contradictions": 0,
        "recent_new_supported_findings": [len(p["findings"]) for p in research_packets],
    })
    if not stop.get("critical_covered") or stop["decision"] == "CONTINUE":
        raise RuntimeError(f"LIVE_ORG_RESEARCH_NOT_STOP_READY:{stop}")
    stop_ref, _, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-RESEARCH-STOP", kind="research_stop_decision",
        declared_schema="die.h03.research-stop-decision.v1", stage_id="F00-STOP", queue="F-research-stop",
        builder=lambda: {**stop, "source_classes_seen": classes_seen},
    )

    knowledge_map_id = "H03-KM-LIVE001-001"
    synth_card = _make_card(
        work_card_id="H03-WC-LIVE001-G-SYNTH", role="SYNTHESIZER", queue="G-knowledge-synthesis",
        inputs=research_packet_refs, artifact_kind="synthesis_model_output",
        output_schema="die.h03.live-synthesis-output.v1", max_attempts=3,
    )
    synth_result = worker.run(
        run_id=RUN_ID, card=synth_card, timeout_seconds=480,
        instruction=(
            "Synthesize the supplied governed research packets. Return exactly JSON with keys supported_findings, contradictions, gaps, "
            "market_wtp_findings, claims. supported_findings items: finding_id,text,evidence_refs. contradictions: contradiction_id,statement,"
            "evidence_refs (at least 2),resolution_state RESOLVED or UNRESOLVED. gaps: gap_id,question,critical boolean. market_wtp_findings: "
            "finding_id,text,evidence_refs,signal_type. claims: claim_id,text,evidence_refs. Every evidence_ref MUST be an evidence_id that appears "
            "inside the supplied source_snapshots; never cite source_id, URL, finding_id, or anything invented. Produce 5-10 practical product "
            "claims that help the buyer achieve the selected problem outcome. Keep market/WTP observations in market_wtp_findings rather than "
            "turning them into product instructions unless the source directly supports the instruction. Preserve real contradictions and mark a "
            "gap critical only if it truly blocks safe usefulness."
        ),
        payload_validator=lambda p: (
            knowledge_synthesis.normalize_synthesis_output(
                knowledge_map_id=knowledge_map_id,
                candidate_id="H03-KPC-LIVE001-001",
                packets=research_packets,
                model_output=p,
            ) and p
        ),
    )
    synth_payload = courier.resolve(synth_result["output_artifacts"][0])
    knowledge_map, candidate = knowledge_synthesis.normalize_synthesis_output(
        knowledge_map_id=knowledge_map_id,
        candidate_id="H03-KPC-LIVE001-001",
        packets=research_packets,
        model_output=synth_payload,
    )
    if candidate["promotion_state"] != "ELIGIBLE_FOR_KNOWLEDGE_VALIDATION":
        raise RuntimeError(f"LIVE_ORG_KNOWLEDGE_PROMOTION_BLOCKED:{candidate['promotion_state']}")

    knowledge_map_ref, _, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-KNOWLEDGE-MAP", kind="knowledge_map",
        declared_schema=knowledge_synthesis.MAP_SCHEMA, stage_id="G10-MAP", queue="G-knowledge-map",
        builder=lambda: knowledge_map,
    )
    source_packet = build_composite_source_packet(research_packets)
    knowledge_package = {
        "schema_version": "die.h03.knowledge-package.v1",
        "knowledge_package_id": "H03-KP-LIVE001-001",
        "holding_id": "H03",
        "version": 1,
        "rights_status": "GOVERNED_EXTERNAL",
        "source_packet": source_packet,
        "claims": copy.deepcopy(candidate["claims"]),
    }
    h03_factory.validate_knowledge_package(knowledge_package)
    kp_ref, knowledge_package, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-KNOWLEDGE-PACKAGE", kind="knowledge_package",
        declared_schema="die.h03.knowledge-package.v1", stage_id="G20-KP", queue="G-knowledge-package",
        builder=lambda: knowledge_package,
    )

    architect_card = _make_card(
        work_card_id="H03-WC-LIVE001-H-PRODUCT-ARCH", role="PRODUCT_ARCHITECT", queue="H-product-architecture",
        inputs=[selected_seed_ref, demand_ref, kp_ref], artifact_kind="product_planning_candidate",
        output_schema="die.h03.live-product-planning-candidate.v1", max_attempts=3,
    )
    architect_result = worker.run(
        run_id=RUN_ID, card=architect_card, timeout_seconds=360,
        instruction=(
            "Design the minimum sufficient useful digital product from the accepted Knowledge Package. Return exactly JSON with title, subtitle, "
            "delivery_shape, recurrence, decision_complexity, explanation_depth, input_capture, lookup_frequency, evidence_density, "
            "reusable_structure, section_plan. delivery_shape must be one of EXECUTE_SEQUENCE, QUICK_VERIFY, ONE_TIME_INPUT_WORKFLOW, "
            "REPEATED_INPUT_WORKFLOW, COMPLEX_OPERATION, LOOKUP_REFERENCE, EVIDENCE_DECISION, REUSABLE_OUTPUT, BROAD_LEARNING, NARRATIVE_LEARNING. "
            "recurrence ONE_TIME or REPEATED; complexity/depth/density LOW|MEDIUM|HIGH; input_capture NONE|LIGHT|STRUCTURED; lookup_frequency LOW|HIGH. "
            "section_plan must have 3-7 sections, each with heading and claim_ids, and collectively cover every accepted claim_id. Select format by "
            "buyer outcome, not by a preference for ebooks. Do not add unsupported claims."
        ),
        payload_validator=lambda p: _validate_product_architect_payload(p, seed=selected_seed, knowledge_package=knowledge_package),
    )
    planning = courier.resolve(architect_result["output_artifacts"][0])
    profile = planning["profile"]
    product_id = "H03-PROD-LIVE001-001"
    blueprint = product_planner.build_product_blueprint(
        product_id=product_id,
        title=planning["title"],
        subtitle=planning["subtitle"],
        profile=profile,
        knowledge_package=knowledge_package,
    )
    profile_ref, _, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-PRODUCT-PLANNING-PROFILE", kind="product_planning_profile",
        declared_schema=product_planner.PROFILE_SCHEMA, stage_id="H10-PROFILE", queue="H-product-profile",
        builder=lambda: profile,
    )
    blueprint_ref, blueprint, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-PRODUCT-BLUEPRINT", kind="product_blueprint",
        declared_schema=product_planner.BLUEPRINT_SCHEMA, stage_id="H20-BLUEPRINT", queue="H-product-blueprint",
        builder=lambda: blueprint,
    )

    content_batches: list[dict[str, Any]] = []
    producer_providers: list[str] = []
    content_refs: list[dict[str, Any]] = []
    for index, section in enumerate(blueprint["sections"]):
        sid = f"SEC-{index+1:03d}"
        card = _make_card(
            work_card_id=f"H03-WC-LIVE001-I-PROD-{sid}", role="PRODUCER", queue=f"I-production-{sid.lower()}",
            inputs=[kp_ref, blueprint_ref], artifact_kind="producer_model_output",
            output_schema="die.h03.live-producer-output.v1", max_attempts=3,
        )
        result = worker.run(
            run_id=RUN_ID, card=card, timeout_seconds=360,
            instruction=(
                f"Write only product section {sid}: {section['heading']}. Allowed claim_ids: {', '.join(section['claim_ids'])}. Return exactly JSON "
                "{\"blocks\":[...]}. Produce 2-6 useful blocks. Each block requires block_id, kind, text, claim_ids. kind must be PARAGRAPH, STEP, "
                "BULLET, CHECKLIST_ITEM, CALLOUT, or INPUT_PROMPT. Each block must be substantive, actionable where appropriate, and use only the "
                "allowed claim_ids. Do not invent facts, citations, provenance, prices, rights, sales, or legal/medical/financial advice. No filler."
            ),
            payload_validator=lambda p, c=card, idx=index: _validate_producer_payload(
                p, card=c, blueprint=blueprint, knowledge_package=knowledge_package, section_index=idx
            ),
        )
        raw = courier.resolve(result["output_artifacts"][0])
        obs = result.get("worker_observation") or {}
        provider = str(obs.get("provider_id") or "UNKNOWN")
        producer_providers.append(provider)
        dispatch = _producer_dispatch_stub(
            card=card,
            blueprint=blueprint,
            section_index=index,
            provider_id=provider,
            effective_model=obs.get("effective_model"),
        )
        batch = semantic_producer.normalize_producer_output(
            dispatch=dispatch,
            knowledge_package=knowledge_package,
            model_output=raw,
        )
        batch["producer_observation"]["execution_mode"] = EXECUTION_MODE
        batch["producer_observation"]["effective_model"] = obs.get("effective_model")
        batch["producer_observation"]["effective_mode"] = obs.get("effective_mode")
        batch_ref, batch, _ = _ensure_local_artifact(
            courier=courier, client=client,
            artifact_id=f"LIVE001-CONTENT-{sid}", kind="content_block_batch",
            declared_schema=semantic_producer.BATCH_SCHEMA, stage_id=f"I{index+1}5-{sid}", queue=f"I-content-batch-{sid.lower()}",
            builder=lambda value=batch: value,
        )
        content_batches.append(batch)
        content_refs.append(batch_ref)

    producer_counts = Counter(producer_providers)
    dominant_producer = producer_counts.most_common(1)[0][0]
    package_ref, package_receipt, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-LOCAL-PRODUCT-PACKAGE", kind="local_product_package",
        declared_schema="die.h03.local-product-package.v1", stage_id="J00-PACKAGE", queue="J-pdf-package",
        builder=lambda: product_packager.build_local_product_package(
            output_root=output_root,
            blueprint=blueprint,
            knowledge_package=knowledge_package,
            content_batches=content_batches,
        ),
    )

    review_bundle_ref, review_bundle, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-REVIEW-BUNDLE", kind="review_bundle",
        declared_schema="die.h03.live-review-bundle.v1", stage_id="K00-REVIEW-BUNDLE", queue="K-review-bundle",
        builder=lambda: {
            "problem_seed": selected_seed,
            "demand_summary": {
                "wtp_assessment": demand_packet["wtp_assessment"],
                "buyer_intent_state": demand_packet["buyer_intent_state"],
                "evidence": demand_packet["evidence"],
            },
            "knowledge_claims": knowledge_package["claims"],
            "product_blueprint": blueprint,
            "content_batches": content_batches,
            "package_receipt": package_receipt,
            "rights_basis": source_packet["rights_policy"],
        },
    )
    review_card_work = _make_card(
        work_card_id="H03-WC-LIVE001-K-REVIEW", role="REVIEWER", queue="K-independent-review",
        inputs=[review_bundle_ref], artifact_kind="review_model_output",
        output_schema="die.h03.live-review-output.v1", max_attempts=2,
    )
    review_result = worker.run(
        run_id=RUN_ID, card=review_card_work, timeout_seconds=360,
        dominant_producer_provider=dominant_producer,
        instruction=(
            "Act as independent pre-Founder product reviewer. Inspect the supplied buyer problem, demand basis, governed claims, product blueprint, "
            "actual produced content, package QA receipt, and rights basis. Return exactly JSON with decision PASS|REVISE|REJECT, "
            "evidence_confidence LOW|MEDIUM|HIGH, risk_flags array, rights_flags array, decision_reasons array with at least two specific reasons. "
            "Check usefulness, internal consistency, unsupported assertions, evidence/claim alignment, dangerous overclaiming, IP/brand/privacy risks, "
            "and whether the product actually delivers the promised outcome. Do not silently rewrite the product and do not authorize publication."
        ),
        payload_validator=_validate_review_payload,
    )
    review_model = courier.resolve(review_result["output_artifacts"][0])
    review_obs = review_result.get("worker_observation") or {}
    lineage_stub = {
        "schema_version": RUN_SCHEMA,
        "run_id": RUN_ID,
        "execution_mode": EXECUTION_MODE,
        "research_packet_ids": [p["research_packet_id"] for p in research_packets],
        "producer_provider_ids": producer_providers,
    }
    review_card = review_engine.build_review_card(
        lineage=lineage_stub,
        problem_seed=selected_seed,
        demand_packet=demand_packet,
        knowledge_package=knowledge_package,
        blueprint=blueprint,
        package_receipt=package_receipt,
        reviewer_provider_id=str(review_obs.get("provider_id") or "UNKNOWN"),
        dominant_producer_provider_id=dominant_producer,
        reviewer_fixture=review_model,
        execution_mode=EXECUTION_MODE,
    )
    review_card["reviewer_observation"]["effective_model"] = review_obs.get("effective_model")
    review_card["reviewer_observation"]["effective_mode"] = review_obs.get("effective_mode")
    review_card_ref, review_card, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-INDEPENDENT-REVIEW", kind="founder_review_card",
        declared_schema=review_engine.SCHEMA, stage_id="K10-REVIEW-CARD", queue="K-independent-review-card",
        builder=lambda: review_card,
    )
    release_gate = product_release_gate.evaluate_release_gate(review_card=review_card, founder_qc=None)

    final_status = "WAITING_FOUNDER_QC" if review_card["decision"] == "PASS" else f"INDEPENDENT_REVIEW_{review_card['decision']}"
    summary = {
        "schema_version": RUN_SCHEMA,
        "holding_id": "H03",
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "status": final_status,
        "execution_mode": EXECUTION_MODE,
        "opportunity_question": OPPORTUNITY_QUESTION,
        "selected_problem_seed": selected_seed,
        "demand": demand_packet,
        "worth_making": worth,
        "research_stop": stop,
        "research_packet_ids": [p["research_packet_id"] for p in research_packets],
        "knowledge_map_id": knowledge_map["knowledge_map_id"],
        "knowledge_package_id": knowledge_package["knowledge_package_id"],
        "product": {
            "product_id": product_id,
            "title": blueprint["title"],
            "form": blueprint["form"],
            "sections": [s["heading"] for s in blueprint["sections"]],
            "package_receipt": package_receipt,
        },
        "producer_provider_ids": producer_providers,
        "dominant_producer_provider_id": dominant_producer,
        "independent_review": review_card,
        "release_gate": release_gate,
        "external_publication": False,
        "paid_ads": False,
        "spend_authorized": False,
        "founder_publication_gate_crossed": False,
    }
    summary_ref, summary, _ = _ensure_local_artifact(
        courier=courier, client=client,
        artifact_id="LIVE001-RUN-SUMMARY", kind="live_organism_run_summary",
        declared_schema=RUN_SCHEMA, stage_id="L00-SUMMARY", queue="L-run-summary",
        builder=lambda: summary,
    )

    qc_dir = _copy_founder_qc_package(
        founder_qc_root=founder_qc_root,
        output_root=output_root,
        product_id=product_id,
        artifacts={
            "problem-seed": selected_seed,
            "demand-wtp": demand_packet,
            "worth-making": worth,
            "research-plan": plan,
            "knowledge-map": knowledge_map,
            "knowledge-package": knowledge_package,
            "independent-review": review_card,
            "run-summary": summary,
        },
    )
    summary["founder_qc_dir"] = str(qc_dir)
    summary["summary_artifact_ref"] = summary_ref
    _json_write(qc_dir / "run-summary.json", summary)
    return summary
