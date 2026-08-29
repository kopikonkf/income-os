#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from common import canonical_sha256, make_dedupe_key, make_signal_id


def adapt(raw: dict[str, Any]) -> dict[str, Any]:
    required = {"source_id","source_name","query","market_locale","language","visible_result_count","observed_at","freshness_window_seconds"}
    missing = sorted(required - raw.keys())
    if missing:
        raise ValueError("missing:" + ",".join(missing))
    count = raw["visible_result_count"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("visible_result_count must be non-negative integer")
    observed = dt.datetime.fromisoformat(raw["observed_at"].replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    recorded = observed + dt.timedelta(seconds=30)
    window = int(raw["freshness_window_seconds"])
    if window < 60:
        raise ValueError("freshness_window_seconds must be >=60")
    expires = recorded + dt.timedelta(seconds=window)
    fingerprint = canonical_sha256(raw)
    subject_id = raw["query"].strip()
    return {
        "schema_version":"die.division001.opportunity-signals.v1",
        "signal_id":make_signal_id("PUBUI", fingerprint),
        "subject":{"kind":"PHRASE","id":subject_id,"parent_seed_id":raw.get("parent_seed_id"),"parent_candidate_id":raw.get("parent_candidate_id")},
        "source":{"source_id":raw["source_id"],"source_name":raw["source_name"],"market_locale":raw["market_locale"],"language":raw["language"]},
        "signal_class":"SUPPLY","signal_type":"SEARCH_RESULTS_COUNT",
        "value":{"kind":"COUNT","numeric_value":count,"boolean_value":None,"text_value":None,"unit":"results"},
        "observed_at":observed.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z"),
        "recorded_at":recorded.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z"),
        "expires_at":expires.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z"),
        "freshness_window_seconds":window,
        "evidence_label":"SYNTHETIC","confidence":"HIGH","collector_id":"fixture-adapter:public-search-ui:v1",
        "acquisition_method":"SYNTHETIC_FIXTURE",
        "policy":{"profile_id":"fixture-public-search-ui","profile_version":"v1","classification":"SYNTHETIC_ONLY"},
        "source_ref":"fixture://public-search-ui/"+fingerprint,
        "evidence_sha256":fingerprint,"cost_usd":0,
        "dedupe_key":make_dedupe_key(raw["source_id"],subject_id,"SEARCH_RESULTS_COUNT",observed.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")),
    }


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("--output")
    args=ap.parse_args(); payload=adapt(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text=json.dumps(payload,indent=2,ensure_ascii=False)+"\n"
    if args.output: Path(args.output).write_text(text,encoding="utf-8",newline="\n")
    else: print(text,end="")
    return 0

if __name__=="__main__": raise SystemExit(main())
