#!/usr/bin/env python3
"""CLI for the governed M-001 U1 closed-loop mission compiler."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))

from income_os_bridge import m001_loop


def _validated(args: argparse.Namespace, default_home: pathlib.Path) -> dict:
    return m001_loop.validate_authorization(
        pathlib.Path(args.request),
        default_home / "state" / "DECISIONS.jsonl",
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="m001_loop")
    sub = parser.add_subparsers(dest="command", required=True)

    default_home = pathlib.Path(os.environ.get("DIE_HOME", r"C:\DIE"))
    for name in ("plan", "materialize"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--request", required=True)
    materialize = sub.choices["materialize"]
    materialize.add_argument("--hermes-bin")

    verify = sub.add_parser("verify-run")
    verify.add_argument("--run-root", required=True)
    verify.add_argument("--output")

    args = parser.parse_args()
    try:
        if args.command in {"plan", "materialize"}:
            validated = _validated(args, default_home)
            root = default_home / "workspaces" / validated["request"]["run_id"]
            if args.command == "plan":
                result = m001_loop.build_plan(validated, root.resolve())
            else:
                result = m001_loop.materialize(
                    validated,
                    root,
                    m001_loop.HermesClient(args.hermes_bin),
                )
        else:
            result = m001_loop.verify_run(
                pathlib.Path(args.run_root),
                pathlib.Path(args.output) if args.output else None,
            )
    except m001_loop.LoopError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
