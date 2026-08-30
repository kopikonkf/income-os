#!/usr/bin/env python3
"""CLI for deterministic Asset QC v1 SHADOW evaluation."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from income_os_bridge import asset_qc


def _write(receipt: dict, output: pathlib.Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(prog="die_asset_qc")
    parser.add_argument("--qa-receipt", required=True)
    parser.add_argument("--observation", required=True)
    parser.add_argument("--rubric", default=str(ROOT / "company" / "contracts" / "die.asset.qc-rubric.v1.json"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        receipt = asset_qc.evaluate(
            pathlib.Path(args.qa_receipt),
            pathlib.Path(args.observation),
            pathlib.Path(args.rubric),
        )
        _write(receipt, pathlib.Path(args.output))
    except asset_qc.AssetQCError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["recommendation"] == "PASS_RECOMMENDED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
