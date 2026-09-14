#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from demand_signal_contract import validate_record
from demand_signal_materializer import load_capabilities, load_evidence, materialize

DEFAULT_QUEUE = Path("/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl")
DEFAULT_SIGNALS = Path("/var/lib/die/h01/demand-intelligence/signals")
DEFAULT_OUT = Path("/var/lib/die/h01/demand-intelligence/materialized/demand-signal-ranking.v1.json")
DEFAULT_CAPABILITIES = H01 / "runtime" / "market-signal-sources"


def load_queue(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="H01-130A deterministic live demand signal materializer")
    ap.add_argument("--queue", default=str(DEFAULT_QUEUE))
    ap.add_argument("--signals-root", default=str(DEFAULT_SIGNALS))
    ap.add_argument("--capabilities-dir", default=str(DEFAULT_CAPABILITIES))
    ap.add_argument("--connector-ids", default="")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ns = ap.parse_args()

    connector_ids = {x.strip() for x in ns.connector_ids.split(",") if x.strip()} or None
    queue = load_queue(Path(ns.queue))
    capabilities = load_capabilities(Path(ns.capabilities_dir))
    evidence = load_evidence(Path(ns.signals_root), connector_ids=connector_ids)
    manifest = materialize(queue, evidence, capabilities)
    bad = []
    for row in manifest["records"]:
        errors = validate_record(row)
        if errors:
            bad.append({"queue_item_id": row.get("queue_item_id"), "errors": errors})
    if bad:
        raise SystemExit("E_MATERIALIZED_RECORDS_INVALID:" + json.dumps(bad[:10], sort_keys=True))

    out = Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "materialization_id": manifest["materialization_id"],
        "queue_items": manifest["source_queue_item_count"],
        "evidence_records": manifest["evidence_record_count"],
        "ranked": manifest["ranked_count"],
        "unranked": manifest["unranked_count"],
        "out": str(out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
