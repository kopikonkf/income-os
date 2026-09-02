from __future__ import annotations

import json
from pathlib import Path

import pytest

from income_os_bridge.submission_dry_run import compose_submission_dry_run, sha256_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-dry-run.v1.schema.json"
FIXTURE = ROOT / "company" / "muxia" / "fixtures" / "SUB-001D-dry-run.fixture.json"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
DOC = ROOT / "docs" / "operations" / "SUBMISSION_DRY_RUN_COMPOSER_V1.md"


def _inputs():
    metadata = {
        "schema": "die.asset.metadata.v1",
        "title": "Practical Shopping Bag for Customer Order Packing",
        "description": "A clean shopping bag visual for small-business customer order packing workflows.",
        "keywords": ["shopping bag", "customer orders", "small business", "packing"],
        "ai_disclosure": "Generative AI content",
    }
    package = {
        "schema_version": "die.asset.submission-package.v1",
        "package_id": "SUBPKG-SUB001D01",
        "created_at": "2026-09-02T17:00:00Z",
        "mission_id": "MISSION-SUB001D01",
        "asset_id": "ASSET-SUB001D01",
        "artifact_sha256": "a" * 64,
        "qa_receipt_sha256": "b" * 64,
        "qc_receipt_sha256": "c" * 64,
        "blueprint_sha256": "d" * 64,
        "metadata_sha256": sha256_json(metadata),
        "platform_profile_sha256": "e" * 64,
        "route_id": "ROUTE-SUB001D01",
        "initial_route_state": "PREPARED",
        "authority_boundary": {"submission_authorized": False, "publication_authorized": False, "credentials_embedded": False, "mutable_after_seal": False},
    }
    mapping = {
        "schema": "die.asset.metadata-platform-map.v1",
        "platform": "DRY_RUN_REFERENCE",
        "profile_id": "QAPROFILE-DRY-RUN-V1",
        "status": "PASS",
        "mapped_fields": {"title": metadata["title"], "description": metadata["description"], "keywords": metadata["keywords"], "ai_disclosure": metadata["ai_disclosure"]},
        "failures": [], "unknown_requirements": [], "semantic_content_invented_by_engine": False,
    }
    return package, metadata, mapping


def test_sub001d_composer_is_deterministic_and_pins_lineage() -> None:
    package, metadata, mapping = _inputs()
    first = compose_submission_dry_run(submission_package=package, metadata=metadata, platform_mapping=mapping, artifact_filename="shopping-bag.png")
    second = compose_submission_dry_run(submission_package=package, metadata=metadata, platform_mapping=mapping, artifact_filename="shopping-bag.png")
    assert first == second
    assert first["composition_sha256"] == second["composition_sha256"]
    assert first["lineage"]["metadata_sha256"] == package["metadata_sha256"]
    assert first["lineage"]["artifact_sha256"] == package["artifact_sha256"]
    assert first["lineage"]["platform_profile_sha256"] == package["platform_profile_sha256"]


def test_sub001d_outputs_platform_ready_metadata_and_actions_but_stops_before_submit() -> None:
    package, metadata, mapping = _inputs()
    result = compose_submission_dry_run(submission_package=package, metadata=metadata, platform_mapping=mapping, artifact_filename="shopping-bag.png")
    assert result["metadata"] == mapping["mapped_fields"]
    assert [x["action"] for x in result["planned_actions"]] == ["ATTACH_ARTIFACT", "APPLY_MAPPED_METADATA", "STOP_BEFORE_SUBMISSION"]
    assert all(x["external"] is False for x in result["planned_actions"])
    assert result["authority_boundary"] == {"submission_authorized": False, "publication_authorized": False, "credential_access_required": False, "external_action_performed": False, "dry_run_only": True}


def test_sub001d_hash_mismatch_and_nonpass_mapping_fail_closed() -> None:
    package, metadata, mapping = _inputs()
    bad_package = dict(package, metadata_sha256="f" * 64)
    with pytest.raises(ValueError, match="metadata hash"):
        compose_submission_dry_run(submission_package=bad_package, metadata=metadata, platform_mapping=mapping, artifact_filename="shopping-bag.png")
    bad_mapping = dict(mapping, status="UNKNOWN")
    with pytest.raises(ValueError, match="mapping must be PASS"):
        compose_submission_dry_run(submission_package=package, metadata=metadata, platform_mapping=bad_mapping, artifact_filename="shopping-bag.png")


def test_sub001d_fixture_exactly_reproduces_composer_output() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    output = compose_submission_dry_run(submission_package=fixture["inputs"]["submission_package"], metadata=fixture["inputs"]["metadata"], platform_mapping=fixture["inputs"]["platform_mapping"], artifact_filename=fixture["inputs"]["artifact_filename"])
    assert output == fixture["expected"]


def test_sub001d_schema_doc_and_graph_keep_dry_run_boundary() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    boundary = schema["properties"]["authority_boundary"]["properties"]
    assert boundary["external_action_performed"] == {"const": False}
    assert boundary["dry_run_only"] == {"const": True}
    doc = DOC.read_text(encoding="utf-8")
    for marker in ["deterministic", "STOP_BEFORE_SUBMISSION", "no marketplace login", "no credential access", "does not grant submission authority"]:
        assert marker in doc
    tasks = {x["id"]: x for x in json.loads(GRAPH.read_text(encoding="utf-8"))["tasks"]}
    assert tasks["SUB-001C"]["status"] == "DONE"
    assert tasks["SUB-001D"]["status"] in {"READY", "DONE"}
    assert tasks["SUB-001E"]["status"] in {"BLOCKED", "READY", "DONE"}
