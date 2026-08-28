
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-007 — QC Benchmark Render pipeline (2 concepts).

Per blueprint U1 raster-only CPU-only:
  raw (pure white bg) -> cutout -> PNG transparent master
  -> composite white -> JPG derivative -> RealESRGAN x4 (realesr-general-x4v3)
Order note: we upscale the MASTER (alpha preserved) so both PNG and JPG are 4x;
JPG derived from upscaled composite.

QC report -> outputs/qc/qc_report_batch01.json
Checks: edge_cleanliness, silhouette_test(64px proxy), text_check(heuristic),
refraction_check, texture_check, resolution_spec.
"""
import json
import pathlib
import sys

import cv2
import numpy as np
from PIL import Image

QC_DIR = engine_paths.OUTPUTS_DIR / "assets" / "qc"
REPORT = engine_paths.OUTPUTS_DIR / "qc" / "qc_report_batch01.json"

ASSETS = [
    {
        "asset_id": "AST-SEED-000027-0001-0001-0001",
        "concept_id": "CON-SEED-000027-0001-0001",
        "raw": QC_DIR / "AST-SEED-000027-0001-0001-0001_raw.png",
        "checks": ["edge_cleanliness", "silhouette", "texture"],
    },
    {
        "asset_id": "AST-SEED-000021-0001-0001-0001",
        "concept_id": "CON-SEED-000021-0001-0001",
        "raw": QC_DIR / "AST-SEED-000021-0001-0001-0001_raw.png",
        "checks": ["edge_cleanliness", "silhouette", "refraction"],
    },
]


def cutout(img: Image.Image) -> Image.Image:
    """Remove pure-white background connected to borders; return RGBA."""
    rgb = np.array(img.convert("RGB"))
    h, w = rgb.shape[:2]
    near_white = np.all(rgb >= 235, axis=2).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(near_white, connectivity=4)
    bg = np.zeros((h, w), dtype=bool)
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        touches = x == 0 or y == 0 or x + ww >= w or y + hh >= h
        # large border-connected white regions = background
        if touches and area > 0.01 * h * w:
            bg |= labels == i
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # feather 1px to soften stair-step
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    out = np.dstack([rgb, alpha])
    return Image.fromarray(out, "RGBA")


def autocrop_alpha(img: Image.Image, pad: int = 32) -> Image.Image:
    a = np.array(img)[:, :, 3]
    ys, xs = np.where(a > 8)
    if len(xs) == 0:
        return img
    x0, x1 = max(0, xs.min() - pad), min(img.width, xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(img.height, ys.max() + pad)
    return img.crop((x0, y0, x1, y1))


def upscale_x4(rgba: Image.Image):
    """RealESRGAN x4 on RGB; alpha upscaled bicubic then cleaned."""
    from basicsr.archs.srvgg_arch import SRVGGNetCompact
    from realesrgan import RealESRGANer

    model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64,
                            num_conv=32, upscale=4, act_type="prelu")
    upsampler = RealESRGANer(scale=4, model_path="realesr-general-x4v3.pth",
                             model=model, tile=512, tile_pad=10, pre_pad=0,
                             half=False, gpu_id=None)
    rgb = np.array(rgba.convert("RGB"))
    up, _ = upsampler.enhance(rgb, outscale=4)
    a = np.array(rgba)[:, :, 3]
    a_up = cv2.resize(a, (up.shape[1], up.shape[0]), interpolation=cv2.INTER_CUBIC)
    _, a_up = cv2.threshold(a_up, 200, 255, cv2.THRESH_BINARY)
    a_up = cv2.GaussianBlur(a_up, (5, 5), 1.2)
    out = np.dstack([up, a_up])
    return Image.fromarray(out, "RGBA")


def qc_edge_cleanliness(rgba: Image.Image) -> dict:
    """Detect white halo / jaggedness at alpha boundary."""
    arr = np.array(rgba)
    a = arr[:, :, 3]
    edge = ((a > 10) & (a < 245)).astype(np.uint8)
    semi_ratio = float(edge.sum()) / max(1, float((a > 10).sum()))
    # halo: pixels just outside object that are near-white AND opaque-ish fringe
    dil = cv2.dilate((a > 128).astype(np.uint8), np.ones((5, 5), np.uint8))
    fringe = ((dil == 1) & (a <= 128)).astype(np.uint8)
    fringe_px = int(fringe.sum())
    return {"semi_transparent_edge_ratio": round(semi_ratio, 4),
            "fringe_px_outside": fringe_px,
            "pass": bool(semi_ratio < 0.15 and fringe_px < 50000)}


def qc_silhouette(rgba: Image.Image) -> dict:
    """64px proxy: object coverage fraction within sane range."""
    small = rgba.resize((64, 64))
    a = np.array(small)[:, :, 3]
    coverage = float((a > 40).sum()) / (64 * 64)
    return {"coverage_at_64px": round(coverage, 3),
            "thumbnail_saved": True,
            "pass": bool(0.08 <= coverage <= 0.85)}


def qc_texture(rgba_orig_small: Image.Image, rgba_up: Image.Image) -> dict:
    """Laplacian variance ratio: upscale must not smear detail."""
    g0 = np.array(rgba_orig_small.convert("L"), dtype=np.float32)
    g1 = np.array(rgba_up.convert("L").resize(
        (rgba_orig_small.width * 2, rgba_orig_small.height * 2)), dtype=np.float32)
    v0 = cv2.Laplacian(g0, cv2.CV_32F).var()
    v1 = cv2.Laplacian(cv2.resize(g1, (g0.shape[1], g0.shape[0])), cv2.CV_32F).var()
    ratio = v1 / max(v0, 1e-6)
    return {"laplacian_var_original": round(float(v0), 1),
            "laplacian_var_upscaled_norm": round(float(ratio), 3),
            "pass": bool(ratio > 0.5)}


def qc_refraction(raw_rgb: np.ndarray, rgba_up: Image.Image) -> dict:
    """Glass edge survival: gradient energy along high-contrast contours."""
    gray = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2GRAY)
    edges_raw = cv2.Canny(gray, 80, 160)
    up_gray = np.array(rgba_up.convert("L"))
    edges_up = cv2.Canny(up_gray, 80, 160)
    e_raw = float((edges_raw > 0).sum())
    scale = (up_gray.shape[0] * up_gray.shape[1]) / max(1.0, float(gray.shape[0] * gray.shape[1]))
    e_up_norm = float((edges_up > 0).sum()) / scale
    retention = e_up_norm / max(e_raw, 1.0)
    return {"edge_pixels_raw": int(e_raw),
            "edge_retention_after_x4": round(retention, 3),
            "pass": bool(0.35 <= retention <= 3.0)}


def qc_text_heuristic(rgba: Image.Image) -> dict:
    """No tesseract on host: high-frequency small-component heuristic proxy.
    Honest limitation recorded; visual review still required."""
    g = np.array(rgba.convert("L"))
    bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 15, 8)
    n, _, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    tiny = sum(1 for i in range(1, n) if 4 <= stats[i][4] <= 120)
    return {"method": "connected_component_proxy (no tesseract on host)",
            "tiny_components": int(tiny),
            "pass": None, "needs_visual_review": True}


def main() -> None:
    results = []
    for spec in ASSETS:
        raw_path = spec["raw"]
        img = Image.open(raw_path)
        raw_rgb = np.array(img.convert("RGB"))

        cut = autocrop_alpha(cutout(img))
        print(f"[{spec['asset_id']}] cutout done {cut.size}")

        up = upscale_x4(cut)
        print(f"[{spec['asset_id']}] upscale done {up.size}")

        png_master = QC_DIR / f"{spec['asset_id']}.png"
        jpg_deriv = QC_DIR / f"{spec['asset_id']}.jpg"
        thumb = QC_DIR / f"{spec['asset_id']}_thumb64.png"
        up.save(png_master)
        white = Image.new("RGB", up.size, (255, 255, 255))
        white.paste(up, mask=up.split()[3])
        white.save(jpg_deriv, quality=92)
        up.resize((64, 64)).save(thumb)

        res = {
            "asset_id": spec["asset_id"],
            "concept_id": spec["concept_id"],
            "master_png": str(png_master),
            "jpg_derivative": str(jpg_deriv),
            "resolution": {"w": up.width, "h": up.height},
        }
        res["qc"] = {}
        res["qc"]["edge_cleanliness"] = qc_edge_cleanliness(up)
        res["qc"]["silhouette_test"] = qc_silhouette(up)
        res["qc"]["text_check"] = qc_text_heuristic(up)
        if "refraction" in spec["checks"]:
            res["qc"]["refraction_check"] = qc_refraction(raw_rgb, up)
        if "texture" in spec["checks"]:
            res["qc"]["texture_check"] = qc_texture(cut, up)
        res["qc"]["resolution_spec"] = {
            "longest_side_px": max(up.width, up.height),
            "required_min": 4000,
            "pass": bool(max(up.width, up.height) >= 4000),
        }

        hard_keys = [k for k in res["qc"] if res["qc"][k].get("pass") is not None]
        res["status"] = ("PASS" if all(res["qc"][k]["pass"] for k in hard_keys) else "FAIL")
        res["status_note"] = (
            "hard checks: " + ", ".join(f"{k}={res['qc'][k]['pass']}" for k in hard_keys)
            + "; text_check needs visual review (no OCR on host)"
        )
        results.append(res)
        print(f"[{spec['asset_id']}] STATUS={res['status']}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "schema": "oae.qc.benchmark.v1",
        "pipeline": "cutout -> PNG master -> RealESRGAN x4 -> JPG derivative",
        "model": "realesr-general-x4v3 tile512 cpu",
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"report: {REPORT}")


if __name__ == "__main__":
    main()
