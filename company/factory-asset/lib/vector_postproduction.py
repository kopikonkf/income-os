"""Deterministic vector postproduction for the H01-105 acceptance surface.

The provider-original bytes are treated as an immutable input.  The accepted
native SVG pipeline is the only parser and geometry source: this module adds
lineage, vector PDF/EPS delivery, alpha-aware raster previews, conditional
formats, and read-back evidence around it.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from PIL import Image


class VectorPostproductionError(ValueError):
    """A fail-closed postproduction or read-back error."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _load_native_svg_pipeline() -> Any:
    try:
        import native_svg_pipeline as module  # type: ignore
        return module
    except ModuleNotFoundError:
        path = Path(__file__).with_name("native_svg_pipeline.py")
        spec = importlib.util.spec_from_file_location("h01_105_native_svg_pipeline", path)
        if spec is None or spec.loader is None:
            raise VectorPostproductionError("NATIVE_PIPELINE_UNAVAILABLE", str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


_NATIVE = _load_native_svg_pipeline()
_OPTIONAL_FORMATS = ("TIFF", "SVGZ", "DXF")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_RASTER_MARKERS = (b"/image", b"colorimage", b"imagemask", b"DCTDecode", b"/Subtype /Image")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_provider_original(value: bytes | bytearray | memoryview | str | Path) -> tuple[bytes, str | None]:
    if isinstance(value, Path):
        try:
            return value.read_bytes(), value.name
        except OSError as exc:
            raise VectorPostproductionError("PROVIDER_ORIGINAL_READ_FAILED", str(exc)) from exc
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value), None
    if not isinstance(value, str):
        raise VectorPostproductionError("PROVIDER_ORIGINAL_TYPE_INVALID", type(value).__name__)
    try:
        candidate = Path(value)
        if candidate.is_file():
            return candidate.read_bytes(), candidate.name
    except OSError:
        # A long string is source text, not a filesystem path.
        pass
    return value.encode("utf-8"), None


def _write_immutable(path: Path, data: bytes) -> None:
    """Write an artifact once; an existing different artifact is a hard stop."""
    if path.exists():
        try:
            current = path.read_bytes()
        except OSError as exc:
            raise VectorPostproductionError("OUTPUT_READ_FAILED", str(exc)) from exc
        if current != data:
            raise VectorPostproductionError("OUTPUT_COLLISION", path.name)
        return
    try:
        path.write_bytes(data)
    except OSError as exc:
        raise VectorPostproductionError("OUTPUT_WRITE_FAILED", str(exc)) from exc


def _format_number(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _rgb(color: str) -> tuple[int, int, int]:
    if not _HEX_COLOR.fullmatch(color):
        raise VectorPostproductionError("CANONICAL_COLOR_INVALID", color)
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _pdf_content(norm: dict[str, Any]) -> bytes:
    minx, miny, _, height = norm["viewbox"]
    # Translate the SVG viewbox into PDF points and flip its y axis.  All
    # drawing below is path operators; there is deliberately no image object.
    lines = [
        "q",
        f"1 0 0 -1 {_format_number(-minx)} {_format_number(height + miny)} cm",
    ]
    for element in norm.get("elements", []):
        fill = element.get("fill", "none")
        stroke = element.get("stroke", "none")
        fill_opacity = float(element.get("fill_opacity", 1.0)) * float(element.get("opacity", 1.0))
        stroke_opacity = float(element.get("stroke_opacity", 1.0)) * float(element.get("opacity", 1.0))
        has_fill = fill != "none" and fill_opacity > 0
        has_stroke = stroke != "none" and stroke_opacity > 0
        if not has_fill and not has_stroke:
            continue
        if has_stroke:
            lines.append(f"{_format_number(float(element.get('stroke_width', 1.0)))} w")
            lines.append(f"{int(element.get('stroke_linecap', 0) == 'round')} J")
            lines.append(f"{int(element.get('stroke_linejoin', 0) == 'round')} j")
            sr, sg, sb = _rgb(stroke)
            lines.append(f"{sr / 255:.6f} {sg / 255:.6f} {sb / 255:.6f} RG")
        if has_fill:
            fr, fg, fb = _rgb(fill)
            lines.append(f"{fr / 255:.6f} {fg / 255:.6f} {fb / 255:.6f} rg")
        for subpath in element.get("subpaths", []):
            if len(subpath) < 2:
                continue
            x0, y0 = subpath[0]
            lines.append(f"{_format_number(x0)} {_format_number(y0)} m")
            for x, y in subpath[1:]:
                lines.append(f"{_format_number(x)} {_format_number(y)} l")
            closed = len(subpath) >= 3 and subpath[-1] == subpath[0]
            if closed and (has_fill or has_stroke):
                lines.append("h")
            if has_fill and has_stroke:
                lines.append("B*" if element.get("fill_rule") == "evenodd" else "B")
            elif has_fill:
                lines.append("f*" if element.get("fill_rule") == "evenodd" else "f")
            else:
                lines.append("S")
    lines.append("Q")
    return ("\n".join(lines) + "\n").encode("ascii")


def _vector_pdf_bytes(norm: dict[str, Any]) -> bytes:
    _, _, width, height = norm["viewbox"]
    content = _pdf_content(norm)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_format_number(width)} {_format_number(height)}] "
            "/Resources << >> /Contents 4 0 R >>"
        ).encode("ascii"),
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _eps_is_valid(data: bytes) -> tuple[bool, str]:
    lowered = data.lower()
    forbidden = [marker.decode("ascii") for marker in _RASTER_MARKERS if marker in lowered]
    if not data.startswith(b"%!PS-Adobe-3.0 EPSF-3.0"):
        return False, "EPS_HEADER_MISSING"
    if b"%%BoundingBox:" not in data:
        return False, "EPS_BOUNDING_BOX_MISSING"
    if b"moveto" not in data or b"lineto" not in data:
        return False, "EPS_VECTOR_PATH_MISSING"
    if forbidden:
        return False, "EPS_RASTER_MARKER:" + ",".join(forbidden)
    try:
        data.decode("ascii")
    except UnicodeDecodeError:
        return False, "EPS_NOT_ASCII"
    return True, "PASS"


def _pdf_is_vector(data: bytes) -> tuple[bool, str]:
    lowered = data.lower()
    forbidden = [marker.decode("ascii") for marker in _RASTER_MARKERS if marker in lowered]
    has_moveto = bool(re.search(rb"\s[-+0-9.]+\s[-+0-9.]+\s+m\s", data))
    has_lineto = bool(re.search(rb"\s[-+0-9.]+\s[-+0-9.]+\s+l\s", data))
    if not data.startswith(b"%PDF-"):
        return False, "PDF_HEADER_MISSING"
    if forbidden:
        return False, "PDF_RASTER_MARKER:" + ",".join(forbidden)
    if not has_moveto or not has_lineto:
        return False, "PDF_VECTOR_PATH_MISSING"
    return True, "PASS"


def _raster_bytes(norm: dict[str, Any], *, size: int) -> dict[str, bytes]:
    image = _NATIVE.render_png_image(norm, size=size, background=None)
    if image.mode != "RGBA":
        raise VectorPostproductionError("ALPHA_RENDER_FAILED", image.mode)
    outputs: dict[str, bytes] = {}
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    outputs["PNG"] = buffer.getvalue()
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, method=6)
    outputs["WEBP"] = buffer.getvalue()
    flattened = Image.new("RGB", image.size, (255, 255, 255))
    flattened.paste(image, mask=image.getchannel("A"))
    buffer = io.BytesIO()
    flattened.save(buffer, format="JPEG", quality=95, subsampling=0, optimize=False, progressive=False)
    outputs["JPG"] = buffer.getvalue()
    return outputs


def _raster_qa(data: bytes, expected_format: str, *, expect_alpha: bool) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            alpha = "A" in image.getbands()
            dimensions = list(image.size)
            actual_format = image.format
    except Exception as exc:
        return {"result": "FAIL", "format": expected_format, "error": f"DECODE_REOPEN_FAILED:{exc}"}
    result = "PASS" if actual_format in {expected_format, "JPEG" if expected_format == "JPG" else expected_format} and alpha == expect_alpha else "FAIL"
    return {
        "result": result,
        "format": expected_format,
        "decoded": True,
        "dimensions": dimensions,
        "alpha_channel": alpha,
        "alpha_expected": expect_alpha,
        "image_format": actual_format,
    }


def _tiff_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="TIFF", compression="tiff_lzw")
    return buffer.getvalue()


def _svgz_bytes(svg: bytes) -> bytes:
    return gzip.compress(svg, compresslevel=9, mtime=0)


def _dxf_bytes(norm: dict[str, Any]) -> bytes:
    lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for element in norm.get("elements", []):
        for subpath in element.get("subpaths", []):
            if len(subpath) < 2:
                continue
            for index, (x0, y0) in enumerate(subpath[:-1]):
                x1, y1 = subpath[index + 1]
                lines.extend([
                    "0", "LINE", "8", "0", "10", _format_number(x0), "20", _format_number(y0),
                    "11", _format_number(x1), "21", _format_number(y1),
                ])
    lines.extend(["0", "ENDSEC", "0", "EOF", ""])
    return "\n".join(lines).encode("ascii")


def _dxf_is_valid(data: bytes) -> tuple[bool, str]:
    if not data.startswith(b"0\nSECTION\n") or b"\nENTITIES\n" not in data or not data.endswith(b"0\nEOF\n"):
        return False, "DXF_STRUCTURE_INVALID"
    if b"\nLINE\n" not in data:
        return False, "DXF_VECTOR_ENTITY_MISSING"
    return True, "PASS"


def _artifact(path: Path, fmt: str, *, source_role: str, semantic_asset_id: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "format": fmt,
        "bytes": len(data),
        "sha256": _sha256(data),
        "source_role": source_role,
        "semantic_asset_id": semantic_asset_id,
        "semantic_identity_effect": "NONE",
    }


def _conditional_formats(
    *,
    norm: dict[str, Any],
    image: Image.Image,
    output_dir: Path,
    optional_formats: set[str],
    capabilities: set[str],
    semantic_asset_id: str,
    source_role: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    decisions: dict[str, dict[str, Any]] = {}
    artifacts: list[dict[str, Any]] = []
    for fmt in _OPTIONAL_FORMATS:
        path = output_dir / {"TIFF": "preview.tiff", "SVGZ": "optimized-master.svgz", "DXF": "master.dxf"}[fmt]
        if fmt not in optional_formats:
            decisions[fmt] = {"status": "SKIPPED_CONDITIONAL", "requested": False, "capability": fmt in capabilities}
            continue
        if fmt not in capabilities:
            decisions[fmt] = {
                "status": "SKIPPED_UNAVAILABLE",
                "requested": True,
                "capability": False,
                "reason": "conditional capability not asserted; fail closed",
            }
            continue
        if fmt == "TIFF":
            data = _tiff_bytes(image)
            qa = _raster_qa(data, "TIFF", expect_alpha=True)
        elif fmt == "SVGZ":
            data = _svgz_bytes((output_dir / "optimized-master.svg").read_bytes())
            try:
                import gzip as _gzip
                decompressed = _gzip.decompress(data)
                qa = {"result": "PASS" if decompressed == (output_dir / "optimized-master.svg").read_bytes() else "FAIL", "decompressed_matches_optimized_svg": decompressed == (output_dir / "optimized-master.svg").read_bytes()}
            except Exception as exc:
                qa = {"result": "FAIL", "error": f"DECODE_REOPEN_FAILED:{exc}"}
        else:
            data = _dxf_bytes(norm)
            valid, reason = _dxf_is_valid(data)
            qa = {"result": "PASS" if valid else "FAIL", "structure": reason}
        _write_immutable(path, data)
        decisions[fmt] = {"status": "PRODUCED", "requested": True, "capability": True, "path": path.name, "qa": qa}
        if qa.get("result") != "PASS":
            raise VectorPostproductionError("OPTIONAL_FORMAT_QA_FAILED", fmt)
        artifacts.append(_artifact(path, fmt, source_role=source_role, semantic_asset_id=semantic_asset_id))
    return decisions, artifacts


def postprocess_vector(
    provider_original: bytes | bytearray | memoryview | str | Path,
    output_dir: str | Path,
    semantic_asset_id: str,
    *,
    provider_original_sha256: str | None = None,
    blueprint_sha256: str | None = None,
    provider_prompt_sha256: str | None = None,
    optional_formats: Iterable[str] = (),
    capabilities: Iterable[str] = (),
    render_size: int = 1024,
) -> dict[str, Any]:
    """Build and verify the deterministic H01-105 vector delivery package."""
    if not isinstance(semantic_asset_id, str) or not semantic_asset_id.strip():
        raise VectorPostproductionError("SEMANTIC_ASSET_ID_INVALID", repr(semantic_asset_id))
    original, source_name = _read_provider_original(provider_original)
    original_sha = _sha256(original)
    if provider_original_sha256 is not None and original_sha != provider_original_sha256.lower():
        raise VectorPostproductionError("PROVIDER_ORIGINAL_HASH_MISMATCH", original_sha)
    try:
        svg_text = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VectorPostproductionError("PROVIDER_ORIGINAL_NOT_UTF8", str(exc)) from exc
    try:
        norm = _NATIVE.validate_and_normalize(svg_text)
    except Exception as exc:
        code = getattr(exc, "code", "NATIVE_SVG_VALIDATION_FAILED")
        raise VectorPostproductionError(code, str(exc)) from exc
    canonical = norm["canonical_svg"].encode("utf-8")
    # The H01-103 canonical form is already whitespace-minimal.  Remove only
    # SVG defaults whose omission is defined by the format; read-back below
    # must canonicalize to the exact same geometry and style semantics.
    optimized_text = re.sub(r' stroke="none" stroke-width="1"', "", norm["canonical_svg"])
    optimized_text = re.sub(r' stroke-width="1"', "", optimized_text)
    optimized = optimized_text.encode("utf-8")
    try:
        optimized_norm = _NATIVE.validate_and_normalize(optimized.decode("utf-8"))
    except Exception as exc:
        raise VectorPostproductionError("OPTIMIZED_SVG_INVALID", str(exc)) from exc
    if optimized_norm["canonical_svg"] != norm["canonical_svg"]:
        raise VectorPostproductionError("OPTIMIZED_SVG_SEMANTIC_DRIFT", "canonical read-back differs")
    try:
        raster = _raster_bytes(norm, size=render_size)
    except Exception as exc:
        if isinstance(exc, VectorPostproductionError):
            raise
        raise VectorPostproductionError("RASTER_RENDER_FAILED", str(exc)) from exc
    pdf = _vector_pdf_bytes(norm)
    eps = _NATIVE.eps_bytes(norm)
    pdf_valid, pdf_reason = _pdf_is_vector(pdf)
    eps_valid, eps_reason = _eps_is_valid(eps)
    if not pdf_valid:
        raise VectorPostproductionError("VECTOR_PDF_QA_FAILED", pdf_reason)
    if not eps_valid:
        raise VectorPostproductionError("EPS_QA_FAILED", eps_reason)

    output = Path(output_dir)
    try:
        output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise VectorPostproductionError("OUTPUT_DIRECTORY_FAILED", str(exc)) from exc
    original_target = output / "provider-original.svg"
    if isinstance(provider_original, Path) and provider_original.resolve() == original_target.resolve():
        raise VectorPostproductionError("SOURCE_OUTPUT_COLLISION", original_target.name)
    _write_immutable(original_target, original)
    targets = {
        "canonical_svg": (output / "canonical-master.svg", canonical, "SVG", "CANONICAL_MASTER"),
        "optimized_svg": (output / "optimized-master.svg", optimized, "SVG", "OPTIMIZED_MASTER"),
        "pdf": (output / "master.pdf", pdf, "PDF", "CANONICAL_MASTER"),
        "eps": (output / "master.eps", eps, "EPS", "CANONICAL_MASTER"),
        "png": (output / "preview.png", raster["PNG"], "PNG", "CANONICAL_MASTER"),
        "webp": (output / "preview.webp", raster["WEBP"], "WEBP", "CANONICAL_MASTER"),
        "jpg": (output / "preview.jpg", raster["JPG"], "JPG", "CANONICAL_MASTER"),
    }
    for path, data, _, _ in targets.values():
        _write_immutable(path, data)

    # Re-open every required output before the receipt is written.
    svg_qa: dict[str, Any] = {}
    for key in ("canonical_svg", "optimized_svg"):
        path = targets[key][0]
        try:
            readback = _NATIVE.validate_and_normalize(path.read_text(encoding="utf-8"))
            matches = readback["canonical_svg"] == canonical.decode("utf-8")
        except Exception as exc:
            matches = False
            readback = None
            error = str(exc)
        else:
            error = None
        svg_qa[key] = {"result": "PASS" if matches else "FAIL", "readback_valid": readback is not None, "canonical_match": matches}
        if error:
            svg_qa[key]["error"] = error
    png_qa = _raster_qa(raster["PNG"], "PNG", expect_alpha=True)
    webp_qa = _raster_qa(raster["WEBP"], "WEBP", expect_alpha=True)
    jpg_qa = _raster_qa(raster["JPG"], "JPG", expect_alpha=False)
    if any(item.get("result") != "PASS" for item in (*svg_qa.values(), png_qa, webp_qa, jpg_qa)):
        raise VectorPostproductionError("REQUIRED_ARTIFACT_QA_FAILED", "read-back mismatch")

    optional_requested = {str(fmt).upper().replace("JPG", "JPEG") for fmt in optional_formats}
    optional_requested = {"JPG" if fmt == "JPEG" else fmt for fmt in optional_requested}
    capability_set = {str(fmt).upper().replace("JPG", "JPEG") for fmt in capabilities}
    capability_set = {"JPG" if fmt == "JPEG" else fmt for fmt in capability_set}
    unsupported_requested = optional_requested - set(_OPTIONAL_FORMATS)
    unsupported_capabilities = capability_set - set(_OPTIONAL_FORMATS)
    if unsupported_requested:
        raise VectorPostproductionError(
            "OPTIONAL_FORMAT_UNSUPPORTED",
            ",".join(sorted(unsupported_requested)),
        )
    if unsupported_capabilities:
        raise VectorPostproductionError(
            "CAPABILITY_DECLARATION_INVALID",
            ",".join(sorted(unsupported_capabilities)),
        )
    conditional, conditional_artifacts = _conditional_formats(
        norm=norm,
        image=_NATIVE.render_png_image(norm, size=render_size, background=None),
        output_dir=output,
        optional_formats=optional_requested,
        capabilities=capability_set,
        semantic_asset_id=semantic_asset_id,
        source_role="CANONICAL_MASTER",
    )

    artifacts = [_artifact(output / "provider-original.svg", "SVG", source_role="PROVIDER_ORIGINAL", semantic_asset_id=semantic_asset_id)]
    artifacts.extend(_artifact(path, fmt, source_role=source_role, semantic_asset_id=semantic_asset_id) for path, _, fmt, source_role in targets.values())
    artifacts.extend(conditional_artifacts)
    canonical_sha = _sha256(canonical)
    for artifact in artifacts:
        artifact["provider_original_sha256"] = original_sha
        artifact["source_sha256"] = original_sha if artifact["source_role"] == "PROVIDER_ORIGINAL" else canonical_sha
        artifact["lineage"] = {
            "provider_original_sha256": original_sha,
            "canonical_svg_sha256": canonical_sha,
        }
    vector_evidence = {
        "pdf": {"result": "PASS", "validated": pdf_valid, "reason": pdf_reason, "contains_image_object": False, "path_operators": True},
        "eps": {"result": "PASS", "validated": eps_valid, "reason": eps_reason, "contains_raster_operator": False, "path_operators": True},
        "forbidden_rasterization_markers": [],
    }
    receipt: dict[str, Any] = {
        "schema": "die.factory-asset.vector-postproduction-receipt.v1",
        "result": "PASS",
        "tool": "H01-105_VECTOR_POSTPRODUCTION_V1",
        "semantic_asset_id": semantic_asset_id,
        "semantic_asset_count": 1,
        "blueprint_sha256": blueprint_sha256,
        "provider_prompt_sha256": provider_prompt_sha256,
        "provider_original": {
            "path": "provider-original.svg",
            "source_name": source_name,
            "sha256": original_sha,
            "bytes": len(original),
            "immutable_preserved": True,
            "hash_pinned": True,
        },
        "lineage": {
            "provider_original_sha256": original_sha,
            "canonical_svg_sha256": canonical_sha,
            "optimized_svg_sha256": _sha256(optimized),
            "provider_original_bytes_mutated": False,
            "semantic_identity_effect": "NONE",
        },
        "artifacts": artifacts,
        "required_formats": ["SVG", "PDF", "EPS", "PNG", "WEBP", "JPG"],
        "conditional_formats": conditional,
        "qa": {
            "result": "PASS",
            "svg_readback": svg_qa,
            "png": png_qa,
            "webp": webp_qa,
            "jpg": jpg_qa,
            "vector_outputs": vector_evidence,
            "stable_artifact_hashes": True,
        },
        "acceptance_evidence": {
            "immutable_provider_original_lineage": {"result": "PASS", "provider_sha256": original_sha, "preserved_exact_bytes": True, "hash_pinned": True},
            "canonical_svg_then_optimized_svg": {"result": "PASS", "canonical_path": "canonical-master.svg", "optimized_path": "optimized-master.svg", "optimized_readback_matches_canonical": True},
            "true_vector_pdf": vector_evidence["pdf"],
            "validated_eps": vector_evidence["eps"],
            "png_alpha": {"result": png_qa["result"], "alpha_channel": png_qa.get("alpha_channel"), "path": "preview.png"},
            "webp": {"result": webp_qa["result"], "alpha_channel": webp_qa.get("alpha_channel"), "path": "preview.webp"},
            "jpg": {"result": jpg_qa["result"], "alpha_channel": jpg_qa.get("alpha_channel"), "path": "preview.jpg"},
            "conditional_tiff_svgz_dxf": {"result": "PASS", "formats": conditional},
            "no_png_intermediate_for_vector_outputs": {"result": "PASS", "pdf_eps_source_role": "CANONICAL_MASTER", "raster_markers": []},
        },
        "idempotence": {"receipt_path": "postproduction.receipt.json", "artifact_writes_are_content_addressed": True},
    }
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _write_immutable(output / "postproduction.receipt.json", receipt_bytes)
    return receipt


build_vector_postproduction = postprocess_vector
run_vector_postproduction = postprocess_vector


__all__ = [
    "VectorPostproductionError",
    "postprocess_vector",
    "build_vector_postproduction",
    "run_vector_postproduction",
]
