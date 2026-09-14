from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from adobe_stock_market_signal import (
    CONNECTOR_ID,
    SOURCE_URL,
    build_adobe_stock_request,
    normalize_adobe_creative_trends,
    parse_adobe_creative_trends_html,
    run_adobe_stock,
)
from market_signal_acquisition import AcquisitionCore, PublicHttpResponse, SourceCapabilityRegistry

REGISTRY = H01 / "runtime" / "market-signal-sources"
CAPABILITY = REGISTRY / f"{CONNECTOR_ID}.json"
CAPABILITY_SCHEMA = H01 / "contracts" / "h01-market-signal-source-capability.v1.schema.json"
EVIDENCE_SCHEMA = H01 / "contracts" / "h01-market-signal-evidence.v1.schema.json"
RECEIPT_SCHEMA = H01 / "contracts" / "h01-market-signal-acquisition-receipt.v1.schema.json"

FIXTURE = """
<html><head>
<meta name="author" content="Brenda Milis">
<meta name="publication-date" content="01-08-2026">
</head><body><main>
<h1>How creators are leveraging Adobe's 2026 Creative Trends</h1>
<p>Adobe Stock creative community examples.</p>
<h2 id="all-the-feels">All the Feels</h2><p>Trend one.</p>
<h2 id="connectioneering">Connectioneering</h2><p>Trend two.</p>
<h2 id="surreal-silliness">Surreal Silliness</h2><p>Trend three.</p>
<h2 id="local-flavor">Local Flavor</h2><p>Trend four.</p>
<h2 id="a-new-horizon">A new horizon</h2>
<p>We determine the Creative Trends by reviewing commercial campaigns and creative projects across all sectors throughout the year. We also work with feedback from our customers in Creative Cloud communities and track search history, which has increased by 150 percent for keywords related to 2026 trends since 2024.</p>
</main></body></html>
"""


class Clock:
    def __init__(self, value: float = 1_800_000_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value


class Fetcher:
    def __init__(self, body: str = FIXTURE):
        self.body = body
        self.fail = False
        self.calls = 0

    def __call__(self, request, capability):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic-adobe-outage")
        return PublicHttpResponse(
            body=self.body.encode("utf-8"),
            content_type="text/html",
            final_url=request["url"],
        )


class AdobeStockAdapterTests(unittest.TestCase):
    def test_capability_is_public_fail_soft_zero_authority_and_proxy_tier(self):
        capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))
        schema = json.loads(CAPABILITY_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(capability, schema)
        self.assertEqual(capability["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(capability["auth_mode"], "NONE")
        self.assertEqual(capability["commercial_intent_tier"], "MARKETPLACE_POPULARITY_PROXY")
        self.assertEqual(capability["allowed_hosts"], ["blog.adobe.com"])
        self.assertFalse(capability["production_blocking"])
        self.assertTrue(all(value is False for value in capability["authority"].values()))

    def test_request_is_bounded_first_party_get_without_secret_headers(self):
        request = build_adobe_stock_request()
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], SOURCE_URL)
        lowered = {name.casefold() for name in request["headers"]}
        self.assertFalse({"authorization", "cookie", "x-api-key", "proxy-authorization"} & lowered)

    def test_parser_extracts_explicit_trends_and_aggregate_search_history_metric(self):
        parsed = parse_adobe_creative_trends_html(FIXTURE)
        self.assertEqual(parsed["publication_date"], "2026-01-08")
        self.assertEqual(parsed["author"], "Brenda Milis")
        self.assertEqual(parsed["trends"], ["All the Feels", "Connectioneering", "Surreal Silliness", "Local Flavor"])
        self.assertEqual(parsed["search_history_growth_percent"], 150.0)
        self.assertEqual(parsed["search_history_growth_since_year"], 2024)
        self.assertTrue(parsed["methodology_mentions_customer_feedback"])
        self.assertTrue(parsed["methodology_mentions_search_history"])

    def test_normalizer_is_deterministic_schema_valid_and_keeps_evidence_classes_distinct(self):
        kwargs = dict(retrieved_at="2026-09-14T16:00:00Z", source_url=SOURCE_URL)
        first = normalize_adobe_creative_trends(FIXTURE, **kwargs)
        second = normalize_adobe_creative_trends(FIXTURE, **kwargs)
        self.assertEqual(first, second)
        metrics = first["normalized_metrics"]
        self.assertEqual(metrics["evidence_class"], "MACRO_TREND")
        self.assertEqual(metrics["confidence"], "MEDIUM_HIGH")
        self.assertEqual(metrics["telemetry_kind"], "EDITORIAL_CREATIVE_TREND_SYNTHESIS")
        self.assertFalse(metrics["direct_customer_search_telemetry"])
        self.assertFalse(metrics["popular_query_ranking"])
        self.assertFalse(metrics["popularity_content_needs_proxy"])
        self.assertTrue(metrics["macro_trend"])
        self.assertFalse(metrics["quantitative_customer_search_telemetry"])
        self.assertIsNone(metrics["search_volume"])
        self.assertIsNone(metrics["visitor_query_count"])
        self.assertEqual(metrics["search_history_growth_percent"], 150.0)
        jsonschema.validate(first, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))

    def test_missing_aggregate_growth_number_does_not_invent_one(self):
        payload = FIXTURE.replace("track search history, which has increased by 150 percent for keywords related to 2026 trends since 2024.", "track search history to identify rising patterns.")
        row = normalize_adobe_creative_trends(payload, retrieved_at="2026-09-14T16:00:00Z", source_url=SOURCE_URL)
        metrics = row["normalized_metrics"]
        self.assertIsNone(metrics["search_history_growth_percent"])
        self.assertIsNone(metrics["search_history_growth_since_year"])
        self.assertIsNone(metrics["growth_semantics"])
        self.assertEqual(metrics["trend_count"], 4)

    def _core(self, root: Path, fetcher: Fetcher, clock: Clock) -> AcquisitionCore:
        return AcquisitionCore(
            registry=SourceCapabilityRegistry(REGISTRY),
            state_root=root,
            now_fn=clock,
            sleep_fn=lambda _seconds: None,
            fetch_fn=fetcher,
        )

    def test_core_persists_immutable_raw_evidence_and_hits_fresh_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fetcher = Fetcher()
            core = self._core(root, fetcher, Clock())
            first = run_adobe_stock(core)
            self.assertEqual(first["status"], "ACQUIRED")
            self.assertEqual(len(first["evidence"]), 1)
            jsonschema.validate(first, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
            self.assertEqual((root / first["raw"]["relative_path"]).read_bytes(), FIXTURE.encode("utf-8"))
            evidence = json.loads((root / first["evidence"][0]["relative_path"]).read_text(encoding="utf-8"))
            jsonschema.validate(evidence, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))
            self.assertEqual(evidence["normalized_metrics"]["trend_count"], 4)
            second = run_adobe_stock(core)
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(second["evidence"], first["evidence"])
            self.assertEqual(fetcher.calls, 1)

    def test_layout_change_fails_soft_without_blocking_production(self):
        with tempfile.TemporaryDirectory() as td:
            core = self._core(Path(td), Fetcher("<html><body>Adobe Stock layout changed</body></html>"), Clock())
            receipt = run_adobe_stock(core)
            self.assertEqual(receipt["status"], "DEGRADED_NO_EVIDENCE")
            self.assertEqual(receipt["evidence"], [])
            self.assertEqual(receipt["error"]["code"], "E_SOURCE_UNAVAILABLE")
            self.assertFalse(receipt["policy"]["source_failure_blocks_production"])
            self.assertFalse(receipt["policy"]["credential_values_read"])

    def test_source_outage_falls_back_to_stale_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fetcher = Fetcher()
            clock = Clock()
            core = self._core(root, fetcher, clock)
            first = run_adobe_stock(core)
            self.assertEqual(first["status"], "ACQUIRED")
            clock.value += 604801
            fetcher.fail = True
            stale = run_adobe_stock(core)
            self.assertEqual(stale["status"], "DEGRADED_STALE_CACHE")
            self.assertTrue(stale["cache"]["hit"])
            self.assertEqual(stale["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(stale["evidence"], first["evidence"])
            self.assertFalse(stale["policy"]["source_failure_blocks_production"])


if __name__ == "__main__":
    unittest.main()
