import importlib.util
import json
import sys
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "company/company-os/die-h01/lib/market_signal_connectors.py"
SCHEMA = json.loads(
    (ROOT / "company/company-os/die-h01/contracts/h01-market-signal-evidence.v1.schema.json").read_text()
)
SPEC = importlib.util.spec_from_file_location("h01_131_connectors", LIB)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class H01131MarketSignalConnectors(unittest.TestCase):
    def test_registry_is_official_bounded_and_scrape_free(self):
        registry = MODULE.connector_registry()
        self.assertEqual(
            set(registry),
            {"wikimedia_pageviews_v1", "google_ads_keyword_historical_v1"},
        )
        for row in registry.values():
            self.assertTrue(row["official"])
            self.assertLessEqual(row["max_requests_per_run"], 12)
            self.assertGreaterEqual(row["min_interval_seconds"], 1.0)
            self.assertFalse(row["autocomplete_core_dependency"])
            self.assertFalse(row["dom_scraping_core_dependency"])

    def test_wikimedia_request_is_official_structured_and_identified(self):
        request = MODULE.build_wikimedia_pageviews_request(
            "shopping bag", "20260901", "20260912"
        )
        self.assertTrue(
            request["url"].startswith(
                "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            )
        )
        self.assertIn("User-Agent", request["headers"])
        self.assertEqual(request["min_interval_seconds"], 1.0)

    def test_wikimedia_normalization_is_deterministic_and_nonblocking(self):
        payload = {"items": [{"views": 10}, {"views": 20}]}
        first = MODULE.normalize_wikimedia_pageviews(
            "shopping bag",
            payload,
            retrieved_at="2026-09-13T00:00:00Z",
            source_url="https://wikimedia.org/example",
        )
        second = MODULE.normalize_wikimedia_pageviews(
            "shopping bag",
            payload,
            retrieved_at="2026-09-13T01:00:00Z",
            source_url="https://wikimedia.org/example",
        )
        jsonschema.Draft202012Validator(SCHEMA).validate(first)
        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(first["evidence_sha256"], second["evidence_sha256"])
        self.assertEqual(first["normalized_metrics"]["pageviews_total"], 30)
        self.assertEqual(first["signal_class"], "TREND")
        self.assertEqual(first["policy"]["object_atlas_validity_effect"], "NONE")
        self.assertEqual(
            first["policy"]["standalone_production_blocking_effect"], "NONE"
        )

    def test_google_ads_normalizes_official_historical_metrics(self):
        payload = {
            "results": [
                {
                    "text": "shopping bag",
                    "keywordMetrics": {
                        "avgMonthlySearches": 12000,
                        "competitionIndex": 67,
                        "lowTopOfPageBidMicros": 500000,
                        "highTopOfPageBidMicros": 1500000,
                    },
                }
            ]
        }
        output = MODULE.normalize_google_ads_historical(
            "shopping bag",
            payload,
            retrieved_at="2026-09-13T00:00:00Z",
        )
        self.assertEqual(len(output), 1)
        jsonschema.Draft202012Validator(SCHEMA).validate(output[0])
        self.assertEqual(
            output[0]["normalized_metrics"]["avg_monthly_searches"], 12000
        )
        self.assertTrue(output[0]["policy"]["auth_required"])
        self.assertFalse(output[0]["policy"]["spend_authorized"])

    def test_projection_matches_h01_130_evidence_reference_shape(self):
        evidence = MODULE.normalize_wikimedia_pageviews(
            "cup",
            {"items": [{"views": 1}]},
            retrieved_at="2026-09-13T00:00:00Z",
            source_url="https://wikimedia.org/x",
        )
        ref = MODULE.to_h01_130_ref(evidence)
        self.assertEqual(
            set(ref),
            {"evidence_id", "evidence_sha256", "signal_class", "freshness"},
        )
        self.assertEqual(ref["signal_class"], "TREND")

    def test_no_connector_expands_action_authority(self):
        evidence = MODULE.normalize_wikimedia_pageviews(
            "trophy",
            {"items": []},
            retrieved_at="2026-09-13T00:00:00Z",
            source_url="https://wikimedia.org/x",
        )
        for key in (
            "production_authorized",
            "submission_authorized",
            "publication_authorized",
            "spend_authorized",
        ):
            self.assertFalse(evidence["policy"][key])


if __name__ == "__main__":
    unittest.main()
