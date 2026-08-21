#!/usr/bin/env python3
"""Commit one normalized decision through the stateless DIE Decision Gateway."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge"
sys.path.insert(0, str(BRIDGE))

import die_event  # noqa: E402
from income_os_bridge import decision_gateway  # noqa: E402


def _load_payload(input_path: str | None) -> object:
    raw = (
        pathlib.Path(input_path).read_text(encoding="utf-8-sig")
        if input_path
        else sys.stdin.read().lstrip("\ufeff")
    )
    return json.loads(raw)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="die_decision_gateway")
    parser.add_argument(
        "--input",
        help="normalized validation-result JSON; omit to read one object from stdin",
    )
    args = parser.parse_args()

    try:
        payload = _load_payload(args.input)
    except (OSError, json.JSONDecodeError):
        result = decision_gateway.rejected_result(
            "E_GATEWAY_INPUT_INVALID",
            "input could not be read as one JSON object",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    result = decision_gateway.process(
        payload,
        writer=die_event.commit_normalized_decision,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "committed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
