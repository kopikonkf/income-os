import copy
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import jsonschema
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"lib"))
from procedural_pattern import produce_pattern
from pattern_qa import verify_pattern

FIXTURES = json.loads((ROOT/"fixtures/procedural-pattern/fixtures.v1.json").read_text())["fixtures"]
SCHEMA = json.loads((ROOT/"schemas/pattern-qa.schema.json").read_text())
NS = "{http://www.w3.org/2000/svg}"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate(tmp_path, index=0):
    request = copy.deepcopy(FIXTURES[index]["request"])
    return request, produce_pattern(request, output_dir=tmp_path/"produced")


def reseal(production):
    """Let adversarial fixtures claim matching hashes; QA must inspect content."""
    master = Path(production["pattern"]["master_path"]).read_bytes()
    png = Path(production["preview"]["path"]).read_bytes()
    sha = digest(master)
    production["pattern"]["master_sha256"] = sha
    production["native_receipt"]["master"].update(sha256=sha, bytes=len(master))
    production["preview"].update(source_master_sha256=sha, sha256=digest(png), bytes=len(png))
    receipt = production["native_receipt"]
    base = {k:v for k,v in receipt.items() if k != "deterministic_receipt_sha256"}
    receipt["deterministic_receipt_sha256"] = digest(json.dumps(base,sort_keys=True,separators=(",",":")).encode())


def edit_master(production, edit):
    path = Path(production["pattern"]["master_path"])
    root = ET.fromstring(path.read_bytes())
    edit(root)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    path.write_bytes(ET.tostring(root))
    reseal(production)


def assert_failed(receipt, code=None):
    jsonschema.Draft202012Validator(SCHEMA).validate(receipt)
    assert receipt["result"] == "FAIL"
    assert receipt["compatibility"]["state"] == "INCOMPATIBLE"
    assert receipt["marketplace_compatibility"] == "COMPATIBILITY_UNKNOWN"
    assert "FAIL" in receipt["checks"].values()
    if code:
        assert receipt["failures"][0]["code"] == code


@pytest.mark.parametrize("index", [0,1])
def test_canonical_fixture_edges_bounds_editability_render_and_preview(tmp_path,index):
    request, production = generate(tmp_path,index)
    paths = [Path(production["pattern"]["master_path"]), Path(production["preview"]["path"])]
    before = [(p.read_bytes(),p.stat().st_mtime_ns) for p in paths]
    result = verify_pattern(request,production)
    assert result["result"] == "PASS", result
    assert all(v=="PASS" for v in result["checks"].values())
    assert result["compatibility"] == {"scope":"FA032_PATTERN_TILE","state":"COMPATIBLE"}
    assert result["marketplace_compatibility"] == "COMPATIBILITY_UNKNOWN"
    assert result["semantic_identity_effect"] == "NONE"
    assert result == verify_pattern(request,production)
    assert result["input"]["semantic_asset_id"] == request["semantic_asset_id"]
    assert before == [(p.read_bytes(),p.stat().st_mtime_ns) for p in paths]
    jsonschema.Draft202012Validator(SCHEMA).validate(result)


@pytest.mark.parametrize("tag", ["image","text","script","foreignObject","use"])
def test_raster_font_script_and_external_masquerades_fail_closed(tmp_path,tag):
    req, production = generate(tmp_path)
    def edit(root):
        root[1].tag=NS+tag
        root[1].set("href","https://invalid.example/never-fetch")
    edit_master(production,edit)
    assert_failed(verify_pattern(req,production),"NON_EDITABLE_CONTENT")


@pytest.mark.parametrize("attribute,value", [("transform","translate(4 0)"),
    ("style","fill:red"),("onclick","alert(1)"),("fill","url(https://invalid.example/fill)"),
    ("stroke","#000000")])
def test_unsupported_svg_styles_never_silently_render(tmp_path,attribute,value):
    req, production=generate(tmp_path)
    edit_master(production, lambda root: root[1].set(attribute,value))
    assert_failed(verify_pattern(req,production))


@pytest.mark.parametrize("path", ["M 1 1 C 2 2 3 3 4 4 Z",
    "M 1 1 L 2 2 L 3 3 L 1 1 Z", "M 1 1 L 3 1 L 3 3 L 1 3 Z",
    "M 1e309 1 L 3 1 L 3 3 L 1e309 1 Z"])
def test_invalid_or_unsupported_paths_rejected(tmp_path,path):
    req, production=generate(tmp_path)
    edit_master(production, lambda root: root[1].set("d",path))
    assert_failed(verify_pattern(req,production))


def test_broken_seam_rejected_even_with_resealed_hashes(tmp_path):
    req, production=generate(tmp_path)
    edit_master(production,lambda root:root[1].set("d","M 9 31 L 18 40 L 9 49 L 0 40 L 9 31 Z"))
    result=verify_pattern(req,production)
    assert_failed(result,"BROKEN_SEAM")
    assert result["checks"]["tile_bounds"]=="PASS"


@pytest.mark.parametrize("change,code", [
    (lambda root: root.set("viewBox","0 0 64 64"),"VIEWBOX_MISMATCH"),
    (lambda root: root[1].set("d","M 0 31 L 9 40 L 0 49 L -9 40 L 0 31 Z"),"PATH_OUT_OF_BOUNDS"),
    (lambda root: root[0].set("d","M 0 0 L 127 0 L 127 128 L 0 128 L 0 0 Z"),"BACKGROUND_MISMATCH"),
    (lambda root: root.remove(root[-1]),"PATH_COUNT_MISMATCH"),
])
def test_tile_and_repeat_geometry_fail_closed(tmp_path,change,code):
    req, production=generate(tmp_path)
    edit_master(production,change)
    assert_failed(verify_pattern(req,production),code)


def test_preview_pixel_drift_with_correct_hash_is_rejected(tmp_path):
    req,production=generate(tmp_path)
    path=Path(production["preview"]["path"])
    with Image.open(path) as image:
        image.load(); image.putpixel((130,2),(255,0,255)); image.save(path)
    reseal(production)
    result=verify_pattern(req,production)
    assert_failed(result,"PREVIEW_INCONSISTENT")
    assert result["checks"]["renderability"]=="PASS"


def test_repeated_but_wrong_tile_preview_is_rejected(tmp_path):
    req,production=generate(tmp_path)
    Image.new("RGB",(384,384),"white").save(production["preview"]["path"])
    reseal(production)
    assert_failed(verify_pattern(req,production),"PREVIEW_INCONSISTENT")


@pytest.mark.parametrize("mutation,code", [
    (lambda p:p["preview"].update(repeat=[1,1]),"PREVIEW_SPEC_MISMATCH"),
    (lambda p:p["preview"].update(dimensions=[1,1]),"PREVIEW_SPEC_MISMATCH"),
    (lambda p:p["pattern"].update(master_sha256="0"*64),"MASTER_HASH_MISMATCH"),
    (lambda p:p["preview"].update(sha256="0"*64),"PREVIEW_HASH_MISMATCH"),
    (lambda p:p["native_receipt"].update(job_id="DIFFERENT-JOB"),"LINEAGE_MISMATCH"),
])
def test_receipt_lineage_and_preview_pins_are_verified(tmp_path,mutation,code):
    req,production=generate(tmp_path)
    mutation(production)
    assert_failed(verify_pattern(req,production),code)


def test_missing_preview_has_no_fabricated_qa_pass(tmp_path):
    req,production=generate(tmp_path)
    Path(production["preview"]["path"]).unlink()
    assert_failed(verify_pattern(req,production))


def test_dtd_is_rejected_without_xml_resolution(tmp_path):
    req,production=generate(tmp_path)
    p=Path(production["pattern"]["master_path"])
    p.write_bytes(b'<!DOCTYPE svg [<!ENTITY hidden "payload">]>'+p.read_bytes())
    reseal(production)
    assert_failed(verify_pattern(req,production),"UNSAFE_XML")


def test_resource_budget_blocks_before_read_or_render(tmp_path):
    req,production=generate(tmp_path)
    req["parameters"].update(tile_width=2048,tile_height=2048,preview_repeat=8)
    assert_failed(verify_pattern(req,production),"RESOURCE_LIMIT")


def test_schema_cannot_certify_partial_checks():
    receipt={"schema":"die.factory-asset.pattern-qa.v1","result":"PASS",
      "input":{"semantic_asset_id":"FASA-EXAMPLE","job_id":"EXAMPLE-JOB","master_sha256":"a"*64,"preview_sha256":"b"*64},
      "checks":dict.fromkeys(["lineage","editable_paths","tile_bounds","seams","renderability","preview_consistency"],"PASS"),
      "failures":[],"compatibility":{"scope":"FA032_PATTERN_TILE","state":"COMPATIBLE"},
      "marketplace_compatibility":"COMPATIBILITY_UNKNOWN","semantic_identity_effect":"NONE"}
    receipt["checks"]["seams"]="NOT_RUN"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(receipt)
