"""Hermes profile delegate to the repo-canonical operator prepare entrypoint.

This wrapper contains no OS- or drive-specific DIE root. Hermes cron workdir may
be the canonical repo root, or DIE_HOME may be supplied explicitly.
"""
from __future__ import annotations

import os
import runpy
from pathlib import Path


def resolve_die_home() -> Path:
    raw = os.environ.get("DIE_HOME")
    root = Path(raw) if raw else Path.cwd()
    root = root.resolve()
    target = root / "bin" / "die_operator_prepare.py"
    if not target.is_file():
        raise RuntimeError(f"E_CANONICAL_PREPARE_MISSING:{target}")
    return root


if __name__ == "__main__":
    die_home = resolve_die_home()
    runpy.run_path(str(die_home / "bin" / "die_operator_prepare.py"), run_name="__main__")