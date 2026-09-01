"""Hash-pinned, role-scoped runtime canon projection.

The projection reads only an explicit repository allowlist and returns bounded
decision facts. Runtime principals never receive raw files, paths outside the
repository, Git tools, or a new MCP surface.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from . import config, snapshot

MANIFEST_SCHEMA = "die.runtime.canon-context.manifest.v1"
CONTEXT_SCHEMA = "die.runtime.canon-context.v1"
PROFILE_ID = "m001-runtime-canon-v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
FACT_LABELS = {"VERIFIED", "OBSERVED", "INFERRED", "HYPOTHESIS", "UNKNOWN"}
CLASSIFICATIONS = {"CANON", "SUPPORTING_INPUT"}

ALLOWED_DOCUMENTS = {
    "pipeline": "docs/pipeline/DIGITAL_INCOME_PIPELINE_CANON.md",
    "atlas": "company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md",
    "atlas_crossjoin_complement": "company/atlas/human-centric/CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md",
    "blueprint": "docs/missions/M001_BLUEPRINT_BATCH1_V2.md",
    "platform_matrix": "docs/pipeline/MATRIX_6_PLATFORM_TOS_STRICTNESS.md",
    "quantity_workbook": "docs/atlas/SCENARIO_1B_QUANTITY_GAME.xlsx",
    "production_playbook": "company/operations/PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md",
}
DOCUMENT_CLASSIFICATIONS = {
    "pipeline": "CANON",
    "atlas": "CANON",
    "atlas_crossjoin_complement": "CANON",
    "blueprint": "CANON",
    "platform_matrix": "SUPPORTING_INPUT",
    "quantity_workbook": "SUPPORTING_INPUT",
    "production_playbook": "CANON",
}
SUPPORTED_PRINCIPALS = {
    "chatgpt-plus-executive": "company_portfolio",
    "division-head-division01": "single_division",
    "die-lnx-executive-001": "company_portfolio",
    "die-lnx-division-001": "single_division",
}
PRINCIPAL_PROFILE_BINDINGS = {
    "chatgpt-plus-executive": "chatgpt-plus-executive",
    "die-lnx-executive-001": "chatgpt-plus-executive",
    "division-head-division01": "division-head-division01",
    "die-lnx-division-001": "division-head-division01",
}


class CanonContextError(snapshot.SnapshotError):
    """A fail-closed runtime canon projection error."""


def _utc(value: dt.datetime | None = None) -> dt.datetime:
    value = value or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _iso(value: dt.datetime | None = None) -> str:
    return _utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _bounded_repo_path(root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise CanonContextError("E_CANON_INVALID", "canon source path is not bounded")
    resolved_root = root.resolve()
    resolved = (resolved_root / Path(*posix.parts)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CanonContextError(
            "E_CANON_INVALID",
            "canon source path escapes the repository root",
        ) from exc
    return resolved


def _validate_fact(row: Any, known_doc_ids: set[str], where: str) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) != {
        "fact_id",
        "label",
        "statement",
        "source_doc_ids",
    }:
        raise CanonContextError("E_CANON_INVALID", f"{where} has invalid fields")
    if not isinstance(row["fact_id"], str) or not row["fact_id"].strip():
        raise CanonContextError("E_CANON_INVALID", f"{where}.fact_id is invalid")
    if row["label"] not in FACT_LABELS:
        raise CanonContextError("E_CANON_INVALID", f"{where}.label is invalid")
    if not isinstance(row["statement"], str) or not row["statement"].strip():
        raise CanonContextError("E_CANON_INVALID", f"{where}.statement is invalid")
    sources = row["source_doc_ids"]
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(item, str) or item not in known_doc_ids for item in sources)
    ):
        raise CanonContextError("E_CANON_INVALID", f"{where}.source_doc_ids is invalid")
    return json.loads(json.dumps(row, ensure_ascii=False))


def _git_directory(root: Path) -> Path:
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        try:
            marker = dot_git.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise CanonContextError(
                "E_CANON_REPO_REVISION",
                "repository metadata is unreadable",
            ) from exc
        if not marker.startswith("gitdir: "):
            raise CanonContextError(
                "E_CANON_REPO_REVISION",
                "repository metadata pointer is invalid",
            )
        return (root / marker.removeprefix("gitdir: ")).resolve()
    raise CanonContextError(
        "E_CANON_REPO_REVISION",
        "repository revision is unavailable",
    )


def _git_ref(git_dir: Path, ref: str) -> str:
    ref_path = git_dir.joinpath(*PurePosixPath(ref).parts)
    if ref_path.is_file():
        return ref_path.read_text(encoding="ascii").strip()
    packed = git_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="ascii").splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            sha, _, name = line.partition(" ")
            if name == ref:
                return sha
    raise CanonContextError(
        "E_CANON_REPO_REVISION",
        "repository HEAD reference is unavailable",
    )


def _repository_revision(root: Path) -> dict[str, str]:
    configured = os.environ.get("DIE_REPO_SHA")
    if configured is not None:
        value = configured.strip().lower()
        if not GIT_SHA.fullmatch(value):
            raise CanonContextError(
                "E_CANON_REPO_REVISION",
                "DIE_REPO_SHA must be a full 40-character commit SHA",
            )
        return {"sha": value, "source": "DIE_REPO_SHA"}

    git_dir = _git_directory(root)
    try:
        head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
    except OSError as exc:
        raise CanonContextError(
            "E_CANON_REPO_REVISION",
            "repository HEAD is unreadable",
        ) from exc
    value = _git_ref(git_dir, head.removeprefix("ref: ")) if head.startswith("ref: ") else head
    value = value.lower()
    if not GIT_SHA.fullmatch(value):
        raise CanonContextError(
            "E_CANON_REPO_REVISION",
            "repository HEAD is not a full commit SHA",
        )
    return {"sha": value, "source": "git-head"}


def _load_manifest(
    root: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        raise CanonContextError("E_CANON_UNAVAILABLE", "canon manifest is unavailable") from exc
    if len(raw) > config.CANON_MANIFEST_MAX_BYTES:
        raise CanonContextError("E_CANON_INVALID", "canon manifest exceeds its byte limit")
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonContextError("E_CANON_INVALID", "canon manifest is invalid JSON") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "profile_id",
        "status",
        "source_documents",
        "common_facts",
        "matrix_digest",
        "workbook_digest",
        "principal_profiles",
    }:
        raise CanonContextError("E_CANON_INVALID", "canon manifest fields are invalid")
    if (
        manifest["schema_version"] != MANIFEST_SCHEMA
        or manifest["profile_id"] != PROFILE_ID
        or manifest["status"] != "GOVERNED"
    ):
        raise CanonContextError("E_CANON_INVALID", "canon manifest identity is invalid")

    rows = manifest["source_documents"]
    if not isinstance(rows, list) or len(rows) != len(ALLOWED_DOCUMENTS):
        raise CanonContextError("E_CANON_INVALID", "canon source registry is incomplete")
    documents: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "doc_id",
            "path",
            "sha256",
            "classification",
        }:
            raise CanonContextError(
                "E_CANON_INVALID",
                f"source_documents[{index}] has invalid fields",
            )
        doc_id = row["doc_id"]
        expected_path = ALLOWED_DOCUMENTS.get(doc_id)
        if expected_path is None or row["path"] != expected_path or doc_id in documents:
            raise CanonContextError("E_CANON_INVALID", "canon source is not allowlisted")
        if (
            row["classification"] not in CLASSIFICATIONS
            or row["classification"] != DOCUMENT_CLASSIFICATIONS[doc_id]
            or not SHA256.fullmatch(row["sha256"])
        ):
            raise CanonContextError("E_CANON_INVALID", "canon source metadata is invalid")
        source_path = _bounded_repo_path(root, row["path"])
        try:
            source_bytes = source_path.read_bytes()
        except OSError as exc:
            raise CanonContextError(
                "E_CANON_UNAVAILABLE",
                f"canon source is unavailable: {doc_id}",
            ) from exc
        actual = _digest(source_bytes)
        if actual != row["sha256"]:
            raise CanonContextError(
                "E_CANON_HASH_MISMATCH",
                f"canon source hash mismatch: {doc_id}",
            )
        documents[doc_id] = dict(row)
    if set(documents) != set(ALLOWED_DOCUMENTS):
        raise CanonContextError("E_CANON_INVALID", "canon source registry is incomplete")

    known = set(documents)
    facts = manifest["common_facts"]
    if not isinstance(facts, list) or not facts:
        raise CanonContextError("E_CANON_INVALID", "common_facts must be non-empty")
    manifest["common_facts"] = [
        _validate_fact(row, known, f"common_facts[{index}]")
        for index, row in enumerate(facts)
    ]

    profiles = manifest["principal_profiles"]
    semantic_profiles = set(PRINCIPAL_PROFILE_BINDINGS.values())
    if not isinstance(profiles, dict) or set(profiles) != semantic_profiles:
        raise CanonContextError("E_CANON_INVALID", "principal_profiles are invalid")
    for principal_id in sorted(semantic_profiles):
        expected_scope = SUPPORTED_PRINCIPALS[principal_id]
        profile = profiles[principal_id]
        if not isinstance(profile, dict) or set(profile) != {
            "scope",
            "required_doc_ids",
            "supporting_doc_ids",
            "role_facts",
        }:
            raise CanonContextError("E_CANON_INVALID", "principal profile fields are invalid")
        required = profile["required_doc_ids"]
        supporting = profile["supporting_doc_ids"]
        if (
            profile["scope"] != expected_scope
            or required != ["pipeline", "atlas", "atlas_crossjoin_complement", "blueprint", "production_playbook"]
            or supporting != ["platform_matrix", "quantity_workbook"]
        ):
            raise CanonContextError("E_CANON_INVALID", "principal canon routing is invalid")
        role_facts = profile["role_facts"]
        if not isinstance(role_facts, list) or not role_facts:
            raise CanonContextError("E_CANON_INVALID", "role_facts must be non-empty")
        profile["role_facts"] = [
            _validate_fact(row, known, f"{principal_id}.role_facts[{index}]")
            for index, row in enumerate(role_facts)
        ]

    matrix = manifest["matrix_digest"]
    workbook = manifest["workbook_digest"]
    if not isinstance(matrix, dict) or set(matrix) != {
        "classification",
        "checked_date",
        "marketplaces",
        "recovery_service",
        "acceptance_estimate_status",
        "contract_rule",
    }:
        raise CanonContextError("E_CANON_INVALID", "matrix digest fields are invalid")
    try:
        dt.date.fromisoformat(matrix["checked_date"])
    except (TypeError, ValueError) as exc:
        raise CanonContextError("E_CANON_INVALID", "matrix checked_date is invalid") from exc
    if (
        matrix["classification"] != "SUPPORTING_INPUT"
        or matrix["marketplaces"] != [
            "Adobe Stock",
            "Dreamstime",
            "123RF",
            "Vecteezy",
            "MotionElements",
        ]
        or matrix["recovery_service"] != "Magnific"
        or matrix["acceptance_estimate_status"] != "HYPOTHESIS"
        or not isinstance(matrix["contract_rule"], str)
        or not matrix["contract_rule"].strip()
    ):
        raise CanonContextError("E_CANON_INVALID", "matrix digest classification is invalid")
    if not isinstance(workbook, dict) or set(workbook) != {
        "classification",
        "model_status",
        "projection_horizon_years",
        "initial_marketplaces",
        "assumed_gross_royalty_usd_per_license",
        "assumed_licenses_per_100_asset_days_per_marketplace",
        "gross_usd_per_asset_day_initial_cohort",
        "gross_usd_per_asset_day_surface_equivalent",
        "gross_usd_per_asset_day_hybrid_proxy",
        "month_36_inventory_surface_equivalent_case",
        "month_36_cumulative_gross_usd_surface_equivalent_case",
        "non_claims",
    }:
        raise CanonContextError("E_CANON_INVALID", "workbook digest fields are invalid")
    numeric_fields = {
        "projection_horizon_years",
        "initial_marketplaces",
        "assumed_gross_royalty_usd_per_license",
        "assumed_licenses_per_100_asset_days_per_marketplace",
        "gross_usd_per_asset_day_initial_cohort",
        "gross_usd_per_asset_day_surface_equivalent",
        "gross_usd_per_asset_day_hybrid_proxy",
        "month_36_inventory_surface_equivalent_case",
        "month_36_cumulative_gross_usd_surface_equivalent_case",
    }
    if (
        workbook["classification"] != "HYPOTHESIS"
        or workbook["model_status"] != "FORMULA_MECHANICS_PASS"
        or any(
            isinstance(workbook[field], bool)
            or not isinstance(workbook[field], (int, float))
            or workbook[field] < 0
            for field in numeric_fields
        )
        or not isinstance(workbook["non_claims"], list)
        or workbook["non_claims"] != [
            "not observed ERVA",
            "not net profit",
            "not annualized run-rate",
            "not proof of $1B/3Y feasibility",
            "not execution authority",
        ]
    ):
        raise CanonContextError("E_CANON_INVALID", "workbook digest classification is invalid")
    return manifest, documents, _digest(raw)


def build_surface(
    granted: dict[str, Any],
    *,
    now: dt.datetime | None = None,
    root: str | Path | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    principal_id = granted.get("principal_id")
    expected_scope = SUPPORTED_PRINCIPALS.get(principal_id)
    if expected_scope is None or granted.get("scope") != expected_scope:
        raise CanonContextError(
            "E_CANON_SCOPE_DENIED",
            "runtime principal has no canon context profile",
        )

    repo_root = Path(root) if root is not None else config.DIE_HOME
    expected_manifest = _bounded_repo_path(
        repo_root,
        "company/runtime-canon-context-v1.json",
    )
    resolved_manifest = Path(manifest_path).resolve() if manifest_path is not None else expected_manifest
    if resolved_manifest != expected_manifest:
        raise CanonContextError("E_CANON_INVALID", "canon manifest path is not allowlisted")
    manifest, documents, manifest_sha = _load_manifest(repo_root, resolved_manifest)
    role_profile_id = PRINCIPAL_PROFILE_BINDINGS[principal_id]
    profile = manifest["principal_profiles"][role_profile_id]

    def projected(doc_id: str) -> dict[str, Any]:
        row = documents[doc_id]
        return {
            "doc_id": doc_id,
            "path": row["path"],
            "sha256": row["sha256"],
            "classification": row["classification"],
            "load_status": "VERIFIED",
        }

    required = [projected(doc_id) for doc_id in profile["required_doc_ids"]]
    supporting = [projected(doc_id) for doc_id in profile["supporting_doc_ids"]]
    generated_at = _iso(now)
    data = {
        "schema_version": CONTEXT_SCHEMA,
        "profile_id": manifest["profile_id"],
        "principal_id": principal_id,
        "scope": expected_scope,
        "repository": _repository_revision(repo_root),
        "manifest": {
            "path": "company/runtime-canon-context-v1.json",
            "sha256": manifest_sha,
            "status": manifest["status"],
        },
        "load_status": "VERIFIED",
        "generated_at": generated_at,
        "required_documents": required,
        "supporting_documents": supporting,
        "decision_facts": manifest["common_facts"] + profile["role_facts"],
        "matrix_digest": manifest["matrix_digest"],
        "workbook_digest": manifest["workbook_digest"],
        "receipt_contract": {
            "required_fields": [
                "principal_id",
                "repository.sha",
                "required_documents",
                "snapshot_id",
                "freshness.created_at",
                "probe_results",
                "verdict",
            ],
            "verdicts": ["PASS", "FAIL"],
            "rule": "Live transport is insufficient; PASS requires this VERIFIED canon context inside the fresh signed snapshot.",
        },
    }
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > config.CANON_CONTEXT_MAX_BYTES:
        raise CanonContextError("E_CANON_TOO_LARGE", "canon context exceeds its byte limit")

    sources = [
        f"repo:{row['path']}@sha256:{row['sha256']}"
        for row in required + supporting
    ]
    sources.append(
        f"repo:company/runtime-canon-context-v1.json@sha256:{manifest_sha}"
    )
    return {
        "surface": "canon_context",
        "as_of": generated_at,
        "completeness": "complete",
        "source_trust": "VERIFIED",
        "sources": sources,
        "notes": [
            "allowlisted structured projection; raw document content is not exposed",
            "current mission truth remains in the other signed semantic surfaces",
        ],
        "data": data,
    }
