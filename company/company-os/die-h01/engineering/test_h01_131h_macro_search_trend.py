from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
sys.path.insert(0, str(H01 / "lib"))

from macro_search_trend_signal import (  # noqa: E402
    GOOGLE_ADS_CONNECTOR_ID,
    GOOGLE_TRENDS_CONNECTOR_ID,
    WIKIMEDIA_CONNECTOR_ID,
    build_google_ads_import_request,
    build_google_trends_import_request,
    build_wikimedia_attention_request,
    normalize_google_ads_macro,
    normalize_google_trends_macro,
    normalize_wikimedia_attention,
    run_google_ads_historical,
    run_google_trends_import,
    run_wikimedia_attention,
)
from market_signal_acquisition import (  # noqa: E402
    AcquisitionCore,
    PublicHttpResponse,
    SourceCapabilityRegistry,
)

REGISTRY = H01 / "runtime" / "market-signal-sources"
CAPABILITY_SCHEMA = json.loads(
    (H01 / "contracts" / "h01-market-signal-source-capability.v1.schema.json").read_text()
)
EVIDENCE_SCHEMA = json.loads(
    (H01 / "contracts" / "h01-market-signal-evidence.v1.schema.json").read_text()
)
RECEIPT_SCHEMA = json.loads(
    (H01 / "contracts" / "h01-market-signal-acquisition-receipt.v1.schema.json").read_text()
)

WIKI_PAYLOAD = {"items": [{"timestamp": "2026090700", "views": 10}, {"timestamp": "2026090800", "views": 20}]}
GOOGLE_ADS_PAYLOAD = {
    "results": [
        {
            "text": "cat illustration",
            "keywordMetrics": {
                "avgMonthlySearches": 12000,
                "competitionIndex": 67,
                "lowTopOfPageBidMicros": 500000,
                "highTopOfPageBidMicros": 1500000,
            },
        }
    ]
}
GOOGLE_TRENDS_PAYLOAD = {
    "query": "cat illustration",
    "source_timestamp": "2026-09-14T00:00:00Z",
    "timeline": [
        {"date": "2026-09-01", "value": 42},
        {"date": "2026-09-08", "value": 57},
    ],
}


class Clock:
    def __init__(self, value: float = 1_800_000_000.0):
        self.value = value
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class Fetcher:
    def __init__(self, body: bytes = b"", content_type: str = "application/json"):
        self.body = body
        self.content_type = content_type
        self.calls = 0
        self.fail = False

    def __call__(self, request, capability):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic-source-outage")
        return PublicHttpResponse(
            body=self.body,
            content_type=self.content_type,
            final_url=request["url"],
        )


class MacroSearchTrendAdapterTests(unittest.TestCase):
    def test_existing_capabilities_are_schema_valid_and_classified(self):
        registry = SourceCapabilityRegistry(REGISTRY)
        for source_id in (WIKIMEDIA_CONNECTOR_ID, GOOGLE_ADS_CONNECTOR_ID, GOOGLE_TRENDS_CONNECTOR_ID):
            capability = registry.get(source_id)
            jsonschema.validate(capability, CAPABILITY_SCHEMA)
            self.assertFalse(capability["production_blocking"])
            self.assertTrue(all(value is False for value in capability["authority"].values()))
        self.assertEqual(registry.get(WIKIMEDIA_CONNECTOR_ID)["commercial_intent_tier"], "ATTENTION_PROXY")
        self.assertEqual(registry.get(GOOGLE_ADS_CONNECTOR_ID)["commercial_intent_tier"], "MACRO_SEARCH")
        self.assertEqual(registry.get(GOOGLE_ADS_CONNECTOR_ID)["adapter_state"], "AUTH_CONTEXT_REQUIRED")
        self.assertEqual(registry.get(GOOGLE_TRENDS_CONNECTOR_ID)["commercial_intent_tier"], "MACRO_SEARCH")
        self.assertEqual(registry.get(GOOGLE_TRENDS_CONNECTOR_ID)["acquisition_mode"], "AUTHORIZED_EXTERNAL_IMPORT")

    def test_requests_are_bounded_and_never_carry_secret_headers(self):
        wiki = build_wikimedia_attention_request("cat", "2026090700", "2026091300")
        ads = build_google_ads_import_request("cat illustration")
        trends = build_google_trends_import_request("cat illustration")
        self.assertTrue(wiki["url"].startswith("https://wikimedia.org/api/rest_v1/metrics/pageviews/"))
        self.assertTrue(ads["url"].startswith("https://googleads.googleapis.com/"))
        self.assertTrue(trends["url"].startswith("https://trends.google.com/"))
        for request in (wiki, ads, trends):
            self.assertEqual(request["method"], "GET")
            self.assertFalse(
                {name.casefold() for name in request["headers"]}
                & {"authorization", "cookie", "proxy-authorization", "x-api-key", "x-goog-api-key"}
            )

    def test_wikimedia_is_attention_proxy_not_customer_search(self):
        first = normalize_wikimedia_attention(
            "cat",
            WIKI_PAYLOAD,
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://wikimedia.org/api/rest_v1/example",
        )
        second = normalize_wikimedia_attention(
            "cat",
            WIKI_PAYLOAD,
            retrieved_at="2026-09-14T01:00:00Z",
            source_url="https://wikimedia.org/api/rest_v1/example",
        )
        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(first["evidence_sha256"], second["evidence_sha256"])
        metrics = first["normalized_metrics"]
        self.assertEqual(metrics["evidence_class"], "ATTENTION_PROXY")
        self.assertEqual(metrics["confidence"], "LOW")
        self.assertEqual(metrics["telemetry_kind"], "PAGEVIEW_ATTENTION")
        self.assertFalse(metrics["direct_customer_search_telemetry"])
        self.assertFalse(metrics["macro_trend"])
        self.assertIsNone(metrics["search_volume"])
        self.assertIsNone(metrics["visitor_query_count"])
        jsonschema.validate(first, EVIDENCE_SCHEMA)

    def test_google_ads_normalizer_preserves_only_source_metrics(self):
        rows = normalize_google_ads_macro(
            "cat illustration",
            GOOGLE_ADS_PAYLOAD,
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://googleads.googleapis.com/v18/customers/authorized:generateKeywordHistoricalMetrics",
        )
        self.assertEqual(len(rows), 1)
        evidence = rows[0]
        metrics = evidence["normalized_metrics"]
        self.assertEqual(metrics["evidence_class"], "MACRO_TREND")
        self.assertEqual(metrics["commercial_intent_tier"], "MACRO_SEARCH")
        self.assertEqual(metrics["confidence"], "HIGH")
        self.assertEqual(metrics["search_volume"], 12000)
        self.assertFalse(metrics["direct_customer_search_telemetry"])
        self.assertTrue(metrics["macro_trend"])
        self.assertTrue(evidence["policy"]["auth_required"])
        jsonschema.validate(evidence, EVIDENCE_SCHEMA)

    def test_google_trends_import_normalizer_preserves_index_without_volume(self):
        evidence = normalize_google_trends_macro(
            "cat illustration",
            GOOGLE_TRENDS_PAYLOAD,
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://trends.google.com/trends/explore",
        )
        metrics = evidence["normalized_metrics"]
        self.assertEqual(evidence["connector_id"], GOOGLE_TRENDS_CONNECTOR_ID)
        self.assertEqual(metrics["evidence_class"], "MACRO_TREND")
        self.assertEqual(metrics["telemetry_kind"], "GOOGLE_TRENDS_INTEREST_INDEX")
        self.assertEqual(metrics["interest_index_points"][1]["interest_index"], 57)
        self.assertEqual(metrics["observation_period"], "2026-09-01/2026-09-08")
        self.assertIsNone(metrics["search_volume"])
        self.assertIsNone(metrics["visitor_query_count"])
        self.assertFalse(metrics["direct_customer_search_telemetry"])
        jsonschema.validate(evidence, EVIDENCE_SCHEMA)

    def _core(self, root: Path, fetcher: Fetcher, clock: Clock) -> AcquisitionCore:
        return AcquisitionCore(
            registry=SourceCapabilityRegistry(REGISTRY),
            state_root=root,
            now_fn=clock,
            sleep_fn=clock.sleep,
            fetch_fn=fetcher,
        )

    def test_wikimedia_routes_immutable_evidence_and_fresh_cache_through_core(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clock = Clock()
            fetcher = Fetcher(json.dumps(WIKI_PAYLOAD).encode("utf-8"))
            core = self._core(root, fetcher, clock)
            first = run_wikimedia_attention(
                core,
                article="cat",
                start_yyyymmddhh="2026090700",
                end_yyyymmddhh="2026091300",
            )
            self.assertEqual(first["status"], "ACQUIRED")
            jsonschema.validate(first, RECEIPT_SCHEMA)
            raw = root / first["raw"]["relative_path"]
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), first["raw"]["sha256"])
            evidence = root / first["evidence"][0]["relative_path"]
            jsonschema.validate(json.loads(evidence.read_text()), EVIDENCE_SCHEMA)
            clock.value += 60
            second = run_wikimedia_attention(
                core,
                article="cat",
                start_yyyymmddhh="2026090700",
                end_yyyymmddhh="2026091300",
            )
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(second["evidence"], first["evidence"])
            self.assertEqual(fetcher.calls, 1)

    def test_google_ads_without_authorized_context_degrades_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            fetcher = Fetcher(json.dumps(GOOGLE_ADS_PAYLOAD).encode("utf-8"))
            core = self._core(Path(td), fetcher, Clock())
            receipt = run_google_ads_historical(core, keyword="cat illustration")
            self.assertEqual(receipt["status"], "DEGRADED_AUTH_REQUIRED")
            self.assertEqual(receipt["evidence"], [])
            self.assertEqual(fetcher.calls, 0)
            self.assertFalse(receipt["policy"]["credential_values_read"])
            self.assertFalse(receipt["policy"]["cookies_or_tokens_read"])

    def test_google_ads_authorized_import_persists_and_replays_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clock = Clock()
            # The payload is a source response fixture supplied by an already
            # authorized context; no token or credential is present or read.
            core = self._core(root, Fetcher(), clock)
            first = run_google_ads_historical(
                core,
                keyword="cat illustration",
                authorized_payload=GOOGLE_ADS_PAYLOAD,
            )
            self.assertEqual(first["status"], "ACQUIRED")
            jsonschema.validate(first, RECEIPT_SCHEMA)
            raw = root / first["raw"]["relative_path"]
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), first["raw"]["sha256"])
            evidence = json.loads((root / first["evidence"][0]["relative_path"]).read_text())
            jsonschema.validate(evidence, EVIDENCE_SCHEMA)
            self.assertEqual(evidence["normalized_metrics"]["search_volume"], 12000)
            second = run_google_ads_historical(
                core,
                keyword="cat illustration",
                authorized_payload={"results": []},
            )
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(second["evidence"], first["evidence"])

    def test_google_trends_requires_import_context_and_uses_core_when_supplied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clock = Clock()
            fetcher = Fetcher()
            core = self._core(root, fetcher, clock)
            missing = run_google_trends_import(core, query="cat illustration")
            self.assertEqual(missing["status"], "DEGRADED_AUTH_REQUIRED")
            self.assertEqual(fetcher.calls, 0)
            first = run_google_trends_import(
                core,
                query="cat illustration",
                authorized_payload=GOOGLE_TRENDS_PAYLOAD,
            )
            self.assertEqual(first["status"], "ACQUIRED")
            evidence = json.loads((root / first["evidence"][0]["relative_path"]).read_text())
            jsonschema.validate(evidence, EVIDENCE_SCHEMA)
            self.assertIsNone(evidence["normalized_metrics"]["search_volume"])
            second = run_google_trends_import(
                core,
                query="cat illustration",
                authorized_payload={"timeline": [{"date": "2026-09-14", "value": 1}]},
            )
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["evidence"], first["evidence"])

    def test_import_url_scope_and_source_failure_are_fail_soft(self):
        with self.assertRaisesRegex(ValueError, "E_GOOGLE_ADS_IMPORT_URL_SCOPE"):
            build_google_ads_import_request("cat", source_locator="https://example.com/metrics")
        with self.assertRaisesRegex(ValueError, "E_GOOGLE_TRENDS_IMPORT_URL_SCOPE"):
            build_google_trends_import_request("cat", source_locator="https://example.com/trends")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clock = Clock()
            core = self._core(root, Fetcher(), clock)
            first = run_google_ads_historical(
                core,
                keyword="cat",
                authorized_payload={"results": []},
            )
            self.assertEqual(first["status"], "ACQUIRED")
            clock.value += 2_592_001
            stale = run_google_ads_historical(
                core,
                keyword="cat",
                authorized_payload={"results": "malformed"},
            )
            self.assertEqual(stale["status"], "DEGRADED_STALE_CACHE")
            self.assertEqual(stale["evidence"], first["evidence"])
            self.assertFalse(stale["policy"]["source_failure_blocks_production"])


if __name__ == "__main__":
    unittest.main()
