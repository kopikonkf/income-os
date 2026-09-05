#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "company/factory-asset/lib/synthetic_throughput.py"
spec = importlib.util.spec_from_file_location("fa120_synthetic_throughput_cli", MODULE)
if spec is None or spec.loader is None:
    raise SystemExit("FA120_MODULE_LOAD_FAILED")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def main() -> int:
    parser = argparse.ArgumentParser(description="FA-120 zero-provider synthetic throughput/backpressure harness")
    parser.add_argument("--staging-root", required=True)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    result = mod.run_synthetic_throughput_acceptance(args.staging_root)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        out = Path(args.receipt)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
