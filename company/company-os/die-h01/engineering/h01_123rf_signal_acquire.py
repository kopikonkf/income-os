#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from market_signal_acquisition import AcquisitionCore, SourceCapabilityRegistry
from rf123_market_signal import run_123rf

DEFAULT_STATE_ROOT = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"


def main() -> int:
    parser = argparse.ArgumentParser(description="H01-131F bounded first-party 123RF Trending Searches acquisition")
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()

    core = AcquisitionCore(
        registry=SourceCapabilityRegistry(Path(args.registry_dir)),
        state_root=Path(args.state_root),
    )
    receipt = run_123rf(core)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
