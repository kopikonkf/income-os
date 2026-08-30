from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "operations" / "ASSET_QA_ENGINE_V1.md"
CORE = ROOT / "bridge" / "income_os_bridge" / "m001_asset_qa.py"
SCHEMA = ROOT / "company" / "schemas" / "die.asset.qa.v1.schema.json"
TAXONOMY = ROOT / "company" / "contracts" / "die.asset.qa-taxonomy.v1.json"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_qa001a_promotes_existing_core_without_expanding_authority() -> None:
    assert CORE.is_file()
    code = CORE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    for marker in [
        "source_sha256 mismatch",
        "QUARANTINE_RIGHTS",
        "QUARANTINE_SAFETY",
        "REVIEW_REQUIRED",
        "exact duplicate binary",
        '"submission_authorized": False',
        '"publication_authorized": False',
        '"hard_vetoes_waivable": False',
    ]:
        assert marker in code
    assert "promoting, not rewriting" not in doc.lower()  # wording is contractual, not a slogan
    assert "Promote the existing M-001 deterministic raster QA" in doc
    assert "It is not subjective visual/commercial QC" in doc
    assert "never grants submission or publication authority" in doc


def test_qa001b_schema_covers_required_defect_families_and_authority_boundary() -> None:
    schema = _load(SCHEMA)
    assert schema["properties"]["schema_version"]["const"] == "die.asset.qa.v1"
    item = schema["properties"]["asset_results"]["items"]
    defect_codes = set(item["properties"]["defects"]["items"]["properties"]["code"]["enum"])
    expected = {
        "INTEGRITY_FILE_MISSING",
        "INTEGRITY_HASH_MISMATCH",
        "LINEAGE_MISSING",
        "LINEAGE_MISMATCH",
        "TECHNICAL_FORMAT_UNSUPPORTED",
        "RIGHTS_UNCLEAR",
        "RIGHTS_FAILED",
        "SAFETY_UNCLEAR",
        "SAFETY_FAILED",
        "WATERMARK_UNCLEAR",
        "WATERMARK_PRESENT",
        "DUPLICATE_ASSET_ID",
        "DUPLICATE_BINARY",
        "METADATA_MISSING",
        "METADATA_INVALID",
        "PACKAGE_INVALID",
        "PLATFORM_PROFILE_UNKNOWN_REQUIREMENT",
        "REVIEW_REQUIRED_VISUAL",
    }
    assert expected <= defect_codes
    authority = schema["properties"]["authority_boundary"]["properties"]
    assert authority["submission_authorized"] == {"const": False}
    assert authority["publication_authorized"] == {"const": False}
    assert authority["hard_vetoes_waivable"] == {"const": False}


def test_taxonomy_declares_hard_veto_and_review_required_semantics() -> None:
    taxonomy = _load(TAXONOMY)
    defects = taxonomy["defects"]
    for code in [
        "INTEGRITY_FILE_MISSING",
        "INTEGRITY_HASH_MISMATCH",
        "LINEAGE_MISSING",
        "LINEAGE_MISMATCH",
        "RIGHTS_UNCLEAR",
        "RIGHTS_FAILED",
        "SAFETY_UNCLEAR",
        "SAFETY_FAILED",
        "WATERMARK_UNCLEAR",
        "WATERMARK_PRESENT",
        "PACKAGE_INVALID",
        "PLATFORM_PROFILE_UNKNOWN_REQUIREMENT",
    ]:
        assert defects[code] == "HARD_VETO"
    assert defects["REVIEW_REQUIRED_VISUAL"] == "REVIEW_REQUIRED"
    assert taxonomy["authority_boundary"] == {
        "submission_authorized": False,
        "publication_authorized": False,
        "hard_vetoes_waivable": False,
    }


def test_task_graph_keeps_qa_contract_batch_closed_as_children_advance() -> None:
    tasks = {row["id"]: row for row in _load(GRAPH)["tasks"]}
    assert tasks["QA-001A"]["status"] == "DONE"
    assert tasks["QA-001B"]["status"] == "DONE"
    assert tasks["QA-001C"]["status"] in {"READY", "DONE"}
    assert tasks["QA-001D"]["status"] in {"READY", "DONE"}
