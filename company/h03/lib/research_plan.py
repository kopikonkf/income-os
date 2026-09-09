from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import cognition_work_card

SCHEMA = "die.h03.research-plan.v1"
SOURCE_CLASSES = {"OFFICIAL_PRIMARY","ACADEMIC_PAPER","GOVERNMENT_PUBLIC_DATA","SPECIALIST_PUBLICATION","MARKETPLACE_LISTING","CUSTOMER_REVIEW","COMMUNITY_DISCUSSION","SEARCH_DEMAND","COMPETITOR_PRODUCT"}
LANES = {"MARKET_WTP","COMMUNITY_PAIN","OFFICIAL_DOMAIN","ACADEMIC","COMPETITOR_SOLUTIONS","GENERAL_KNOWLEDGE"}


def validate_research_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema_version") != SCHEMA or plan.get("holding_id") != "H03":
        raise ValueError("RESEARCH_PLAN_SCHEMA_INVALID")
    for f in ("research_plan_id","problem_seed_id","worth_making_decision_id"):
        if not isinstance(plan.get(f), str) or not plan[f].strip():
            raise ValueError(f"RESEARCH_PLAN_FIELD_REQUIRED:{f}")
    questions = plan.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("RESEARCH_PLAN_QUESTIONS_REQUIRED")
    seen: set[str] = set()
    for q in questions:
        if not isinstance(q, dict) or not q.get("question_id") or q["question_id"] in seen:
            raise ValueError("RESEARCH_PLAN_QUESTION_ID_INVALID")
        seen.add(q["question_id"])
        if not isinstance(q.get("question"), str) or len(q["question"].strip()) < 8 or q.get("lane") not in LANES or not isinstance(q.get("critical"), bool):
            raise ValueError("RESEARCH_PLAN_QUESTION_INVALID")
        classes = q.get("required_source_classes")
        if not isinstance(classes, list) or not classes or not set(classes).issubset(SOURCE_CLASSES):
            raise ValueError("RESEARCH_PLAN_SOURCE_CLASS_INVALID")
        if not isinstance(q.get("minimum_independent_sources"), int) or q["minimum_independent_sources"] < 1:
            raise ValueError("RESEARCH_PLAN_SOURCE_MIN_INVALID")
    budget = plan.get("budget")
    if not isinstance(budget, dict) or not isinstance(budget.get("max_research_jobs"), int) or not isinstance(budget.get("max_sources"), int) or budget["max_research_jobs"] < 1 or budget["max_sources"] < 1:
        raise ValueError("RESEARCH_PLAN_BUDGET_INVALID")
    if len(questions) > budget["max_research_jobs"]:
        raise ValueError("RESEARCH_PLAN_QUESTIONS_EXCEED_JOB_BUDGET")
    stop = plan.get("stop_policy")
    if not isinstance(stop, dict) or any(not isinstance(stop.get(k), int) for k in ("minimum_source_classes","diminishing_returns_window_packets","minimum_new_supported_findings_in_window")):
        raise ValueError("RESEARCH_PLAN_STOP_POLICY_INVALID")
    if stop["minimum_source_classes"] < 1 or stop["diminishing_returns_window_packets"] < 1 or stop["minimum_new_supported_findings_in_window"] < 0:
        raise ValueError("RESEARCH_PLAN_STOP_POLICY_INVALID")
    if plan.get("truth_status") != "PLAN":
        raise ValueError("RESEARCH_PLAN_TRUTH_STATUS_INVALID")
    return plan


def build_research_work_cards(plan: dict[str, Any]) -> list[dict[str, Any]]:
    validate_research_plan(plan)
    cards: list[dict[str, Any]] = []
    for q in plan["questions"]:
        role = "MARKET_RESEARCHER" if q["lane"] in {"MARKET_WTP","COMMUNITY_PAIN","COMPETITOR_SOLUTIONS"} else "KNOWLEDGE_RESEARCHER"
        card = {
            "schema_version": cognition_work_card.CARD_SCHEMA,
            "work_card_id": f"H03-WC-RSCH-{plan['research_plan_id']}-{q['question_id']}",
            "holding_id": "H03",
            "task_id": "H03-RSCH-002",
            "role": role,
            "queue": "research",
            "idempotency_key": f"h03-rsch:{plan['research_plan_id']}:{q['question_id']}",
            "input_artifacts": [{"artifact_id": plan["research_plan_id"], "kind": "research_plan", "ref": f"artifact://research-plan/{plan['research_plan_id']}", "sha256": None}],
            "output_contract": {"artifact_kind":"research_packet","schema_version":"die.h03.research-packet.v1"},
            "capability_requirements": cognition_work_card.standard_web_ai_capabilities(),
            "terminal_policy": {"max_attempts":3,"retryable_failures":["RATE_LIMITED","PROVIDER_UNAVAILABLE","PROFILE_UNAVAILABLE"]}
        }
        cards.append(cognition_work_card.validate_work_card(card))
    return cards


def evaluate_stop(plan: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    validate_research_plan(plan)
    completed = int(progress.get("completed_jobs", 0))
    source_count = int(progress.get("source_count", 0))
    covered = set(progress.get("covered_question_ids") or [])
    classes = set(progress.get("source_classes_seen") or [])
    unresolved_critical = int(progress.get("unresolved_critical_contradictions", 0))
    recent_findings = list(progress.get("recent_new_supported_findings") or [])
    critical_ids = {q["question_id"] for q in plan["questions"] if q["critical"]}
    critical_covered = critical_ids.issubset(covered)
    coverage_ready = critical_covered and unresolved_critical == 0 and len(classes) >= plan["stop_policy"]["minimum_source_classes"]

    if completed >= plan["budget"]["max_research_jobs"] or source_count >= plan["budget"]["max_sources"]:
        return {"decision":"STOP_BUDGET","critical_covered":critical_covered}
    if coverage_ready:
        return {"decision":"STOP_CONFIDENCE","critical_covered":True}
    window = plan["stop_policy"]["diminishing_returns_window_packets"]
    if critical_covered and len(recent_findings) >= window and sum(recent_findings[-window:]) < plan["stop_policy"]["minimum_new_supported_findings_in_window"]:
        return {"decision":"STOP_DIMINISHING_RETURNS","critical_covered":True}
    return {"decision":"CONTINUE","critical_covered":critical_covered}
