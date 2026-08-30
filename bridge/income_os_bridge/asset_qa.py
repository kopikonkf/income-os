"""First-class deterministic Asset QA v1 boundary.

This module promotes the proven M-001 raster QA core behind a reusable receipt
contract and adds fail-closed platform/package preflight.  It deliberately does
not perform subjective aesthetic/commercial QC and never grants submission or
publication authority.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from typing import Any

from . import m001_asset_qa

RECEIPT_SCHEMA = "die.asset.qa.v1"
PLATFORM_PROFILE_SCHEMA = "die.asset.qa-platform-profile.v1"
LEGACY_MISSION_ID = "M-001"
HEX = set("0123456789abcdef")

REQUIREMENT_KEYS = (
    "accepted_formats",
    "minimum_megapixels",
    "metadata_constraints",
    "ai_disclosure",
    "similarity_distinctness",
    "account_eligibility",
    "content_restrictions",
    "upload_package_constraints",
)
PROFILE_KEYS = {
    "schema_version",
    "profile_id",
    "platform",
    "profile_version",
    "effective_date",
    "checked_at",
    "source_document",
    "requirements",
}
ALLOWED_PLATFORMS = {
    "Adobe Stock",
    "Dreamstime",
    "123RF",
    "Vecteezy",
    "MotionElements",
}
SEVERITY = {
    "INTEGRITY_FILE_MISSING": "HARD_VETO",
    "INTEGRITY_HASH_MISMATCH": "HARD_VETO",
    "INTEGRITY_RASTER_CORRUPT": "FAIL",
    "LINEAGE_MISSING": "HARD_VETO",
    "LINEAGE_MISMATCH": "HARD_VETO",
    "TECHNICAL_FORMAT_UNSUPPORTED": "FAIL",
    "TECHNICAL_DIMENSION_BELOW_MINIMUM": "FAIL",
    "RIGHTS_UNCLEAR": "HARD_VETO",
    "RIGHTS_FAILED": "HARD_VETO",
    "SAFETY_UNCLEAR": "HARD_VETO",
    "SAFETY_FAILED": "HARD_VETO",
    "WATERMARK_UNCLEAR": "HARD_VETO",
    "WATERMARK_PRESENT": "HARD_VETO",
    "DUPLICATE_ASSET_ID": "FAIL",
    "DUPLICATE_BINARY": "FAIL",
    "METADATA_MISSING": "FAIL",
    "METADATA_INVALID": "FAIL",
    "PACKAGE_INVALID": "HARD_VETO",
    "PLATFORM_PROFILE_UNKNOWN_REQUIREMENT": "HARD_VETO",
    "REVIEW_REQUIRED_VISUAL": "REVIEW_REQUIRED",
}


class AssetQAError(RuntimeError):
    """Malformed QA input or contract violation."""


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetQAError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AssetQAError(f"expected JSON object: {path}")
    return value


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in HEX for char in value)
    )


def _defect(code: str, message: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    if code not in SEVERITY:
        raise AssetQAError(f"unknown defect code: {code}")
    return {
        "code": code,
        "severity": SEVERITY[code],
        "message": message,
        "evidence_refs": list(evidence_refs or []),
    }


def _dedupe_defects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row["code"]), str(row.get("message", "")))
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _reason_defects(reasons: list[Any]) -> list[dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    for raw in reasons:
        if not isinstance(raw, str):
            continue
        reason = raw.lower()
        if "source artifact does not exist" in reason:
            defects.append(_defect("INTEGRITY_FILE_MISSING", raw))
        elif "source_sha256 mismatch" in reason:
            defects.append(_defect("INTEGRITY_HASH_MISMATCH", raw))
        elif any(token in reason for token in ("invalid png", "png chunk", "png lacks", "truncated jpeg", "jpeg lacks", "invalid jpeg", "jpeg dimensions")):
            defects.append(_defect("INTEGRITY_RASTER_CORRUPT", raw))
        elif "format " in reason and " is not allowed" in reason:
            defects.append(_defect("TECHNICAL_FORMAT_UNSUPPORTED", raw))
        elif " mp below " in reason:
            defects.append(_defect("TECHNICAL_DIMENSION_BELOW_MINIMUM", raw))
        elif "duplicate asset_id" in reason:
            defects.append(_defect("DUPLICATE_ASSET_ID", raw))
        elif "exact duplicate binary" in reason:
            defects.append(_defect("DUPLICATE_BINARY", raw))
        elif " mismatch" in reason:
            defects.append(_defect("LINEAGE_MISMATCH", raw))
        elif reason.startswith("missing ") and " review" in reason:
            # Review state is classified from review_states; missing visual evidence
            # must remain REVIEW_REQUIRED rather than becoming a lineage hard veto.
            continue
        elif reason.startswith("missing ") or reason.startswith("invalid source_sha256") or reason.startswith("invalid prompt_hash"):
            defects.append(_defect("LINEAGE_MISSING", raw))
    return defects


def _review_defects(review_states: dict[str, Any]) -> list[dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    rights = review_states.get("rights")
    safety = review_states.get("safety")
    watermark = review_states.get("watermark")
    visual = review_states.get("visual")
    if rights == "FAIL":
        defects.append(_defect("RIGHTS_FAILED", "rights review failed"))
    elif rights not in {"CLEAR", "PASS"}:
        defects.append(_defect("RIGHTS_UNCLEAR", "rights review is not clear"))
    if safety == "FAIL":
        defects.append(_defect("SAFETY_FAILED", "safety review failed"))
    elif safety not in {"CLEAR", "PASS"}:
        defects.append(_defect("SAFETY_UNCLEAR", "safety review is not clear"))
    if watermark == "FAIL":
        defects.append(_defect("WATERMARK_PRESENT", "watermark review failed"))
    elif watermark not in {"CLEAR", "PASS"}:
        defects.append(_defect("WATERMARK_UNCLEAR", "watermark review is not clear"))
    if visual == "UNKNOWN":
        defects.append(_defect("REVIEW_REQUIRED_VISUAL", "visual evidence requires review"))
    return defects


def _canonical_route(legacy_route: Any) -> str:
    if legacy_route == "T1_PASS":
        return "PASS"
    allowed = {
        "RECREATE_TECHNICAL",
        "QUARANTINE_RIGHTS",
        "QUARANTINE_SAFETY",
        "ARCHIVE_RESEARCH_ONLY",
        "REVIEW_REQUIRED",
        "T1_MARKET_FIT_FAIL",
        "T1_RECOVERABLE",
        "BLOCK_SUBMISSION",
    }
    return str(legacy_route) if legacy_route in allowed else "BLOCK_SUBMISSION"


def promote_m001_receipt(legacy: dict[str, Any], *, mission_id: str = LEGACY_MISSION_ID) -> dict[str, Any]:
    """Translate a proven M-001 QA receipt into the first-class v1 contract."""
    if legacy.get("schema_version") != m001_asset_qa.RECEIPT_SCHEMA:
        raise AssetQAError("legacy receipt schema mismatch")
    source_manifest_sha = legacy.get("source_manifest_sha256")
    if not _is_sha256(source_manifest_sha):
        raise AssetQAError("legacy source manifest hash is invalid")
    rows = legacy.get("routes")
    if not isinstance(rows, list):
        raise AssetQAError("legacy routes must be an array")

    assets: list[dict[str, Any]] = []
    all_defects: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raw = {}
        defects = _reason_defects(raw.get("reasons") if isinstance(raw.get("reasons"), list) else [])
        review_states = raw.get("review_states") if isinstance(raw.get("review_states"), dict) else {}
        defects.extend(_review_defects(review_states))
        defects = _dedupe_defects(defects)
        all_defects.extend(defects)
        asset_id = raw.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            asset_id = f"index-{index}"
        source_sha = raw.get("source_sha256")
        assets.append(
            {
                "asset_id": asset_id,
                "source_sha256": source_sha if _is_sha256(source_sha) else None,
                "route": _canonical_route(raw.get("route")),
                "defects": defects,
            }
        )

    summary = {
        "hard_veto_count": sum(row["severity"] == "HARD_VETO" for row in all_defects),
        "fail_count": sum(row["severity"] == "FAIL" for row in all_defects),
        "review_required_count": sum(row["severity"] == "REVIEW_REQUIRED" for row in all_defects),
    }
    return {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_id": f"QAREC-M001-{source_manifest_sha[:16].upper()}",
        "evaluated_at": legacy.get("evaluated_at") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mission_id": mission_id,
        "batch_id": str(legacy.get("batch_id") or "UNKNOWN"),
        "blueprint_id": str(legacy.get("blueprint_id") or "UNKNOWN"),
        "source_manifest_sha256": source_manifest_sha,
        "qa_scope": "UNIVERSAL",
        "platform_profile": None,
        "batch_state": legacy.get("batch_state") if legacy.get("batch_state") in {"PASS", "FAIL", "BLOCKED_REVIEW"} else "FAIL",
        "hard_veto": summary["hard_veto_count"] > 0,
        "defect_summary": summary,
        "asset_results": assets,
        "package_result": None,
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "hard_vetoes_waivable": False,
        },
    }


def evaluate_m001_manifest(
    manifest_path: pathlib.Path,
    workspace: pathlib.Path,
    *,
    min_assets: int,
    max_assets: int,
    min_pass_rate: float = 0.80,
) -> dict[str, Any]:
    """Compatibility adapter: run existing M-001 logic then promote its receipt."""
    legacy = m001_asset_qa.evaluate_manifest(
        manifest_path,
        workspace,
        min_assets=min_assets,
        max_assets=max_assets,
        min_pass_rate=min_pass_rate,
    )
    return promote_m001_receipt(legacy)


def load_platform_profile(path: pathlib.Path) -> dict[str, Any]:
    """Load a dated profile with strict fields; UNKNOWN requirements remain valid but block preflight."""
    profile = _load_json(path)
    if set(profile) != PROFILE_KEYS:
        extra = sorted(set(profile) - PROFILE_KEYS)
        missing = sorted(PROFILE_KEYS - set(profile))
        raise AssetQAError(f"platform profile fields invalid; missing={missing}; extra={extra}")
    if profile["schema_version"] != PLATFORM_PROFILE_SCHEMA:
        raise AssetQAError("platform profile schema mismatch")
    if profile["platform"] not in ALLOWED_PLATFORMS:
        raise AssetQAError("unsupported platform profile")
    if not isinstance(profile["profile_id"], str) or not profile["profile_id"]:
        raise AssetQAError("profile_id is required")
    if not isinstance(profile["profile_version"], int) or isinstance(profile["profile_version"], bool) or profile["profile_version"] < 1:
        raise AssetQAError("profile_version must be a positive integer")
    for field in ("effective_date", "checked_at", "source_document"):
        if not isinstance(profile[field], str) or not profile[field]:
            raise AssetQAError(f"{field} is required")
    requirements = profile["requirements"]
    if not isinstance(requirements, dict) or set(requirements) != set(REQUIREMENT_KEYS):
        raise AssetQAError("platform profile requirements are incomplete or contain unknown fields")
    for key in REQUIREMENT_KEYS:
        req = requirements[key]
        if not isinstance(req, dict) or set(req) != {"status", "value", "evidence_refs"}:
            raise AssetQAError(f"requirement {key} fields are invalid")
        if req["status"] not in {"KNOWN", "UNKNOWN"}:
            raise AssetQAError(f"requirement {key} status is invalid")
        refs = req["evidence_refs"]
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise AssetQAError(f"requirement {key} evidence_refs are invalid")
        if req["status"] == "UNKNOWN" and req["value"] is not None:
            raise AssetQAError(f"UNKNOWN requirement {key} must have null value")
        if req["status"] == "KNOWN" and not refs:
            raise AssetQAError(f"KNOWN requirement {key} needs evidence")
    return {**profile, "profile_sha256": _sha256(path)}


def unknown_profile_requirements(profile: dict[str, Any]) -> list[str]:
    requirements = profile.get("requirements")
    if not isinstance(requirements, dict):
        raise AssetQAError("profile requirements missing")
    return [key for key in REQUIREMENT_KEYS if requirements[key]["status"] == "UNKNOWN"]


def _package_base_defects(package: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    required_strings = (
        "package_id",
        "mission_id",
        "batch_id",
        "blueprint_id",
        "asset_id",
        "asset_format",
    )
    for field in required_strings:
        if not isinstance(package.get(field), str) or not package[field]:
            defects.append(_defect("PACKAGE_INVALID", f"missing {field}"))
    for field in ("blueprint_sha256", "asset_sha256"):
        if not _is_sha256(package.get(field)):
            defects.append(_defect("PACKAGE_INVALID", f"invalid {field}"))
    if package.get("platform") != platform:
        defects.append(_defect("PACKAGE_INVALID", "package platform does not match QA profile"))
    if package.get("submission_status") != "PREPARED_NOT_SUBMITTED":
        defects.append(_defect("PACKAGE_INVALID", "package must remain PREPARED_NOT_SUBMITTED"))
    if package.get("submission_authorized") is not False:
        defects.append(_defect("PACKAGE_INVALID", "QA input cannot carry submission authority"))
    megapixels = package.get("megapixels")
    if not isinstance(megapixels, (int, float)) or isinstance(megapixels, bool) or megapixels <= 0:
        defects.append(_defect("PACKAGE_INVALID", "megapixels must be positive"))
    metadata = package.get("metadata")
    if not isinstance(metadata, dict):
        defects.append(_defect("METADATA_MISSING", "metadata object is required"))
    else:
        expected = {"title", "description", "keywords", "ai_disclosure"}
        if set(metadata) != expected:
            defects.append(_defect("METADATA_INVALID", "metadata fields are incomplete or unknown"))
        if not isinstance(metadata.get("title"), str) or not isinstance(metadata.get("description"), str):
            defects.append(_defect("METADATA_INVALID", "title and description must be strings"))
        if not isinstance(metadata.get("keywords"), list) or any(not isinstance(value, str) or not value for value in metadata.get("keywords", [])):
            defects.append(_defect("METADATA_INVALID", "keywords must be non-empty strings"))
        if not isinstance(metadata.get("ai_disclosure"), bool):
            defects.append(_defect("METADATA_INVALID", "ai_disclosure must be boolean"))
    return defects


def _known_requirement_defects(package: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    reqs = profile["requirements"]
    metadata = package.get("metadata") if isinstance(package.get("metadata"), dict) else {}

    formats = reqs["accepted_formats"]
    if formats["status"] == "KNOWN":
        allowed = formats["value"]
        if not isinstance(allowed, list) or package.get("asset_format") not in allowed:
            defects.append(_defect("TECHNICAL_FORMAT_UNSUPPORTED", "asset format fails platform profile"))

    mp = reqs["minimum_megapixels"]
    if mp["status"] == "KNOWN":
        minimum = mp["value"]
        actual = package.get("megapixels")
        if not isinstance(minimum, (int, float)) or not isinstance(actual, (int, float)) or actual < minimum:
            defects.append(_defect("TECHNICAL_DIMENSION_BELOW_MINIMUM", "asset megapixels fail platform profile"))

    meta = reqs["metadata_constraints"]
    if meta["status"] == "KNOWN" and isinstance(meta["value"], dict):
        required_any = meta["value"].get("required_any", [])
        if isinstance(required_any, list) and required_any and not any(metadata.get(field) for field in required_any):
            defects.append(_defect("METADATA_MISSING", "platform profile requires metadata content"))

    ai = reqs["ai_disclosure"]
    if ai["status"] == "KNOWN" and isinstance(ai["value"], dict) and ai["value"].get("required") is True:
        if metadata.get("ai_disclosure") is not True:
            defects.append(_defect("METADATA_INVALID", "platform profile requires AI disclosure"))

    similarity = reqs["similarity_distinctness"]
    if similarity["status"] == "KNOWN" and isinstance(similarity["value"], dict) and similarity["value"].get("review_required") is True:
        if not isinstance(package.get("similarity_review_ref"), str) or not package["similarity_review_ref"]:
            defects.append(_defect("PACKAGE_INVALID", "similarity/distinctness evidence is required"))

    account = reqs["account_eligibility"]
    if account["status"] == "KNOWN" and isinstance(account["value"], dict) and account["value"].get("eligible") is not True:
        defects.append(_defect("PACKAGE_INVALID", "account is not eligible under platform profile"))

    restrictions = reqs["content_restrictions"]
    if restrictions["status"] == "KNOWN" and isinstance(restrictions["value"], dict) and restrictions["value"].get("review_required") is True:
        if not isinstance(package.get("content_review_ref"), str) or not package["content_review_ref"]:
            defects.append(_defect("PACKAGE_INVALID", "content-restriction evidence is required"))

    upload = reqs["upload_package_constraints"]
    if upload["status"] == "KNOWN" and isinstance(upload["value"], dict):
        if upload["value"].get("must_be_prepared_not_submitted") is True and package.get("submission_status") != "PREPARED_NOT_SUBMITTED":
            defects.append(_defect("PACKAGE_INVALID", "upload package state violates platform profile"))
    return defects


def evaluate_platform_preflight(
    package: dict[str, Any],
    profile_path: pathlib.Path,
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate one prepared package against a strict dated platform profile."""
    if not isinstance(package, dict):
        raise AssetQAError("package must be an object")
    profile = load_platform_profile(profile_path)
    defects = _package_base_defects(package, profile["platform"])
    unknown = unknown_profile_requirements(profile)
    for key in unknown:
        defects.append(_defect("PLATFORM_PROFILE_UNKNOWN_REQUIREMENT", f"platform requirement is UNKNOWN: {key}"))
    defects.extend(_known_requirement_defects(package, profile))
    defects = _dedupe_defects(defects)
    hard_count = sum(row["severity"] == "HARD_VETO" for row in defects)
    fail_count = sum(row["severity"] == "FAIL" for row in defects)
    review_count = sum(row["severity"] == "REVIEW_REQUIRED" for row in defects)
    state = "FAIL" if hard_count or fail_count else ("BLOCKED_REVIEW" if review_count else "PASS")
    source_hash = package.get("asset_sha256") if _is_sha256(package.get("asset_sha256")) else "0" * 64
    stamp = evaluated_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_id": f"QAREC-PLATFORM-{hashlib.sha256((str(package.get('package_id')) + profile['profile_sha256']).encode()).hexdigest()[:16].upper()}",
        "evaluated_at": stamp,
        "mission_id": str(package.get("mission_id") or "UNKNOWN"),
        "batch_id": str(package.get("batch_id") or "UNKNOWN"),
        "blueprint_id": str(package.get("blueprint_id") or "UNKNOWN"),
        **({"blueprint_sha256": package["blueprint_sha256"]} if _is_sha256(package.get("blueprint_sha256")) else {}),
        "source_manifest_sha256": hashlib.sha256(json.dumps(package, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
        "qa_scope": "PLATFORM_PREFLIGHT",
        "platform_profile": {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "effective_date": profile["effective_date"],
            "profile_sha256": profile["profile_sha256"],
        },
        "batch_state": state,
        "hard_veto": hard_count > 0,
        "defect_summary": {
            "hard_veto_count": hard_count,
            "fail_count": fail_count,
            "review_required_count": review_count,
        },
        "asset_results": [
            {
                "asset_id": str(package.get("asset_id") or "UNKNOWN"),
                "source_sha256": source_hash if source_hash != "0" * 64 else None,
                "route": "PASS" if state == "PASS" else "BLOCK_SUBMISSION",
                "defects": defects,
            }
        ],
        "package_result": {
            "state": state,
            "defects": [row["code"] for row in defects],
        },
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "hard_vetoes_waivable": False,
        },
    }
