import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"lib"))
import pattern_engine_acceptance as engine
from asset_identity import AssetIdentityInvariantError, assert_identity_invariants

FIXTURES = json.loads((ROOT/"fixtures/procedural-pattern/fixtures.v1.json").read_text())["fixtures"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda row: row["name"])
def test_complete_pattern_acceptance_and_independent_package_regeneration(tmp_path, fixture):
    a = engine.accept_fixture(fixture["request"], output_dir=tmp_path/"a")
    b = engine.accept_fixture(fixture["request"], output_dir=tmp_path/"b")
    assert a["result"] == "PASS", a
    assert a == b
    assert a["package"]["semantic_asset_count"] == 1
    assert a["package"]["derivative_count"] == 2
    assert a["package_manifest"]["semantic_asset_id"] == fixture["request"]["semantic_asset_id"]
    assert a["identity_transition"]["transition"] == "PACKAGING_VARIANT"
    assert a["native_receipt"]["master"]["native_editable"] is True
    assert a["marketplace_compatibility"] == "COMPATIBILITY_UNKNOWN"
    assert a["package"]["upload_action"] == a["package"]["publication_action"] == "NONE"


def test_qa_failure_blocks_package_even_if_producer_claims_success(tmp_path, monkeypatch):
    real = engine.produce_pattern
    def corrupt(request, *, output_dir):
        result = real(request, output_dir=output_dir)
        Path(result["pattern"]["master_path"]).write_text('<svg><image href="raster.png"/></svg>')
        return result
    monkeypatch.setattr(engine, "produce_pattern", corrupt)
    result = engine.accept_fixture(FIXTURES[0]["request"], output_dir=tmp_path/"bad")
    assert result["result"] == "FAIL"
    assert result["stage"] == "PATTERN_QA"
    assert not (tmp_path/"bad/package").exists()


def test_output_root_cannot_overwrite_existing_acceptance(tmp_path):
    root = tmp_path/"existing"
    root.mkdir()
    sentinel = root/"master.svg"
    sentinel.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        engine.accept_fixture(FIXTURES[0]["request"], output_dir=root)
    assert sentinel.read_bytes() == b"preserve"


def test_packaging_cannot_mint_new_semantic_asset():
    before = json.loads((ROOT/"fixtures/shopping-bag-blueprint-v2/pattern.json").read_text())
    after = copy.deepcopy(before)
    after["derivatives"].append({"derivative_id": "PNG", "format": "PNG", "purpose": "PREVIEW", "semantic_identity_effect": "NONE"})
    after["semantic_identity"]["semantic_asset_id"] = "FASA-FAKE-SECOND-ASSET"
    with pytest.raises(AssetIdentityInvariantError, match="PACKAGING_MINTED_SEMANTIC_ID"):
        assert_identity_invariants(before, after)
