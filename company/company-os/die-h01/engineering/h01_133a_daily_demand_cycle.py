#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))
sys.path.insert(0, str(H01 / "engineering"))

from daily_demand_cycle import build_cycle, load_capabilities, load_evidence, persist_cycle, refresh_default_sources
from h01_daily_selector import build_manifest, load_queue, produced_ids

DEFAULT_QUEUE = Path("/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl")
DEFAULT_RUNS = Path("/var/lib/die/h01/runs")
DEFAULT_SIGNALS = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_OUTPUT = Path("/var/lib/die/h01/demand-intelligence/daily")
DEFAULT_REGISTRY = H01 / "runtime" / "market-signal-sources"
DEFAULT_CONNECTORS = "123rf_trending_search_v1,wikimedia_pageviews_v1,google_ads_keyword_historical_v1"
DEFAULT_PROVIDERS = ("gemini", "qwen", "claude", "chatgpt", "manus", "copilot")


def main() -> int:
    ap = argparse.ArgumentParser(description="H01-133A operational Daily Demand Intelligence Cycle v1")
    ap.add_argument("--queue", default=str(DEFAULT_QUEUE))
    ap.add_argument("--runs-root", default=str(DEFAULT_RUNS))
    ap.add_argument("--signals-root", default=str(DEFAULT_SIGNALS))
    ap.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--connector-ids", default=DEFAULT_CONNECTORS)
    ap.add_argument("--day-key", default="")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--provider-cycle", default=",".join(DEFAULT_PROVIDERS))
    ap.add_argument("--article", default="Cat")
    ap.add_argument("--keyword", default="cat")
    ap.add_argument("--skip-refresh", action="store_true", help="Use currently materialized signal store only; intended for fail-soft/fallback acceptance and controlled operation.")
    ns = ap.parse_args()

    day_key = ns.day_key or datetime.now(timezone.utc).date().isoformat()
    connector_ids = {x.strip() for x in ns.connector_ids.split(",") if x.strip()}
    providers = tuple(x.strip() for x in ns.provider_cycle.split(",") if x.strip())
    if not providers:
        raise SystemExit("E_PROVIDER_CYCLE")

    signals_root = Path(ns.signals_root)
    refresh_results = [] if ns.skip_refresh else refresh_default_sources(
        state_root=signals_root,
        registry_dir=Path(ns.registry_dir),
        day_key=day_key,
        article=ns.article,
        keyword=ns.keyword,
    )
    evidence = load_evidence(signals_root, connector_ids=connector_ids)
    capabilities = load_capabilities(Path(ns.registry_dir))
    queue_path = Path(ns.queue)
    queue = load_queue(queue_path)
    produced = produced_ids(Path(ns.runs_root))
    cycle = build_cycle(
        queue_rows=queue,
        produced=produced,
        evidence_rows=evidence,
        capabilities=capabilities,
        day_key=day_key,
        selector_builder=build_manifest,
        limit=ns.limit,
        providers=providers,
    )
    persisted = persist_cycle(
        cycle,
        output_root=Path(ns.output_root),
        queue_path=queue_path,
        effective_evidence_rows=evidence,
        refresh_results=refresh_results,
    )
    print(json.dumps({
        "status": "PASS",
        "cycle_id": cycle["cycle_id"],
        "day_key": day_key,
        "refresh": {row.get("source"): row.get("status") for row in refresh_results},
        "evidence_records": len(evidence),
        "ranked_materialized": cycle["materialization"]["ranked_count"],
        "ranked_selected": cycle["selector"]["selection"]["ranked_selected"],
        "fallback_selected": cycle["selector"]["selection"]["fallback_selected"],
        "selection_id": cycle["selector"]["selection_id"],
        "receipt": persisted["paths"]["cycle_receipt"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
