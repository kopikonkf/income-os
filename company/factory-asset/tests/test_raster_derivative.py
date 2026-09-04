import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
pytest.importorskip("fcntl", reason="FA-021 acceptance requires Linux flock")
import raster_derivative as worker


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(path, mode="RGBA", tagged=True):
    image = Image.new(mode, (8, 6), (220, 40, 70, 128) if mode == "RGBA" else (220, 40, 70))
    if mode == "RGBA":
        image.putpixel((0, 0), (255, 0, 0, 0))
        image.putpixel((1, 0), (0, 0, 255, 255))
    info = PngImagePlugin.PngInfo()
    if tagged:
        info.add(b"sRGB", b"\x00")
    info.add_text("Comment", "must not propagate")
    image.save(path, pnginfo=info)
    return path


def recipe(master, fmt="JPEG", alpha="FLATTEN_WHITE"):
    output = {"format": fmt, "purpose": "MARKETPLACE_DELIVERY",
              "width_px": 8, "height_px": 6, "color_space": "SRGB",
              "alpha_policy": alpha, "semantic_identity_effect": "NONE"}
    if fmt != "TIFF":
        output["quality"] = 92
    return {
        "schema": "die.factory-asset.derivative-recipe.v1",
        "recipe_id": "raster-test-v1", "recipe_version": "1.0.0",
        "input": {"master_sha256": sha(master.read_bytes()), "semantic_asset_id": "FASA-TEST_ASSET", "format": "PNG"},
        "output": output,
        "marketplace_profile": {"platform_id": "ADOBE_STOCK", "profile_revision": "1.0"},
        "idempotency": {"key_material": ["master_sha256", "recipe_id", "recipe_version",
                        "marketplace_profile.platform_id", "marketplace_profile.profile_revision", "output"],
                        "output_collision_action": "VERIFY_HASH_AND_REUSE_OR_FAIL"},
        "qa": {"magic_mime_match": True, "decode_reopen": True, "sha256": True, "dimensions_if_raster": True},
        "compatibility": {"unknown_action": "BLOCK_PACKAGE", "require_profile_match": True},
    }


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP", "TIFF"])
def test_deterministic_decodable_durable_receipts_and_master_unchanged(tmp_path, fmt):
    master = source(tmp_path / "master.png")
    before = master.read_bytes(), master.stat().st_mtime_ns
    r = recipe(master, fmt)
    first = worker.convert(master, r, tmp_path / "a")
    second = worker.convert(master, r, tmp_path / "b")
    artifact = Path(first["artifact_path"])
    assert artifact.read_bytes() == Path(second["artifact_path"]).read_bytes()
    receipt = first["receipt"]
    schema = json.loads((ROOT / "schemas/derivative-receipt.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(receipt)
    assert receipt == json.loads(Path(first["receipt_path"]).read_text())
    assert receipt["output"]["sha256"] == sha(artifact.read_bytes())
    assert receipt["output"]["bytes"] == artifact.stat().st_size
    assert receipt["input"]["semantic_asset_id"] == r["input"]["semantic_asset_id"]
    assert receipt["output"]["semantic_identity_effect"] == "NONE"
    assert all(receipt["qa"][k] for k in ("magic_mime_match", "decode_reopen", "sha256_verified"))
    assert receipt["result"] == "FAIL"
    assert receipt["compatibility"]["state"] == "COMPATIBILITY_UNKNOWN"
    with Image.open(artifact) as decoded:
        decoded.load()
        assert decoded.format == fmt and decoded.size == (8, 6)
        assert "A" not in decoded.getbands()
        assert "Comment" not in decoded.info and "icc_profile" not in decoded.info
    stamps = {p.name: (p.stat().st_ino, p.stat().st_mtime_ns) for p in artifact.parent.iterdir()}
    assert worker.convert(master, r, tmp_path / "a")["conversion_status"] == "REUSED"
    assert stamps == {p.name: (p.stat().st_ino, p.stat().st_mtime_ns) for p in artifact.parent.iterdir()}
    assert (master.read_bytes(), master.stat().st_mtime_ns) == before


@pytest.mark.parametrize("fmt", ["WEBP", "TIFF"])
def test_preserve_alpha_values_and_resize(tmp_path, fmt):
    master = source(tmp_path / "master.png")
    r = recipe(master, fmt, "PRESERVE")
    r["output"].update(width_px=4, height_px=3)
    result = worker.convert(master, r, tmp_path / "out")
    with Image.open(master) as original, Image.open(result["artifact_path"]) as output:
        expected = original.convert("RGBA").resize((4, 3), Image.Resampling.LANCZOS)
        assert output.size == (4, 3)
        assert output.convert("RGBA").getchannel("A").tobytes() == expected.getchannel("A").tobytes()


def test_flatten_white_pixel_values_are_explicit(tmp_path):
    master = source(tmp_path / "master.png")
    result = worker.convert(master, recipe(master, "TIFF"), tmp_path / "out")
    with Image.open(result["artifact_path"]) as output:
        assert output.getpixel((0, 0)) == (255, 255, 255)
        assert output.getpixel((1, 0)) == (0, 0, 255)
        assert output.getpixel((2, 0)) == (237, 147, 162)


def test_forbid_accepts_rgb_and_rejects_alpha(tmp_path):
    rgb = source(tmp_path / "rgb.png", "RGB")
    worker.convert(rgb, recipe(rgb, "TIFF", "FORBID"), tmp_path / "out")
    rgba = source(tmp_path / "rgba.png")
    with pytest.raises(worker.RasterDerivativeError, match="ALPHA_FORBIDDEN"):
        worker.convert(rgba, recipe(rgba, "TIFF", "FORBID"), tmp_path / "never")
    assert not (tmp_path / "never").exists()


@pytest.mark.parametrize("change,code", [
    (lambda r: r["input"].update(master_sha256="0" * 64), "MASTER_HASH_MISMATCH"),
    (lambda r: r["input"].update(format="JPEG"), "INPUT_FORMAT_UNSUPPORTED"),
    (lambda r: r["output"].update(format="PDF"), "OUTPUT_FORMAT_UNSUPPORTED"),
    (lambda r: r["output"].update(alpha_policy="PRESERVE"), "ALPHA_FORMAT_CONFLICT"),
    (lambda r: r["output"].pop("alpha_policy"), "RECIPE_INCOMPLETE"),
    (lambda r: r["output"].pop("quality"), "RECIPE_INCOMPLETE"),
    (lambda r: r["output"].update(width_px=0), "SCHEMA_INVALID"),
    (lambda r: r["output"].update(width_px=100_000_000), "OUTPUT_TOO_LARGE"),
    (lambda r: r["output"].update(color_space="DISPLAY_P3"), "COLOR_POLICY_UNSUPPORTED"),
    (lambda r: r["output"].update(semantic_identity_effect="NEW_ASSET"), "SCHEMA_INVALID"),
    (lambda r: r.update(recipe_version="2.0.0"), "RECIPE_VERSION_UNSUPPORTED"),
    (lambda r: r["marketplace_profile"].update(profile_revision="9.9"), "PROFILE_REVISION_MISMATCH"),
    (lambda r: r["marketplace_profile"].update(platform_id="UNKNOWN"), "PROFILE_UNKNOWN"),
])
def test_rejects_invalid_pins_and_specs_before_output(tmp_path, change, code):
    master = source(tmp_path / "master.png")
    r = recipe(master)
    change(r)
    with pytest.raises(worker.RasterDerivativeError, match=code):
        worker.convert(master, r, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("kind,code", [("untagged", "COLOR_EVIDENCE_REQUIRED"),
                                     ("fake", "MASTER_MAGIC_MISMATCH"), ("truncated", "MASTER_DECODE_FAILED")])
def test_invalid_master_never_produces_artifacts(tmp_path, kind, code):
    master = source(tmp_path / "master.png", tagged=kind != "untagged")
    if kind == "fake":
        master.write_bytes(b"not an image")
    if kind == "truncated":
        master.write_bytes(master.read_bytes()[:40])
    with pytest.raises(worker.RasterDerivativeError, match=code):
        worker.convert(master, recipe(master), tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("target", ["artifact", "receipt", "manifest", "symlink", "partial"])
def test_collision_does_not_overwrite_or_repair(tmp_path, target):
    master = source(tmp_path / "master.png")
    r = recipe(master)
    result = worker.convert(master, r, tmp_path / "out")
    folder = Path(result["artifact_path"]).parent
    file = folder / {"artifact": "derivative.jpg", "receipt": "receipt.json",
                     "manifest": "manifest.json", "symlink": "derivative.jpg", "partial": "receipt.json"}[target]
    if target == "symlink":
        file.unlink()
        file.symlink_to(master)
    elif target == "partial":
        file.unlink()
    else:
        file.write_bytes(b"existing unrelated content")
    master_before = master.read_bytes()
    snapshot = {p.name: p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(worker.RasterDerivativeError, match="OUTPUT_COLLISION"):
        worker.convert(master, r, tmp_path / "out")
    assert snapshot == {p.name: p.read_bytes() for p in folder.iterdir()}
    assert master.read_bytes() == master_before


def test_parallel_duplicate_ownership_has_one_creator(tmp_path):
    master = source(tmp_path / "master.png")
    r = recipe(master, "TIFF")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: worker.convert(master, r, tmp_path / "out"), range(4)))
    assert sorted(x["conversion_status"] for x in results) == ["CREATED", "REUSED", "REUSED", "REUSED"]
    assert len({x["artifact_path"] for x in results}) == 1
    assert not list((tmp_path / "out").glob(".fa021-*"))


def test_failed_staging_leaves_no_published_output(tmp_path, monkeypatch):
    master = source(tmp_path / "master.png")
    def failed_write(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(worker, "_write", failed_write)
    with pytest.raises(worker.RasterDerivativeError, match="IO_ERROR.*simulated disk failure"):
        worker.convert(master, recipe(master), tmp_path / "out")
    assert [p.name for p in (tmp_path / "out").iterdir()] == [".fa021.lock"]


def test_cli_reports_conversion_and_separate_package_block(tmp_path):
    master = source(tmp_path / "master.png")
    path = tmp_path / "recipe.json"
    path.write_text(json.dumps(recipe(master)))
    command = [sys.executable, str(ROOT / "bin/derive_raster.py"), "--master", str(master),
               "--recipe", str(path), "--output-root", str(tmp_path / "out")]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    body = json.loads(first.stdout)
    assert body["conversion_status"] == "CREATED" and body["receipt"]["result"] == "FAIL"
    again = subprocess.run(command, capture_output=True, text=True)
    assert again.returncode == 0 and json.loads(again.stdout)["conversion_status"] == "REUSED"
    master.write_bytes(b"corrupted")
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode == 2
    body = json.loads(failed.stdout)
    assert body["code"] == "MASTER_HASH_MISMATCH"
    assert "receipt" not in body and "artifact_path" not in body


def test_palette_transparency_is_not_silently_discarded(tmp_path):
    master = tmp_path / "palette.png"
    image = Image.new("P", (8, 6), 0)
    image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
    image.putpixel((1, 0), 1)
    info = PngImagePlugin.PngInfo()
    info.add(b"sRGB", bytes([0]))
    image.save(master, pnginfo=info, transparency=0)
    result = worker.convert(master, recipe(master, "TIFF", "PRESERVE"), tmp_path / "out")
    with Image.open(result["artifact_path"]) as output:
        assert output.getpixel((0, 0))[3] == 0
        assert output.getpixel((1, 0))[3] == 255
    with pytest.raises(worker.RasterDerivativeError, match="ALPHA_FORBIDDEN"):
        worker.convert(master, recipe(master, "TIFF", "FORBID"), tmp_path / "no-alpha")


def test_quality_is_pinned_in_identity_and_changes_bytes(tmp_path):
    master = source(tmp_path / "master.png")
    r = recipe(master)
    first = worker.convert(master, r, tmp_path / "out")
    r["output"]["quality"] = 45
    second = worker.convert(master, r, tmp_path / "out")
    assert first["receipt"]["idempotency_key"] != second["receipt"]["idempotency_key"]
    assert first["receipt"]["output"]["sha256"] != second["receipt"]["output"]["sha256"]


def test_encoder_version_mismatch_blocks_before_output(tmp_path, monkeypatch):
    master = source(tmp_path / "master.png")
    monkeypatch.setattr(worker.PIL, "__version__", "0.0.0")
    with pytest.raises(worker.RasterDerivativeError, match="ENCODER_VERSION_MISMATCH"):
        worker.convert(master, recipe(master), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_bad_encoder_output_fails_qa_before_publication(tmp_path, monkeypatch):
    master = source(tmp_path / "master.png")
    monkeypatch.setattr(worker, "_encode", lambda *args: (b"invalid", None))
    with pytest.raises(worker.RasterDerivativeError, match="OUTPUT_MAGIC_MISMATCH"):
        worker.convert(master, recipe(master), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_receipt_cannot_be_reused_under_different_semantic_parent(tmp_path):
    master = source(tmp_path / "master.png")
    r = recipe(master)
    result = worker.convert(master, r, tmp_path / "out")
    receipt_before = Path(result["receipt_path"]).read_bytes()
    r["input"]["semantic_asset_id"] = "FASA-OTHER_ASSET"
    with pytest.raises(worker.RasterDerivativeError, match="OUTPUT_COLLISION"):
        worker.convert(master, r, tmp_path / "out")
    assert Path(result["receipt_path"]).read_bytes() == receipt_before
