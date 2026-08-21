#!/usr/bin/env python3
"""Run the dedicated ChatGPT Plus Executive Line 1 read-only MCP transport."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge"
sys.path.insert(0, str(BRIDGE))

from income_os_bridge import mcp_server  # noqa: E402


def main() -> int:
    return mcp_server.serve()


if __name__ == "__main__":
    raise SystemExit(main())
