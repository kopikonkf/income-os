#!/usr/bin/env bash
set -euo pipefail

ROOT=${UP001_RUNTIME_ROOT:-/var/lib/die/postprocess/upscale}
VENV="$ROOT/venv"
MODEL_DIR=${UP001_MODEL_DIR:-/var/lib/die/models/realesrgan}
MODEL="$MODEL_DIR/realesr-general-x4v3.pth"
MODEL_URL="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
MODEL_SHA256="8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292"

mkdir -p "$ROOT" "$MODEL_DIR"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/pip" install \
  numpy==2.5.2 pillow==12.3.0 opencv-python-headless==4.11.0.86 \
  scipy==1.18.1 scikit-image==0.26.0 addict==2.4.0 future==1.0.0 \
  lmdb==2.3.0 pyyaml==6.0.3 requests==2.34.2 tqdm==4.70.0 yapf==0.43.0
"$VENV/bin/pip" install \
  torch==2.13.0+cpu torchvision==0.28.0+cpu \
  --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/pip" install --no-build-isolation --no-deps basicsr==1.4.2
"$VENV/bin/pip" install --no-build-isolation --no-deps realesrgan==0.3.0

if [[ ! -f "$MODEL" ]]; then
  tmp="$MODEL.tmp"
  curl -L --fail --retry 2 --connect-timeout 8 --max-time 60 -o "$tmp" "$MODEL_URL"
  mv "$tmp" "$MODEL"
fi
printf '%s  %s\n' "$MODEL_SHA256" "$MODEL" | sha256sum -c -
chmod 0644 "$MODEL"

"$VENV/bin/python" - <<'PY'
import sys, types
from torchvision.transforms.functional import rgb_to_grayscale
shim = types.ModuleType("torchvision.transforms.functional_tensor")
shim.rgb_to_grayscale = rgb_to_grayscale
sys.modules.setdefault("torchvision.transforms.functional_tensor", shim)
from basicsr.archs.srvgg_arch import SRVGGNetCompact  # noqa: F401
from realesrgan import RealESRGANer  # noqa: F401
import torch
assert torch.cuda.is_available() is False
print("UP001_RUNTIME_IMPORT_PASS")
PY
