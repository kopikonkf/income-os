from __future__ import annotations

import hashlib
import json
import re
from typing import Any


class AssetIdentityInvariantError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def semantic_identity_material(blueprint: dict[str, Any]) -> dict[str, Any]:
    semantic = blueprint["semantic_identity"]
    return {
        "asset_type": blueprint["asset_type"],
        "commercial_use_case": _normalize_text(semantic["commercial_use_case"]),
        "intent": semantic["intent"],
        "subject": _normalize_text(semantic["subject"]),
    }


def semantic_fingerprint(blueprint: dict[str, Any]) -> str:
    return _sha256(semantic_identity_material(blueprint))


def packaging_identity_material(blueprint: dict[str, Any]) -> dict[str, Any]:
    derivatives = sorted(
        [dict(row) for row in blueprint.get("derivatives", [])],
        key=lambda row: (row.get("derivative_id", ""), row.get("purpose", ""), row.get("format", "")),
    )
    policy = blueprint.get("policy", {})
    return {
        "master_spec": dict(blueprint.get("master_spec", {})),
        "derivatives": derivatives,
        "marketplace_profiles": sorted(policy.get("marketplace_profiles", [])),
        "compatibility_state": policy.get("compatibility_state"),
    }


def packaging_fingerprint(blueprint: dict[str, Any]) -> str:
    return _sha256(packaging_identity_material(blueprint))


def classify_identity_transition(before: dict[str, Any], after: dict[str, Any]) -> str:
    semantic_same = semantic_fingerprint(before) == semantic_fingerprint(after)
    packaging_same = packaging_fingerprint(before) == packaging_fingerprint(after)
    if semantic_same and packaging_same:
        return "IDENTICAL"
    if semantic_same:
        return "PACKAGING_VARIANT"
    return "SEMANTIC_VARIANT"


def assert_identity_invariants(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_semantic_id = before["semantic_identity"]["semantic_asset_id"]
    after_semantic_id = after["semantic_identity"]["semantic_asset_id"]
    before_blueprint_id = before["blueprint_id"]
    after_blueprint_id = after["blueprint_id"]
    before_semantic_fp = semantic_fingerprint(before)
    after_semantic_fp = semantic_fingerprint(after)
    transition = classify_identity_transition(before, after)

    if before_semantic_fp == after_semantic_fp:
        if before_semantic_id != after_semantic_id:
            raise AssetIdentityInvariantError(
                "PACKAGING_MINTED_SEMANTIC_ID",
                "format/resolution/derivative/marketplace packaging changes must retain semantic_asset_id",
            )
    else:
        if before_semantic_id == after_semantic_id:
            raise AssetIdentityInvariantError(
                "SEMANTIC_ID_REUSED_FOR_DISTINCT_WORK",
                "a changed commercial use case/subject/intent/asset_type requires a new semantic_asset_id",
            )
        if before_blueprint_id == after_blueprint_id:
            raise AssetIdentityInvariantError(
                "DISTINCT_USE_CASE_REQUIRES_SEPARATE_BLUEPRINT",
                "a semantic variant requires a separate blueprint_id",
            )

    for row in after.get("derivatives", []):
        if row.get("semantic_identity_effect") != "NONE":
            raise AssetIdentityInvariantError(
                "DERIVATIVE_CHANGED_SEMANTIC_IDENTITY",
                f"derivative {row.get('derivative_id')} must have semantic_identity_effect=NONE",
            )

    return {
        "schema": "die.factory-asset.asset-identity-transition.v1",
        "transition": transition,
        "before": {
            "blueprint_id": before_blueprint_id,
            "semantic_asset_id": before_semantic_id,
            "semantic_fingerprint": before_semantic_fp,
            "packaging_fingerprint": packaging_fingerprint(before),
        },
        "after": {
            "blueprint_id": after_blueprint_id,
            "semantic_asset_id": after_semantic_id,
            "semantic_fingerprint": after_semantic_fp,
            "packaging_fingerprint": packaging_fingerprint(after),
        },
        "packaging_variants_create_new_semantic_asset": False,
    }