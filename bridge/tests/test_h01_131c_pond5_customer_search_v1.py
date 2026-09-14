import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company/company-os/die-h01"
ADAPTER = H01 / "lib/pond5_customer_search.py"
CORE = H01 / "lib/market_signal_acquisition.py"
REGISTRY_DIR = H01 / "runtime/market-signal-sources"
EVIDENCE_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-evidence.v1.schema.json").read_text())
RECEIPT_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-acquisition-receipt.v1.schema.json").read_text())
CAPABILITY_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-source-capability.v1.schema.json").read_text())


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load("h01_131c_pond5", ADAPTER)
M = _load("h01_131c_acquisition", CORE)


HTML_FIXTURE = """
<html><head><meta name="description" content="Illustrations Data &amp; Trends - August 2026"></head>
<body>
<h1>Illustrations</h1>
<p>Top customer search terms compared with prior weeks.</p>
<h2>Top Search Terms</h2><ul>
  <li><a href="https://www.pond5.com/search/computer">computer</a></li>
  <li><a href="https://www.pond5.com/search/abstract">abstract</a></li>
  <li><a href="https://www.pond5.com/search/calendar">calendar</a></li>
</ul>
<h2>Trending Up</h2><ul><li data-change-percent="27%">back to school 27%</li></ul>
<h2>Trending Down</h2><ul><li data-change-percent="12%">winter sale 12%</li></ul>
</body></html>
"""


class Clock:
    def __init__(self, value=1_800_000_000.0):
        self.value = float(value)
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


class Fetcher:
    def __init__(self, body: bytes, *, fail: bool = False):
        self.body = body
        self.fail = fail
        self.calls = 0

    def __call__(self, request, capability):
        self.calls += 1
        if self.fail:
            raise RuntimeError("simulated Pond5 outage")
        return M.PublicHttpResponse(
            body=self.body,
            content_type="text/html",
            final_url=request["url"],
        )


class H01131CPond5(unittest.TestCase):
    def test_capability_is_first_party_public_and_schema_valid(self):
        path = REGISTRY_DIR / "pond5_customer_search_data_trends_v1.json"
        capability = json.loads(path.read_text())
        jsonschema.Draft202012Validator(CAPABILITY_SCHEMA).validate(capability)
        self.assertEqual(capability["adapter_state"], "ACTIVE")
        self.assertEqual(capability["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(capability["commercial_intent_tier"], "DIRECT_MARKETPLACE_QUERY")
        self.assertFalse(capability["production_blocking"])
        self.assertFalse(any(capability["authority"].values()))

    def test_request_is_bounded_and_allowlisted(self):
        request = P.build_pond5_data_trends_request("Illustrations")
        self.assertEqual(request["connector_id"], P.SOURCE_ID)
        self.assertEqual(request["method"], "GET")
        self.assertEqual(request["url"], "https://contributor.pond5.com/data-trends/illustrations/")
        self.assertIn("User-Agent", request["headers"])
        self.assertEqual(request["max_requests_per_run"], 1)
        with self.assertRaises(ValueError):
            P.build_pond5_data_trends_request("../../credentials")

    def test_html_parser_extracts_terms_period_and_explicit_changes(self):
        first = P.normalize_pond5_data_trends(
            HTML_FIXTURE,
            media_type="illustrations",
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://contributor.pond5.com/data-trends/illustrations/",
        )
        second = P.normalize_pond5_data_trends(
            HTML_FIXTURE,
            media_type="illustrations",
            retrieved_at="2026-09-15T00:00:00Z",
            source_url="https://contributor.pond5.com/data-trends/illustrations/",
        )
        jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(first)
        self.assertEqual(first["evidence_id"], second["evidence_id"])
        self.assertEqual(first["evidence_sha256"], second["evidence_sha256"])
        metrics = first["normalized_metrics"]
        self.assertEqual(metrics["media_type"], "illustrations")
        self.assertEqual(metrics["observation_period"], "August 2026")
        self.assertEqual([row["term"] for row in metrics["top_search_terms"]], ["computer", "abstract", "calendar"])
        self.assertEqual(metrics["trending_up"][0]["change_percent"], 27.0)
        self.assertEqual(metrics["trending_down"][0]["change_percent"], -12.0)
        self.assertEqual(metrics["trend_comparison_period"], "prior_weeks")
        self.assertEqual(first["evidence_class"], "DIRECT_CUSTOMER_SEARCH_TELEMETRY")
        self.assertEqual(first["confidence"], "HIGH")
        self.assertIsNone(metrics["search_volume"])
        self.assertIsNone(metrics["visitor_query_count"])

    def test_json_import_is_deterministic_and_does_not_fabricate_counts(self):
        payload = {
            "media_type": "illustrations",
            "observation_period": "August 2026",
            "comparison_period": "prior weeks",
            "top_search_terms": [
                {"term": "computer", "rank": 1},
                {"term": "abstract", "rank": 2},
            ],
            "trending_up": [{"term": "calendar", "percentage": "35%"}],
            "trending_down": [{"term": "winter", "percentage": 18}],
        }
        output = P.normalize_pond5_data_trends(
            payload,
            media_type="illustrations",
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://contributor.pond5.com/data-trends/illustrations/",
        )
        jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(output)
        self.assertEqual(output["normalized_metrics"]["trending_up"][0]["change_percent"], 35.0)
        self.assertEqual(output["normalized_metrics"]["trending_down"][0]["change_percent"], -18.0)
        self.assertFalse(output["normalized_metrics"]["quantitative_counts_provided"])
        self.assertNotIn("avg_monthly_searches", output["normalized_metrics"])

    def test_missing_percentages_remain_missing_on_ranked_terms_page(self):
        page = """
        <h1>Illustrations</h1>
        <p>Most popular customer search terms for August 2026.</p>
        <h2>Top Search Terms</h2>
        <a href="/search/computer">computer</a>
        <a href="/search/abstract">abstract</a>
        <a href="/search/calendar">calendar</a>
        <a href="/search/texture">texture</a>
        """
        output = P.normalize_pond5_data_trends(
            page,
            media_type="illustrations",
            retrieved_at="2026-09-14T00:00:00Z",
            source_url="https://contributor.pond5.com/data-trends/illustrations/",
        )
        metrics = output["normalized_metrics"]
        self.assertEqual(metrics["observation_period"], "August 2026")
        self.assertEqual([row["term"] for row in metrics["top_search_terms"]], ["computer", "abstract", "calendar", "texture"])
        self.assertEqual(metrics["trending_up"], [])
        self.assertEqual(metrics["trending_down"], [])
        self.assertIsNone(metrics["trend_comparison_period"])
        self.assertFalse(metrics["quantitative_counts_provided"])

    def test_public_snapshot_import_is_bounded_and_uses_core_persistence(self):
        payload = {
            "observation_period": "August 2026",
            "top_customer_search_terms": ["computer", "abstract"],
        }
        with tempfile.TemporaryDirectory() as td:
            snapshot = Path(td) / "pond5.html"
            snapshot.write_bytes(HTML_FIXTURE.encode())
            self.assertEqual(P.load_public_snapshot(snapshot), HTML_FIXTURE.encode())
            with self.assertRaises(P.Pond5ParseError):
                P.load_public_snapshot(snapshot, max_bytes=8)
            core = M.AcquisitionCore(
                registry=M.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td) / "state",
                fetch_fn=Fetcher(b"should not be used"),
            )
            receipt = P.acquire_pond5_data_trends_from_import(core, payload)
            self.assertEqual(receipt["status"], "ACQUIRED")
            self.assertEqual(receipt["evidence"][0]["relative_path"].split("/")[0], "sources")
            evidence_path = Path(td) / "state" / receipt["evidence"][0]["relative_path"]
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual([row["term"] for row in evidence["normalized_metrics"]["top_search_terms"]], ["computer", "abstract"])
            with self.assertRaises(ValueError):
                P.acquire_pond5_data_trends_from_import(
                    core,
                    payload,
                    source_url="https://www.pond5.com/data-trends/illustrations/",
                )

    def test_acquisition_core_persists_immutable_raw_and_normalized_evidence(self):
        body = HTML_FIXTURE.encode()
        fetcher = Fetcher(body)
        clock = Clock()
        with tempfile.TemporaryDirectory() as td:
            core = M.AcquisitionCore(
                registry=M.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                fetch_fn=fetcher,
            )
            receipt = P.acquire_pond5_data_trends(core, media_type="illustrations")
            jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(receipt)
            self.assertEqual(receipt["status"], "ACQUIRED")
            self.assertEqual(receipt["effective_freshness"], "FRESH")
            raw_path = Path(td) / receipt["raw"]["relative_path"]
            self.assertEqual(hashlib.sha256(raw_path.read_bytes()).hexdigest(), receipt["raw"]["sha256"])
            evidence_path = Path(td) / receipt["evidence"][0]["relative_path"]
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(evidence["normalized_metrics"]["top_search_terms"][0]["term"], "computer")
            self.assertEqual(M.sha256_value(evidence), receipt["evidence"][0]["sha256"])

    def test_fresh_cache_and_source_outage_are_nonblocking(self):
        fetcher = Fetcher(HTML_FIXTURE.encode())
        clock = Clock()
        with tempfile.TemporaryDirectory() as td:
            core = M.AcquisitionCore(
                registry=M.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                fetch_fn=fetcher,
            )
            first = P.acquire_pond5_data_trends(core)
            clock.value += 60
            second = P.acquire_pond5_data_trends(core)
            self.assertEqual(first["status"], "ACQUIRED")
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertEqual(fetcher.calls, 1)
            clock.value += 86401
            fetcher.fail = True
            refresh_run = M.AcquisitionCore(
                registry=M.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                fetch_fn=fetcher,
            )
            stale = P.acquire_pond5_data_trends(refresh_run)
            self.assertEqual(stale["status"], "DEGRADED_STALE_CACHE")
            self.assertFalse(stale["policy"]["source_failure_blocks_production"])
            self.assertEqual(stale["evidence"], first["evidence"])

    def test_source_outage_without_cache_is_honest_no_evidence(self):
        fetcher = Fetcher(b"", fail=True)
        with tempfile.TemporaryDirectory() as td:
            core = M.AcquisitionCore(
                registry=M.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                fetch_fn=fetcher,
            )
            receipt = P.acquire_pond5_data_trends(core)
            self.assertEqual(receipt["status"], "DEGRADED_NO_EVIDENCE")
            self.assertEqual(receipt["effective_freshness"], "UNKNOWN")
            self.assertEqual(receipt["evidence"], [])
            self.assertFalse(receipt["policy"]["production_authorized"])


if __name__ == "__main__":
    unittest.main()
