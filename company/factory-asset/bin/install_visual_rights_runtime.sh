#!/usr/bin/env bash
set -euo pipefail

VENV=/opt/die/factory-asset-rights/venv
MODEL_DIR=/var/lib/die/models/clip
MODEL_SHA=afeb0e10f9e5a86da6080e35cf09123aca3b358a0c3e3b6c78a7b63bc04b6762
CLIP_COMMIT=d05afc436d78f1c48dc0dbf8e5980a9d471f35f6

sudo -n apt-get update -qq
sudo -n apt-get install -y -qq tesseract-ocr python3-venv
sudo -n mkdir -p /opt/die/factory-asset-rights "$MODEL_DIR"
if [ ! -x "$VENV/bin/python" ]; then
  sudo -n python3 -m venv "$VENV"
fi
sudo -n "$VENV/bin/pip" install --upgrade pip
sudo -n "$VENV/bin/pip" install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.0+cpu' 'torchvision==0.29.0+cpu'
sudo -n "$VENV/bin/pip" install 'pillow==11.3.0' 'ftfy==6.3.1' 'regex==2026.9.3' 'tqdm==4.70.0' "git+https://github.com/openai/CLIP.git@${CLIP_COMMIT}"
sudo -n chown -R "$(id -un)":die-runtime "$MODEL_DIR"
"$VENV/bin/python" - <<'PY'
import clip, hashlib, pathlib
model, _ = clip.load('RN50', device='cpu', download_root='/var/lib/die/models/clip')
files = list(pathlib.Path('/var/lib/die/models/clip').glob('RN50.pt'))
if len(files) != 1:
    raise SystemExit('E_CLIP_CHECKPOINT_MISSING')
p = files[0]
h = hashlib.sha256(p.read_bytes()).hexdigest()
expected = 'afeb0e10f9e5a86da6080e35cf09123aca3b358a0c3e3b6c78a7b63bc04b6762'
if h != expected:
    raise SystemExit(f'E_CLIP_CHECKPOINT_HASH:{h}')
print(f'CLIP_RN50_READY sha256={h}')
PY
"$VENV/bin/python" - <<'PY'
import torch, torchvision
if '+cpu' not in torch.__version__:
    raise SystemExit(f'E_TORCH_NOT_CPU:{torch.__version__}')
print(f'torch={torch.__version__} torchvision={torchvision.__version__}')
PY
tesseract --version | head -1