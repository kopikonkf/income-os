"""DIE Operator kill switch — deterministic pause/resume setter.

Founder-only. Invoked by the die-operator-switch gateway plugin when an
allowlisted Telegram message contains exactly one of:
    /die_pause_operator
    /die_resume_operator

The LLM never observes or processes these commands (the plugin skips
dispatch), so it cannot ignore, override, or clear the pause.

Usage:
  python bin/die_operator_switch.py set   --state paused|resumed --sender <id> [--reason text]
  python bin/die_operator_switch.py status

Pause semantics per ORCHESTRATOR_CONTRACT.md / PROACTIVE_OPERATOR_V1.md §10:
only die-proactive-operator-v1 is disabled; deterministic monitoring crons,
Kanban cards, and state/* are untouched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bridge"))
from income_os_bridge import config as die_config

DIE = die_config.DIE_HOME
OP = die_config.STATE / "operator"
PAUSE_FLAG = OP / "PAUSE"
EVENT_PY = DIE / "bin" / "die_event.py"


def utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z")


def clean_env():
    env = dict(os.environ)
    for key in list(env):
        if any(x in key.upper() for x in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")):
            env.pop(key, None)
    return env


def emit(cls: str, summary: str, detail_ref: str | None) -> None:
    cmd = [sys.executable, str(EVENT_PY), "event",
           "--class", cls, "--source", "operator-switch",
           "--summary", summary[:140], "--mission-id", "M-001"]
    if detail_ref:
        cmd += ["--detail-ref", detail_ref]
    subprocess.run(cmd, cwd=str(DIE), env=clean_env(), capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=30)


def cmd_set(args) -> int:
    OP.mkdir(parents=True, exist_ok=True)
    if args.state == "paused":
        PAUSE_FLAG.write_text(json.dumps({
            "paused": True,
            "paused_at": utc_iso(),
            "paused_by_sender": str(args.sender),
            "reason": args.reason or "",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        emit("NOTICE", f"operator PAUSED by founder (sender {args.sender})",
             str(PAUSE_FLAG))
        print("OPERATOR_PAUSED")
    else:
        existed = PAUSE_FLAG.exists()
        if existed:
            PAUSE_FLAG.unlink()
        if existed:
            emit("NOTICE", f"operator RESUMED by founder (sender {args.sender})",
                 None)
            print("OPERATOR_RESUMED")
        else:
            print("OPERATOR_ALREADY_RESUMED")
    return 0


def cmd_status(_args) -> int:
    if PAUSE_FLAG.exists():
        try:
            print("PAUSED:", PAUSE_FLAG.read_text(encoding="utf-8"))
        except OSError:
            print("PAUSED (flag unreadable)")
    else:
        print("RESUMED (no pause flag)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_set = sub.add_parser("set")
    p_set.add_argument("--state", required=True, choices=["paused", "resumed"])
    p_set.add_argument("--sender", default="unknown")
    p_set.add_argument("--reason", default="")
    p_set.set_defaults(func=cmd_set)
    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
