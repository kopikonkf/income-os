from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "bridge" / "income_os_bridge"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


UP = load("up001_engine_test", BRIDGE / "asset_upscale.py")
META = load("meta001_engine_test", BRIDGE / "asset_metadata.py")
RIGHTS = load("rights001_engine_test", BRIDGE / "rights_preflight.py")
sys.path.insert(0, str(ROOT / 'bridge'))
from income_os_bridge import asset_qa as ASSET_QA


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def make_png(path: Path, width: int, height: int) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    # One transparent RGBA row repeated; valid enough for standard decoders too.
    raw = b"".join(b"\x00" + b"\x00\x00\x00\x00" * width for _ in range(height))
    path.write_bytes(signature + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", zlib.compress(raw)) + png_chunk(b"IEND", b""))


def test_up001_noop_is_first_class_and_preserves_hash(tmp_path: Path) -> None:
    src = tmp_path / "source.png"
    make_png(src, 2048, 2048)
    policy = {
        "schema": UP.POLICY_SCHEMA, "engine": "test", "model_name": "x4", "model_path": str(tmp_path / "missing.pth"),
        "model_sha256": "0" * 64, "scale": 4, "tile": 512, "tile_pad": 10, "pre_pad": 0, "half": False, "gpu_id": None,
        "backend_argv": [sys.executable],
    }
    rec = UP.process(source=src, output=tmp_path / "out.png", policy=policy, min_width=1024, min_height=1024, min_megapixels=1)
    assert rec["status"] == "PASS"
    assert rec["action"] == "NO_OP"
    assert rec["transformed"] is False
    assert rec["source"]["sha256"] == rec["output"]["sha256"]


def test_up001_rights_failure_is_never_recovered(tmp_path: Path) -> None:
    src = tmp_path / "source.png"
    make_png(src, 64, 64)
    policy = {
        "schema": UP.POLICY_SCHEMA, "engine": "test", "model_name": "x4", "model_path": str(tmp_path / "missing.pth"),
        "model_sha256": "0" * 64, "scale": 4, "tile": 512, "tile_pad": 10, "pre_pad": 0, "half": False, "gpu_id": None,
        "backend_argv": [sys.executable],
    }
    rec = UP.process(source=src, output=tmp_path / "out.png", policy=policy, min_width=1024, min_height=1024, min_megapixels=1, rights_state="FAIL")
    assert rec["status"] == "BLOCKED_RIGHTS_SAFETY"
    assert rec["authority_boundary"]["rights_or_safety_recoverable"] is False


def test_up001_model_hash_and_x4_lineage_are_enforced(tmp_path: Path) -> None:
    src = tmp_path / "source.png"
    make_png(src, 8, 6)
    model = tmp_path / "model.pth"
    model.write_bytes(b"pinned-model")
    backend = tmp_path / "backend.py"
    backend.write_text(
        "import struct,sys,zlib\n"
        "def c(k,d): return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)\n"
        "w,h=32,24; hdr=struct.pack('>IIBBBBB',w,h,8,6,0,0,0); raw=b''.join(b'\\0'+b'\\0\\0\\0\\0'*w for _ in range(h)); "
        "open(sys.argv[2],'wb').write(b'\\x89PNG\\r\\n\\x1a\\n'+c(b'IHDR',hdr)+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b''))\n",
        encoding="utf-8",
    )
    policy = {
        "schema": UP.POLICY_SCHEMA, "engine": "fake", "model_name": "x4", "model_path": str(model),
        "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(), "scale": 4, "tile": 512, "tile_pad": 10, "pre_pad": 0,
        "half": False, "gpu_id": None, "backend_argv": [sys.executable, str(backend), "{input}", "{output}", "{model}"],
    }
    out = tmp_path / "out.png"
    rec = UP.process(source=src, output=out, policy=policy, min_width=100, min_height=100, min_megapixels=1)
    assert rec["status"] == "PASS"
    assert rec["action"] == "UPSCALE_X4"
    assert (rec["output"]["width"], rec["output"]["height"]) == (32, 24)
    assert rec["checks"]["x4_dimensions"] is True
    assert rec["model"]["sha256"] == policy["model_sha256"]


def blueprint() -> dict:
    return {
        "blueprint_id": "BP-TEST-001",
        "metadata_direction": {
            "title_direction": "Describe practical cable organization and remote-work desk utility without keyword stuffing.",
            "primary_keywords": ["cable organizer", "desk organization", "remote work"],
            "secondary_keywords": ["cable management", "home office", "workspace utility", "organized desk"],
            "category_direction": ["business", "technology", "objects"],
        },
    }


def authored(bp: dict) -> dict:
    return {
        "schema": "die.division001.asset-metadata-authoring.v1",
        "author_principal_id": "division-head-division01",
        "blueprint_id": bp["blueprint_id"],
        "blueprint_sha256": META.canonical_sha256(bp),
        "title": "Practical Cable Organizer for Remote Work Desk",
        "description": "A practical cable organizer showing clear desk organization utility for a remote work setup.",
        "primary_keywords": ["cable organizer", "desk organization", "remote work"],
        "secondary_keywords": ["cable management", "home office", "workspace utility"],
        "categories": ["business", "technology", "objects"],
        "ai_disclosure": "Generative AI content",
    }


def test_meta001_compiler_cannot_invent_keywords_or_bypass_division_authority() -> None:
    bp = blueprint()
    a = authored(bp)
    compiled = META.compile_metadata(bp, a)
    assert compiled["semantic_author"] == "division-head-division01"
    assert compiled["semantic_content_invented_by_engine"] is False
    bad = dict(a)
    bad["primary_keywords"] = a["primary_keywords"] + ["invented commercial keyword"]
    with pytest.raises(META.MetadataError, match="E_PRIMARY_KEYWORD_INVENTED"):
        META.compile_metadata(bp, bad)
    bad_author = dict(a)
    bad_author["author_principal_id"] = "worker-001"
    with pytest.raises(META.MetadataError, match="E_SEMANTIC_AUTHORITY"):
        META.compile_metadata(bp, bad_author)


def test_meta001_png_sidecar_embed_readback_and_final_hash(tmp_path: Path) -> None:
    bp = blueprint()
    metadata = META.compile_metadata(bp, authored(bp))
    src = tmp_path / "source.png"
    out = tmp_path / "final.png"
    sidecar = tmp_path / "final.metadata.json"
    make_png(src, 16, 16)
    receipt = META.inject(src, out, sidecar, metadata)
    assert receipt["readback_verified"] is True
    assert receipt["lineage_hash_changed"] is True
    assert receipt["output_sha256"] == META.sha256(out)
    assert META.read_back(out)["keywords"] == metadata["keywords"]
    assert json.loads(sidecar.read_text())["metadata"]["title"] == metadata["title"]


def test_meta001_jpeg_writes_xmp_and_iptc_iim_and_preflight(tmp_path: Path) -> None:
    bp = blueprint()
    metadata = META.compile_metadata(bp, authored(bp))
    src = tmp_path / "source.jpg"
    # Minimal SOI/EOI stream is sufficient for deterministic segment/readback testing.
    src.write_bytes(b"\xff\xd8\xff\xd9")
    out = tmp_path / "final.jpg"
    sidecar = tmp_path / "final.metadata.json"
    receipt = META.inject(src, out, sidecar, metadata)
    assert receipt["embedded"] == ["IPTC-IIM", "XMP"]
    raw = out.read_bytes()
    assert b"Photoshop 3.0\x00" in raw
    assert META.XMP_HEADER in raw
    assert META.platform_preflight(metadata, max_title=200, max_keywords=49, require_ai_disclosure=True)["status"] == "PASS"


def rights_evidence(asset: Path, **overrides):
    base = {
        "artifact_path": str(asset),
        "artifact_sha256": RIGHTS.sha256(asset),
        "extracted_text": [],
        "protected_terms": ["acmebrand", "fictionalmark"],
        "allowed_terms": [],
        "detector_findings": [],
        "human_visual_review": {"state": "CLEAR", "reviewer": "bounded-visual-review", "evidence_ref": "review://1"},
        "release_evidence": {"required": False, "state": "NOT_REQUIRED", "refs": []},
        "source_lineage_clear": True,
    }
    base.update(overrides)
    return base


def test_rights001_clear_requires_complete_evidence(tmp_path: Path) -> None:
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"asset")
    receipt = RIGHTS.evaluate(rights_evidence(asset))
    assert receipt["state"] == "CLEAR"
    assert receipt["legal_clearance_claimed"] is False
    assert receipt["authority_boundary"]["qa_hard_veto_waivable"] is False


def test_rights001_brand_text_fails_and_uncertain_visual_maps_to_qa_hard_veto(tmp_path: Path) -> None:
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"asset")
    failed = RIGHTS.evaluate(rights_evidence(asset, extracted_text=["AcmeBrandÂ®"]))
    assert failed["state"] == "FAIL"
    states = RIGHTS.qa_review_states(failed)
    defects = ASSET_QA._review_defects(states)
    assert any(x["code"] == "RIGHTS_FAILED" and x["severity"] == "HARD_VETO" for x in defects)

    unclear = RIGHTS.evaluate(rights_evidence(asset, human_visual_review={"state": "NOT_REVIEWED", "reviewer": "none", "evidence_ref": "review://pending"}))
    assert unclear["state"] == "UNCLEAR"
    defects = ASSET_QA._review_defects(RIGHTS.qa_review_states(unclear))
    assert any(x["code"] == "RIGHTS_UNCLEAR" and x["severity"] == "HARD_VETO" for x in defects)



def test_meta001_platform_mapping_uses_canonical_qa_profile_and_fails_closed_on_unknown_contract() -> None:
    bp = blueprint()
    metadata = META.compile_metadata(bp, authored(bp))
    profile = json.loads((ROOT / "company/contracts/qa-platform-profiles/adobe-stock.v1.json").read_text())
    mapped = META.platform_mapping_preflight(metadata, profile)
    assert mapped["platform"] == "Adobe Stock"
    assert mapped["semantic_content_invented_by_engine"] is False
    assert mapped["status"] == "PASS"
    unknown = json.loads(json.dumps(profile))
    unknown["requirements"]["metadata_constraints"] = {"status": "UNKNOWN", "value": None, "evidence_refs": []}
    blocked = META.platform_mapping_preflight(metadata, unknown)
    assert blocked["status"] == "BLOCKED_UNKNOWN_REQUIREMENT"
    assert "metadata_constraints" in blocked["unknown_requirements"]
