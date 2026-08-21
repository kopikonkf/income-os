#!/usr/bin/env python3
"""Audit Executive MCP activation readiness without provisioning or deployment."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridge"
sys.path.insert(0, str(BRIDGE))

from income_os_bridge import activation_readiness  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = activation_readiness.evaluate(root=ROOT)
    print(activation_readiness.render(result))
    return 0 if result["activation_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
