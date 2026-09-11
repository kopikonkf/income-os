from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "company" / "h03" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from live_org_runner import run_live_org


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or resume the bounded H03 LIVE-ORG-001 internal organism.")
    parser.add_argument("--artifact-root", required=True, type=Path, help="Host-local durable Artifact Courier root.")
    parser.add_argument("--output-root", required=True, type=Path, help="Host-local deterministic product package root.")
    parser.add_argument("--founder-qc-root", required=True, type=Path, help="Host-local Founder QC handoff root.")
    parser.add_argument("--mc-endpoint", default="http://127.0.0.1:8891", help="Mission Control local endpoint.")
    args = parser.parse_args()

    summary = run_live_org(
        artifact_root=args.artifact_root,
        output_root=args.output_root,
        founder_qc_root=args.founder_qc_root,
        mc_endpoint=args.mc_endpoint,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
