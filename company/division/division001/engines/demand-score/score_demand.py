#!/usr/bin/env python3
"""Deterministic Demand Score v1 scorer.

Consumes validated OE-001 Opportunity Signal receipts plus explicitly normalized
versioned deterministic/canon evidence. Missing required evidence never becomes
zero; it yields no numeric final score.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent
DIVISION_ROOT = ROOT.parent
SIGNALS_ROOT = DIVISION_ROOT / "opportunity-signals"
MODEL_PATH = ROOT / "DEMAND_SCORE_MODEL_V1.contract.json"
INPUT_SCHEMA_PATH = ROOT / "die.division001.demand-score-input.v1.schema.json"
OUTPUT_SCHEMA_PATH = ROOT / "die.division001.demand-score.v1.schema.json"
OUTPUT_VALIDATOR_PATH = ROOT / "validate_demand_score.py"
SIGNAL_SCHEMA_PATH = SIGNALS_ROOT / "die.division001.opportunity-signals.v1.schema.json"
SIGNAL_VALIDATOR_PATH = SIGNALS_ROOT / "validate_signal_receipt.py"

SIGNAL_CLASS_COMPONENT = {
    "DEMAND": "external_demand",
    "SUPPLY": "supply_competition",
    "COMPETITION": "supply_competition",
    "COMMERCIAL_INTENT": "commercial_intent",
    "TREND": "trend_seasonality",
    "PLATFORM_FIT": "platform_fit",
}
CONF_RANK = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


class ScoreError(RuntimeError):
    pass


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ScoreError(f"cannot load module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ScoreError("timestamp must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


def _z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _transform_signal(receipt: dict[str, Any]) -> tuple[float | None, str | None]:
    signal_type = receipt["signal_type"]
    value = receipt["value"]
    kind = value["kind"]
    numeric = value.get("numeric_value")
    boolean = value.get("boolean_value")

    if signal_type in {
        "SEARCH_INTEREST_INDEX", "TREND_INDEX", "SEASONALITY_INDEX"
    } and kind == "INDEX":
        return _clamp01(float(numeric) / 100.0), "index_0_100"

    if signal_type in {"SEARCH_INTEREST_DELTA", "TREND_DELTA"} and kind == "DELTA":
        return _clamp01((float(numeric) + 100.0) / 200.0), "delta_minus100_plus100"

    if signal_type in {
        "AUTOCOMPLETE_PRESENCE", "RELATED_QUERY_PRESENCE", "BUYER_TERM_PRESENCE",
        "LICENSE_SURFACE_PRESENCE", "CONTENT_TYPE_SURFACE_PRESENCE",
        "FILTER_OPTION_PRESENCE", "AI_LABEL_SURFACE_PRESENCE",
    } and kind == "BOOLEAN":
        return (1.0 if boolean else 0.0), "boolean_presence"

    if signal_type == "AUTOCOMPLETE_RANK" and kind == "RANK":
        rank = int(numeric)
        return (_clamp01(1.0 - (rank - 1) / 9.0) if rank <= 10 else 0.0), "rank_reciprocal_10"

    if signal_type in {"VISIBLE_DOWNLOAD_COUNT", "VISIBLE_POPULARITY_COUNT"} and kind == "COUNT":
        score = math.log10(1.0 + float(numeric)) / math.log10(10001.0)
        return _clamp01(score), "count_demand_log10k"

    if signal_type in {"SEARCH_RESULTS_COUNT", "VISIBLE_CONTRIBUTOR_COUNT", "EXACT_PHRASE_RESULT_COUNT"} and kind == "COUNT":
        saturation = math.log10(1.0 + float(numeric)) / math.log10(100001.0)
        return _clamp01(1.0 - min(1.0, saturation)), "count_competition_log100k"

    if signal_type in {"SPONSORED_RESULT_SHARE", "TOP_RESULT_CONCENTRATION_RATIO"} and kind == "RATIO":
        return _clamp01(1.0 - float(numeric)), "competition_ratio_invert"

    # ASSET_TYPE_MIX_RATIO and VISIBLE_PRICE_POINT are deliberately unsupported
    # until their semantic direction/units are explicit in a later model version.
    return None, None


def _evidence_ref_signal(receipt: dict[str, Any], freshness: str) -> dict[str, Any]:
    return {
        "evidence_kind": "OPPORTUNITY_SIGNAL",
        "evidence_id": receipt["signal_id"],
        "evidence_sha256": _canonical_sha(receipt),
        "signal_class": receipt["signal_class"],
        "signal_type": receipt["signal_type"],
        "observed_at": receipt["observed_at"],
        "expires_at": receipt["expires_at"],
        "freshness_state": freshness,
        "source_ref": receipt["source_ref"],
    }


def _evidence_ref_normalized(item: dict[str, Any], freshness: str) -> dict[str, Any]:
    return {
        "evidence_kind": item["evidence_kind"],
        "evidence_id": item["evidence_id"],
        "evidence_sha256": item["evidence_sha256"],
        "signal_class": None,
        "signal_type": None,
        "observed_at": None,
        "expires_at": item["valid_until"],
        "freshness_state": freshness,
        "source_ref": item["source_ref"],
    }


def _component_confidence(values: list[str]) -> str:
    if not values:
        return "NONE"
    return min(values, key=lambda x: CONF_RANK[x])


def _empty_component(cid: str, state: str = "UNKNOWN", refs: list[dict[str, Any]] | None = None, notes: str | None = None) -> dict[str, Any]:
    return {
        "component_id": cid,
        "state": state,
        "normalized_score": None,
        "confidence": "NONE",
        "evidence_refs": refs or [],
        "normalization_transform_id": None,
        "normalization_transform_version": None,
        "notes": notes,
    }


def _validate_input(payload: dict[str, Any]) -> None:
    schema = json.loads(INPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        details = []
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or "$"
            details.append(f"{path}:{err.message}")
        raise ScoreError("E_INPUT_SCHEMA:" + " | ".join(details))


def score(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_input(payload)
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    model_by = {row["component_id"]: row for row in model["components"]}
    signal_schema = json.loads(SIGNAL_SCHEMA_PATH.read_text(encoding="utf-8"))
    signal_validator = _load_module("oe001_signal_validator_for_score", SIGNAL_VALIDATOR_PATH)
    evaluated = _parse_time(payload["evaluated_at"])

    # De-duplicate exact evidence and fail on conflicting identities.
    identity_hash: dict[str, str] = {}
    evidence_items: list[dict[str, Any]] = []
    for item in payload["evidence"]:
        if item["evidence_kind"] == "OPPORTUNITY_SIGNAL":
            receipt = item["receipt"]
            identity = str(receipt.get("signal_id", "<missing>"))
            digest = _canonical_sha(receipt)
        else:
            identity = item["evidence_id"]
            digest = _canonical_sha(item)
        prior = identity_hash.get(identity)
        if prior is not None:
            if prior == digest:
                continue
            raise ScoreError(f"E_INPUT_EVIDENCE_CONFLICT:{identity}")
        identity_hash[identity] = digest
        evidence_items.append(item)

    market: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected_by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stale_by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in evidence_items:
        if item["evidence_kind"] == "OPPORTUNITY_SIGNAL":
            receipt = item["receipt"]
            signal_errors = signal_validator.validate(receipt, signal_schema, as_of=evaluated)
            component_id = SIGNAL_CLASS_COMPONENT.get(receipt.get("signal_class"))
            if component_id is None:
                continue
            # Subject mismatch is rejected evidence, never silently scored.
            if receipt.get("subject", {}).get("kind") != payload["subject"]["kind"] or receipt.get("subject", {}).get("id") != payload["subject"]["id"]:
                rejected_by_component[component_id].append(_evidence_ref_signal(receipt, "REJECTED"))
                continue
            if signal_errors:
                # Distinguish pure staleness from other invalidity.
                if signal_errors == ["E_SIGNAL_STALE:expired"]:
                    stale_by_component[component_id].append(_evidence_ref_signal(receipt, "STALE"))
                else:
                    rejected_by_component[component_id].append(_evidence_ref_signal(receipt, "REJECTED"))
                continue
            transformed, transform_id = _transform_signal(receipt)
            if transformed is None or transform_id is None:
                rejected_by_component[component_id].append(_evidence_ref_signal(receipt, "REJECTED"))
                continue
            market[component_id].append({
                "score": transformed,
                "transform_id": transform_id,
                "source_id": receipt["source"]["source_id"],
                "confidence": receipt["confidence"],
                "ref": _evidence_ref_signal(receipt, "FRESH"),
                "expires": _parse_time(receipt["expires_at"]),
            })
            continue

        component_id = item["component_id"]
        policy = model_by[component_id]
        if item["evidence_kind"] not in policy["allowed_evidence_kinds"]:
            rejected_by_component[component_id].append(_evidence_ref_normalized(item, "REJECTED"))
            continue
        valid_until = item["valid_until"]
        if valid_until is None:
            # Pinned version evidence is explicitly version-valid by its hash.
            freshness = "VERSION_VALID"
            expires = None
        else:
            expires = _parse_time(valid_until)
            freshness = "STALE" if evaluated >= expires else "FRESH"
        if freshness == "STALE":
            stale_by_component[component_id].append(_evidence_ref_normalized(item, "STALE"))
            continue
        normalized[component_id].append({
            "score": float(item["normalized_value"]),
            "confidence": item["confidence"],
            "ref": _evidence_ref_normalized(item, freshness),
            "expires": expires,
        })

    components: list[dict[str, Any]] = []
    component_expiries: list[dt.datetime] = []
    component_confidences: list[str] = []

    for policy in model["components"]:
        cid = policy["component_id"]
        accepted_market = market.get(cid, [])
        accepted_norm = normalized.get(cid, [])
        if accepted_market:
            # Avoid repeated same-source observations dominating a component:
            # median within each source, then median across sources.
            source_scores: dict[str, list[float]] = defaultdict(list)
            for row in accepted_market:
                source_scores[row["source_id"]].append(row["score"])
            per_source = [statistics.median(vals) for _, vals in sorted(source_scores.items())]
            value = float(statistics.median(per_source))
            refs = [row["ref"] for row in accepted_market]
            conf = _component_confidence([row["confidence"] for row in accepted_market])
            component_confidences.append(conf)
            for row in accepted_market:
                component_expiries.append(row["expires"])
            components.append({
                "component_id": cid,
                "state": "KNOWN",
                "normalized_score": round(value, 6),
                "confidence": conf,
                "evidence_refs": refs,
                "normalization_transform_id": "source-median-v1",
                "normalization_transform_version": "1.0.0",
                "notes": "Per-signal transforms are versioned in the model; aggregation is median within source then median across sources.",
            })
        elif accepted_norm:
            value = float(statistics.median([row["score"] for row in accepted_norm]))
            refs = [row["ref"] for row in accepted_norm]
            conf = _component_confidence([row["confidence"] for row in accepted_norm])
            component_confidences.append(conf)
            for row in accepted_norm:
                if row["expires"] is not None:
                    component_expiries.append(row["expires"])
            components.append({
                "component_id": cid,
                "state": "KNOWN",
                "normalized_score": round(value, 6),
                "confidence": conf,
                "evidence_refs": refs,
                "normalization_transform_id": "normalized-evidence-median-v1",
                "normalization_transform_version": "1.0.0",
                "notes": "Explicit pre-normalized deterministic/canon evidence; median aggregation.",
            })
        elif stale_by_component.get(cid):
            components.append(_empty_component(cid, "STALE", stale_by_component[cid], "Only stale evidence was available at evaluated_at."))
        elif rejected_by_component.get(cid):
            components.append(_empty_component(cid, "REJECTED", rejected_by_component[cid], "Evidence existed but failed policy/provenance/transform validation."))
        else:
            components.append(_empty_component(cid, "UNKNOWN", [], "No accepted evidence supplied."))

    by = {row["component_id"]: row for row in components}
    required = [row["component_id"] for row in model["components"] if row["required_for_complete"]]
    required_known = sum(1 for cid in required if by[cid]["state"] == "KNOWN")
    applicable = [row for row in components if row["state"] != "NOT_APPLICABLE"]
    known = [row for row in applicable if row["state"] == "KNOWN"]
    evidence_cov = len(known) / len(applicable) if applicable else 0.0
    required_cov = required_known / len(required) if required else 0.0

    hard_status = payload["hard_veto"]["status"]
    if hard_status == "BLOCKED":
        status = "HARD_VETO"
    elif required_known == 0:
        status = "INSUFFICIENT_EVIDENCE"
    elif required_known < len(required) or hard_status != "CLEAR":
        status = "PARTIAL"
    else:
        status = "COMPLETE"

    nonrisk_known = [row for row in known if row["component_id"] != "risk_penalty"]
    known_weight = sum(float(model_by[row["component_id"]]["weight"]) for row in nonrisk_known)
    known_weight_ratio = known_weight / float(model["weight_sum_nonrisk"]) if model["weight_sum_nonrisk"] else 0.0

    risk = by["risk_penalty"]
    if risk["state"] == "KNOWN":
        raw_penalty = float(risk["normalized_score"])
        deduction = raw_penalty * float(model["scoring_policy"]["risk_penalty_multiplier"])
        risk_adjustment = {"state": "APPLIED", "raw_penalty": round(raw_penalty, 6), "multiplier": 0.15, "applied_deduction": round(deduction, 6)}
    else:
        raw_penalty = None
        deduction = 0.0
        risk_adjustment = {"state": risk["state"], "raw_penalty": None, "multiplier": 0.15, "applied_deduction": 0.0}

    final_score: float | None = None
    confidence = "NONE"
    if status == "COMPLETE":
        if known_weight <= 0:
            raise ScoreError("E_INTERNAL:no_known_nonrisk_weight")
        weighted = sum(float(model_by[row["component_id"]]["weight"]) * float(row["normalized_score"]) for row in nonrisk_known)
        base_score = weighted / known_weight
        final_score = round(_clamp01(base_score - deduction), 6)
        if evidence_cov >= 0.80 and all(CONF_RANK[c] >= CONF_RANK["HIGH"] for c in component_confidences):
            confidence = "HIGH"
        elif evidence_cov >= 0.60 and all(CONF_RANK[c] >= CONF_RANK["MEDIUM"] for c in component_confidences):
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

    # Output validity never extends beyond the earliest known expiring evidence.
    if component_expiries:
        expires = min(component_expiries)
    else:
        expires = evaluated + dt.timedelta(seconds=60)
    if expires <= evaluated:
        # This should only happen if stale evidence leaked into KNOWN, which is a bug.
        raise ScoreError("E_INTERNAL:output_expiry_not_future")

    result = {
        "schema_version": "die.division001.demand-score.v1",
        "score_id": payload["score_id"],
        "subject": payload["subject"],
        "model": {
            "model_id": model["model_id"],
            "model_version": model["model_version"],
            "contract_sha256": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
        },
        "evaluated_at": _z(evaluated),
        "expires_at": _z(expires),
        "score_status": status,
        "final_score": final_score,
        "confidence": confidence,
        "evidence_coverage_ratio": round(evidence_cov, 6),
        "required_coverage_ratio": round(required_cov, 6),
        "known_weight_ratio": round(known_weight_ratio, 6),
        "risk_adjustment": risk_adjustment,
        "hard_veto": payload["hard_veto"],
        "components": components,
    }

    output_schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    output_validator = _load_module("oe002_output_validator_for_score", OUTPUT_VALIDATOR_PATH)
    output_errors = output_validator.validate(result, output_schema, model)
    if output_errors:
        raise ScoreError("E_OUTPUT_INVALID:" + " | ".join(output_errors))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--output")
    args = ap.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = score(payload)
    except (OSError, json.JSONDecodeError, ScoreError) as exc:
        print(json.dumps({"schema":"die.division001.demand-score-run.v1","status":"FAIL","error":str(exc)}, indent=2))
        return 2
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
