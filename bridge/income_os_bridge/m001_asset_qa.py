"""Deterministic universal-QA gate for M-001 raster asset manifests.

The engine verifies file integrity, lineage, structured review receipts, rights,
safety, watermark state, dimensions, and exact duplicates.  It does not pretend
to automate aesthetic judgment: missing visual evidence blocks the batch for a
bounded human/vision review.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import struct
import zlib
from typing import Any

MANIFEST_SCHEMA = "die.m001.asset-batch.v1"
RECEIPT_SCHEMA = "die.m001.universal-qa-receipt.v1"
HEX64 = set("0123456789abcdef")


class QAError(RuntimeError):
    """Malformed or unsafe QA input."""


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QAError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QAError(f"expected JSON object: {path}")
    return value


def _safe_path(workspace: pathlib.Path, relative: Any, label: str) -> pathlib.Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise QAError(f"{label} must be a non-empty POSIX relative path")
    candidate_value = pathlib.Path(relative)
    if candidate_value.is_absolute() or ".." in candidate_value.parts:
        raise QAError(f"{label} must stay inside the workspace")
    candidate = (workspace / candidate_value).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise QAError(f"{label} resolves outside the workspace") from exc
    return candidate


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_dimensions(path: pathlib.Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise QAError("invalid PNG signature")
    cursor = 8
    dimensions: tuple[int, int] | None = None
    saw_iend = False
    while cursor + 12 <= len(raw):
        length = struct.unpack(">I", raw[cursor : cursor + 4])[0]
        chunk_end = cursor + 12 + length
        if chunk_end > len(raw):
            raise QAError("truncated PNG chunk")
        chunk_type = raw[cursor + 4 : cursor + 8]
        data = raw[cursor + 8 : cursor + 8 + length]
        expected_crc = struct.unpack(">I", raw[cursor + 8 + length : chunk_end])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
            raise QAError("PNG chunk CRC mismatch")
        if chunk_type == b"IHDR":
            if length != 13 or dimensions is not None:
                raise QAError("invalid PNG IHDR")
            dimensions = struct.unpack(">II", data[:8])
        if chunk_type == b"IEND":
            saw_iend = True
            if chunk_end != len(raw):
                raise QAError("unexpected bytes after PNG IEND")
            break
        cursor = chunk_end
    if dimensions is None or not saw_iend:
        raise QAError("PNG lacks IHDR or IEND")
    return dimensions


def _jpeg_dimensions(path: pathlib.Path) -> tuple[int, int]:
    if path.stat().st_size < 4:
        raise QAError("truncated JPEG")
    with path.open("rb") as trailer:
        trailer.seek(-2, 2)
        if trailer.read(2) != b"\xff\xd9":
            raise QAError("JPEG lacks end marker")
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise QAError("invalid JPEG start marker")
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if not marker or marker in {b"\xd8", b"\xd9"}:
                continue
            size_raw = handle.read(2)
            if len(size_raw) != 2:
                break
            size = struct.unpack(">H", size_raw)[0]
            if size < 2:
                break
            code = marker[0]
            if code in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                payload = handle.read(5)
                if len(payload) != 5:
                    break
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            handle.seek(size - 2, 1)
    raise QAError("JPEG dimensions not found")


def image_info(path: pathlib.Path) -> tuple[str, int, int]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        width, height = _png_dimensions(path)
        return "PNG", width, height
    if suffix in {".jpg", ".jpeg"}:
        width, height = _jpeg_dimensions(path)
        return "JPEG", width, height
    raise QAError(f"unsupported raster format: {suffix or '<none>'}")


def _review(
    asset: dict[str, Any], name: str, workspace: pathlib.Path
) -> tuple[str, str | None]:
    reviews = asset.get("reviews")
    if not isinstance(reviews, dict) or not isinstance(reviews.get(name), dict):
        return "UNKNOWN", f"missing {name} review"
    review = reviews[name]
    state = review.get("state")
    if state not in {"CLEAR", "PASS", "FAIL", "UNKNOWN"}:
        return "UNKNOWN", f"invalid {name} review state"
    evidence_ref = review.get("evidence_ref")
    try:
        evidence = _safe_path(workspace, evidence_ref, f"reviews.{name}.evidence_ref")
    except QAError as exc:
        return "UNKNOWN", str(exc)
    if not evidence.is_file():
        return "UNKNOWN", f"missing {name} evidence file"
    return str(state), None


def _lineage_errors(asset: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors = []
    required_strings = (
        "asset_id",
        "blueprint_id",
        "candidate_id",
        "master_id",
        "engine",
        "generated_at",
        "source_path",
        "source_sha256",
        "prompt_hash",
    )
    for field in required_strings:
        if not isinstance(asset.get(field), str) or not asset[field]:
            errors.append(f"missing {field}")
    for field in ("blueprint_id", "candidate_id", "master_id"):
        if asset.get(field) != manifest.get(field):
            errors.append(f"{field} mismatch")
    for field in ("source_sha256", "prompt_hash"):
        value = asset.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in HEX64 for c in value)
        ):
            errors.append(f"invalid {field}")
    return errors


def evaluate_manifest(
    manifest_path: pathlib.Path,
    workspace: pathlib.Path,
    *,
    min_assets: int,
    max_assets: int,
    min_pass_rate: float = 0.80,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    try:
        manifest_path.resolve().relative_to(workspace)
    except ValueError as exc:
        raise QAError("manifest must stay inside the assigned workspace") from exc
    manifest = _load_json(manifest_path)
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise QAError(f"manifest schema must be {MANIFEST_SCHEMA}")
    for field in ("batch_id", "blueprint_id", "candidate_id", "master_id"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise QAError(f"manifest {field} is required")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise QAError("manifest assets must be an array")
    technical = manifest.get("technical_requirements")
    if not isinstance(technical, dict):
        raise QAError("technical_requirements object is required")
    min_megapixels = technical.get("min_megapixels")
    if (
        not isinstance(min_megapixels, (int, float))
        or isinstance(min_megapixels, bool)
        or min_megapixels <= 0
    ):
        raise QAError("min_megapixels must be positive")
    formats_value = technical.get("allowed_formats")
    if not isinstance(formats_value, list) or not formats_value:
        raise QAError("allowed_formats must be a non-empty array")
    allowed_formats = {
        str(value).upper().replace("JPG", "JPEG") for value in formats_value
    }

    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    rows: list[dict[str, Any]] = []
    hard_rights_failures = 0
    hard_safety_failures = 0
    review_required = 0
    pass_count = 0

    for index, raw_asset in enumerate(assets):
        if not isinstance(raw_asset, dict):
            rows.append(
                {
                    "index": index,
                    "route": "ARCHIVE_RESEARCH_ONLY",
                    "reasons": ["asset is not an object"],
                }
            )
            continue
        asset = raw_asset
        asset_id = asset.get("asset_id") or f"index-{index}"
        reasons = _lineage_errors(asset, manifest)
        route: str | None = None
        if asset_id in seen_ids:
            route = "T1_MARKET_FIT_FAIL"
            reasons.append("duplicate asset_id")
        seen_ids.add(str(asset_id))

        source_path: pathlib.Path | None = None
        actual_sha: str | None = None
        image_format: str | None = None
        width = height = 0
        try:
            source_path = _safe_path(workspace, asset.get("source_path"), "source_path")
            if not source_path.is_file():
                raise QAError("source artifact does not exist")
            actual_sha = _sha256(source_path)
            if actual_sha != asset.get("source_sha256"):
                raise QAError("source_sha256 mismatch")
            image_format, width, height = image_info(source_path)
            if image_format not in allowed_formats:
                raise QAError(f"format {image_format} is not allowed")
        except (OSError, QAError) as exc:
            route = route or "RECREATE_TECHNICAL"
            reasons.append(str(exc))

        if actual_sha and actual_sha in seen_hashes:
            route = "T1_MARKET_FIT_FAIL"
            reasons.append("exact duplicate binary")
        if actual_sha:
            seen_hashes.add(actual_sha)

        review_states: dict[str, str] = {}
        for review_name in (
            "rights",
            "safety",
            "watermark",
            "lineage",
            "technical",
            "visual",
        ):
            state, error = _review(asset, review_name, workspace)
            review_states[review_name] = state
            if error:
                reasons.append(error)

        if review_states["rights"] not in {"CLEAR", "PASS"}:
            route = "QUARANTINE_RIGHTS"
            hard_rights_failures += 1
        elif review_states["safety"] not in {"CLEAR", "PASS"}:
            route = "QUARANTINE_SAFETY"
            hard_safety_failures += 1
        elif review_states["watermark"] not in {"CLEAR", "PASS"}:
            route = route or "RECREATE_TECHNICAL"
        elif review_states["lineage"] not in {"CLEAR", "PASS"}:
            route = route or "ARCHIVE_RESEARCH_ONLY"
        elif review_states["technical"] not in {"CLEAR", "PASS"}:
            route = route or "RECREATE_TECHNICAL"
        elif review_states["visual"] == "UNKNOWN":
            route = route or "REVIEW_REQUIRED"
            review_required += 1
        elif review_states["visual"] not in {"CLEAR", "PASS"}:
            route = route or "RECREATE_TECHNICAL"

        megapixels = width * height / 1_000_000 if width and height else 0
        if source_path and megapixels < float(min_megapixels):
            recovery = asset.get("recovery")
            if isinstance(recovery, dict) and recovery.get("eligible") is True:
                route = route or "T1_RECOVERABLE"
            else:
                route = route or "RECREATE_TECHNICAL"
            reasons.append(f"{megapixels:.3f} MP below {min_megapixels} MP")

        if reasons and route is None:
            route = "ARCHIVE_RESEARCH_ONLY"
        if route is None:
            route = "T1_PASS"
            pass_count += 1
        rows.append(
            {
                "asset_id": asset_id,
                "route": route,
                "source_sha256": actual_sha,
                "format": image_format,
                "width": width,
                "height": height,
                "megapixels": round(megapixels, 3),
                "review_states": review_states,
                "reasons": reasons,
            }
        )

    total = len(assets)
    pass_rate = pass_count / total if total else 0.0
    count_ok = min_assets <= total <= max_assets
    if review_required:
        batch_state = "BLOCKED_REVIEW"
    elif (
        hard_rights_failures
        or hard_safety_failures
        or not count_ok
        or pass_rate < min_pass_rate
    ):
        batch_state = "FAIL"
    else:
        batch_state = "PASS"
    return {
        "schema_version": RECEIPT_SCHEMA,
        "source_manifest_sha256": _sha256(manifest_path),
        "batch_id": manifest["batch_id"],
        "blueprint_id": manifest["blueprint_id"],
        "batch_state": batch_state,
        "total_assets": total,
        "asset_count_in_range": count_ok,
        "pass_count": pass_count,
        "pass_rate": round(pass_rate, 6),
        "minimum_pass_rate": min_pass_rate,
        "hard_rights_failures": hard_rights_failures,
        "hard_safety_failures": hard_safety_failures,
        "review_required": review_required,
        "routes": rows,
        "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "hard_vetoes_waivable": False,
        },
    }


def write_receipt(
    receipt: dict[str, Any], output: pathlib.Path, workspace: pathlib.Path
) -> None:
    workspace = workspace.resolve()
    try:
        output.resolve().relative_to(workspace)
    except ValueError as exc:
        raise QAError("QA receipt must stay inside the assigned workspace") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(output)
