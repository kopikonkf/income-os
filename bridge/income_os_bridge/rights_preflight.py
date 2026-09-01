"""RIGHTS-001 conservative rights/IP risk evidence producer.

This module is not legal clearance. It evaluates deterministic textual/logo
signals supplied by bounded detectors or reviewers, produces a structured
rights state, and deliberately leaves visually uncertain cases unresolved so
Asset QA maps them to RIGHTS_UNCLEAR HARD_VETO.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "die.asset.rights-preflight.v1"
RISK_CLASSES = {
    "brand_logo_trademark",
    "copyrighted_character_artwork",
    "trade_dress_product_design",
    "likeness_publicity",
    "property_release_sensitive",
    "watermark_attribution_conflict",
    "uncertain_missing_evidence",
}


class RightsError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(value: str) -> str:
    return " ".join(str(value).split()).strip()


def deterministic_text_checks(*, extracted_text: list[str], protected_terms: list[str], allowed_terms: list[str] | None = None) -> list[dict[str, Any]]:
    allowed = {_norm(x).casefold() for x in (allowed_terms or []) if _norm(x)}
    protected = {_norm(x).casefold() for x in protected_terms if _norm(x)}
    findings: list[dict[str, Any]] = []
    for raw in extracted_text:
        text = _norm(raw)
        folded = text.casefold()
        if not text:
            continue
        if any(token in folded for token in ("©", "®", "™", "watermark", "all rights reserved")):
            findings.append({"class": "watermark_attribution_conflict", "signal": text, "decision": "FAIL"})
        for term in protected:
            if term not in allowed and term in folded:
                findings.append({"class": "brand_logo_trademark", "signal": term, "decision": "FAIL"})
    return findings


def evaluate(evidence: dict[str, Any]) -> dict[str, Any]:
    required = {
        "artifact_path", "artifact_sha256", "extracted_text", "protected_terms", "allowed_terms",
        "detector_findings", "human_visual_review", "release_evidence", "source_lineage_clear",
    }
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise RightsError("E_EVIDENCE_SHAPE")
    artifact = Path(evidence["artifact_path"])
    if not artifact.is_file() or sha256(artifact) != evidence["artifact_sha256"]:
        raise RightsError("E_ARTIFACT_LINEAGE")
    findings = deterministic_text_checks(
        extracted_text=list(evidence["extracted_text"]),
        protected_terms=list(evidence["protected_terms"]),
        allowed_terms=list(evidence["allowed_terms"]),
    )
    for raw in evidence["detector_findings"]:
        if not isinstance(raw, dict) or raw.get("class") not in RISK_CLASSES or raw.get("decision") not in {"PASS", "FAIL", "UNKNOWN"}:
            raise RightsError("E_DETECTOR_FINDING")
        findings.append({"class": raw["class"], "signal": _norm(raw.get("signal", "detector finding")), "decision": raw["decision"]})

    visual = evidence["human_visual_review"]
    if not isinstance(visual, dict) or set(visual) != {"state", "reviewer", "evidence_ref"} or visual["state"] not in {"CLEAR", "FAIL", "UNKNOWN", "NOT_REVIEWED"}:
        raise RightsError("E_VISUAL_REVIEW_SHAPE")
    releases = evidence["release_evidence"]
    if not isinstance(releases, dict) or set(releases) != {"required", "state", "refs"} or releases["state"] not in {"NOT_REQUIRED", "PRESENT", "MISSING", "UNKNOWN"}:
        raise RightsError("E_RELEASE_EVIDENCE")

    failures = [x for x in findings if x["decision"] == "FAIL"]
    unknowns = [x for x in findings if x["decision"] == "UNKNOWN"]
    if visual["state"] == "FAIL":
        failures.append({"class": "uncertain_missing_evidence", "signal": "human visual rights review failed", "decision": "FAIL"})
    elif visual["state"] in {"UNKNOWN", "NOT_REVIEWED"}:
        unknowns.append({"class": "uncertain_missing_evidence", "signal": "visual rights review not clear", "decision": "UNKNOWN"})
    if releases["required"] and releases["state"] != "PRESENT":
        unknowns.append({"class": "property_release_sensitive", "signal": "required release evidence not present", "decision": "UNKNOWN"})
    if evidence["source_lineage_clear"] is not True:
        unknowns.append({"class": "uncertain_missing_evidence", "signal": "source lineage not clear", "decision": "UNKNOWN"})

    if failures:
        state = "FAIL"
        qa_review_state = "FAIL"
    elif unknowns:
        state = "UNCLEAR"
        qa_review_state = "UNKNOWN"
    else:
        state = "CLEAR"
        qa_review_state = "CLEAR"
    return {
        "schema": SCHEMA,
        "artifact_sha256": evidence["artifact_sha256"],
        "state": state,
        "qa_review_state": qa_review_state,
        "findings": findings + unknowns,
        "hard_veto_expected": state in {"FAIL", "UNCLEAR"},
        "legal_clearance_claimed": False,
        "authority_boundary": {
            "qa_hard_veto_waivable": False,
            "submission_authorized": False,
            "publication_authorized": False,
        },
    }


def qa_review_states(receipt: dict[str, Any], *, safety: str = "CLEAR", watermark: str = "CLEAR", visual: str = "PASS") -> dict[str, str]:
    state = receipt.get("qa_review_state")
    if state not in {"CLEAR", "FAIL", "UNKNOWN"}:
        raise RightsError("E_RECEIPT_STATE")
    return {"rights": state, "safety": safety, "watermark": watermark, "visual": visual}
