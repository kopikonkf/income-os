from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def compose_submission_dry_run(
    *,
    submission_package: dict[str, Any],
    metadata: dict[str, Any],
    platform_mapping: dict[str, Any],
    artifact_filename: str,
) -> dict[str, Any]:
    """Compose a deterministic, side-effect-free submission plan.

    The result describes files/metadata/actions an adapter may later consume. It
    never logs in, submits, publishes, reads credentials, or grants authority.
    """
    required_package = {
        "schema_version",
        "package_id",
        "asset_id",
        "artifact_sha256",
        "metadata_sha256",
        "platform_profile_sha256",
        "route_id",
        "initial_route_state",
        "authority_boundary",
    }
    missing = sorted(required_package - set(submission_package))
    if missing:
        raise ValueError(f"submission package missing required fields: {', '.join(missing)}")
    if submission_package["schema_version"] != "die.asset.submission-package.v1":
        raise ValueError("unsupported submission package schema")
    if submission_package["initial_route_state"] != "PREPARED":
        raise ValueError("dry-run composer requires PREPARED package")
    boundary = submission_package.get("authority_boundary", {})
    if any(
        boundary.get(field) is not False
        for field in ("submission_authorized", "publication_authorized", "credentials_embedded", "mutable_after_seal")
    ):
        raise ValueError("submission package authority boundary is not fail-closed")
    if not artifact_filename or artifact_filename != artifact_filename.strip() or "/" in artifact_filename or "\\" in artifact_filename:
        raise ValueError("artifact_filename must be one normalized basename")
    if platform_mapping.get("status") != "PASS":
        raise ValueError("platform metadata mapping must be PASS before dry-run composition")
    mapped_fields = platform_mapping.get("mapped_fields")
    if not isinstance(mapped_fields, dict) or not mapped_fields:
        raise ValueError("platform metadata mapping must contain mapped_fields")

    observed_metadata_sha256 = sha256_json(metadata)
    if observed_metadata_sha256 != submission_package["metadata_sha256"]:
        raise ValueError("metadata hash differs from immutable submission package pin")

    package_copy = deepcopy(submission_package)
    mapped_copy = deepcopy(mapped_fields)
    mapping_copy = deepcopy(platform_mapping)
    package_sha256 = sha256_json(package_copy)
    platform_mapping_sha256 = sha256_json(mapping_copy)

    planned_actions = [
        {"sequence": 1, "action": "ATTACH_ARTIFACT", "target": artifact_filename, "external": False},
        {"sequence": 2, "action": "APPLY_MAPPED_METADATA", "target": "submission_form", "external": False},
        {"sequence": 3, "action": "STOP_BEFORE_SUBMISSION", "target": "founder_authority_gate", "external": False},
    ]
    lineage = {
        "submission_package_sha256": package_sha256,
        "artifact_sha256": submission_package["artifact_sha256"],
        "metadata_sha256": observed_metadata_sha256,
        "platform_profile_sha256": submission_package["platform_profile_sha256"],
        "platform_mapping_sha256": platform_mapping_sha256,
    }
    composition_material = {
        "schema_version": "die.asset.submission-dry-run.v1",
        "package_id": submission_package["package_id"],
        "asset_id": submission_package["asset_id"],
        "route_id": submission_package["route_id"],
        "artifact": {"filename": artifact_filename, "sha256": submission_package["artifact_sha256"]},
        "metadata": mapped_copy,
        "planned_actions": planned_actions,
        "lineage": lineage,
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "credential_access_required": False,
            "external_action_performed": False,
            "dry_run_only": True,
        },
    }
    composition_sha256 = sha256_json(composition_material)
    return {**composition_material, "composition_sha256": composition_sha256}
