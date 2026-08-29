#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "die.division001.worth-making.v1.schema.json"
MODEL_PATH = ROOT / "WORTH_MAKING_FACTOR_MODEL_V1.json"
PRECHECK_SCHEMA = ROOT / "die.division001.worth-making-precheck.v1.schema.json"


class WorthMakingError(RuntimeError):
    pass


def canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _schema_errors(payload: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [e.message for e in errors]


def validate(payload: dict[str, Any], *, precheck: dict[str, Any] | None = None) -> list[str]:
    errors = ["E_SCHEMA:" + x for x in _schema_errors(payload, SCHEMA_PATH)]
    if errors:
        return errors
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    expected = {row["factor_id"]: row["weight"] for row in model["factors"]}
    rows = payload["factors"]
    seen = [row["factor_id"] for row in rows]
    if len(seen) != len(set(seen)) or set(seen) != set(expected):
        errors.append("E_FACTORS:exact_factor_set_required")
    for row in rows:
        fid = row["factor_id"]
        if fid in expected and row["weight"] != expected[fid]:
            errors.append("E_FACTORS:weight_mismatch:" + fid)
        if row["score"] is None:
            if row["evidence_label"] != "UNKNOWN":
                errors.append("E_FACTORS:null_score_requires_UNKNOWN:" + fid)
        else:
            if row["evidence_label"] == "UNKNOWN":
                errors.append("E_FACTORS:numeric_score_forbids_UNKNOWN:" + fid)
            if not row["evidence_refs"]:
                errors.append("E_FACTORS:numeric_score_requires_evidence:" + fid)

    unknown = [row for row in rows if row["score"] is None]
    if unknown:
        if payload["total_score"] is not None:
            errors.append("E_TOTAL:unknown_factor_requires_null_total")
        if payload["recommendation"] == "VALIDATE":
            errors.append("E_RECOMMENDATION:VALIDATE_requires_complete_factors")
        if payload["confidence"] == "HIGH":
            errors.append("E_CONFIDENCE:HIGH_forbidden_with_unknown_factor")
    else:
        expected_total = sum(float(row["score"]) * expected[row["factor_id"]] for row in rows) / 100.0
        if payload["total_score"] is None or abs(float(payload["total_score"]) - expected_total) > 1e-6:
            errors.append("E_TOTAL:weighted_total_mismatch")
        total = expected_total
        if payload["recommendation"] == "VALIDATE" and total < model["thresholds"]["VALIDATE_MIN"]:
            errors.append("E_RECOMMENDATION:VALIDATE_below_threshold")
        if payload["recommendation"] == "RESEARCH" and total < model["thresholds"]["RESEARCH_MIN"]:
            errors.append("E_RECOMMENDATION:RESEARCH_below_threshold")
        if total < model["thresholds"]["RESEARCH_MIN"] and payload["recommendation"] != "DEFER":
            errors.append("E_RECOMMENDATION:below_60_requires_DEFER")

    signal_ids = [x["signal_id"] for x in payload["upstream"]["source_signals"]]
    if len(signal_ids) != len(set(signal_ids)):
        errors.append("E_UPSTREAM:duplicate_signal_id")

    if precheck is not None:
        perrors = _schema_errors(precheck, PRECHECK_SCHEMA)
        if perrors:
            errors.append("E_PRECHECK_SCHEMA:" + perrors[0])
        else:
            if precheck["status"] != "PASS" or precheck["hard_veto"] != "CLEAR":
                errors.append("E_PRECHECK:not_PASS")
            if payload["upstream"]["precheck_id"] != precheck["precheck_id"]:
                errors.append("E_PRECHECK:id_mismatch")
            if payload["upstream"]["precheck_sha256"] != canonical_sha(precheck):
                errors.append("E_PRECHECK:hash_mismatch")
            if payload["candidate"]["candidate_id"] != precheck["candidate_id"]:
                errors.append("E_PRECHECK:candidate_mismatch")
            if payload["upstream"]["longtail_candidate_sha256"] != precheck["candidate_sha256"]:
                errors.append("E_PRECHECK:candidate_hash_mismatch")
            if payload["upstream"]["demand_score_id"] != precheck["demand_score_id"]:
                errors.append("E_PRECHECK:score_id_mismatch")
            if payload["upstream"]["demand_score_sha256"] != precheck["demand_score_sha256"]:
                errors.append("E_PRECHECK:score_hash_mismatch")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--precheck")
    args = ap.parse_args()
    try:
        payload = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
        precheck = json.loads(Path(args.precheck).read_text(encoding="utf-8")) if args.precheck else None
        errors = validate(payload, precheck=precheck)
        print(json.dumps({"schema": "die.division001.worth-making-validation.v1", "status": "PASS" if not errors else "FAIL", "artifact_sha256": canonical_sha(payload), "errors": errors}, indent=2))
        return 0 if not errors else 2
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "die.division001.worth-making-validation.v1", "status": "FAIL", "errors": [str(exc)]}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())