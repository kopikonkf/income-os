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
from vecteezy_market_signal import (
    CONNECTOR_ID,
    build_vecteezy_request,
    normalize_vecteezy_popular,
    parse_vecteezy_html,
    run_vecteezy,
)

REGISTRY = H01 / "runtime" / "market-signal-sources"
CAPABILITY = REGISTRY / f"{CONNECTOR_ID}.json"
CAPABILITY_SCHEMA = H01 / "contracts" / "h01-market-signal-source-capability.v1.schema.json"
EVIDENCE_SCHEMA = H01 / "contracts" / "h01-market-signal-evidence.v1.schema.json"

FIXTURE = """
<html><body>
<a data-menu-tracking-category-param="background" data-menu-tracking-content-type-param="vector" href="/free-vector/background"><div>Backgrounds</div></a>
<a data-menu-tracking-category-param="flowers" data-menu-tracking-content-type-param="vector" href="/free-vector/flowers"><div>Flowers</div></a>
<a data-menu-tracking-category-param="Backgrounds" data-menu-tracking-content-type-param="vector" href="/free-vector/background"><div>Backgrounds</div></a>
<div data-controller="top-popular-searches">
  <ol>
    <li><span class="popular-searches__list__counter">1</span><a data-action="click->top-popular-searches#trackPopularClick" href="/free-svg/background">background</a></li>
    <li><span class="popular-searches__list__counter">2</span><a data-action="click->top-popular-searches#trackPopularClick" href="/free-svg/flower">flower</a></li>
    <li><span class="popular-searches__list__counter">3</span><a data-action="click->top-popular-searches#trackPopularClick" href="/free-svg/logo">logo</a></li>
  </ol>
</div>
</body></html>
"""

VECTOR_FIXTURE = FIXTURE.replace("/free-svg/background", "/free-vector/background").replace("/free-svg/flower", "/free-vector/flower").replace("/free-svg/logo", "/free-vector/logo")


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
            raise RuntimeError("synthetic-source-outage")
        return PublicHttpResponse(
            body=self.body.encode("utf-8"),
            content_type="text/html",
            final_url=request["url"],
        )


class VecteezyAdapterTests(unittest.TestCase):
    def test_capability_contract_is_public_fail_soft_and_zero_authority(self):
        capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))
        schema = json.loads(CAPABILITY_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(capability, schema)
        self.assertEqual(capability["commercial_intent_tier"], "MARKETPLACE_POPULAR_QUERY")
        self.assertEqual(capability["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(capability["auth_mode"], "NONE")
        self.assertFalse(capability["production_blocking"])
        self.assertTrue(all(value is False for value in capability["authority"].values()))

    def test_requests_are_bounded_first_party_gets_without_secret_headers(self):
        for surface, suffix in (("svg", "/popular-svgs"), ("vector", "/popular-vectors")):
            request = build_vecteezy_request(surface)
            self.assertEqual(request["method"], "GET")
            self.assertEqual(request["url"], "https://www.vecteezy.com" + suffix)
            lowered = {name.casefold() for name in request["headers"]}
            self.assertFalse({"authorization", "cookie", "x-api-key"} & lowered)

    def test_parser_and_normalizer_preserve_rank_without_fabricated_volume(self):
        parsed = parse_vecteezy_html(FIXTURE, surface="svg")
        self.assertEqual([row["term"] for row in parsed["popular_terms"]], ["background", "flower", "logo"])
        self.assertEqual([row["rank"] for row in parsed["popular_terms"]], [1, 2, 3])
        self.assertEqual([row["term"] for row in parsed["trending_vector_categories"]], ["background", "flowers"])
        kwargs = dict(surface="svg", retrieved_at="2026-09-14T15:00:00Z", source_url="https://www.vecteezy.com/popular-svgs")
        first = normalize_vecteezy_popular(FIXTURE, **kwargs)
        second = normalize_vecteezy_popular(FIXTURE, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 1)
        popular = first[0]
        self.assertEqual(popular["normalized_metrics"]["evidence_class"], "MARKETPLACE_POPULAR_QUERY")
        self.assertEqual(popular["normalized_metrics"]["confidence"], "MEDIUM_HIGH")
        self.assertEqual(popular["normalized_metrics"]["rank_semantics"], "ORDINAL_POPULARITY_ONLY")
        self.assertIsNone(popular["normalized_metrics"]["search_volume"])
        self.assertIsNone(popular["normalized_metrics"]["visitor_query_count"])
        self.assertFalse(popular["normalized_metrics"]["quantitative_customer_search_telemetry"])
        vector_rows = normalize_vecteezy_popular(VECTOR_FIXTURE, surface="vector", retrieved_at="2026-09-14T15:00:00Z", source_url="https://www.vecteezy.com/popular-vectors")
        self.assertEqual(len(vector_rows), 2)
        trend = vector_rows[1]
        self.assertEqual(trend["normalized_metrics"]["confidence"], "MEDIUM")
        schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
        for row in first + vector_rows:
            jsonschema.validate(row, schema)

    def _core(self, state_root: Path, fetcher: Fetcher, clock: Clock) -> AcquisitionCore:
        return AcquisitionCore(
            registry=SourceCapabilityRegistry(REGISTRY),
            state_root=state_root,
            now_fn=clock,
            sleep_fn=lambda _seconds: None,
            fetch_fn=fetcher,
        )

    def test_vector_surface_parser(self):
        parsed = parse_vecteezy_html(VECTOR_FIXTURE, surface="vector")
        self.assertEqual(parsed["media_type"], "VECTOR")
        self.assertEqual([row["rank"] for row in parsed["popular_terms"]], [1, 2, 3])
        self.assertEqual([row["term"] for row in parsed["popular_terms"]], ["background", "flower", "logo"])

    def test_missing_trending_block_preserves_vector_popular_evidence(self):
        payload = "\n".join(line for line in VECTOR_FIXTURE.splitlines() if "data-menu-tracking-category-param" not in line)
        rows = normalize_vecteezy_popular(
            payload,
            surface="vector",
            retrieved_at="2026-09-14T15:00:00Z",
            source_url="https://www.vecteezy.com/popular-vectors",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["normalized_metrics"]["telemetry_kind"], "POPULAR_QUERY_RANKING")
        self.assertEqual(rows[0]["normalized_metrics"]["ranked_term_count"], 3)

    def test_core_persists_immutable_raw_and_evidence_then_hits_fresh_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fetcher = Fetcher()
            clock = Clock()
            core = self._core(root, fetcher, clock)
            receipt = run_vecteezy(core, surface="svg")
            self.assertEqual(receipt["status"], "ACQUIRED")
            self.assertEqual(len(receipt["evidence"]), 1)
            receipt_schema = json.loads((H01 / "contracts" / "h01-market-signal-acquisition-receipt.v1.schema.json").read_text(encoding="utf-8"))
            jsonschema.validate(receipt, receipt_schema)
            raw_path = root / receipt["raw"]["relative_path"]
            self.assertEqual(raw_path.read_bytes(), FIXTURE.encode("utf-8"))
            evidence_schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
            for ref in receipt["evidence"]:
                evidence_path = root / ref["relative_path"]
                row = json.loads(evidence_path.read_text(encoding="utf-8"))
                jsonschema.validate(row, evidence_schema)
                self.assertEqual(row["normalized_metrics"]["search_volume"], None)
            second = run_vecteezy(core, surface="svg")
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(second["raw"]["sha256"], receipt["raw"]["sha256"])
            self.assertEqual(second["evidence"], receipt["evidence"])
            self.assertEqual(fetcher.calls, 1)

    def test_layout_change_fails_soft_without_blocking_production(self):
        with tempfile.TemporaryDirectory() as td:
            fetcher = Fetcher("<html><body>layout changed</body></html>")
            core = self._core(Path(td), fetcher, Clock())
            receipt = run_vecteezy(core, surface="svg")
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
            first = run_vecteezy(core, surface="svg")
            self.assertEqual(first["status"], "ACQUIRED")
            clock.value += 86401
            fetcher.fail = True
            stale = run_vecteezy(core, surface="svg")
            self.assertEqual(stale["status"], "DEGRADED_STALE_CACHE")
            self.assertTrue(stale["cache"]["hit"])
            self.assertEqual(stale["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(stale["evidence"], first["evidence"])
            self.assertFalse(stale["policy"]["source_failure_blocks_production"])


if __name__ == "__main__":
    unittest.main()
