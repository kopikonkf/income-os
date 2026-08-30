"""Deterministic Asset QC v1 SHADOW evaluator.

QC consumes a first-class QA receipt plus a bounded reviewer observation and
produces a recommendation receipt.  It never overrides QA hard vetoes and never
grants release, submission, publication, or delegation authority.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from typing import Any

QC_SCHEMA = "die.asset.qc.v1"
OBSERVATION_SCHEMA = "die.asset.qc-observation.v1"
QA_SCHEMA = "die.asset.qa.v1"
RUBRIC_SCHEMA = "die.asset.qc-rubric.v1"
HEX = set("0123456789abcdef")


class AssetQCError(RuntimeError):
    """Malformed QC input or authority/lineage contract violation."""


def _load(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetQCError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssetQCError(f"expected JSON object: {path}")
    return value


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in HEX for ch in value)


def load_rubric(path: pathlib.Path) -> dict[str, Any]:
    rubric = _load(path)
    if rubric.get("schema_version") != RUBRIC_SCHEMA:
        raise AssetQCError("rubric schema mismatch")
    if rubric.get("mode") != "SHADOW_ONLY":
        raise AssetQCError("QC-B01 rubric must remain SHADOW_ONLY")
    factors = rubric.get("factors")
    if not isinstance(factors, dict) or not factors:
        raise AssetQCError("rubric factors are required")
    weight_sum = 0.0
    for name, row in factors.items():
        if not isinstance(name, str) or not name or not isinstance(row, dict):
            raise AssetQCError("rubric factor is invalid")
        weight = row.get("weight")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
            raise AssetQCError(f"rubric factor weight invalid: {name}")
        weight_sum += float(weight)
    if abs(weight_sum - 1.0) > 1e-9:
        raise AssetQCError("rubric factor weights must sum to 1")
    defects = rubric.get("defect_classes")
    if not isinstance(defects, dict) or not defects:
        raise AssetQCError("rubric defect classes are required")
    policy = rubric.get("recommendation_policy")
    if not isinstance(policy, dict):
        raise AssetQCError("recommendation policy missing")
    authority = rubric.get("authority_boundary")
    expected_false = (
        "release_authorized",
        "submission_authorized",
        "publication_authorized",
        "qa_hard_veto_waivable",
        "self_promotion_allowed",
        "delegation_thresholds_defined_here",
    )
    if not isinstance(authority, dict) or any(authority.get(key) is not False for key in expected_false):
        raise AssetQCError("rubric authority boundary expands authority")
    return {**rubric, "rubric_sha256": _sha256(path)}


def _validate_observation(observation: dict[str, Any], rubric: dict[str, Any]) -> None:
    if observation.get("schema_version") != OBSERVATION_SCHEMA:
        raise AssetQCError("observation schema mismatch")
    for field in ("asset_id", "blueprint_id", "reviewer_id", "reviewer_version"):
        if not isinstance(observation.get(field), str) or not observation[field]:
            raise AssetQCError(f"observation field required: {field}")
    for field in ("asset_sha256", "blueprint_sha256"):
        if not _is_sha(observation.get(field)):
            raise AssetQCError(f"observation hash invalid: {field}")
    factors = observation.get("factors")
    expected = set(rubric["factors"])
    if not isinstance(factors, dict) or set(factors) != expected:
        raise AssetQCError("observation factors must exactly match rubric factors")
    allowed_defects = set(rubric["defect_classes"])
    for name, row in factors.items():
        if not isinstance(row, dict) or set(row) != {"score", "confidence", "defect_classes", "evidence_refs"}:
            raise AssetQCError(f"observation factor fields invalid: {name}")
        score = row["score"]
        confidence = row["confidence"]
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 4:
            raise AssetQCError(f"factor score invalid: {name}")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise AssetQCError(f"factor confidence invalid: {name}")
        defects = row["defect_classes"]
        if not isinstance(defects, list) or any(item not in allowed_defects for item in defects):
            raise AssetQCError(f"factor defect class invalid: {name}")
        refs = row["evidence_refs"]
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
            raise AssetQCError(f"factor evidence refs invalid: {name}")


def _qa_gate(qa: dict[str, Any], observation: dict[str, Any]) -> tuple[bool, str]:
    if qa.get("schema_version") != QA_SCHEMA:
        raise AssetQCError("QA receipt schema mismatch")
    assets = qa.get("asset_results")
    if not isinstance(assets, list):
        raise AssetQCError("QA asset_results missing")
    matches = [row for row in assets if isinstance(row, dict) and row.get("asset_id") == observation["asset_id"]]
    if len(matches) != 1:
        raise AssetQCError("QA receipt must contain exactly one matching asset_id")
    source_sha = matches[0].get("source_sha256")
    if source_sha != observation["asset_sha256"]:
        raise AssetQCError("QA/QC asset hash lineage mismatch")
    blocked = qa.get("hard_veto") is True or qa.get("batch_state") != "PASS" or matches[0].get("route") != "PASS"
    reason = "QA hard veto/non-PASS route" if blocked else "QA PASS lineage verified"
    return (not blocked), reason


def evaluate(
    qa_receipt_path: pathlib.Path,
    observation_path: pathlib.Path,
    rubric_path: pathlib.Path,
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Produce a deterministic SHADOW recommendation receipt."""
    qa = _load(qa_receipt_path)
    observation = _load(observation_path)
    rubric = load_rubric(rubric_path)
    _validate_observation(observation, rubric)
    qa_pass, qa_reason = _qa_gate(qa, observation)

    weighted_score = 0.0
    weighted_confidence = 0.0
    defects: set[str] = set()
    evidence: set[str] = {f"qa:{_sha256(qa_receipt_path)}", f"observation:{_sha256(observation_path)}", f"rubric:{rubric['rubric_sha256']}"}
    for name, factor in rubric["factors"].items():
        row = observation["factors"][name]
        weight = float(factor["weight"])
        weighted_score += (float(row["score"]) / 4.0) * weight * 100.0
        weighted_confidence += float(row["confidence"]) * weight
        defects.update(row["defect_classes"])
        evidence.update(row["evidence_refs"])

    score = round(weighted_score, 4)
    confidence = round(weighted_confidence, 4)
    critical = any(rubric["defect_classes"][code].get("critical") is True for code in defects)
    policy = rubric["recommendation_policy"]
    if not qa_pass:
        recommendation = "BLOCKED_BY_QA"
    elif critical or score < float(policy["review_score_min"]):
        recommendation = "FAIL_RECOMMENDED"
    elif score < float(policy["pass_score_min"]) or confidence < float(policy["minimum_confidence_for_pass_recommendation"]):
        recommendation = "REVIEW_RECOMMENDED"
    else:
        recommendation = "PASS_RECOMMENDED"

    qa_sha = _sha256(qa_receipt_path)
    observation_sha = _sha256(observation_path)
    identity_material = "|".join((qa_sha, observation_sha, rubric["rubric_sha256"], recommendation))
    stamp = evaluated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return {
        "schema_version": QC_SCHEMA,
        "receipt_id": f"QCREC-{hashlib.sha256(identity_material.encode('utf-8')).hexdigest()[:20].upper()}",
        "evaluated_at": stamp,
        "asset_id": observation["asset_id"],
        "asset_sha256": observation["asset_sha256"],
        "blueprint_id": observation["blueprint_id"],
        "blueprint_sha256": observation["blueprint_sha256"],
        "qa_receipt_sha256": qa_sha,
        "rubric_id": rubric["rubric_id"],
        "rubric_version": rubric["rubric_version"],
        "reviewer_id": observation["reviewer_id"],
        "reviewer_version": observation["reviewer_version"],
        "score": score,
        "confidence": confidence,
        "recommendation": recommendation,
        "defect_classes": sorted(defects),
        "evidence_refs": sorted(evidence),
        "mode": "SHADOW_ONLY",
        "qa_gate": {"passed": qa_pass, "reason": qa_reason},
        "authority_boundary": {
            "release_authorized": False,
            "submission_authorized": False,
            "publication_authorized": False,
            "qa_hard_veto_waivable": False,
            "self_promotion_allowed": False,
        },
    }
