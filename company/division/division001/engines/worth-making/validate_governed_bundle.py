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
RESULT_SCHEMA = ROOT / "die.division001.worth-making-governed-result.v1.schema.json"
PRECHECK_MODULE = ROOT / "precheck_worth_making.py"
WM_MODULE = ROOT / "validate_worth_making.py"
EXEC_MODULE = ROOT / "validate_executive_review.py"
ATTEMPT_MODULE = ROOT / "validate_attempt_lineage.py"


class GovernedBundleError(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GovernedBundleError("E_MODULE_LOAD:" + path.name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRE = _load("oe004e_pre", PRECHECK_MODULE)
WM = _load("oe004e_wm", WM_MODULE)
EXEC = _load("oe004e_exec", EXEC_MODULE)
ATTEMPT = _load("oe004e_attempt", ATTEMPT_MODULE)


def canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise GovernedBundleError("E_TIME_TZ")
    return parsed.astimezone(dt.timezone.utc)


def _result(bundle_id: str, validated_at: str, repository_sha: str, decision: str, errors: list[str], precheck: dict | None, division: dict | None, review: dict | None, attempt: dict | None) -> dict[str, Any]:
    payload = {
        "schema_version": "die.division001.worth-making-governed-result.v1",
        "bundle_id": bundle_id,
        "validated_at": validated_at,
        "repository_sha": repository_sha,
        "status": "PASS" if not errors else "FAIL",
        "decision": decision if not errors else "INVALID",
        "precheck_sha256": canonical_sha(precheck) if precheck is not None else None,
        "division_artifact_sha256": canonical_sha(division) if division is not None else None,
        "executive_review_sha256": canonical_sha(review) if review is not None else None,
        "attempt_sha256": canonical_sha(attempt) if attempt is not None else None,
        "errors": sorted(set(errors)),
        "production_authority_granted": False,
    }
    schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    return payload


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    required = {"bundle_id", "validated_at", "repository_sha", "precheck_input", "precheck", "division_artifact", "executive_review", "attempt"}
    missing = sorted(required - set(bundle))
    bundle_id = str(bundle.get("bundle_id", "WMBUNDLE-INVALID-00000001"))
    validated_at = str(bundle.get("validated_at", "1970-01-01T00:00:00Z"))
    repository_sha = str(bundle.get("repository_sha", "0" * 40))
    if missing:
        return _result(bundle_id, validated_at, repository_sha, "INVALID", ["E_BUNDLE_MISSING:" + ",".join(missing)], bundle.get("precheck"), bundle.get("division_artifact"), bundle.get("executive_review"), bundle.get("attempt"))

    pre_input = bundle["precheck_input"]
    precheck = bundle["precheck"]
    division = bundle["division_artifact"]
    review = bundle["executive_review"]
    attempt = bundle["attempt"]
    previous = bundle.get("previous_attempt")
    errors: list[str] = []

    try:
        now = parse_time(validated_at)
    except GovernedBundleError as exc:
        return _result(bundle_id, validated_at, repository_sha, "INVALID", [str(exc)], precheck, division, review, attempt)

    # Replay deterministic precheck from its full source input and require byte-semantic identity.
    try:
        replay = PRE.evaluate(pre_input)
        if replay != precheck:
            errors.append("E_PRECHECK_REPLAY:mismatch")
    except Exception as exc:
        errors.append("E_PRECHECK_REPLAY:" + str(exc))

    # Current freshness, not merely freshness at original precheck time.
    try:
        score = pre_input["demand_score"]
        if now >= parse_time(score["expires_at"]):
            errors.append("E_FRESHNESS:demand_score_stale")
        if parse_time(score["evaluated_at"]) > now:
            errors.append("E_FRESHNESS:demand_score_from_future")
        for name, gate in pre_input["hard_gates"].items():
            if gate["status"] == "CLEAR":
                if not gate.get("expires_at") or now >= parse_time(gate["expires_at"]):
                    errors.append("E_FRESHNESS:hard_gate_stale:" + name)
        if parse_time(pre_input["evaluated_at"]) > now:
            errors.append("E_FRESHNESS:precheck_from_future")
    except Exception as exc:
        errors.append("E_FRESHNESS:precheck_input:" + str(exc))

    # Revalidate semantic author artifact and its current snapshot/repository provenance.
    try:
        werrors = WM.validate(division, precheck=precheck)
        errors.extend("E_DIVISION:" + x for x in werrors)
        if division["snapshot"]["repository_sha"] != repository_sha:
            errors.append("E_REPOSITORY:division_sha_mismatch")
        if parse_time(division["snapshot"]["as_of"]) > now:
            errors.append("E_FRESHNESS:division_from_future")
        if now >= parse_time(division["snapshot"]["expires_at"]):
            errors.append("E_FRESHNESS:division_stale")
    except Exception as exc:
        errors.append("E_DIVISION:" + str(exc))

    # Revalidate Executive review, exact Division hash, principal and current freshness.
    try:
        eerrors = EXEC.validate(review, division_artifact=division, precheck=precheck)
        errors.extend("E_EXECUTIVE:" + x for x in eerrors)
        if review["snapshot"]["repository_sha"] != repository_sha:
            errors.append("E_REPOSITORY:executive_sha_mismatch")
        if parse_time(review["reviewed_at"]) > now:
            errors.append("E_FRESHNESS:review_from_future")
        if now >= parse_time(review["expires_at"]):
            errors.append("E_FRESHNESS:review_stale")
    except Exception as exc:
        errors.append("E_EXECUTIVE:" + str(exc))

    # Immutable attempt lineage.
    try:
        aerrors = ATTEMPT.validate(attempt, precheck=precheck, division=division, review=review, previous=previous)
        errors.extend("E_ATTEMPT:" + x for x in aerrors)
        if parse_time(attempt["created_at"]) < parse_time(review["reviewed_at"]):
            errors.append("E_ATTEMPT:created_before_review")
        if parse_time(attempt["created_at"]) > now:
            errors.append("E_ATTEMPT:created_in_future")
    except Exception as exc:
        errors.append("E_ATTEMPT:" + str(exc))

    if errors:
        return _result(bundle_id, validated_at, repository_sha, "INVALID", errors, precheck, division, review, attempt)

    outcome = review["outcome"]
    if outcome == "REVISE":
        decision = "RETURN_TO_DIVISION"
    elif outcome == "VETO_PENDING_EVIDENCE":
        decision = "WAITING_EVIDENCE"
    elif outcome == "ESCALATE_FOUNDER":
        decision = "ESCALATE_FOUNDER"
    elif division["recommendation"] == "VALIDATE":
        decision = "PROMOTABLE_TO_BLUEPRINT"
    else:
        decision = "NOT_PROMOTABLE"

    return _result(bundle_id, validated_at, repository_sha, decision, [], precheck, division, review, attempt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    args = ap.parse_args()
    try:
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        result = validate_bundle(bundle)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 2
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema_version": "die.division001.worth-making-governed-result.v1", "status": "FAIL", "decision": "INVALID", "errors": [str(exc)]}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())