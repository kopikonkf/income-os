#!/usr/bin/env python3
"""CLI for deterministic M-001 universal asset QA."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from income_os_bridge import m001_asset_qa


def main() -> int:
    parser = argparse.ArgumentParser(prog="m001_asset_qa")
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--manifest", required=True)
    evaluate.add_argument("--workspace", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.add_argument("--min-assets", type=int, required=True)
    evaluate.add_argument("--max-assets", type=int, required=True)
    evaluate.add_argument("--min-pass-rate", type=float, default=0.80)
    args = parser.parse_args()
    try:
        workspace = pathlib.Path(args.workspace)
        receipt = m001_asset_qa.evaluate_manifest(
            pathlib.Path(args.manifest),
            workspace,
            min_assets=args.min_assets,
            max_assets=args.max_assets,
            min_pass_rate=args.min_pass_rate,
        )
        m001_asset_qa.write_receipt(receipt, pathlib.Path(args.output), workspace)
    except m001_asset_qa.QAError as exc:
        print(
            json.dumps(
                {"batch_state": "BLOCKED", "error": str(exc)}, ensure_ascii=False
            )
        )
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if receipt["batch_state"] == "PASS":
        return 0
    return 3 if receipt["batch_state"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
