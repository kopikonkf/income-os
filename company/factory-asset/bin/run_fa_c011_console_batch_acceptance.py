#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from console_batch_acceptance import run_console_batch_acceptance  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FA-C011 deterministic zero-provider Factory Console batch acceptance")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    result = run_console_batch_acceptance(Path(args.workspace))
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
