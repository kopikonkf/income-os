#!/usr/bin/env python3
"""Run the dedicated ChatGPT Plus Executive Line 2 MCP transport."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge"
sys.path.insert(0, str(BRIDGE))
sys.path.insert(0, str(ROOT / "bin"))

import die_event  # noqa: E402
from income_os_bridge import executive_mcp_server  # noqa: E402


def main() -> int:
    return executive_mcp_server.serve(
        writer=die_event.commit_normalized_decision,
    )


if __name__ == "__main__":
    raise SystemExit(main())
