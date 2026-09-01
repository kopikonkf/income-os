#!/usr/bin/env python3
"""CPU-only RealESRGAN backend matching the migrated Windows reference."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import types


def _install_torchvision_compat() -> None:
    """BasicSR 1.4.2 still imports functional_tensor on modern torchvision."""
    try:
        import torchvision.transforms.functional_tensor  # type: ignore  # noqa: F401
    except ImportError:
        from torchvision.transforms.functional import rgb_to_grayscale
        shim = types.ModuleType("torchvision.transforms.functional_tensor")
        shim.rgb_to_grayscale = rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = shim


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", required=True)
    args = ap.parse_args()

    _install_torchvision_compat()
    import cv2
    import numpy as np
    from PIL import Image
    from basicsr.archs.srvgg_arch import SRVGGNetCompact
    from realesrgan import RealESRGANer

    src = Image.open(args.input).convert("RGBA")
    model = SRVGGNetCompact(
        num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32,
        upscale=4, act_type="prelu",
    )
    upsampler = RealESRGANer(
        scale=4,
        model_path=str(Path(args.model).resolve()),
        model=model,
        tile=512,
        tile_pad=10,
        pre_pad=0,
        half=False,
        gpu_id=None,
    )
    rgb = np.array(src.convert("RGB"))
    up, _ = upsampler.enhance(rgb, outscale=4)
    alpha = np.array(src)[:, :, 3]
    alpha_up = cv2.resize(alpha, (up.shape[1], up.shape[0]), interpolation=cv2.INTER_CUBIC)
    _, alpha_up = cv2.threshold(alpha_up, 200, 255, cv2.THRESH_BINARY)
    alpha_up = cv2.GaussianBlur(alpha_up, (5, 5), 1.2)
    out = np.dstack([up, alpha_up])
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGBA").save(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
