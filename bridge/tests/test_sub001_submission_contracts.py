from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-package.v1.schema.json"
ROUTE_SCHEMA = ROOT / "company" / "schemas" / "die.asset.submission-route-state.v1.schema.json"
DOC = ROOT / "docs" / "operations" / "COMMON_SUBMISSION_PACKAGE_V1.md"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_sub001a_package_pins_all_required_provenance_hashes() -> None:
    schema = _load(PACKAGE_SCHEMA)
    assert schema["properties"]["schema_version"]["const"] == "die.asset.submission-package.v1"
    required = set(schema["required"])
    assert {
        "artifact_sha256",
        "qa_receipt_sha256",
        "qc_receipt_sha256",
        "blueprint_sha256",
        "metadata_sha256",
        "platform_profile_sha256",
        "route_id",
    } <= required
    assert schema["properties"]["initial_route_state"] == {"const": "PREPARED"}
    authority = schema["properties"]["authority_boundary"]["properties"]
    assert authority["submission_authorized"] == {"const": False}
    assert authority["publication_authorized"] == {"const": False}
    assert authority["credentials_embedded"] == {"const": False}
    assert authority["mutable_after_seal"] == {"const": False}


def test_sub001a_route_schema_distinguishes_full_external_lifecycle() -> None:
    schema = _load(ROUTE_SCHEMA)
    states = schema["properties"]["state"]["enum"]
    assert states == [
        "PREPARED",
        "AUTHORIZED",
        "SUBMITTED",
        "REVIEW_PENDING",
        "APPROVED",
        "REJECTED",
        "RECONCILED",
    ]
    assert schema["properties"]["attempt"]["minimum"] == 0
    authority = schema["properties"]["authority_boundary"]["properties"]
    assert authority["submission_action_performed"] == {"const": False}
    assert authority["publication_action_performed"] == {"const": False}
    assert authority["credential_material_present"] == {"const": False}


def test_sub001a_contract_is_packaging_only_and_does_not_grant_marketplace_authority() -> None:
    doc = DOC.read_text(encoding="utf-8")
    for marker in [
        "immutable packaging contract",
        "does not submit",
        "does not publish",
        "does not read or embed marketplace credentials",
        "Founder authority remains external",
        "PREPARED",
        "AUTHORIZED",
        "SUBMITTED",
        "REVIEW_PENDING",
        "APPROVED",
        "REJECTED",
        "RECONCILED",
    ]:
        assert marker in doc


def test_sub001a_graph_opens_only_authority_boundary_next() -> None:
    tasks = {row["id"]: row for row in _load(GRAPH)["tasks"]}
    assert tasks["SUB-001A"]["status"] in {"READY", "DONE"}
    assert tasks["SUB-001B"]["status"] in {"BLOCKED", "READY", "DONE"}
    assert tasks["SUB-001C"]["status"] in {"BLOCKED", "READY", "DONE"}
