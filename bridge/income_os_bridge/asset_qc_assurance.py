"""Calibration, SHADOW review, delegation, and drift safeguards for Asset QC v1.

This module deliberately separates engine capability from authority.  It can
measure agreement and evaluate a Founder-ratified policy, but it cannot create
ratification, waive QA gates, or authorize marketplace submission.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from typing import Any, Iterable

from . import asset_qc

CALIBRATION_SCHEMA = "die.asset.qc-calibration.v1"
SHADOW_SCHEMA = "die.asset.qc-shadow-case.v1"
DELEGATION_POLICY_SCHEMA = "die.asset.qc-delegation-policy.v1"
AUDIT_POLICY_SCHEMA = "die.asset.qc-audit-policy.v1"
LABEL_SCHEMA = "die.asset.qc-label.v1"
GROUND_TRUTH_LABELERS = {"Founder", "Founder-delegated-manual-reviewer"}


class AssetQCAssuranceError(RuntimeError):
    """Malformed calibration/shadow/delegation input."""


def _load(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetQCAssuranceError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssetQCAssuranceError(f"expected JSON object: {path}")
    return value


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _engine_decision(recommendation: str) -> str:
    mapping = {
        "PASS_RECOMMENDED": "PASS",
        "FAIL_RECOMMENDED": "FAIL",
        "REVIEW_RECOMMENDED": "REVIEW",
        "BLOCKED_BY_QA": "FAIL",
    }
    try:
        return mapping[recommendation]
    except KeyError as exc:
        raise AssetQCAssuranceError(f"unsupported QC recommendation: {recommendation}") from exc


def _validate_label(label: dict[str, Any]) -> None:
    if label.get("schema_version") != LABEL_SCHEMA:
        raise AssetQCAssuranceError("QC label schema mismatch")
    if label.get("labeler_principal_id") not in GROUND_TRUTH_LABELERS:
        raise AssetQCAssuranceError("labeler is not an accepted QC ground-truth principal")
    if label.get("decision") not in {"PASS", "FAIL", "REVIEW"}:
        raise AssetQCAssuranceError("invalid Founder/manual QC decision")
    if not isinstance(label.get("asset_id"), str) or not label["asset_id"]:
        raise AssetQCAssuranceError("label asset_id missing")
    if not isinstance(label.get("asset_class"), str) or not label["asset_class"]:
        raise AssetQCAssuranceError("label asset_class missing")
    for field in ("asset_sha256", "blueprint_sha256", "qa_receipt_sha256"):
        value = label.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise AssetQCAssuranceError(f"invalid label hash: {field}")
    defects = label.get("defect_classes")
    if not isinstance(defects, list) or any(not isinstance(value, str) or not value for value in defects):
        raise AssetQCAssuranceError("label defect_classes invalid")


def _validate_qc_receipt(qc: dict[str, Any]) -> None:
    if qc.get("schema_version") != asset_qc.QC_SCHEMA:
        raise AssetQCAssuranceError("QC receipt schema mismatch")
    if qc.get("mode") != "SHADOW_ONLY":
        raise AssetQCAssuranceError("calibration source QC receipt must be SHADOW_ONLY")
    authority = qc.get("authority_boundary")
    if not isinstance(authority, dict) or authority.get("release_authorized") is not False or authority.get("submission_authorized") is not False:
        raise AssetQCAssuranceError("QC receipt expands authority")
    if qc.get("recommendation") not in {"PASS_RECOMMENDED", "FAIL_RECOMMENDED", "REVIEW_RECOMMENDED", "BLOCKED_BY_QA"}:
        raise AssetQCAssuranceError("QC recommendation invalid")
    confidence = qc.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        raise AssetQCAssuranceError("QC confidence invalid")


def _assert_label_qc_lineage(label: dict[str, Any], qc: dict[str, Any]) -> None:
    checks = (
        ("asset_id", "asset_id"),
        ("asset_sha256", "asset_sha256"),
        ("blueprint_id", "blueprint_id"),
        ("blueprint_sha256", "blueprint_sha256"),
        ("qa_receipt_sha256", "qa_receipt_sha256"),
    )
    for label_field, qc_field in checks:
        if label.get(label_field) != qc.get(qc_field):
            raise AssetQCAssuranceError(f"label/QC lineage mismatch: {label_field}")


def build_shadow_case(
    label_path: pathlib.Path,
    qc_receipt_path: pathlib.Path,
    rubric_path: pathlib.Path,
) -> dict[str, Any]:
    label = _load(label_path)
    qc = _load(qc_receipt_path)
    rubric = asset_qc.load_rubric(rubric_path)
    _validate_label(label)
    _validate_qc_receipt(qc)
    _assert_label_qc_lineage(label, qc)

    engine_decision = _engine_decision(str(qc["recommendation"]))
    founder_decision = str(label["decision"])
    reasons: list[str] = []
    if founder_decision != engine_decision:
        reasons.append("DISAGREEMENT")
    minimum_confidence = float(rubric["recommendation_policy"]["minimum_confidence_for_pass_recommendation"])
    if float(qc["confidence"]) < minimum_confidence:
        reasons.append("LOW_CONFIDENCE")
    if qc["recommendation"] == "REVIEW_RECOMMENDED":
        reasons.append("ENGINE_REVIEW")
    if qc["recommendation"] == "BLOCKED_BY_QA":
        reasons.append("QA_BLOCKED")

    label_sha = _sha256(label_path)
    qc_sha = _sha256(qc_receipt_path)
    identity = _hash_value({"label": label_sha, "qc": qc_sha, "rubric": rubric["rubric_sha256"]})
    return {
        "schema_version": SHADOW_SCHEMA,
        "case_id": f"QCSHADOW-{identity[:20].upper()}",
        "asset_id": label["asset_id"],
        "asset_sha256": label["asset_sha256"],
        "asset_class": label["asset_class"],
        "founder_decision": founder_decision,
        "engine_decision": engine_decision,
        "engine_recommendation": qc["recommendation"],
        "confidence": float(qc["confidence"]),
        "agreement": founder_decision == engine_decision,
        "queue_required": bool(reasons),
        "queue_reasons": sorted(set(reasons)),
        "founder_label_sha256": label_sha,
        "qc_receipt_sha256": qc_sha,
        "authority_boundary": {
            "release_authorized": False,
            "submission_authorized": False,
            "founder_final": True,
        },
    }


def build_disagreement_queue(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    retained = [case for case in cases if case.get("queue_required") is True]
    retained.sort(key=lambda row: str(row.get("case_id")))
    return {
        "schema_version": "die.asset.qc-disagreement-queue.v1",
        "queue_count": len(retained),
        "cases": retained,
        "authority_boundary": {"release_authorized": False, "submission_authorized": False},
    }


def _confidence_band(confidence: float) -> str:
    if confidence < 0.25:
        return "0.00-0.24"
    if confidence < 0.50:
        return "0.25-0.49"
    if confidence < 0.75:
        return "0.50-0.74"
    return "0.75-1.00"


def build_calibration_report(
    label_paths: Iterable[pathlib.Path],
    qc_receipt_paths: Iterable[pathlib.Path],
    rubric_path: pathlib.Path,
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    labels = list(label_paths)
    qc_paths = list(qc_receipt_paths)
    if not labels or len(labels) != len(qc_paths):
        raise AssetQCAssuranceError("calibration requires equal non-empty label/QC sets")
    rubric = asset_qc.load_rubric(rubric_path)

    label_by_asset: dict[str, tuple[pathlib.Path, dict[str, Any]]] = {}
    for path in labels:
        value = _load(path)
        _validate_label(value)
        asset_id = str(value["asset_id"])
        if asset_id in label_by_asset:
            raise AssetQCAssuranceError("duplicate calibration label asset_id")
        label_by_asset[asset_id] = (path, value)

    qc_by_asset: dict[str, tuple[pathlib.Path, dict[str, Any]]] = {}
    for path in qc_paths:
        value = _load(path)
        _validate_qc_receipt(value)
        asset_id = str(value.get("asset_id") or "")
        if not asset_id or asset_id in qc_by_asset:
            raise AssetQCAssuranceError("duplicate/missing calibration QC asset_id")
        qc_by_asset[asset_id] = (path, value)
    if set(label_by_asset) != set(qc_by_asset):
        raise AssetQCAssuranceError("calibration label/QC asset sets differ")

    reviewer_pairs = {(str(value["reviewer_id"]), str(value["reviewer_version"])) for _, value in qc_by_asset.values()}
    if len(reviewer_pairs) != 1:
        raise AssetQCAssuranceError("calibration report cannot mix reviewer versions")
    reviewer_id, reviewer_version = next(iter(reviewer_pairs))

    case_rows: list[dict[str, Any]] = []
    label_hashes: list[str] = []
    input_refs: list[str] = []
    critical_classes = {name for name, row in rubric["defect_classes"].items() if row.get("critical") is True}
    per_defect = {name: {"founder_count": 0, "engine_count": 0, "miss_count": 0} for name in rubric["defect_classes"]}
    per_asset: dict[str, dict[str, int]] = {}
    band_acc: dict[str, list[tuple[float, bool]]] = {name: [] for name in ("0.00-0.24", "0.25-0.49", "0.50-0.74", "0.75-1.00")}

    for asset_id in sorted(label_by_asset):
        label_path, label = label_by_asset[asset_id]
        qc_path, qc = qc_by_asset[asset_id]
        _assert_label_qc_lineage(label, qc)
        engine = _engine_decision(str(qc["recommendation"]))
        founder = str(label["decision"])
        agreement = engine == founder
        founder_defects = set(label["defect_classes"])
        engine_defects = set(qc.get("defect_classes") if isinstance(qc.get("defect_classes"), list) else [])
        unknown_defects = (founder_defects | engine_defects) - set(rubric["defect_classes"])
        if unknown_defects:
            raise AssetQCAssuranceError(f"unknown defect class in calibration: {sorted(unknown_defects)}")
        hard_misses = sorted((founder_defects & critical_classes) - engine_defects)
        false_pass = engine == "PASS" and founder == "FAIL"
        false_fail = engine == "FAIL" and founder == "PASS"
        confidence = float(qc["confidence"])
        band_acc[_confidence_band(confidence)].append((confidence, agreement))
        for code in founder_defects:
            per_defect[code]["founder_count"] += 1
        for code in engine_defects:
            per_defect[code]["engine_count"] += 1
        for code in hard_misses:
            per_defect[code]["miss_count"] += 1
        asset_class = str(label["asset_class"])
        stats = per_asset.setdefault(asset_class, {"count": 0, "agreement": 0, "false_pass": 0, "false_fail": 0, "hard_defect_miss": 0})
        stats["count"] += 1
        stats["agreement"] += int(agreement)
        stats["false_pass"] += int(false_pass)
        stats["false_fail"] += int(false_fail)
        stats["hard_defect_miss"] += len(hard_misses)
        label_sha = _sha256(label_path)
        qc_sha = _sha256(qc_path)
        label_hashes.append(label_sha)
        input_refs.extend((f"label:{label_sha}", f"qc:{qc_sha}"))
        case_rows.append({
            "asset_id": asset_id,
            "asset_class": asset_class,
            "founder_decision": founder,
            "engine_decision": engine,
            "agreement": agreement,
            "false_pass": false_pass,
            "false_fail": false_fail,
            "hard_defect_misses": hard_misses,
            "confidence": confidence,
        })

    count = len(case_rows)
    agreement_count = sum(row["agreement"] for row in case_rows)
    false_pass_count = sum(row["false_pass"] for row in case_rows)
    false_fail_count = sum(row["false_fail"] for row in case_rows)
    hard_miss_count = sum(len(row["hard_defect_misses"]) for row in case_rows)
    mean_confidence = sum(row["confidence"] for row in case_rows) / count

    confidence_bands: list[dict[str, Any]] = []
    weighted_gap = 0.0
    for band, values in band_acc.items():
        if not values:
            confidence_bands.append({"band": band, "count": 0, "mean_confidence": None, "agreement_rate": None, "calibration_gap": None})
            continue
        band_conf = sum(value for value, _ in values) / len(values)
        band_agreement = sum(agree for _, agree in values) / len(values)
        gap = abs(band_conf - band_agreement)
        weighted_gap += gap * len(values)
        confidence_bands.append({"band": band, "count": len(values), "mean_confidence": round(band_conf, 6), "agreement_rate": round(band_agreement, 6), "calibration_gap": round(gap, 6)})

    normalized_asset = {
        key: {
            **value,
            "agreement_rate": round(value["agreement"] / value["count"], 6),
            "false_pass_rate": round(value["false_pass"] / value["count"], 6),
            "false_fail_rate": round(value["false_fail"] / value["count"], 6),
        }
        for key, value in sorted(per_asset.items())
    }
    corpus_sha = _hash_value(sorted(label_hashes))
    stamp = evaluated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report_identity = _hash_value({"corpus": corpus_sha, "rubric": rubric["rubric_sha256"], "reviewer_id": reviewer_id, "reviewer_version": reviewer_version})
    return {
        "schema_version": CALIBRATION_SCHEMA,
        "report_id": f"QCCAL-{report_identity[:20].upper()}",
        "evaluated_at": stamp,
        "rubric_id": rubric["rubric_id"],
        "rubric_version": rubric["rubric_version"],
        "corpus_sha256": corpus_sha,
        "reviewer_id": reviewer_id,
        "reviewer_version": reviewer_version,
        "case_count": count,
        "metrics": {
            "agreement_rate": round(agreement_count / count, 6),
            "false_pass_rate": round(false_pass_count / count, 6),
            "false_fail_rate": round(false_fail_count / count, 6),
            "hard_defect_miss_count": hard_miss_count,
            "mean_confidence": round(mean_confidence, 6),
            "confidence_calibration_gap": round(weighted_gap / count, 6),
        },
        "confidence_bands": confidence_bands,
        "per_defect_class": per_defect,
        "per_asset_class": normalized_asset,
        "input_refs": sorted(input_refs),
        "authority_boundary": {"release_authorized": False, "submission_authorized": False, "self_promotion_allowed": False},
    }


def load_delegation_policy(path: pathlib.Path) -> dict[str, Any]:
    policy = _load(path)
    if policy.get("schema_version") != DELEGATION_POLICY_SCHEMA:
        raise AssetQCAssuranceError("delegation policy schema mismatch")
    mode = policy.get("mode")
    if mode not in {"SHADOW_ONLY", "CALIBRATED_RECOMMENDER", "BOUNDED_AUTO_QC", "SAMPLED_AUDIT"}:
        raise AssetQCAssuranceError("delegation mode invalid")
    authority = policy.get("authority_boundary")
    if not isinstance(authority, dict) or any(authority.get(key) is not False for key in ("submission_authorized", "publication_authorized", "qa_hard_veto_waivable", "self_promotion_allowed")):
        raise AssetQCAssuranceError("delegation policy expands forbidden authority")
    if mode != "SHADOW_ONLY":
        if policy.get("status") != "FOUNDER_RATIFIED":
            raise AssetQCAssuranceError("non-SHADOW delegation requires Founder ratification")
        ratification = policy.get("ratification")
        if not isinstance(ratification, dict) or ratification.get("ratified_by") != "Founder" or not ratification.get("ratified_at"):
            raise AssetQCAssuranceError("Founder ratification evidence missing")
        expected = ratification.get("policy_sha256")
        body = json.loads(json.dumps(policy))
        body["ratification"]["policy_sha256"] = None
        if expected != _hash_value(body):
            raise AssetQCAssuranceError("delegation policy ratification hash mismatch")
    return policy


def evaluate_delegation(
    policy_path: pathlib.Path,
    calibration_report: dict[str, Any],
    *,
    asset_class: str,
    marketplace: str,
    now: str,
) -> dict[str, Any]:
    policy = load_delegation_policy(policy_path)
    mode = str(policy["mode"])
    base = {
        "schema_version": "die.asset.qc-delegation-evaluation.v1",
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "mode": mode,
        "qc_release_authorized": False,
        "submission_authorized": False,
        "reasons": [],
    }
    if mode == "SHADOW_ONLY":
        base["reasons"] = ["SHADOW_ONLY"]
        return base
    scope = policy.get("scope")
    if not isinstance(scope, dict):
        raise AssetQCAssuranceError("delegation scope missing")
    checks = (
        (asset_class, scope.get("asset_classes"), "ASSET_CLASS_OUT_OF_SCOPE"),
        (marketplace, scope.get("marketplaces"), "MARKETPLACE_OUT_OF_SCOPE"),
        (calibration_report.get("reviewer_id"), scope.get("reviewer_ids"), "REVIEWER_OUT_OF_SCOPE"),
        (calibration_report.get("reviewer_version"), scope.get("reviewer_versions"), "REVIEWER_VERSION_OUT_OF_SCOPE"),
    )
    reasons: list[str] = []
    for value, allowed, code in checks:
        if not isinstance(allowed, list) or value not in allowed:
            reasons.append(code)
    try:
        current = dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
        valid_from = dt.datetime.fromisoformat(str(scope["valid_from"]).replace("Z", "+00:00"))
        valid_until = dt.datetime.fromisoformat(str(scope["valid_until"]).replace("Z", "+00:00"))
        if current < valid_from or current > valid_until:
            reasons.append("POLICY_EXPIRED_OR_NOT_YET_VALID")
    except Exception as exc:
        raise AssetQCAssuranceError("delegation scope validity window invalid") from exc
    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict):
        raise AssetQCAssuranceError("ratified non-SHADOW policy thresholds missing")
    metrics = calibration_report.get("metrics")
    if not isinstance(metrics, dict):
        raise AssetQCAssuranceError("calibration metrics missing")
    requirements = (
        (calibration_report.get("case_count", 0) >= thresholds.get("min_case_count", 10**18), "CALIBRATION_CASE_COUNT_TOO_LOW"),
        (metrics.get("agreement_rate", -1) >= thresholds.get("min_agreement_rate", 2), "AGREEMENT_BELOW_THRESHOLD"),
        (metrics.get("false_pass_rate", 2) <= thresholds.get("max_false_pass_rate", -1), "FALSE_PASS_ABOVE_THRESHOLD"),
        (metrics.get("hard_defect_miss_count", 10**18) <= thresholds.get("max_hard_defect_miss_count", -1), "HARD_DEFECT_MISS_ABOVE_THRESHOLD"),
        (metrics.get("confidence_calibration_gap", 2) <= thresholds.get("max_confidence_calibration_gap", -1), "CONFIDENCE_GAP_ABOVE_THRESHOLD"),
    )
    reasons.extend(code for ok, code in requirements if not ok)
    if mode == "CALIBRATED_RECOMMENDER":
        reasons.append("RECOMMENDER_MODE_RETAINS_FOUNDER_FINAL")
    elif not reasons and mode in {"BOUNDED_AUTO_QC", "SAMPLED_AUDIT"}:
        base["qc_release_authorized"] = True
    base["reasons"] = sorted(set(reasons))
    return base


def compare_calibration_reports(
    baseline: dict[str, Any],
    current: dict[str, Any],
    audit_policy_path: pathlib.Path,
) -> dict[str, Any]:
    audit = _load(audit_policy_path)
    if audit.get("schema_version") != AUDIT_POLICY_SCHEMA:
        raise AssetQCAssuranceError("audit policy schema mismatch")
    reasons: list[str] = []
    blocking: list[str] = []
    if baseline.get("corpus_sha256") != current.get("corpus_sha256"):
        blocking.append("CORPUS_MISMATCH")
    if baseline.get("rubric_id") != current.get("rubric_id") or baseline.get("rubric_version") != current.get("rubric_version"):
        blocking.append("RUBRIC_MISMATCH")
    base_metrics = baseline.get("metrics")
    current_metrics = current.get("metrics")
    if not isinstance(base_metrics, dict) or not isinstance(current_metrics, dict):
        raise AssetQCAssuranceError("calibration metrics missing for audit")
    guard = audit.get("drift_guardrails")
    if not isinstance(guard, dict):
        raise AssetQCAssuranceError("audit drift guardrails missing")
    deltas = {
        "agreement_rate": round(float(current_metrics["agreement_rate"]) - float(base_metrics["agreement_rate"]), 6),
        "false_pass_rate": round(float(current_metrics["false_pass_rate"]) - float(base_metrics["false_pass_rate"]), 6),
        "hard_defect_miss_count": int(current_metrics["hard_defect_miss_count"]) - int(base_metrics["hard_defect_miss_count"]),
        "confidence_calibration_gap": round(float(current_metrics["confidence_calibration_gap"]) - float(base_metrics["confidence_calibration_gap"]), 6),
    }
    if -deltas["agreement_rate"] > float(guard["max_agreement_drop"]):
        reasons.append("AGREEMENT_DRIFT")
    if deltas["false_pass_rate"] > float(guard["max_false_pass_rate_increase"]):
        blocking.append("FALSE_PASS_REGRESSION")
    if deltas["hard_defect_miss_count"] > int(guard["max_hard_defect_miss_increase"]):
        blocking.append("HARD_DEFECT_MISS_REGRESSION")
    if deltas["confidence_calibration_gap"] > float(guard["max_confidence_calibration_gap_increase"]):
        reasons.append("CONFIDENCE_CALIBRATION_DRIFT")
    status = "BLOCKED" if blocking else ("REVIEW_REQUIRED" if reasons else "PASS")
    return {
        "schema_version": "die.asset.qc-audit.v1",
        "status": status,
        "baseline_reviewer": {"id": baseline.get("reviewer_id"), "version": baseline.get("reviewer_version")},
        "current_reviewer": {"id": current.get("reviewer_id"), "version": current.get("reviewer_version")},
        "deltas": deltas,
        "blocking_reasons": sorted(blocking),
        "review_reasons": sorted(reasons),
        "authority_boundary": {"release_authorized": False, "submission_authorized": False, "self_promotion_allowed": False},
    }
