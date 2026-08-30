#!/usr/bin/env python3
"""CLI for first-class DIE Asset QA v1 universal and platform preflight."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from income_os_bridge import asset_qa, m001_asset_qa


def _load_object(path: pathlib.Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise asset_qa.AssetQAError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise asset_qa.AssetQAError(f"expected JSON object: {path}")
    return value


def _write(receipt: dict, output: pathlib.Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(prog="die_asset_qa")
    sub = parser.add_subparsers(dest="command", required=True)

    universal = sub.add_parser("m001-universal")
    universal.add_argument("--manifest", required=True)
    universal.add_argument("--workspace", required=True)
    universal.add_argument("--output", required=True)
    universal.add_argument("--min-assets", type=int, required=True)
    universal.add_argument("--max-assets", type=int, required=True)
    universal.add_argument("--min-pass-rate", type=float, default=0.80)

    platform = sub.add_parser("platform-preflight")
    platform.add_argument("--package", required=True)
    platform.add_argument("--profile", required=True)
    platform.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.command == "m001-universal":
            receipt = asset_qa.evaluate_m001_manifest(
                pathlib.Path(args.manifest),
                pathlib.Path(args.workspace),
                min_assets=args.min_assets,
                max_assets=args.max_assets,
                min_pass_rate=args.min_pass_rate,
            )
        else:
            receipt = asset_qa.evaluate_platform_preflight(
                _load_object(pathlib.Path(args.package)),
                pathlib.Path(args.profile),
            )
        _write(receipt, pathlib.Path(args.output))
    except (asset_qa.AssetQAError, m001_asset_qa.QAError) as exc:
        print(json.dumps({"batch_state": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if receipt["batch_state"] == "PASS":
        return 0
    return 2 if receipt["batch_state"] == "BLOCKED_REVIEW" else 3


if __name__ == "__main__":
    raise SystemExit(main())
