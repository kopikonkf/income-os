from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import zlib

import pytest

from income_os_bridge import asset_qa, m001_asset_qa

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROFILES = ROOT / "company" / "contracts" / "qa-platform-profiles"
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _asset(workspace: pathlib.Path, asset_id: str, *, rights="PASS", visual=True) -> dict:
    path = workspace / "assets" / f"{asset_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png(10, 10))
    reviews = {}
    for name in ("rights", "safety", "watermark", "lineage", "technical", "visual"):
        if name == "visual" and not visual:
            continue
        evidence = workspace / "evidence" / f"{asset_id}-{name}.json"
        _write_json(evidence, {"review": name})
        reviews[name] = {
            "state": rights if name == "rights" else "PASS",
            "evidence_ref": evidence.relative_to(workspace).as_posix(),
        }
    return {
        "asset_id": asset_id,
        "blueprint_id": "BP-QA",
        "candidate_id": "C-QA",
        "master_id": "MASTER-13",
        "engine": "chatgpt",
        "generated_at": "2026-08-30T00:00:00Z",
        "source_path": path.relative_to(workspace).as_posix(),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "prompt_hash": "a" * 64,
        "reviews": reviews,
    }


def _manifest(workspace: pathlib.Path, assets: list[dict]) -> pathlib.Path:
    path = workspace / "manifest.json"
    _write_json(
        path,
        {
            "schema_version": m001_asset_qa.MANIFEST_SCHEMA,
            "batch_id": "BATCH-QA",
            "blueprint_id": "BP-QA",
            "candidate_id": "C-QA",
            "master_id": "MASTER-13",
            "technical_requirements": {"min_megapixels": 0.0001, "allowed_formats": ["PNG"]},
            "assets": assets,
        },
    )
    return path


def _known_profile(path: pathlib.Path) -> pathlib.Path:
    req = lambda value: {"status": "KNOWN", "value": value, "evidence_refs": ["FIXTURE"]}
    _write_json(
        path,
        {
            "schema_version": asset_qa.PLATFORM_PROFILE_SCHEMA,
            "profile_id": "QAPROFILE-DREAMSTIME-V99",
            "platform": "Dreamstime",
            "profile_version": 99,
            "effective_date": "2026-08-30",
            "checked_at": "2026-08-30",
            "source_document": "fixture-only",
            "requirements": {
                "accepted_formats": req(["JPEG"]),
                "minimum_megapixels": req(3),
                "metadata_constraints": req({"required_any": ["title", "description"]}),
                "ai_disclosure": req({"required": True}),
                "similarity_distinctness": req({"review_required": True}),
                "account_eligibility": req({"eligible": True}),
                "content_restrictions": req({"review_required": True}),
                "upload_package_constraints": req({"must_be_prepared_not_submitted": True}),
            },
        },
    )
    return path


def _package() -> dict:
    return {
        "package_id": "PKG-QA-1",
        "mission_id": "M-001",
        "batch_id": "BATCH-QA",
        "blueprint_id": "BP-QA",
        "blueprint_sha256": "b" * 64,
        "asset_id": "ASSET-QA-1",
        "asset_sha256": "c" * 64,
        "asset_format": "JPEG",
        "megapixels": 4,
        "platform": "Dreamstime",
        "metadata": {
            "title": "Useful isolated object",
            "description": "AI-generated utility raster for fixture validation",
            "keywords": ["utility", "object"],
            "ai_disclosure": True,
        },
        "similarity_review_ref": "evidence/similarity.json",
        "content_review_ref": "evidence/content.json",
        "submission_status": "PREPARED_NOT_SUBMITTED",
        "submission_authorized": False,
    }


def test_m001_compatibility_adapter_preserves_pass_and_route(tmp_path: pathlib.Path) -> None:
    manifest = _manifest(tmp_path, [_asset(tmp_path, "A-1")])
    legacy = m001_asset_qa.evaluate_manifest(manifest, tmp_path, min_assets=1, max_assets=1)
    promoted = asset_qa.evaluate_m001_manifest(manifest, tmp_path, min_assets=1, max_assets=1)
    assert legacy["batch_state"] == promoted["batch_state"] == "PASS"
    assert legacy["routes"][0]["route"] == "T1_PASS"
    assert promoted["asset_results"][0]["route"] == "PASS"
    assert promoted["qa_scope"] == "UNIVERSAL"
    assert promoted["authority_boundary"] == {
        "submission_authorized": False,
        "publication_authorized": False,
        "hard_vetoes_waivable": False,
    }


def test_m001_promotion_maps_rights_hard_veto_and_visual_review(tmp_path: pathlib.Path) -> None:
    rights_manifest = _manifest(tmp_path, [_asset(tmp_path, "A-R", rights="FAIL")])
    rights = asset_qa.evaluate_m001_manifest(rights_manifest, tmp_path, min_assets=1, max_assets=1)
    assert rights["batch_state"] == "FAIL"
    assert rights["hard_veto"] is True
    assert "RIGHTS_FAILED" in {d["code"] for d in rights["asset_results"][0]["defects"]}

    visual_manifest = _manifest(tmp_path, [_asset(tmp_path, "A-V", visual=False)])
    visual = asset_qa.evaluate_m001_manifest(visual_manifest, tmp_path, min_assets=1, max_assets=1)
    assert visual["batch_state"] == "BLOCKED_REVIEW"
    assert visual["hard_veto"] is False
    assert "REVIEW_REQUIRED_VISUAL" in {d["code"] for d in visual["asset_results"][0]["defects"]}


def test_m001_promotion_preserves_corrupt_and_duplicate_failures(tmp_path: pathlib.Path) -> None:
    corrupt = _asset(tmp_path, "A-C")
    source = tmp_path / corrupt["source_path"]
    source.write_bytes(b"not-png")
    corrupt["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    receipt = asset_qa.evaluate_m001_manifest(_manifest(tmp_path, [corrupt]), tmp_path, min_assets=1, max_assets=1)
    assert receipt["batch_state"] == "FAIL"
    assert "INTEGRITY_RASTER_CORRUPT" in {d["code"] for d in receipt["asset_results"][0]["defects"]}

    first = _asset(tmp_path, "A-D")
    second = dict(first)
    second["asset_id"] = "A-D-2"
    duplicate = asset_qa.evaluate_m001_manifest(_manifest(tmp_path, [first, second]), tmp_path, min_assets=2, max_assets=2)
    assert duplicate["batch_state"] == "FAIL"
    assert duplicate["asset_results"][1]["route"] == "T1_MARKET_FIT_FAIL"
    assert "DUPLICATE_BINARY" in {d["code"] for d in duplicate["asset_results"][1]["defects"]}


def test_canonical_marketplace_profiles_are_dated_versioned_and_fail_closed() -> None:
    files = sorted(PROFILES.glob("*.json"))
    assert {p.name for p in files} == {
        "123rf.v1.json",
        "adobe-stock.v1.json",
        "dreamstime.v1.json",
        "motionelements.v1.json",
        "vecteezy.v1.json",
    }
    for path in files:
        profile = asset_qa.load_platform_profile(path)
        assert profile["profile_version"] == 1
        assert profile["effective_date"] == "2026-08-24"
        assert profile["checked_at"] == "2026-08-24"
        assert profile["platform"] != "Magnific"
        assert asset_qa.unknown_profile_requirements(profile)


def test_unknown_profile_requirement_blocks_before_submission() -> None:
    package = _package()
    receipt = asset_qa.evaluate_platform_preflight(package, PROFILES / "dreamstime.v1.json", evaluated_at="2026-08-30T00:00:00+00:00")
    assert receipt["batch_state"] == "FAIL"
    assert receipt["hard_veto"] is True
    assert receipt["asset_results"][0]["route"] == "BLOCK_SUBMISSION"
    assert "PLATFORM_PROFILE_UNKNOWN_REQUIREMENT" in receipt["package_result"]["defects"]
    assert receipt["authority_boundary"]["submission_authorized"] is False


def test_strict_profile_rejects_unknown_fields(tmp_path: pathlib.Path) -> None:
    profile_path = _known_profile(tmp_path / "profile.json")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["invented_requirement"] = True
    _write_json(profile_path, profile)
    with pytest.raises(asset_qa.AssetQAError, match="profile fields invalid"):
        asset_qa.load_platform_profile(profile_path)


def test_platform_package_preflight_passes_known_fixture_and_fails_metadata(tmp_path: pathlib.Path) -> None:
    profile = _known_profile(tmp_path / "profile.json")
    package = _package()
    passed = asset_qa.evaluate_platform_preflight(package, profile, evaluated_at="2026-08-30T00:00:00+00:00")
    assert passed["batch_state"] == "PASS"
    assert passed["hard_veto"] is False
    assert passed["package_result"] == {"state": "PASS", "defects": []}
    assert passed["platform_profile"]["profile_version"] == 99
    assert passed["authority_boundary"]["submission_authorized"] is False

    package["metadata"]["ai_disclosure"] = False
    failed = asset_qa.evaluate_platform_preflight(package, profile, evaluated_at="2026-08-30T00:00:00+00:00")
    assert failed["batch_state"] == "FAIL"
    assert "METADATA_INVALID" in failed["package_result"]["defects"]

def test_cli_platform_preflight_writes_receipt_and_fails_closed(tmp_path: pathlib.Path) -> None:
    package_path = tmp_path / "package.json"
    output_path = tmp_path / "receipt.json"
    _write_json(package_path, _package())
    command = [
        sys.executable,
        str(ROOT / "bin" / "die_asset_qa.py"),
        "platform-preflight",
        "--package",
        str(package_path),
        "--profile",
        str(PROFILES / "dreamstime.v1.json"),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 3
    receipt = json.loads(output_path.read_text(encoding="utf-8"))
    assert receipt["batch_state"] == "FAIL"
    assert receipt["hard_veto"] is True
    assert receipt["authority_boundary"]["submission_authorized"] is False
    assert "PLATFORM_PROFILE_UNKNOWN_REQUIREMENT" in receipt["package_result"]["defects"]

