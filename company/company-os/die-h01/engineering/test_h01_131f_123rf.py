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

from market_signal_acquisition import AcquisitionCore, PublicHttpResponse, SourceCapabilityRegistry
from rf123_market_signal import (
    CONNECTOR_ID,
    SOURCE_URL,
    build_123rf_request,
    normalize_123rf_trending,
    parse_123rf_trending_html,
    run_123rf,
)

REGISTRY = H01 / "runtime" / "market-signal-sources"
CAPABILITY = REGISTRY / f"{CONNECTOR_ID}.json"
CAPABILITY_SCHEMA = H01 / "contracts" / "h01-market-signal-source-capability.v1.schema.json"
EVIDENCE_SCHEMA = H01 / "contracts" / "h01-market-signal-evidence.v1.schema.json"
RECEIPT_SCHEMA = H01 / "contracts" / "h01-market-signal-acquisition-receipt.v1.schema.json"

FIXTURE = """
<html><body>
<h2 class="TrendingWords_mainTitle__abc">Trending Searches</h2>
<div class="TrendingWords_gridContainer__xyz">
  <a class="TrendingWords_gridItem__one" href="https://www.123rf.com/free-stock-images/abstract.html"><img alt="Abstract" src="x.jpg"/></a>
  <a class="TrendingWords_gridItem__two" href="https://www.123rf.com/free-stock-images/animals.html"><img alt="Animals" src="y.jpg"/></a>
  <a class="TrendingWords_gridItem__three" href="https://www.123rf.com/free-stock-images/business.html"><img alt="Business" src="z.jpg"/></a>
</div>
</body></html>
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
            raise RuntimeError("synthetic-123rf-outage")
        return PublicHttpResponse(
            body=self.body.encode("utf-8"),
            content_type="text/html",
            final_url=request["url"],
        )


class RF123AdapterTests(unittest.TestCase):
    def test_capability_is_public_fail_soft_and_zero_authority(self):
        capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))
        schema = json.loads(CAPABILITY_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(capability, schema)
        self.assertEqual(capability["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(capability["auth_mode"], "NONE")
        self.assertEqual(capability["commercial_intent_tier"], "MARKETPLACE_POPULAR_QUERY")
        self.assertFalse(capability["production_blocking"])
        self.assertTrue(all(value is False for value in capability["authority"].values()))

    def test_request_is_bounded_first_party_get_without_secret_headers(self):
        request = build_123rf_request()
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], SOURCE_URL)
        lowered = {name.casefold() for name in request["headers"]}
        self.assertFalse({"authorization", "cookie", "x-api-key", "proxy-authorization"} & lowered)

    def test_parser_preserves_presentation_order_without_inventing_rank(self):
        parsed = parse_123rf_trending_html(FIXTURE)
        self.assertEqual([row["term"] for row in parsed["terms"]], ["Abstract", "Animals", "Business"])
        self.assertEqual([row["presentation_position"] for row in parsed["terms"]], [1, 2, 3])
        self.assertTrue(all("rank" not in row for row in parsed["terms"]))

    def test_normalizer_is_deterministic_schema_valid_and_non_quantitative(self):
        kwargs = dict(retrieved_at="2026-09-14T16:00:00Z", source_url=SOURCE_URL)
        first = normalize_123rf_trending(FIXTURE, **kwargs)
        second = normalize_123rf_trending(FIXTURE, **kwargs)
        self.assertEqual(first, second)
        metrics = first["normalized_metrics"]
        self.assertEqual(metrics["evidence_class"], "MARKETPLACE_TRENDING_SEARCH_LABELS")
        self.assertEqual(metrics["confidence"], "MEDIUM")
        self.assertEqual(metrics["rank_semantics"], "UNRANKED_PRESENTATION_ORDER")
        self.assertFalse(metrics["direct_customer_search_telemetry"])
        self.assertFalse(metrics["popular_query_ranking"])
        self.assertFalse(metrics["popularity_content_needs_proxy"])
        self.assertFalse(metrics["macro_trend"])
        self.assertIsNone(metrics["search_volume"])
        self.assertIsNone(metrics["visitor_query_count"])
        jsonschema.validate(first, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))

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
            first = run_123rf(core)
            self.assertEqual(first["status"], "ACQUIRED")
            self.assertEqual(len(first["evidence"]), 1)
            jsonschema.validate(first, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
            self.assertEqual((root / first["raw"]["relative_path"]).read_bytes(), FIXTURE.encode("utf-8"))
            evidence = json.loads((root / first["evidence"][0]["relative_path"]).read_text(encoding="utf-8"))
            jsonschema.validate(evidence, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))
            second = run_123rf(core)
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(second["evidence"], first["evidence"])
            self.assertEqual(fetcher.calls, 1)

    def test_layout_change_fails_soft_without_blocking_production(self):
        with tempfile.TemporaryDirectory() as td:
            core = self._core(Path(td), Fetcher("<html><body>layout changed</body></html>"), Clock())
            receipt = run_123rf(core)
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
            first = run_123rf(core)
            self.assertEqual(first["status"], "ACQUIRED")
            clock.value += 86401
            fetcher.fail = True
            stale = run_123rf(core)
            self.assertEqual(stale["status"], "DEGRADED_STALE_CACHE")
            self.assertTrue(stale["cache"]["hit"])
            self.assertEqual(stale["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(stale["evidence"], first["evidence"])
            self.assertFalse(stale["policy"]["source_failure_blocks_production"])


if __name__ == "__main__":
    unittest.main()
