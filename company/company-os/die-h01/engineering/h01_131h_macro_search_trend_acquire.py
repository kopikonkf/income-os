#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from macro_search_trend_signal import run_google_ads_historical, run_wikimedia_attention
from market_signal_acquisition import AcquisitionCore, SourceCapabilityRegistry

DEFAULT_STATE_ROOT = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="H01-131H bounded Wikimedia attention and Google Ads macro-search acquisition"
    )
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--article", default="Cat")
    parser.add_argument("--start", default="2026090700")
    parser.add_argument("--end", default="2026091300")
    parser.add_argument("--keyword", default="cat")
    args = parser.parse_args()

    core = AcquisitionCore(
        registry=SourceCapabilityRegistry(Path(args.registry_dir)),
        state_root=Path(args.state_root),
    )
    result = {
        "wikimedia": run_wikimedia_attention(
            core,
            article=args.article,
            start_yyyymmddhh=args.start,
            end_yyyymmddhh=args.end,
        ),
        "google_ads": run_google_ads_historical(core, keyword=args.keyword),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
