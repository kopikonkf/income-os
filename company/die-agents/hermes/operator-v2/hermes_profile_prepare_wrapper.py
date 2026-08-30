"""Hermes profile delegate to the repo-canonical operator prepare entrypoint.

No OS- or drive-specific DIE root is encoded. The wrapper resolves DIE_HOME or
uses the cron workdir. During staged migration it can fall back to the legacy
canonical tick in the same root if the new prepare entrypoint has not yet been
published into that live root. Linux activation does not require this wrapper.
"""
from __future__ import annotations

import importlib.util
import os
import runpy
from pathlib import Path


def resolve_die_home() -> Path:
    raw = os.environ.get("DIE_HOME")
    root = (Path(raw) if raw else Path.cwd()).resolve()
    if not (root / "bin").is_dir():
        raise RuntimeError(f"E_DIE_ROOT_INVALID:{root}")
    return root


def main() -> int:
    die_home = resolve_die_home()
    canonical = die_home / "bin" / "die_operator_prepare.py"
    if canonical.is_file():
        runpy.run_path(str(canonical), run_name="__main__")
        return 0
    legacy = die_home / "bin" / "die_operator_tick.py"
    if not legacy.is_file():
        raise RuntimeError(f"E_OPERATOR_PREPARE_MISSING:{canonical};E_LEGACY_TICK_MISSING:{legacy}")
    spec = importlib.util.spec_from_file_location("die_operator_tick_profile_compat", legacy)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_LEGACY_LOAD:{legacy}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return int(module.main(["prepare"]))


if __name__ == "__main__":
    raise SystemExit(main())