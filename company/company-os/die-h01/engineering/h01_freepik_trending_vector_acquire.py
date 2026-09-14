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
from market_signal_freepik import SOURCE_ID, acquire_freepik_trending_vectors, evidence_semantics

DEFAULT_STATE_ROOT = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="H01-131E compliance-gated Freepik/Magnific trending-vector signal adapter"
    )
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()

    registry = SourceCapabilityRegistry(Path(args.registry_dir))
    core = AcquisitionCore(registry=registry, state_root=Path(args.state_root))
    receipt = acquire_freepik_trending_vectors(core)
    output = {
        "receipt": receipt,
        "semantics": evidence_semantics(),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
