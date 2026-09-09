from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "die.h03.product-planning-profile.v1"
BLUEPRINT_SCHEMA = "die.h03.product-blueprint.v1"

_DELIVERY_SHAPES = {
    "EXECUTE_SEQUENCE","QUICK_VERIFY","ONE_TIME_INPUT_WORKFLOW","REPEATED_INPUT_WORKFLOW",
    "COMPLEX_OPERATION","LOOKUP_REFERENCE","EVIDENCE_DECISION","REUSABLE_OUTPUT",
    "BROAD_LEARNING","NARRATIVE_LEARNING"
}
_LEVELS = {"LOW","MEDIUM","HIGH"}


def validate_planning_profile(profile: dict[str, Any], *, available_claim_ids: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(profile, dict) or profile.get("schema_version") != PROFILE_SCHEMA or profile.get("holding_id") != "H03":
        raise ValueError("PRODUCT_PLANNING_PROFILE_SCHEMA_INVALID")
    for field in ("planning_profile_id","problem_seed_id","knowledge_package_id","desired_outcome"):
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise ValueError(f"PRODUCT_PLANNING_FIELD_REQUIRED:{field}")
    if profile.get("delivery_shape") not in _DELIVERY_SHAPES:
        raise ValueError("PRODUCT_PLANNING_DELIVERY_SHAPE_INVALID")
    if profile.get("recurrence") not in {"ONE_TIME","REPEATED"}:
        raise ValueError("PRODUCT_PLANNING_RECURRENCE_INVALID")
    for field in ("decision_complexity","explanation_depth","evidence_density"):
        if profile.get(field) not in _LEVELS:
            raise ValueError(f"PRODUCT_PLANNING_LEVEL_INVALID:{field}")
    if profile.get("input_capture") not in {"NONE","LIGHT","STRUCTURED"}:
        raise ValueError("PRODUCT_PLANNING_INPUT_CAPTURE_INVALID")
    if profile.get("lookup_frequency") not in {"LOW","HIGH"}:
        raise ValueError("PRODUCT_PLANNING_LOOKUP_FREQUENCY_INVALID")
    if not isinstance(profile.get("reusable_structure"), bool):
        raise ValueError("PRODUCT_PLANNING_REUSABLE_STRUCTURE_INVALID")
    sections = profile.get("section_plan")
    if not isinstance(sections, list) or not sections:
        raise ValueError("PRODUCT_PLANNING_SECTIONS_REQUIRED")
    seen_headings: set[str] = set()
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("heading"), str) or not section["heading"].strip():
            raise ValueError("PRODUCT_PLANNING_SECTION_INVALID")
        heading = section["heading"].strip()
        if heading in seen_headings:
            raise ValueError("PRODUCT_PLANNING_DUPLICATE_SECTION")
        seen_headings.add(heading)
        claims = section.get("claim_ids")
        if not isinstance(claims, list) or not claims or len(claims) != len(set(claims)) or any(not isinstance(c, str) or not c.strip() for c in claims):
            raise ValueError("PRODUCT_PLANNING_SECTION_CLAIMS_INVALID")
        if available_claim_ids is not None:
            missing = [c for c in claims if c not in available_claim_ids]
            if missing:
                raise ValueError("PRODUCT_PLANNING_UNKNOWN_CLAIM:" + ",".join(missing))
    return profile


def select_product_form(profile: dict[str, Any]) -> dict[str, Any]:
    validate_planning_profile(profile)
    shape = profile["delivery_shape"]
    recurrence = profile["recurrence"]
    input_capture = profile["input_capture"]
    reusable = profile["reusable_structure"]
    explanation = profile["explanation_depth"]
    evidence = profile["evidence_density"]
    decision = profile["decision_complexity"]
    lookup = profile["lookup_frequency"]

    reasons: list[str] = []
    if shape == "REUSABLE_OUTPUT" or reusable:
        form = "template"
        reasons.append("REUSABLE_OUTPUT_STRUCTURE")
    elif shape == "REPEATED_INPUT_WORKFLOW" and input_capture == "STRUCTURED":
        form = "workbook"
        reasons.append("REPEATED_STRUCTURED_INPUT")
    elif shape == "ONE_TIME_INPUT_WORKFLOW" and input_capture in {"LIGHT","STRUCTURED"}:
        form = "worksheet"
        reasons.append("ONE_TIME_INPUT_CAPTURE")
    elif shape == "QUICK_VERIFY":
        form = "checklist"
        reasons.append("FAST_EXECUTION_VERIFICATION")
    elif shape == "LOOKUP_REFERENCE" or (lookup == "HIGH" and explanation == "LOW"):
        form = "reference_sheet"
        reasons.append("HIGH_FREQUENCY_LOOKUP")
    elif shape == "COMPLEX_OPERATION" or (decision == "HIGH" and recurrence == "REPEATED"):
        form = "playbook"
        reasons.append("COMPLEX_OPERATIONAL_EXECUTION")
    elif shape == "EVIDENCE_DECISION":
        if evidence == "HIGH" or explanation == "HIGH":
            form = "report"
            reasons.append("EVIDENCE_DENSE_DECISION_SUPPORT")
        else:
            form = "research_brief"
            reasons.append("BOUNDED_DECISION_BRIEF")
    elif shape == "EXECUTE_SEQUENCE":
        form = "guide"
        reasons.append("SEQUENTIAL_OUTCOME")
    elif shape == "BROAD_LEARNING":
        form = "handbook"
        reasons.append("BROAD_DURABLE_REFERENCE")
    elif shape == "NARRATIVE_LEARNING":
        # Ebook is an explicit narrative-learning outcome, never a generic fallback.
        form = "ebook"
        reasons.append("EXPLICIT_NARRATIVE_LEARNING")
    else:
        raise ValueError("PRODUCT_FORM_SELECTION_UNREACHABLE")
    return {"form":form,"reason_codes":reasons}


def _template_registry() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "templates" / "pdf-template-registry.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def select_template_for_form(form: str) -> str:
    registry = _template_registry()
    preferred = {
        "checklist":"worksheet.spacious.v1",
        "worksheet":"worksheet.spacious.v1",
        "workbook":"worksheet.spacious.v1",
        "template":"worksheet.spacious.v1",
        "report":"report.compact.v1",
        "reference_sheet":"report.compact.v1",
        "research_brief":"report.compact.v1",
        "guide":"guide.clean.v1",
        "ebook":"guide.clean.v1",
        "handbook":"guide.clean.v1",
        "playbook":"guide.clean.v1",
    }
    selected = preferred.get(form)
    if selected is None:
        raise ValueError(f"PRODUCT_FORM_UNSUPPORTED:{form}")
    template = (registry.get("templates") or {}).get(selected)
    if not template or form not in (template.get("supported_forms") or []):
        raise ValueError(f"PRODUCT_TEMPLATE_FORM_MISMATCH:{form}:{selected}")
    return selected


def build_product_blueprint(*, product_id: str, title: str, profile: dict[str, Any], knowledge_package: dict[str, Any], subtitle: str = "") -> dict[str, Any]:
    if not isinstance(product_id, str) or not product_id.strip() or not isinstance(title, str) or not title.strip():
        raise ValueError("PRODUCT_BLUEPRINT_ID_TITLE_REQUIRED")
    if not isinstance(knowledge_package, dict) or knowledge_package.get("schema_version") != "die.h03.knowledge-package.v1" or knowledge_package.get("holding_id") != "H03":
        raise ValueError("PRODUCT_BLUEPRINT_ACCEPTED_KNOWLEDGE_REQUIRED")
    if knowledge_package.get("knowledge_package_id") != profile.get("knowledge_package_id"):
        raise ValueError("PRODUCT_BLUEPRINT_KNOWLEDGE_MISMATCH")
    claim_ids = {c.get("claim_id") for c in (knowledge_package.get("claims") or []) if c.get("claim_id")}
    validate_planning_profile(profile, available_claim_ids=claim_ids)
    selection = select_product_form(profile)
    template_id = select_template_for_form(selection["form"])
    return {
        "schema_version": BLUEPRINT_SCHEMA,
        "product_id": product_id.strip(),
        "knowledge_package_id": knowledge_package["knowledge_package_id"],
        "form": selection["form"],
        "title": title.strip(),
        "subtitle": subtitle.strip(),
        "sections": [{"heading":s["heading"].strip(),"claim_ids":list(s["claim_ids"])} for s in profile["section_plan"]],
        "metadata": {
            "template_id": template_id,
            "problem_seed_id": profile["problem_seed_id"],
            "planning_profile_id": profile["planning_profile_id"],
            "desired_outcome": profile["desired_outcome"],
            "form_selection_reason_codes": selection["reason_codes"],
            "format_selection_policy": "OUTCOME_ORIENTED_V1",
            "page_count_target": None,
        }
    }
