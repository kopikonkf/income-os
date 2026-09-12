import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("vector_postproduction", ROOT / "company/factory-asset/lib/vector_postproduction.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


GOOD_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M 12 18 C 12 8 88 8 88 18 L 78 88 L 22 88 Z" fill="#336699" stroke="#000000" stroke-width="2"/>
  <circle cx="50" cy="48" r="12" fill="#ffffff" stroke="#000000" stroke-width="2"/>
</svg>'''


def _load_image(path: Path):
    with Image.open(path) as image:
        image.load()
        return image.format, image.mode, image.size, image.getbands()


def test_required_vector_postproduction_preserves_lineage_and_all_required_formats(tmp_path):
    receipt = MODULE.postprocess_vector(
        GOOD_SVG,
        tmp_path,
        "FASA-H01-105-TEST",
        provider_original_sha256=hashlib.sha256(GOOD_SVG).hexdigest(),
        blueprint_sha256="a" * 64,
        provider_prompt_sha256="b" * 64,
    )

    assert receipt["result"] == "PASS"
    assert (tmp_path / "provider-original.svg").read_bytes() == GOOD_SVG
    assert receipt["provider_original"]["immutable_preserved"] is True
    assert receipt["provider_original"]["hash_pinned"] is True
    assert receipt["lineage"]["provider_original_bytes_mutated"] is False
    assert all(artifact["provider_original_sha256"] == receipt["provider_original"]["sha256"] for artifact in receipt["artifacts"])
    assert all("lineage" in artifact and artifact["lineage"]["canonical_svg_sha256"] == receipt["lineage"]["canonical_svg_sha256"] for artifact in receipt["artifacts"])
    assert receipt["acceptance_evidence"]["immutable_provider_original_lineage"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["canonical_svg_then_optimized_svg"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["canonical_svg_then_optimized_svg"]["optimized_readback_matches_canonical"] is True

    for name in ("canonical-master.svg", "optimized-master.svg", "master.pdf", "master.eps", "preview.png", "preview.webp", "preview.jpg", "postproduction.receipt.json"):
        assert (tmp_path / name).is_file(), name
    for fmt in ("SVG", "PDF", "EPS", "PNG", "WEBP", "JPG"):
        assert sum(artifact["format"] == fmt for artifact in receipt["artifacts"]) >= 1
    assert all(artifact["semantic_identity_effect"] == "NONE" for artifact in receipt["artifacts"])
    assert receipt["semantic_asset_count"] == 1

    pdf = (tmp_path / "master.pdf").read_bytes()
    eps = (tmp_path / "master.eps").read_bytes()
    assert b"/Subtype /Image" not in pdf and b"/Image" not in pdf
    assert b" m\n" in pdf and b" l\n" in pdf
    assert b"%!PS-Adobe-3.0 EPSF-3.0" in eps
    assert b"moveto" in eps and b"lineto" in eps
    assert receipt["acceptance_evidence"]["true_vector_pdf"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["validated_eps"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["no_png_intermediate_for_vector_outputs"]["result"] == "PASS"

    assert _load_image(tmp_path / "preview.png")[0:2] == ("PNG", "RGBA")
    assert _load_image(tmp_path / "preview.webp")[0:2] == ("WEBP", "RGBA")
    assert _load_image(tmp_path / "preview.jpg")[0:2] == ("JPEG", "RGB")
    assert receipt["acceptance_evidence"]["png_alpha"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["webp"]["result"] == "PASS"
    assert receipt["acceptance_evidence"]["jpg"]["result"] == "PASS"

    assert all(receipt["conditional_formats"][fmt]["status"] == "SKIPPED_CONDITIONAL" for fmt in ("TIFF", "SVGZ", "DXF"))
    assert receipt["acceptance_evidence"]["conditional_tiff_svgz_dxf"]["result"] == "PASS"


def test_conditional_formats_are_capability_gated_and_idempotent(tmp_path):
    kwargs = {"optional_formats": {"TIFF", "SVGZ", "DXF"}, "capabilities": {"TIFF", "SVGZ", "DXF"}}
    first = MODULE.postprocess_vector(GOOD_SVG, tmp_path, "FASA-H01-105-OPTIONAL", **kwargs)
    first_bytes = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    second = MODULE.postprocess_vector(GOOD_SVG, tmp_path, "FASA-H01-105-OPTIONAL", **kwargs)
    second_bytes = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    assert first == second
    assert first_bytes == second_bytes
    assert all(first["conditional_formats"][fmt]["status"] == "PRODUCED" for fmt in ("TIFF", "SVGZ", "DXF"))
    assert _load_image(tmp_path / "preview.tiff")[0:2] == ("TIFF", "RGBA")
    assert (tmp_path / "optimized-master.svgz").read_bytes().startswith(b"\x1f\x8b")
    assert b"\nLINE\n" in (tmp_path / "master.dxf").read_bytes()
    assert first["acceptance_evidence"]["conditional_tiff_svgz_dxf"]["result"] == "PASS"


def test_vector_outputs_do_not_depend_on_png_bytes_and_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    def forbidden_png(*args, **kwargs):
        raise AssertionError("PNG intermediary must not be used to create vector outputs")

    monkeypatch.setattr(MODULE._NATIVE, "png_bytes", forbidden_png)
    receipt = MODULE.postprocess_vector(GOOD_SVG, tmp_path, "FASA-H01-105-NO-PNG")
    assert receipt["qa"]["vector_outputs"]["pdf"]["result"] == "PASS"
    assert receipt["qa"]["vector_outputs"]["eps"]["result"] == "PASS"
    with pytest.raises(MODULE.VectorPostproductionError) as error:
        MODULE.postprocess_vector(GOOD_SVG, tmp_path / "mismatch", "FASA-H01-105-HASH", provider_original_sha256="0" * 64)
    assert error.value.code == "PROVIDER_ORIGINAL_HASH_MISMATCH"


def test_existing_different_artifact_is_not_overwritten(tmp_path):
    (tmp_path / "provider-original.svg").write_bytes(b"unrelated")
    with pytest.raises(MODULE.VectorPostproductionError) as error:
        MODULE.postprocess_vector(GOOD_SVG, tmp_path, "FASA-H01-105-COLLISION")
    assert error.value.code == "OUTPUT_COLLISION"
    assert (tmp_path / "provider-original.svg").read_bytes() == b"unrelated"


def test_unsupported_conditional_conversion_fails_closed(tmp_path):
    with pytest.raises(MODULE.VectorPostproductionError) as error:
        MODULE.postprocess_vector(
            GOOD_SVG,
            tmp_path,
            "FASA-H01-105-UNSUPPORTED",
            optional_formats={"AI"},
            capabilities={"AI"},
        )
    assert error.value.code == "OPTIONAL_FORMAT_UNSUPPORTED"
