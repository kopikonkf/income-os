#!/usr/bin/env python3
"""Validate one semantic state request. This command never writes canonical state."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

BRIDGE = pathlib.Path(__file__).resolve().parents[1] / "bridge"
sys.path.insert(0, str(BRIDGE))

from income_os_bridge import state_request  # noqa: E402


def _load_payload(input_path: str | None) -> object:
    raw = (
        pathlib.Path(input_path).read_text(encoding="utf-8-sig")
        if input_path
        else sys.stdin.read().lstrip("\ufeff")
    )
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(prog="die_state_request")
    parser.add_argument(
        "--input",
        help="JSON request file; omit to read one JSON object from stdin",
    )
    args = parser.parse_args()

    try:
        request = _load_payload(args.input)
        result = state_request.validate_and_normalize(request)
    except json.JSONDecodeError as exc:
        print(
            json.dumps(
                {"accepted": False, "code": "E_REQUEST_INVALID", "message": str(exc)},
                ensure_ascii=False,
            )
        )
        return 2
    except state_request.StateRequestError as exc:
        print(
            json.dumps(
                {"accepted": False, "code": exc.code, "message": exc.message},
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
