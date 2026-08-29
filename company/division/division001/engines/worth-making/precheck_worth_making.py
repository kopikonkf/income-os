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
DIVISION = ROOT.parent
LONGTAIL_SCHEMA = DIVISION / "longtail" / "die.division001.longtail-candidate.v1.schema.json"
DEMAND_DIR = DIVISION / "demand-score"
DEMAND_SCHEMA = DEMAND_DIR / "die.division001.demand-score.v1.schema.json"
DEMAND_MODEL = DEMAND_DIR / "DEMAND_SCORE_MODEL_V1.contract.json"
DEMAND_VALIDATOR = DEMAND_DIR / "validate_demand_score.py"
INPUT_SCHEMA = ROOT / "die.division001.worth-making-precheck-input.v1.schema.json"
OUTPUT_SCHEMA = ROOT / "die.division001.worth-making-precheck.v1.schema.json"
REQUIRED_COMPONENTS = {"external_demand", "supply_competition", "commercial_intent"}
HARD_GATE_NAMES = ("rights_ip", "safety_deception", "platform_expression_eligibility", "production_tool_rights")


class PrecheckError(RuntimeError):
    pass


def canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PrecheckError("E_TIME_TZ")
    return parsed.astimezone(dt.timezone.utc)


def _load_demand_validator():
    spec = importlib.util.spec_from_file_location("oe004_precheck_demand_validator", DEMAND_VALIDATOR)
    if spec is None or spec.loader is None:
        raise PrecheckError("E_DEMAND_VALIDATOR_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema_validate(payload: dict[str, Any], schema_path: Path, code: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        raise PrecheckError(code + ":" + errors[0].message)


def _gate_effective(name: str, gate: dict[str, Any], as_of: dt.datetime, blocking: list[str], unknown: list[str]) -> str:
    status = gate["status"]
    if status == "BLOCKED":
        blocking.append("HARD_GATE_" + name.upper())
        return "BLOCKED"
    if status == "UNKNOWN":
        unknown.append("HARD_GATE_" + name.upper() + "_UNKNOWN")
        return "UNKNOWN"
    if not gate.get("evidence_ref") or not gate.get("evidence_sha256") or not gate.get("observed_at") or not gate.get("expires_at"):
        unknown.append("HARD_GATE_" + name.upper() + "_EVIDENCE_MISSING")
        return "UNKNOWN"
    observed = parse_time(gate["observed_at"])
    expires = parse_time(gate["expires_at"])
    if observed > as_of:
        unknown.append("HARD_GATE_" + name.upper() + "_OBSERVED_IN_FUTURE")
        return "UNKNOWN"
    if as_of >= expires:
        unknown.append("HARD_GATE_" + name.upper() + "_STALE")
        return "UNKNOWN"
    return "CLEAR"


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    _schema_validate(payload, INPUT_SCHEMA, "E_PRECHECK_INPUT_SCHEMA")
    candidate = payload["candidate"]
    score = payload["demand_score"]
    _schema_validate(candidate, LONGTAIL_SCHEMA, "E_CANDIDATE_SCHEMA")
    _schema_validate(score, DEMAND_SCHEMA, "E_DEMAND_SCORE_SCHEMA")
    demand_validator = _load_demand_validator()
    demand_schema = json.loads(DEMAND_SCHEMA.read_text(encoding="utf-8"))
    demand_model = json.loads(DEMAND_MODEL.read_text(encoding="utf-8"))
    demand_errors = demand_validator.validate(score, demand_schema, demand_model)
    if demand_errors:
        raise PrecheckError("E_DEMAND_SCORE_SEMANTIC:" + demand_errors[0])
    as_of = parse_time(payload["evaluated_at"])

    blocking: list[str] = []
    unknown: list[str] = []
    gate_results: dict[str, str] = {}

    if score["subject"]["id"] != candidate["phrase"] or score["subject"].get("parent_seed_id") != candidate["parent_seed"]["seed_id"] or score["subject"].get("parent_candidate_id") != candidate["candidate_id"]:
        raise PrecheckError("E_SCORE_CANDIDATE_LINEAGE")

    longtail = payload["longtail_guard"]
    candidate_sha = canonical_sha(candidate)
    if longtail["candidate_id"] != candidate["candidate_id"] or longtail["candidate_sha256"] != candidate_sha:
        raise PrecheckError("E_LONGTAIL_GUARD_CANDIDATE_BINDING")
    longtail_status = longtail["status"]
    if longtail_status == "REJECTED":
        gate_results["longtail_guard"] = "BLOCKED"
        blocking.append("LONGTAIL_GUARD_REJECTED")
    elif longtail_status == "REVIEW":
        gate_results["longtail_guard"] = "UNKNOWN"
        unknown.append("LONGTAIL_GUARD_REVIEW")
    else:
        gate_results["longtail_guard"] = "CLEAR"

    if score["score_status"] == "HARD_VETO" or score["hard_veto"]["status"] == "BLOCKED":
        gate_results["demand_score"] = "BLOCKED"
        blocking.append("DEMAND_SCORE_HARD_VETO")
    elif score["score_status"] != "COMPLETE" or score["final_score"] is None or score["hard_veto"]["status"] != "CLEAR":
        gate_results["demand_score"] = "UNKNOWN"
        unknown.append("DEMAND_SCORE_NOT_COMPLETE")
    elif as_of >= parse_time(score["expires_at"]):
        gate_results["demand_score"] = "UNKNOWN"
        unknown.append("DEMAND_SCORE_STALE")
    else:
        by_id = {row["component_id"]: row for row in score["components"]}
        missing = sorted(REQUIRED_COMPONENTS - set(by_id))
        if missing:
            gate_results["demand_score"] = "UNKNOWN"
            unknown.append("MANDATORY_COMPONENT_MISSING:" + ",".join(missing))
        else:
            component_failures = []
            for cid in sorted(REQUIRED_COMPONENTS):
                row = by_id[cid]
                if row["state"] != "KNOWN" or not row["evidence_refs"]:
                    component_failures.append(cid)
                    continue
                if not any(ref["evidence_kind"] == "OPPORTUNITY_SIGNAL" and ref["freshness_state"] == "FRESH" for ref in row["evidence_refs"]):
                    component_failures.append(cid)
            if component_failures:
                gate_results["demand_score"] = "UNKNOWN"
                unknown.append("MANDATORY_EVIDENCE_NOT_FRESH:" + ",".join(component_failures))
            else:
                gate_results["demand_score"] = "CLEAR"

    for name in HARD_GATE_NAMES:
        gate_results[name] = _gate_effective(name, payload["hard_gates"][name], as_of, blocking, unknown)

    spend = payload["spend"]
    if spend["authorization_status"] == "DENIED":
        gate_results["spend"] = "BLOCKED"
        blocking.append("SPEND_DENIED")
    elif spend["estimated_cost_usd"] > 0 and spend["authorization_status"] != "AUTHORIZED":
        gate_results["spend"] = "UNKNOWN"
        unknown.append("SPEND_AUTH_REQUIRED")
    elif spend["authorization_status"] == "AUTHORIZED" and (not spend.get("authorization_ref") or not spend.get("authorization_sha256")):
        gate_results["spend"] = "UNKNOWN"
        unknown.append("SPEND_AUTH_RECEIPT_MISSING")
    elif spend["estimated_cost_usd"] == 0 and spend["authorization_status"] == "MISSING":
        gate_results["spend"] = "UNKNOWN"
        unknown.append("SPEND_STATUS_AMBIGUOUS")
    else:
        gate_results["spend"] = "CLEAR"

    gate_results["buyer_hypothesis_seed"] = "CLEAR"
    buyer_seed_sha = canonical_sha(payload["buyer_hypothesis_seed"])

    if blocking:
        status, veto = "BLOCKED", "BLOCKED"
    elif unknown:
        status, veto = "WAITING_EVIDENCE", "UNKNOWN"
    else:
        status, veto = "PASS", "CLEAR"

    result = {
        "schema_version": "die.division001.worth-making-precheck.v1",
        "precheck_id": payload["precheck_id"],
        "evaluated_at": payload["evaluated_at"],
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate_sha,
        "demand_score_id": score["score_id"],
        "demand_score_sha256": canonical_sha(score),
        "status": status,
        "hard_veto": veto,
        "gate_results": gate_results,
        "blocking_codes": sorted(set(blocking)),
        "unknown_codes": sorted(set(unknown)),
        "buyer_hypothesis_seed_sha256": buyer_seed_sha,
        "worth_making_semantics_authored": False,
    }
    _schema_validate(result, OUTPUT_SCHEMA, "E_PRECHECK_OUTPUT_SCHEMA")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--output")
    args = ap.parse_args()
    try:
        result = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
        text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8", newline="\n")
        else:
            print(text, end="")
        return 0
    except (OSError, json.JSONDecodeError, PrecheckError) as exc:
        print(json.dumps({"schema": "die.division001.worth-making-precheck-run.v1", "status": "FAIL", "error": str(exc)}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())