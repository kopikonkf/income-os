#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "die.division001.demand-score.v1.schema.json"
MODEL_PATH = ROOT / "DEMAND_SCORE_MODEL_V1.contract.json"


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(payload: dict[str, Any], schema: dict[str, Any], model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "$"
        errors.append(f"E_SCHEMA:{path}:{err.message}")
    if errors:
        return errors

    model_sha = file_sha256(MODEL_PATH)
    if payload["model"]["contract_sha256"] != model_sha:
        errors.append("E_MODEL_CONTRACT_HASH:mismatch")

    model_components = {row["component_id"]: row for row in model["components"]}
    components = payload["components"]
    ids = [row["component_id"] for row in components]
    if len(ids) != len(set(ids)):
        errors.append("E_COMPONENT_SET:duplicate_component_id")
    if set(ids) != set(model_components):
        errors.append("E_COMPONENT_SET:not_exact_model_component_set")
        return errors

    evaluated = parse_time(payload["evaluated_at"])
    output_expires = parse_time(payload["expires_at"])
    if output_expires <= evaluated:
        errors.append("E_OUTPUT_EXPIRY:not_after_evaluated_at")

    evidence_owner: dict[str, str] = {}
    earliest_known_signal_expiry: dt.datetime | None = None
    known_count = 0
    applicable_count = 0
    required_ids = {cid for cid, row in model_components.items() if row["required_for_complete"]}
    required_known = 0

    for comp in components:
        cid = comp["component_id"]
        state = comp["state"]
        refs = comp["evidence_refs"]
        score = comp["normalized_score"]
        confidence = comp["confidence"]
        transform_id = comp["normalization_transform_id"]
        transform_ver = comp["normalization_transform_version"]
        policy = model_components[cid]

        if state != "NOT_APPLICABLE":
            applicable_count += 1
        if state == "KNOWN":
            known_count += 1
            if cid in required_ids:
                required_known += 1
            if score is None:
                errors.append(f"E_COMPONENT_STATE:{cid}:KNOWN_requires_score")
            if not refs:
                errors.append(f"E_COMPONENT_STATE:{cid}:KNOWN_requires_evidence")
            if confidence == "NONE":
                errors.append(f"E_COMPONENT_STATE:{cid}:KNOWN_requires_confidence")
            if not transform_id or not transform_ver:
                errors.append(f"E_COMPONENT_STATE:{cid}:KNOWN_requires_transform")
        elif state == "UNKNOWN":
            if score is not None or refs or confidence != "NONE" or transform_id is not None or transform_ver is not None:
                errors.append(f"E_COMPONENT_STATE:{cid}:UNKNOWN_must_be_empty")
        elif state == "STALE":
            if score is not None or not refs or confidence != "NONE":
                errors.append(f"E_COMPONENT_STATE:{cid}:STALE_contract")
        elif state == "REJECTED":
            if score is not None or not refs or confidence != "NONE":
                errors.append(f"E_COMPONENT_STATE:{cid}:REJECTED_contract")
        elif state == "NOT_APPLICABLE":
            if score is not None or confidence != "NONE" or transform_id is not None or transform_ver is not None:
                errors.append(f"E_COMPONENT_STATE:{cid}:NOT_APPLICABLE_contract")

        for ref in refs:
            kind = ref["evidence_kind"]
            if kind == "LEGACY_HEURISTIC":
                errors.append(f"E_LEGACY_HEURISTIC:{cid}:not_production_evidence")
                continue
            if kind not in policy["allowed_evidence_kinds"]:
                errors.append(f"E_EVIDENCE_KIND:{cid}:{kind}")
            owner = evidence_owner.get(ref["evidence_id"])
            if owner is not None and owner != cid:
                errors.append(f"E_EVIDENCE_DOUBLE_COUNT:{ref['evidence_id']}:{owner}:{cid}")
            else:
                evidence_owner[ref["evidence_id"]] = cid

            if kind == "OPPORTUNITY_SIGNAL":
                if ref["signal_class"] not in policy["allowed_signal_classes"]:
                    errors.append(f"E_SIGNAL_CLASS:{cid}:{ref['signal_class']}")
                if ref["signal_type"] is None or ref["observed_at"] is None or ref["expires_at"] is None:
                    errors.append(f"E_SIGNAL_PROVENANCE:{cid}:missing_signal_fields")
                    continue
                expires = parse_time(ref["expires_at"])
                is_stale = evaluated >= expires
                if state == "KNOWN":
                    if ref["freshness_state"] != "FRESH" or is_stale:
                        errors.append(f"E_FRESHNESS:{cid}:KNOWN_requires_fresh_signal")
                    if earliest_known_signal_expiry is None or expires < earliest_known_signal_expiry:
                        earliest_known_signal_expiry = expires
                if state == "STALE":
                    if ref["freshness_state"] != "STALE" or not is_stale:
                        errors.append(f"E_FRESHNESS:{cid}:STALE_requires_expired_signal")
            else:
                if ref["signal_class"] is not None or ref["signal_type"] is not None:
                    errors.append(f"E_EVIDENCE_PROVENANCE:{cid}:{kind}_must_not_claim_signal")
                if state == "KNOWN" and ref["freshness_state"] not in {"VERSION_VALID", "FRESH"}:
                    errors.append(f"E_FRESHNESS:{cid}:non_signal_known_not_valid")

    expected_cov = 0.0 if applicable_count == 0 else known_count / applicable_count
    expected_req = 0.0 if not required_ids else required_known / len(required_ids)
    if abs(payload["evidence_coverage_ratio"] - expected_cov) > 1e-6:
        errors.append("E_COVERAGE:evidence_coverage_ratio_mismatch")
    if abs(payload["required_coverage_ratio"] - expected_req) > 1e-6:
        errors.append("E_COVERAGE:required_coverage_ratio_mismatch")

    status = payload["score_status"]
    final_score = payload["final_score"]
    hard_veto = payload["hard_veto"]["status"]
    if status == "COMPLETE":
        if required_known != len(required_ids) or final_score is None or hard_veto != "CLEAR":
            errors.append("E_SCORE_STATUS:COMPLETE_contract")
    elif status == "PARTIAL":
        if not (0 < required_known < len(required_ids)) or final_score is not None or hard_veto == "BLOCKED":
            errors.append("E_SCORE_STATUS:PARTIAL_contract")
    elif status == "INSUFFICIENT_EVIDENCE":
        if required_known != 0 or final_score is not None or hard_veto == "BLOCKED":
            errors.append("E_SCORE_STATUS:INSUFFICIENT_contract")
    elif status == "HARD_VETO":
        if hard_veto != "BLOCKED" or final_score is not None:
            errors.append("E_SCORE_STATUS:HARD_VETO_contract")

    if status != "COMPLETE" and payload["confidence"] != "NONE":
        errors.append("E_CONFIDENCE:non_complete_must_be_NONE_v1")
    if status == "COMPLETE" and payload["confidence"] == "NONE":
        errors.append("E_CONFIDENCE:complete_requires_confidence")

    if earliest_known_signal_expiry is not None and output_expires > earliest_known_signal_expiry:
        errors.append("E_OUTPUT_EXPIRY:exceeds_earliest_known_signal_expiry")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("score")
    ap.add_argument("--schema", default=str(SCHEMA_PATH))
    ap.add_argument("--model", default=str(MODEL_PATH))
    args = ap.parse_args()
    payload = json.loads(Path(args.score).read_text(encoding="utf-8"))
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    errors = validate(payload, schema, model)
    print(json.dumps({"schema":"die.division001.demand-score-validation.v1","score_id":payload.get("score_id"),"status":"PASS" if not errors else "FAIL","errors":errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
