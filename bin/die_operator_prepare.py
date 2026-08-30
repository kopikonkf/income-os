#!/usr/bin/env python3
"""Canonical OS-neutral DIE operator prepare entrypoint.

Default mode preserves the current v1 PROPOSE_ONLY cron behavior. `--mode v2`
uses the receipt-driven Operator v2 prepare pipeline. No machine-specific drive
path is encoded here.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_MODULE_LOAD:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--mode", choices=["v1-compat", "v2"], default="v1-compat")
    known, rest = ap.parse_known_args(argv)
    if known.mode == "v1-compat":
        legacy = _load("die_operator_tick_compat", ROOT / "bin" / "die_operator_tick.py")
        return legacy.main(["prepare", *rest])
    v2 = _load("die_operator_v2_prepare", ROOT / "company" / "die-agents" / "hermes" / "operator-v2" / "prepare_operator_v2.py")
    return v2.main(rest)


if __name__ == "__main__":
    raise SystemExit(main())