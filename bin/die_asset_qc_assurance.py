#!/usr/bin/env python3
"""CLI for Asset QC calibration, SHADOW queue, drift audit, and delegation evaluation."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from income_os_bridge import asset_qc_assurance


def _load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise asset_qc_assurance.AssetQCAssuranceError(f"expected JSON object: {path}")
    return value


def _write(value: dict, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(prog="die_asset_qc_assurance")
    sub = parser.add_subparsers(dest="command", required=True)

    shadow = sub.add_parser("shadow")
    shadow.add_argument("--label", required=True)
    shadow.add_argument("--qc-receipt", required=True)
    shadow.add_argument("--rubric", default=str(ROOT / "company" / "contracts" / "die.asset.qc-rubric.v1.json"))
    shadow.add_argument("--output", required=True)

    calibrate = sub.add_parser("calibrate")
    calibrate.add_argument("--label", action="append", required=True)
    calibrate.add_argument("--qc-receipt", action="append", required=True)
    calibrate.add_argument("--rubric", default=str(ROOT / "company" / "contracts" / "die.asset.qc-rubric.v1.json"))
    calibrate.add_argument("--output", required=True)

    audit = sub.add_parser("audit")
    audit.add_argument("--baseline", required=True)
    audit.add_argument("--current", required=True)
    audit.add_argument("--audit-policy", default=str(ROOT / "company" / "contracts" / "qc" / "die.asset.qc-audit-policy.v1.json"))
    audit.add_argument("--output", required=True)

    delegation = sub.add_parser("delegation")
    delegation.add_argument("--policy", required=True)
    delegation.add_argument("--calibration", required=True)
    delegation.add_argument("--asset-class", required=True)
    delegation.add_argument("--marketplace", required=True)
    delegation.add_argument("--now", required=True)
    delegation.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.command == "shadow":
            result = asset_qc_assurance.build_shadow_case(pathlib.Path(args.label), pathlib.Path(args.qc_receipt), pathlib.Path(args.rubric))
        elif args.command == "calibrate":
            result = asset_qc_assurance.build_calibration_report([pathlib.Path(value) for value in args.label], [pathlib.Path(value) for value in args.qc_receipt], pathlib.Path(args.rubric))
        elif args.command == "audit":
            result = asset_qc_assurance.compare_calibration_reports(_load(pathlib.Path(args.baseline)), _load(pathlib.Path(args.current)), pathlib.Path(args.audit_policy))
        else:
            result = asset_qc_assurance.evaluate_delegation(pathlib.Path(args.policy), _load(pathlib.Path(args.calibration)), asset_class=args.asset_class, marketplace=args.marketplace, now=args.now)
        _write(result, pathlib.Path(args.output))
    except (asset_qc_assurance.AssetQCAssuranceError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
