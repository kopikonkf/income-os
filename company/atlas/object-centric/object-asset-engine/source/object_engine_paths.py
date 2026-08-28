"""OS-neutral path contract for the Object Asset Engine.

Source is Git-tracked under /srv/die. Mutable engine data is always outside the
repo under DIE_OBJECT_ENGINE_ROOT (Linux default /var/lib/die/atlas/object-asset-engine).
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ROOT = "/var/lib/die/atlas/object-asset-engine"
ROOT = Path(os.environ.get("DIE_OBJECT_ENGINE_ROOT", DEFAULT_ROOT)).expanduser().resolve()
DB_DIR = ROOT / "db"
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"
STATE_DIR = ROOT / "state"
CANON_DB = DB_DIR / "object_asset_engine.db"
SEED_LIBRARY_DB = DB_DIR / "seed_library.db"
CONFIG_FILE = ROOT / "config.json"
GEMINI_KEY_FILE = os.environ.get("DIE_OBJECT_ENGINE_GEMINI_KEY_FILE", "").strip()

def require_gemini_key_file() -> Path:
    if not GEMINI_KEY_FILE:
        raise RuntimeError("DIE_OBJECT_ENGINE_GEMINI_KEY_FILE_REQUIRED")
    path = Path(GEMINI_KEY_FILE).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError("DIE_OBJECT_ENGINE_GEMINI_KEY_FILE_MISSING")
    return path

def ensure_runtime_dirs() -> None:
    for path in (DB_DIR, DATA_DIR, OUTPUTS_DIR, REPORTS_DIR, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)
