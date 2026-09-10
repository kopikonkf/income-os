from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_equal(label: str, *values: Any) -> Any:
    clean = [v for v in values if v is not None]
    if not clean or any(v != clean[0] for v in clean[1:]):
        raise ValueError(f"ASSET_TRACE_MISMATCH:{label}")
    return clean[0]


def build_asset_operations(repo_root: Path) -> dict[str, Any]:
    base = repo_root / "company/factory-asset"
    registry = _load(base / "registries/governed-canary-assets.v1.json")
    live = _load(base / "fixtures/governed-canary/FA-202-live-result.json")
    post = _load(base / "fixtures/governed-canary/FA-204-metadata-rights-result.json")
    acceptance = _load(base / "fixtures/governed-canary/FA-206-v1-acceptance-result.json")

    record = registry["assets"][0]
    semantic_id = _require_equal(
        "semantic_asset_id",
        record.get("semantic_asset_id"), live.get("semantic_asset_id"),
        post.get("semantic_asset_id"), acceptance.get("semantic_asset_id"),
    )
    master_sha = _require_equal(
        "master_sha256",
        record.get("master_sha256"), live.get("master", {}).get("sha256"),
        post.get("master_sha256"), acceptance.get("live_hashes", {}).get("master_png", {}).get("sha256"),
    )
    metadata_sha = _require_equal(
        "metadata_sha256",
        record.get("metadata_sha256"), post.get("metadata", {}).get("metadata_sha256"),
        acceptance.get("founder_qc", {}).get("exact_hashes", {}).get("metadata_bundle"),
    )
    package_sha = _require_equal(
        "package_plan_sha256",
        record.get("package_plan_sha256"),
        post.get("package_readiness", {}).get("package_plan", {}).get("package_plan_sha256"),
        acceptance.get("founder_qc", {}).get("exact_hashes", {}).get("package_plan"),
    )

    live_hashes = acceptance["live_hashes"]
    provider_original_sha = _require_equal(
        "provider_original_sha256",
        live.get("provider_original", {}).get("sha256"), live_hashes["provider_original"]["sha256"],
    )
    derivatives = []
    for row in record.get("derivatives", []):
        derivatives.append({
            "derivative_id": row["derivative_id"],
            "format": row["format"],
            "purpose": row["purpose"],
            "sha256": row["sha256"],
            "bytes": row.get("bytes"),
            "dimensions": row.get("dimensions"),
            "recipe_id": row.get("recipe_id"),
            "qa_state": row.get("technical_qa", "UNKNOWN"),
            "compatibility_state": row.get("compatibility", "UNKNOWN"),
            "semantic_identity_effect": row.get("semantic_identity_effect", "NONE"),
        })

    metadata = post["metadata"]
    binary = post["binary_metadata"]
    rights = post["rights_signal"]
    readiness = post["package_readiness"]
    founder_qc = acceptance["founder_qc"]
    authority = acceptance["truth_boundaries"]

    exact_hashes = {
        "provider_original": provider_original_sha,
        "master": master_sha,
        "metadata_bundle": metadata_sha,
        "package_plan": package_sha,
        "listing_jpeg": binary["output_sha256"],
    }
    for row in derivatives:
        exact_hashes[f"derivative:{row['derivative_id']}"] = row["sha256"]

    content_hash_index = [
        {"sha256": sha, "semantic_asset_id": semantic_id, "role": role}
        for role, sha in exact_hashes.items()
    ]

    item = {
        "semantic_asset_id": semantic_id,
        "blueprint_id": record["blueprint_id"],
        "canonical_truth": bool(record.get("canonical_truth")),
        "provider_original": {
            "sha256": provider_original_sha,
            "bytes": live["provider_original"].get("bytes"),
            "format": live["provider_original"].get("media", {}).get("format"),
            "dimensions": [
                live["provider_original"].get("media", {}).get("width_px"),
                live["provider_original"].get("media", {}).get("height_px"),
            ],
            "immutable": bool(live["provider_original"].get("immutable_after_postprocess")),
            "provider_id": live["provider_route"].get("provider_id"),
            "cluster_id": live["provider_route"].get("cluster_id"),
            "transport": live["provider_route"].get("transport"),
        },
        "master": {
            "sha256": master_sha,
            "format": live["master"].get("format"),
            "dimensions": live["master"].get("dimensions"),
            "normalization_method": live["master"].get("lineage", {}).get("normalization_method"),
            "technical_qa": acceptance["acceptance_matrix"].get("technical_qa", "UNKNOWN"),
        },
        "derivatives": derivatives,
        "metadata": {
            "metadata_sha256": metadata_sha,
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "keywords": metadata.get("keywords", []),
            "ai_generated": metadata.get("ai_generated"),
            "ai_disclosure": metadata.get("ai_disclosure"),
            "listing_filename": metadata.get("listing_filename"),
            "delivery": metadata.get("metadata_delivery"),
            "binary_metadata_result": binary.get("result"),
            "listing_sha256": binary.get("output_sha256"),
            "iptc_readback": binary.get("iptc_readback"),
            "xmp_readback": binary.get("xmp_readback"),
            "platform_form_ai_disclosure_still_required": binary.get("platform_form_ai_disclosure_still_required"),
        },
        "qa_rights": {
            "automated_rights_signal": rights.get("result"),
            "detector_states": rights.get("detector_states", {}),
            "blocking_signals": rights.get("blocking_signals", []),
            "review_signals": rights.get("review_signals", []),
            "human_rights_clearance": bool(rights.get("human_rights_clearance")),
            "legal_clearance_claimed": bool(rights.get("legal_clearance_claimed")),
            "founder_qc_required": bool(readiness.get("founder_qc_required")),
            "founder_qc_decision": founder_qc.get("decision", "UNKNOWN"),
        },
        "package": {
            "state": readiness.get("result"),
            "blockers": readiness.get("blockers", []),
            "package_plan_sha256": package_sha,
            "marketplace": record.get("package_compatibility", {}).get("marketplace"),
            "marketplace_delivery_derivative_id": record.get("package_compatibility", {}).get("marketplace_delivery_derivative_id"),
        },
        "lineage": {
            "provider_original_sha256": provider_original_sha,
            "master_sha256": master_sha,
            "metadata_sha256": metadata_sha,
            "package_plan_sha256": package_sha,
            "registry_revision": registry.get("revision"),
            "state_history": registry.get("history", []),
        },
        "authority": {
            "submission_authorized": bool(authority.get("submission_authorized")),
            "publication_authorized": bool(authority.get("publication_authorized")),
            "marketplace_upload": bool(authority.get("marketplace_upload")),
            "provider_calls_performed": bool(authority.get("provider_calls_performed")),
            "spend_usd": authority.get("spend_usd", 0),
        },
        "exact_hashes": exact_hashes,
        "evidence_refs": [
            "company/factory-asset/fixtures/governed-canary/FA-202-live-result.json",
            "company/factory-asset/registries/governed-canary-assets.v1.json",
            "company/factory-asset/fixtures/governed-canary/FA-204-metadata-rights-result.json",
            "company/factory-asset/fixtures/governed-canary/FA-206-v1-acceptance-result.json",
        ],
    }
    return {
        "schema": "die.factory-asset.console-asset-operations.v1",
        "mode": "READ_ONLY_CANONICAL_TRACE",
        "evidence_mode": "GOVERNED_CANARY_FA202_FA206",
        "asset_count": 1,
        "derivative_count": len(derivatives),
        "assets": [item],
        "content_hash_index": content_hash_index,
        "authority": item["authority"],
    }


