from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ModuleNotFoundError:  # only needed for preview dimensions
    Image = None  # type: ignore

HERE = Path(__file__).resolve()
H01_ROOT = HERE.parents[1]
DEFAULT_PROFILES = H01_ROOT / "marketplace" / "marketplace-delivery-profiles.v1.json"
# Engineering-local registry copy (task says add/repair under engineering)
ENGINEERING_REGISTRY = HERE.parent / "marketplace-delivery-profiles.v1.json"

PROFILE_SET = {"ADOBE", "VECTEEZY", "123RF", "DREAMSTIME", "VECTORSTOCK", "MOTIONELEMENTS"}
# Fixed ZIP timestamp for determinism (1980-01-01)
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class MarketplaceDeliveryError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _sha_json(value: Any) -> str:
    return _sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketplaceDeliveryError("JSON_READ_FAILED", str(path)) from exc
    if not isinstance(value, dict):
        raise MarketplaceDeliveryError("JSON_OBJECT_REQUIRED", str(path))
    return value


def load_profiles(path: Path | None = None) -> dict[str, Any]:
    # Prefer explicit path, then engineering registry, then default marketplace path
    candidates = []
    if path is not None:
        candidates.append(Path(path))
    candidates.append(ENGINEERING_REGISTRY)
    candidates.append(DEFAULT_PROFILES)
    data = None
    for cand in candidates:
        if cand.is_file():
            data = _json(cand)
            break
    if data is None:
        raise MarketplaceDeliveryError("PROFILES_NOT_FOUND", str(candidates))
    if set(data.get("profiles", {})) != PROFILE_SET:
        raise MarketplaceDeliveryError("PROFILE_SET_INVALID", ",".join(sorted(data.get("profiles", {}))))
    return data


def _select_source(post: Path, rule: dict[str, Any]) -> tuple[Path, str, str]:
    primary = post / str(rule["source"])
    if primary.is_file():
        return primary, str(rule["target"]), str(rule["format"])
    fallback = rule.get("fallback")
    if fallback:
        candidate = post / str(fallback)
        if candidate.is_file():
            return candidate, str(rule.get("fallback_target") or rule["target"]), str(rule.get("fallback_format") or rule["format"])
    raise MarketplaceDeliveryError("DELIVERY_SOURCE_MISSING", str(primary))


def _svg_viewbox(path: Path) -> tuple[float, float] | None:
    text = path.read_text(errors="ignore")[:8192]
    match = re.search(r'viewBox=["\']\s*[-+0-9.eE]+\s+[-+0-9.eE]+\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*["\']', text)
    if not match:
        return None
    try:
        return abs(float(match.group(1))), abs(float(match.group(2)))
    except ValueError:
        return None

def _svg_delivery_area(path: Path) -> float | None:
    text = path.read_text(errors="ignore")[:8192]
    wm = re.search(r'<svg\b[^>]*\bwidth=["\']([0-9.]+)["\']', text)
    hm = re.search(r'<svg\b[^>]*\bheight=["\']([0-9.]+)["\']', text)
    if wm and hm:
        try: return float(wm.group(1)) * float(hm.group(1))
        except ValueError: pass
    dims = _svg_viewbox(path)
    return dims[0] * dims[1] if dims else None


def _eps_area(path: Path) -> int | None:
    text = path.read_text(errors="ignore")[:16384]
    match = re.search(r"^%%BoundingBox:\s+0\s+0\s+(\d+)\s+(\d+)\s*$", text, re.MULTILINE)
    return int(match.group(1)) * int(match.group(2)) if match else None


def _image_dimensions(path: Path) -> tuple[int, int] | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def _compatibility(marketplace: str, profile: dict[str, Any], selected: list[dict[str, Any]]):
    blockers: list[str] = []
    notes: list[str] = []
    by_format = {row["format"]: Path(row["source_path"]) for row in selected}
    constraints = profile.get("constraints") or {}
    if marketplace == "ADOBE":
        svg = by_format.get("SVG")
        area = _svg_delivery_area(svg) if svg else None
        if area is None:
            blockers.append("ADOBE_SVG_ARTBOARD_UNKNOWN")
        elif area < constraints.get("artboard_min_mp", 15) * 1_000_000:
            blockers.append("ADOBE_SVG_ARTBOARD_BELOW_15MP")
        elif area > constraints.get("artboard_max_mp", 65) * 1_000_000:
            blockers.append("ADOBE_SVG_ARTBOARD_ABOVE_65MP")
        if svg and svg.stat().st_size > constraints.get("max_file_mb", 45) * 1024 * 1024:
            blockers.append("ADOBE_FILE_ABOVE_45MB")
        notes.append("SVG_DIRECT_DELIVERY_METADATA_AS_SUBMISSION_FIELDS")
        notes.append("GENERATIVE_AI_DISCLOSURE_REQUIRED")
    if marketplace == "VECTEEZY":
        eps = by_format.get("EPS")
        area = _eps_area(eps) if eps else None
        if area is None:
            blockers.append("VECTEEZY_EPS_BOUNDING_BOX_UNKNOWN")
        elif area < 4000000 or area > 25000000:
            blockers.append("VECTEEZY_EPS_ARTBOARD_OUTSIDE_RANGE")
        # Structural target, not certified Illustrator save
        notes.append("ILLUSTRATOR_10_STRUCTURAL_TARGET_ONLY")
        notes.append("NATIVE_ILLUSTRATOR_SAVE_NOT_CERTIFIED")
        notes.append("GENERATIVE_AI_DISCLOSURE_REQUIRED")
    if marketplace == "123RF":
        eps = by_format.get("EPS")
        jpg = by_format.get("JPG")
        if eps is None:
            blockers.append("123RF_EPS_MISSING")
        if jpg is None:
            blockers.append("123RF_JPG_MISSING")
        else:
            dims = _image_dimensions(jpg) if jpg else None
            if dims is not None and (dims[0] < 1600 or dims[1] < 1600):
                blockers.append("123RF_JPG_TOO_SMALL")
            elif dims is None and Image is not None:
                blockers.append("123RF_JPG_UNREADABLE")
        # same basename is structural; verified later but also note
        notes.append("SAME_BASENAME_REQUIRED")
        notes.append("GENERATIVE_AI_DISCLOSURE_REQUIRED")
    if marketplace == "DREAMSTIME":
        jpg = by_format.get("JPG")
        dims = _image_dimensions(jpg) if jpg else None
        # high-res check: require >=1600x1600 as proxy for high-res
        if jpg is None:
            blockers.append("DREAMSTIME_JPG_MISSING")
        elif dims is not None and (dims[0] < 1600 or dims[1] < 1600):
            blockers.append("DREAMSTIME_JPG_TOO_SMALL")
        notes.append("JPG_PRIMARY_SVG_ADDITIONAL")
        notes.append("GENERATIVE_AI_DISCLOSURE_REQUIRED")
        notes.append("AI_CATEGORY_REQUIRED")
    if marketplace == "VECTORSTOCK":
        eps = by_format.get("EPS")
        jpg = by_format.get("JPG")
        if eps is None:
            blockers.append("VECTORSTOCK_EPS_MISSING")
        if jpg is None:
            blockers.append("VECTORSTOCK_JPG_MISSING")
        else:
            dims = _image_dimensions(jpg) if jpg else None
            if dims is not None:
                if max(dims) > 3000:
                    notes.append("VECTORSTOCK_PREVIEW_NORMALIZE")
                elif max(dims) < 1000 or min(dims) < 1000:
                    blockers.append("VECTORSTOCK_JPG_TOO_SMALL")
            elif Image is not None:
                blockers.append("VECTORSTOCK_JPG_UNREADABLE")
        notes.append("SAME_BASENAME_REQUIRED")
        notes.append("DETERMINISTIC_ZIP_CONTAINS_EPS")
        notes.append("AI_CHECKBOX_REQUIRED")
        notes.append("GENERATIVE_AI_DISCLOSURE_REQUIRED")
    if marketplace == "MOTIONELEMENTS":
        eps = by_format.get("EPS")
        jpg = by_format.get("JPG")
        if eps is None:
            blockers.append("MOTIONELEMENTS_EPS_MISSING")
        if jpg is None:
            blockers.append("MOTIONELEMENTS_JPG_MISSING")
        notes.append("SAME_BASENAME_REQUIRED")
        notes.append("DETERMINISTIC_ZIP_EPS_AND_JPG")
        notes.append("AI_GENERATED_ACCOUNT_REQUIRED")
        notes.append("AI_DISCLOSURE_REQUIRED")
    # Generic: ensure ai disclosure fields exist? Not blocker here but will be in metadata
    status = "COMPATIBLE" if not blockers else "REVIEW_REQUIRED"
    return status, blockers, notes


def _write_immutable(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != data:
            raise MarketplaceDeliveryError("OUTPUT_COLLISION", str(target))
        return
    target.write_bytes(data)

def _copy_exact(source: Path, target: Path) -> dict[str, Any]:
    data = source.read_bytes()
    _write_immutable(target, data)
    h = _sha_bytes(data)
    return {"path": target.name, "sha256": h, "bytes": len(data), "source_sha256": h, "source_path": str(source), "transformation": "COPY_EXACT"}

def _adobe_delivery_svg(source: Path, target: Path, target_area: float = 16_000_000.0) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8")
    dims = _svg_viewbox(source)
    if not dims or dims[0] <= 0 or dims[1] <= 0:
        raise MarketplaceDeliveryError("ADOBE_SVG_VIEWBOX_INVALID", str(source))
    scale = (target_area / (dims[0] * dims[1])) ** 0.5
    width = dims[0] * scale; height = dims[1] * scale
    root = re.search(r'<svg\b([^>]*)>', text)
    if not root:
        raise MarketplaceDeliveryError("ADOBE_SVG_ROOT_MISSING", str(source))
    attrs = re.sub(r'\s+(?:width|height)=["\'][^"\']*["\']', '', root.group(1))
    replacement = f'<svg{attrs} width="{width:.3f}" height="{height:.3f}">'
    out = (text[:root.start()] + replacement + text[root.end():]).encode("utf-8")
    _write_immutable(target, out)
    return {"path": target.name, "sha256": _sha_bytes(out), "bytes": len(out), "source_sha256": _sha_file(source), "source_path": str(source), "transformation": "EXPLICIT_ARTBOARD_16MP_PRESERVE_VIEWBOX", "delivery_width": round(width,3), "delivery_height": round(height,3), "delivery_area": round(width*height,3)}

def _vectorstock_preview(source: Path, target: Path) -> dict[str, Any]:
    if Image is None:
        raise MarketplaceDeliveryError("PIL_REQUIRED", "VectorStock preview normalization")
    import io
    with Image.open(source) as image:
        image = image.convert("RGB")
        # Deterministic resize: max edge 3000, preserve aspect, LANCZOS
        try:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        except AttributeError:
            resample = Image.BICUBIC  # type: ignore[attr-defined]
        image.thumbnail((3000, 3000), resample)
        if min(image.size) < 1000:
            raise MarketplaceDeliveryError("VECTORSTOCK_JPG_TOO_SMALL", str(image.size))
        dims = list(image.size)
        buf = io.BytesIO(); image.save(buf, format="JPEG", quality=95, subsampling=0, optimize=False, progressive=False)
        data = buf.getvalue()
    _write_immutable(target, data)
    return {"path": target.name, "sha256": _sha_bytes(data), "bytes": len(data), "source_sha256": _sha_file(source), "source_path": str(source), "transformation": "RGB_JPEG_MAX_3000", "dimensions": dims}


def _metadata_for_market(metadata: dict[str, Any], marketplace: str) -> dict[str, Any]:
    # Common metadata from workspace metadata.json, plus marketplace flag
    base = {
        "schema": "die.h01.marketplace-metadata.v1",
        "marketplace": marketplace,
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "keywords": metadata.get("keywords") or [],
        "ai_generated": metadata.get("ai_generated"),
        "ai_disclosure": metadata.get("ai_disclosure"),
        "source_metadata_sha256": metadata.get("metadata_sha256") or _sha_json({k: metadata.get(k) for k in ("title", "description", "keywords", "ai_generated", "ai_disclosure")}),
        "semantic_asset_id": metadata.get("semantic_asset_id"),
    }
    # Marketplace-specific flags
    if marketplace == "MOTIONELEMENTS":
        base["ai_account_required"] = True
        base["ai_generated_flag"] = bool(metadata.get("ai_generated"))
    if marketplace in {"ADOBE", "VECTEEZY", "DREAMSTIME", "VECTORSTOCK", "MOTIONELEMENTS", "123RF"}:
        base["ai_disclosure_required"] = True
    return base


def _deterministic_zip(file_paths: list[Path], zip_path: Path) -> dict[str, Any]:
    import io
    sorted_paths = sorted(file_paths, key=lambda p: p.name)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for member in sorted_paths:
            info = zipfile.ZipInfo(member.name, date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = (0o644 << 16)
            zf.writestr(info, member.read_bytes())
    data = buffer.getvalue()
    _write_immutable(zip_path, data)
    return {"path": zip_path.name, "sha256": _sha_bytes(data), "bytes": len(data), "members": [p.name for p in sorted_paths]}

def _load_workspace_metadata(workspace: Path) -> dict[str, Any]:
    meta_path = workspace / "metadata.json"
    if not meta_path.is_file():
        raise MarketplaceDeliveryError("METADATA_MISSING", str(meta_path))
    meta = _json(meta_path)
    # Ensure required fields; allow minimal but propagate
    # Compute deterministic sha if not present
    if "metadata_sha256" not in meta:
        meta["metadata_sha256"] = _sha_json({k: meta.get(k) for k in ("title", "description", "keywords", "ai_generated", "ai_disclosure", "semantic_asset_id")})
    return meta


def _load_rights_signal(workspace: Path, explicit: Any = None) -> dict[str, Any]:
    if explicit is not None:
        if isinstance(explicit, dict) and "result" in explicit:
            return {"result": str(explicit["result"]), "source": "explicit"}
        if isinstance(explicit, str):
            return {"result": explicit, "source": "explicit"}
    # Try workspace files – hyphen variant is canonical per spec
    for name in ("rights-signal.json", "rights_signal.json", "rights.json"):
        p = workspace / name
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "result" in data:
                    return {"result": str(data["result"]), "source": str(p), "raw": data}
                # If file contains plain string
                if isinstance(data, str):
                    return {"result": data, "source": str(p)}
            except Exception:
                continue
    # Fallback: not evaluated
    return {"result": "NOT_EVALUATED", "source": "missing"}


def _normalize_founder_qc(value: Any) -> str:
    if value is None:
        return "NOT_RECORDED"
    if isinstance(value, dict) and "result" in value:
        return str(value["result"])
    return str(value)


def build_marketplace_package(
    workspace: Any,
    marketplace: str,
    output_root: Any,
    profiles_path: Any | None = None,
    founder_qc: Any = "NOT_RECORDED",
    rights_signal: Any | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace)
    output_root = Path(output_root)
    if marketplace not in PROFILE_SET:
        raise MarketplaceDeliveryError("MARKETPLACE_UNKNOWN", marketplace)
    if not workspace.is_dir():
        raise MarketplaceDeliveryError("WORKSPACE_NOT_FOUND", str(workspace))

    profiles = load_profiles(Path(profiles_path) if profiles_path else None)
    profile = profiles["profiles"][marketplace]

    metadata = _load_workspace_metadata(workspace)
    rights = _load_rights_signal(workspace, rights_signal)
    founder_qc_norm = _normalize_founder_qc(founder_qc)

    # Select sources and prepare target directory
    # Output is deterministic path: output_root / marketplace.lower()
    # Use marketplace as given (upper) for directory to keep deterministic but case-insensitive
    out_dir = output_root / marketplace.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    files_dir = out_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    post = workspace / "postproduction"
    if not post.is_dir():
        raise MarketplaceDeliveryError("POSTPRODUCTION_MISSING", str(post))
    selected: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for rule in profile.get("delivery", []):
        src, target_name, fmt = _select_source(post, rule)
        target = files_dir / target_name
        if marketplace == "ADOBE" and fmt == "SVG":
            info = _adobe_delivery_svg(src, target)
        elif marketplace == "VECTORSTOCK" and fmt == "JPG":
            info = _vectorstock_preview(src, target)
        else:
            info = _copy_exact(src, target)
        info.update({
            "format": fmt,
            "role": rule.get("role"),
            "target": target_name,
            "source_path": str(src),
            "semantic_asset_id": metadata.get("semantic_asset_id"),
            "semantic_identity_effect": "NONE",
        })
        selected.append({"format": fmt, "source_path": str(target), "target": target_name, "role": rule.get("role")})
        artifacts.append(info)

    compat_status, blockers, notes = _compatibility(marketplace, profile, selected)

    # Marketplace-specific container handling
    zip_info: dict[str, Any] | None = None
    # Enforce same-basename where required
    if profile.get("same_basename_required"):
        # Check that all targets share same basename (stem)
        stems = {Path(a["target"]).stem for a in artifacts}
        if len(stems) != 1:
            blockers.append(f"{marketplace}_SAME_BASENAME_VIOLATION")
            compat_status = "REVIEW_REQUIRED"

    # VECTORSTOCK: deterministic ZIP containing EPS
    if marketplace == "VECTORSTOCK":
        eps_artifact = next((a for a in artifacts if a["format"] == "EPS"), None)
        if eps_artifact:
            eps_file = files_dir / eps_artifact["target"]
            zip_path = files_dir / "asset.zip"
            # ZIP contains EPS only deterministically
            zinfo = _deterministic_zip([eps_file], zip_path)
            zinfo["role"] = "PACKAGE_CONTAINER"
            zinfo["format"] = "ZIP"
            zinfo["contains"] = [eps_artifact["target"]]
            zip_info = zinfo
        # Ensure preview jpg is 1000-3000: already checked; if >3000 we noted but not blocked (could normalize)
        # Do not claim normalization, just note

    # MOTIONELEMENTS: deterministic ZIP containing EPS+JPG same basename
    if marketplace == "MOTIONELEMENTS":
        # ZIP must contain both EPS and JPG with same basename
        eps_file = files_dir / "asset.eps"
        jpg_file = files_dir / "asset.jpg"
        # Ensure both exist; if not, fallback to whatever artifacts exist
        zip_inputs: list[Path] = []
        for a in artifacts:
            p = files_dir / a["target"]
            if p.is_file():
                zip_inputs.append(p)
        zip_path = files_dir / "asset.zip"
        if zip_inputs:
            zinfo = _deterministic_zip(zip_inputs, zip_path)
            zinfo["role"] = "PACKAGE_CONTAINER"
            zinfo["format"] = "ZIP"
            zinfo["contains"] = sorted([p.name for p in zip_inputs])
            zip_info = zinfo
        # Verify ZIP contains same basename
        if zip_info and len({Path(n).stem for n in zip_info["contains"]}) != 1:
            blockers.append("MOTIONELEMENTS_ZIP_BASENAME_MISMATCH")
            compat_status = "REVIEW_REQUIRED"

    # DREAMSTIME: fallback logic already handled via _select_source; ensure primary JPG present
    # ADOBE: sidecar metadata handling
    # VECTEEZY: declare target without cert claim – already in notes

    # Re-evaluate compat after structural checks
    if blockers:
        compat_status = "REVIEW_REQUIRED"

    # submission_eligible logic
    rights_pass = rights.get("result") == "PASS"
    founder_pass = founder_qc_norm == "PASS"
    compat_pass = compat_status == "COMPATIBLE"
    submission_eligible = bool(compat_pass and rights_pass and founder_pass)

    # Build marketplace metadata sidecar
    market_metadata = _metadata_for_market(metadata, marketplace)
    sidecar_path = files_dir / "metadata.json"
    # Deterministic JSON
    sidecar_bytes = (json.dumps(market_metadata, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _write_immutable(sidecar_path, sidecar_bytes)
    sidecar_sha = _sha_bytes(sidecar_bytes)

    # Write manifest
    manifest: dict[str, Any] = {
        "schema": "die.h01.marketplace-delivery-package.v1",
        "marketplace": marketplace,
        "profile_schema": profiles.get("schema"),
        "policy_date": profiles.get("policy_date"),
        "workspace": str(workspace),
        "output_dir": str(out_dir),
        "semantic_asset_id": metadata.get("semantic_asset_id"),
        "artifacts": sorted(artifacts, key=lambda x: x["target"]),
        "sidecar_metadata": {
            "path": "files/metadata.json",
            "sha256": sidecar_sha,
            "bytes": len(sidecar_bytes),
            "content": market_metadata,
        },
        "source_hashes": {a["target"]: a["sha256"] for a in artifacts},
        "source_metadata_sha256": metadata.get("metadata_sha256"),
        "common_metadata": metadata,
        "compatibility": {
            "status": compat_status,
            "blockers": sorted(blockers),
            "notes": sorted(notes),
            "result": "PASS" if compat_pass else "REVIEW_REQUIRED",
        },
        "rights_signal": rights,
        "founder_qc": founder_qc_norm,
        "submission_eligible": submission_eligible,
        # Action surfaces must be NONE
        "login_action": "NONE",
        "upload_action": "NONE",
        "submission_action": "NONE",
        "publication_action": "NONE",
        "spend_action": "NONE",
        # EPS compatibility disclosure (honest)
        "eps_compatibility": profile.get("eps_compatibility") or ("ILLUSTRATOR_10_STRUCTURAL_TARGET_ONLY" if marketplace == "VECTEEZY" else None),
        "native_illustrator_save_certified": False,
        "deterministic": True,
        "semantic_identity_effect": "NONE",
    }
    if zip_info:
        manifest["package_zip"] = {k: v for k, v in zip_info.items() if k not in ("source_path",)}
        # Also include ZIP in artifacts list for package completeness but keep separate
        manifest["package_container"] = profile.get("package_container")

    # Add same-basename flag
    if profile.get("same_basename_required"):
        manifest["same_basename_required"] = True
        stems = {Path(a["target"]).stem for a in artifacts}
        manifest["same_basename_actual"] = len(stems) == 1
        manifest["same_basename_stems"] = sorted(stems)
    else:
        manifest["same_basename_required"] = False

    # Include AI disclosure fields explicitly
    manifest["ai_disclosure"] = market_metadata.get("ai_disclosure")
    manifest["ai_generated"] = market_metadata.get("ai_generated")

    # Stable non-circular hash: manifest file contains no self-hash.
    # The file hash is stored only in the separate receipt.
    manifest_path = out_dir / "manifest.json"
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _write_immutable(manifest_path, manifest_bytes)
    manifest_file_sha = _sha_bytes(manifest_bytes)
    manifest_content_sha = _sha_json(manifest)

    receipt_path = out_dir / "delivery.receipt.json"
    receipt = {
        "schema": "die.h01.marketplace-delivery-receipt.v1",
        "marketplace": marketplace,
        "result": compat_status,
        "submission_eligible": submission_eligible,
        "manifest_content_sha256": manifest_content_sha,
        "manifest_file_sha256": manifest_file_sha,
        "manifest_sha256": manifest_file_sha,
        "artifacts_sha256": {a["target"]: a["sha256"] for a in artifacts},
        "sidecar_sha256": sidecar_sha,
        "login_action": "NONE",
        "upload_action": "NONE",
        "submission_action": "NONE",
        "publication_action": "NONE",
        "spend_action": "NONE",
    }
    if zip_info:
        receipt["zip_sha256"] = zip_info["sha256"]
        receipt["zip_path"] = f"files/{zip_info['path']}"
    receipt_bytes = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _write_immutable(receipt_path, receipt_bytes)
    # Enrich returned dict without mutating file bytes (non-circular)
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_file_sha256"] = manifest_file_sha
    manifest["manifest_content_sha256"] = manifest_content_sha
    manifest["manifest_sha256"] = manifest_file_sha
    manifest["receipt_path"] = str(receipt_path)
    manifest["receipt_sha256"] = _sha_bytes(receipt_bytes)

    return manifest


def build_all_marketplace_packages(
    workspace: Any,
    output_root: Any,
    profiles_path: Any | None = None,
    founder_qc: Any = "NOT_RECORDED",
    rights_signal: Any | None = None,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for mp in sorted(PROFILE_SET):
        results[mp] = build_marketplace_package(workspace, mp, output_root, profiles_path, founder_qc, rights_signal)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="H01-134 Marketplace Delivery Adapter v1 – deterministic local packaging")
    parser.add_argument("--workspace", required=True, help="Path to postproduction workspace (contains metadata.json, master.eps, preview.jpg, etc.)")
    parser.add_argument("--output", required=True, help="Output root for marketplace packages")
    parser.add_argument("--marketplace", help="Single marketplace (ADOBE/VECTEEZY/123RF/DREAMSTIME/VECTORSTOCK/MOTIONELEMENTS); if omitted, builds all")
    parser.add_argument("--profiles", help="Path to marketplace-delivery-profiles.v1.json")
    parser.add_argument("--founder-qc", default="NOT_RECORDED", help="Founder QC result: PASS/FAIL/NOT_RECORDED")
    parser.add_argument("--rights-result", help="Rights signal result: PASS/REVIEW_REQUIRED/BLOCK/NOT_EVALUATED")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    rights_signal = {"result": args.rights_result} if args.rights_result else None

    if args.marketplace:
        mp = args.marketplace.upper()
        manifest = build_marketplace_package(workspace, mp, output_root, args.profiles, args.founder_qc, rights_signal)
        print(json.dumps({"marketplace": mp, "submission_eligible": manifest["submission_eligible"], "compatibility": manifest["compatibility"]["status"], "manifest": manifest["manifest_path"]}, indent=2))
    else:
        results = build_all_marketplace_packages(workspace, output_root, args.profiles, args.founder_qc, rights_signal)
        for mp, manifest in sorted(results.items()):
            print(f"{mp}: eligible={manifest['submission_eligible']} compat={manifest['compatibility']['status']} -> {manifest['output_dir']}")


if __name__ == "__main__":
    main()
