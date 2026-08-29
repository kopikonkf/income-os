#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "die.executive.worth-making-review.v1.schema.json"
WM_SCHEMA = ROOT / "die.division001.worth-making.v1.schema.json"
PRECHECK_SCHEMA = ROOT / "die.division001.worth-making-precheck.v1.schema.json"
WM_VALIDATOR_PATH = ROOT / "validate_worth_making.py"
CHALLENGE_IDS = {
    "evidence_weakness_contradiction",
    "score_inflation_double_counting",
    "portfolio_overlap_cannibalization",
    "strategic_opportunity_cost",
    "product_expression_fit",
    "hypotheses_remaining",
}

class ReviewError(RuntimeError):
    pass


def canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ReviewError("E_TIME_TZ")
    return parsed.astimezone(dt.timezone.utc)


def _schema_errors(payload: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [e.message for e in errors]


def _load_wm_validator():
    spec = importlib.util.spec_from_file_location("oe004_wm_validator_for_exec", WM_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise ReviewError("E_WM_VALIDATOR_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(review: dict[str, Any], *, division_artifact: dict[str, Any] | None = None, precheck: dict[str, Any] | None = None) -> list[str]:
    errors = ["E_SCHEMA:" + x for x in _schema_errors(review, SCHEMA_PATH)]
    if errors:
        return errors
    rows = review["challenges"]
    ids = [row["challenge_id"] for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != CHALLENGE_IDS:
        errors.append("E_CHALLENGES:exact_six_required")
    assessments = [row["assessment"] for row in rows]
    outcome = review["outcome"]
    if outcome == "NO_VETO":
        if any(x in {"MATERIAL_CONCERN", "UNKNOWN"} for x in assessments):
            errors.append("E_OUTCOME:NO_VETO_with_material_or_unknown")
    elif outcome == "REVISE":
        if not any(x in {"CONCERN", "MATERIAL_CONCERN"} for x in assessments):
            errors.append("E_OUTCOME:REVISE_requires_concern")
        if not review["required_actions"]:
            errors.append("E_OUTCOME:REVISE_requires_actions")
    elif outcome == "VETO_PENDING_EVIDENCE":
        if "UNKNOWN" not in assessments:
            errors.append("E_OUTCOME:VETO_PENDING_EVIDENCE_requires_UNKNOWN")
        if not review["required_actions"]:
            errors.append("E_OUTCOME:VETO_PENDING_EVIDENCE_requires_actions")
    elif outcome == "ESCALATE_FOUNDER":
        if not review.get("escalation_reason"):
            errors.append("E_OUTCOME:ESCALATE_requires_reason")
    if outcome != "ESCALATE_FOUNDER" and review.get("escalation_reason") is not None:
        errors.append("E_OUTCOME:escalation_reason_only_for_escalation")
    if parse_time(review["reviewed_at"]) >= parse_time(review["expires_at"]):
        errors.append("E_TIME:review_expiry")

    if precheck is not None:
        perrors = _schema_errors(precheck, PRECHECK_SCHEMA)
        if perrors:
            errors.append("E_PRECHECK_SCHEMA:" + perrors[0])
        else:
            if precheck["status"] != "PASS" or precheck["hard_veto"] != "CLEAR":
                errors.append("E_PRECHECK:not_PASS")
            if review["precheck"]["precheck_id"] != precheck["precheck_id"]:
                errors.append("E_PRECHECK:id_mismatch")
            if review["precheck"]["sha256"] != canonical_sha(precheck):
                errors.append("E_PRECHECK:hash_mismatch")

    if division_artifact is not None:
        if _schema_errors(division_artifact, WM_SCHEMA):
            errors.append("E_DIVISION_ARTIFACT:schema")
        else:
            wm_validator = _load_wm_validator()
            werrors = wm_validator.validate(division_artifact, precheck=precheck)
            if werrors:
                errors.append("E_DIVISION_ARTIFACT:invalid:" + werrors[0])
            ref = review["division_artifact"]
            if ref["artifact_id"] != division_artifact["artifact_id"]:
                errors.append("E_DIVISION_ARTIFACT:id_mismatch")
            if ref["sha256"] != canonical_sha(division_artifact):
                errors.append("E_DIVISION_ARTIFACT:hash_mismatch")
            if ref["author_principal_id"] != division_artifact["principal"]["principal_id"]:
                errors.append("E_DIVISION_ARTIFACT:principal_mismatch")
            if ref["recommendation"] != division_artifact["recommendation"]:
                errors.append("E_DIVISION_ARTIFACT:recommendation_mismatch")
            if ref["total_score"] != division_artifact["total_score"]:
                errors.append("E_DIVISION_ARTIFACT:total_score_mismatch")
            if ref["confidence"] != division_artifact["confidence"]:
                errors.append("E_DIVISION_ARTIFACT:confidence_mismatch")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("review")
    ap.add_argument("--division-artifact")
    ap.add_argument("--precheck")
    args = ap.parse_args()
    try:
        review = json.loads(Path(args.review).read_text(encoding="utf-8"))
        division = json.loads(Path(args.division_artifact).read_text(encoding="utf-8")) if args.division_artifact else None
        precheck = json.loads(Path(args.precheck).read_text(encoding="utf-8")) if args.precheck else None
        errors = validate(review, division_artifact=division, precheck=precheck)
        print(json.dumps({"schema": "die.executive.worth-making-review-validation.v1", "status": "PASS" if not errors else "FAIL", "review_sha256": canonical_sha(review), "errors": errors}, indent=2))
        return 0 if not errors else 2
    except (OSError, json.JSONDecodeError, ReviewError) as exc:
        print(json.dumps({"schema": "die.executive.worth-making-review-validation.v1", "status": "FAIL", "errors": [str(exc)]}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())