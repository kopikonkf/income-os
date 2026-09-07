#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from console_provider_canary import ConsoleProviderCanaryError, run_console_provider_canary  # noqa: E402


def _live_executor_factory(*, repo_root: Path, request_path: Path, playwright_entry: Path, control_base_url: str):
    script = repo_root / "company/factory-asset/bin/run_fa_c010_cluster_provider_executor.mjs"

    def execute(request: dict[str, Any], workspace: Path) -> dict[str, Any]:
        cp = subprocess.run(
            [
                "node",
                str(script),
                "--repo-root",
                str(repo_root),
                "--request",
                str(request_path),
                "--workspace",
                str(workspace),
                "--playwright-entry",
                str(playwright_entry),
                "--control-base-url",
                control_base_url,
            ],
            text=True,
            capture_output=True,
            timeout=420,
            check=False,
        )
        if cp.returncode != 0:
            tail = (cp.stderr or cp.stdout or "E_EXECUTOR_FAILED")[-1200:].replace("\n", " ").strip()
            raise ConsoleProviderCanaryError("E_PROVIDER_EXECUTOR", tail)
        lines = [line for line in cp.stdout.splitlines() if line.strip()]
        if not lines:
            raise ConsoleProviderCanaryError("E_PROVIDER_EXECUTOR_OUTPUT", "executor returned no JSON result")
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise ConsoleProviderCanaryError("E_PROVIDER_EXECUTOR_OUTPUT", "executor result is not valid JSON") from exc

    return execute


def main() -> int:
    ap = argparse.ArgumentParser(description="FA-C010 bounded Factory Console real-provider canary")
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=ROOT)
    ap.add_argument("--playwright-entry", type=Path, required=True)
    ap.add_argument("--control-base-url", default="http://127.0.0.1:39121")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--replay-only", action="store_true")
    args = ap.parse_args()
    if args.live == args.replay_only:
        raise SystemExit("exactly one of --live or --replay-only is required")

    repo_root = args.repo_root.resolve()
    request_path = args.request.resolve()
    workspace = args.workspace.resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))

    if args.replay_only:
        if not (workspace / "final-result.json").is_file():
            raise SystemExit("replay-only requires an existing accepted final-result.json; no state was mutated")

        def no_provider(_: dict[str, Any], __: Path) -> dict[str, Any]:
            raise ConsoleProviderCanaryError("E_REPLAY_PROVIDER_CALL", "replay-only must never invoke provider execution")

        execute = no_provider
    else:
        execute = _live_executor_factory(
            repo_root=repo_root,
            request_path=request_path,
            playwright_entry=args.playwright_entry.resolve(),
            control_base_url=args.control_base_url,
        )

    result = run_console_provider_canary(request=request, workspace=workspace, execute_provider=execute)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
