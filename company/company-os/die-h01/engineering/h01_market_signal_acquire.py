#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from market_signal_acquisition import AcquisitionCore, SourceCapabilityRegistry
from market_signal_connectors import build_wikimedia_pageviews_request, normalize_wikimedia_pageviews

DEFAULT_STATE_ROOT = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"


def _wiki_dates(days: int) -> tuple[str, str]:
    if days < 1 or days > 90:
        raise ValueError("E_DAYS_RANGE")
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start.strftime("%Y%m%d00"), end.strftime("%Y%m%d00")


def run_wikimedia(core: AcquisitionCore, query: str, *, days: int, project: str) -> dict:
    start, end = _wiki_dates(days)
    request = build_wikimedia_pageviews_request(query, start, end, project=project)

    def normalize(payload, retrieved_at: str, source_url: str):
        return normalize_wikimedia_pageviews(
            query,
            payload,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    return core.acquire(
        source_id="wikimedia_pageviews_v1",
        query_key=f"wiki:{project}:{query.casefold().strip()}:{start}:{end}",
        request=request,
        normalizer=normalize,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="H01-131A bounded first-party market signal acquisition core")
    parser.add_argument("--source", default="wikimedia_pageviews_v1")
    parser.add_argument("--query", required=True)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--project", default="en.wikipedia.org")
    parser.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()

    registry = SourceCapabilityRegistry(Path(args.registry_dir))
    core = AcquisitionCore(registry=registry, state_root=Path(args.state_root))

    if args.source == "wikimedia_pageviews_v1":
        receipt = run_wikimedia(core, args.query, days=args.days, project=args.project)
    elif args.source == "google_ads_keyword_historical_v1":
        capability = registry.get(args.source)
        request = {
            "method": "GET",
            "url": "https://googleads.googleapis.com/authorized-external-context-required",
            "headers": {"User-Agent": "DIE-H01/1.0"},
        }
        receipt = core.acquire(
            source_id=args.source,
            query_key=f"gads:{args.query.casefold().strip()}",
            request=request,
            normalizer=lambda payload, retrieved_at, source_url: [],
        )
        assert capability["adapter_state"] == "AUTH_CONTEXT_REQUIRED"
    else:
        raise SystemExit(f"E_SOURCE_ADAPTER_NOT_IMPLEMENTED:{args.source}")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
