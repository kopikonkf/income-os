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

from fa122_load_evaluator import evaluate_fa122  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FA-122 live-load unique-master, QA, duplicate, resource and policy evidence")
    parser.add_argument("--live-result", required=True)
    parser.add_argument("--contract", default=str(ROOT / "company/factory-asset/contracts/fa122-live-load.v1.json"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = evaluate_fa122(live_result_path=args.live_result, contract_path=args.contract, output_path=args.output)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
