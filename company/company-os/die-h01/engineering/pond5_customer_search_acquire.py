#!/usr/bin/env python3
"""Bounded Pond5 Data & Trends acquisition/import entry point for H01-131C."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from market_signal_acquisition import AcquisitionCore, SourceCapabilityRegistry  # noqa: E402
from pond5_customer_search import (  # noqa: E402
    acquire_pond5_data_trends,
    acquire_pond5_data_trends_from_import,
    load_public_snapshot,
)

DEFAULT_STATE_ROOT = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"


def main() -> int:
    parser = argparse.ArgumentParser(description="H01-131C bounded Pond5 customer-search acquisition")
    parser.add_argument("--media-type", default="illustrations")
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--import-file", help="bounded public Pond5 HTML/JSON snapshot; no browser state is read")
    parser.add_argument("--query-key")
    args = parser.parse_args()

    registry = SourceCapabilityRegistry(Path(args.registry_dir))
    core = AcquisitionCore(registry=registry, state_root=Path(args.state_root))
    if args.import_file:
        snapshot = load_public_snapshot(
            Path(args.import_file),
            max_bytes=registry.get("pond5_customer_search_data_trends_v1")["max_response_bytes"],
        )
        receipt = acquire_pond5_data_trends_from_import(
            core,
            snapshot,
            media_type=args.media_type,
            query_key=args.query_key,
        )
    else:
        receipt = acquire_pond5_data_trends(
            core,
            media_type=args.media_type,
            query_key=args.query_key,
        )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
