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
CORE_PATH = H01 / "lib/market_signal_acquisition.py"
ADAPTER_PATH = H01 / "lib/shutterstock_search_trends_v1.py"
REGISTRY_DIR = H01 / "runtime/market-signal-sources"
CAP_PATH = REGISTRY_DIR / "shutterstock_search_trends_v1.json"
CAP_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-source-capability.v1.schema.json").read_text())
REC_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-acquisition-receipt.v1.schema.json").read_text())
EVIDENCE_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-evidence.v1.schema.json").read_text())


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load("h01_131b_core", CORE_PATH)
ADAPTER = _load("h01_131b_shutterstock", ADAPTER_PATH)

SAMPLE_HTML = """
<!doctype html>
<html><body>
  <h3>Trending searches</h3>
  <a href="/search/coffee-drawing">
    <span>coffee drawing</span><span>Results:453,182</span>
    <span>Demand:Low</span><span>Growth:16%</span>
  </a>
  <a href="/search/green-tick-icon">
    <span>green tick icon</span><span>Results:86,508</span>
    <span>Demand:Low</span><span>Growth:371%</span>
  </a>
  <a href="/search/full-moon-icon">
    <span>full moon icon</span><span>Results:45,490</span>
    <span>Demand:Low</span><span>Growth:1,329%</span>
  </a>
</body></html>
""".strip()


def _active_registry(temp_root: Path) -> Path:
    registry = temp_root / "registry"
    registry.mkdir()
    cap = json.loads(CAP_PATH.read_text())
    cap["adapter_state"] = "ACTIVE"
    (registry / f"{cap['source_id']}.json").write_text(json.dumps(cap, indent=2) + "\n")
    return registry


class Fetcher:
    def __init__(self, *, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def __call__(self, request, capability):
        self.calls += 1
        if self.fail:
            raise RuntimeError("simulated first-party access/layout outage")
        return CORE.PublicHttpResponse(
            body=SAMPLE_HTML.encode("utf-8"),
            content_type="text/html",
            final_url=ADAPTER.SOURCE_URL,
        )


class H01131BShutterstockSearchTrendsV1(unittest.TestCase):
    def test_source_capability_is_schema_valid_fail_soft_and_has_zero_authority(self):
        cap = json.loads(CAP_PATH.read_text())
        jsonschema.Draft202012Validator(CAP_SCHEMA).validate(cap)
        self.assertEqual(cap["source_id"], ADAPTER.SOURCE_ID)
        self.assertEqual(cap["adapter_state"], "DISABLED")
        self.assertEqual(cap["auth_mode"], "NONE")
        self.assertEqual(cap["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(cap["commercial_intent_tier"], "DIRECT_MARKETPLACE_QUERY")
        self.assertFalse(cap["production_blocking"])
        self.assertTrue(all(value is False for value in cap["authority"].values()))

    def test_request_is_bounded_first_party_and_contains_no_secret_headers(self):
        cap = json.loads(CAP_PATH.read_text())
        request = ADAPTER.build_request()
        sanitized = CORE.sanitize_request(request, cap)
        self.assertEqual(sanitized["method"], "GET")
        self.assertEqual(sanitized["url"], "https://www.shutterstock.com/trends")
        names = {name.casefold() for name in sanitized["headers"]}
        self.assertTrue(names.isdisjoint(CORE.SECRET_HEADER_NAMES))

    def test_parser_extracts_explicit_fields_without_inventing_volume(self):
        rows = ADAPTER.parse_search_trends_html(SAMPLE_HTML)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], {
            "search_term": "coffee drawing",
            "rank": 1,
            "result_count": 453182,
            "demand_band": "Low",
            "growth_percent": 16,
        })
        self.assertEqual(rows[2]["growth_percent"], 1329)

    def test_normalizer_is_deterministic_and_matches_shared_evidence_contract(self):
        first = ADAPTER.normalize_search_trends(
            SAMPLE_HTML,
            "2026-09-14T12:00:00Z",
            ADAPTER.SOURCE_URL,
        )
        second = ADAPTER.normalize_search_trends(
            SAMPLE_HTML,
            "2026-09-14T13:00:00Z",
            ADAPTER.SOURCE_URL,
        )
        self.assertEqual(len(first), 3)
        for row in first:
            jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(row)
            metrics = row["normalized_metrics"]
            self.assertEqual(metrics["evidence_class"], "DIRECT_CUSTOMER_SEARCH_TELEMETRY")
            self.assertEqual(metrics["commercial_intent_tier"], "DIRECT_MARKETPLACE_QUERY")
            self.assertIsNone(metrics["customer_query_count"])
            self.assertIsNone(metrics["visitor_query_count"])
            self.assertEqual(metrics["result_count_semantics"], "CONTENT_RESULT_COUNT_NOT_CUSTOMER_QUERY_COUNT")
        self.assertEqual([x["evidence_id"] for x in first], [x["evidence_id"] for x in second])
        self.assertEqual([x["evidence_sha256"] for x in first], [x["evidence_sha256"] for x in second])

    def test_layout_drift_raises_source_specific_error(self):
        with self.assertRaisesRegex(ADAPTER.ShutterstockSearchTrendsLayoutError, "E_SHUTTERSTOCK_TRENDS_NO_ROWS"):
            ADAPTER.parse_search_trends_html("<html><body>layout changed</body></html>")

    def test_active_adapter_routes_immutable_raw_and_evidence_through_shared_core(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = CORE.SourceCapabilityRegistry(_active_registry(root))
            fetcher = Fetcher()
            core = CORE.AcquisitionCore(
                registry=registry,
                state_root=root / "state",
                fetch_fn=fetcher,
            )
            receipt = ADAPTER.acquire_search_trends(core)
            jsonschema.Draft202012Validator(REC_SCHEMA).validate(receipt)
            self.assertEqual(receipt["status"], "ACQUIRED")
            self.assertEqual(fetcher.calls, 1)
            self.assertEqual(len(receipt["evidence"]), 3)
            raw_path = root / "state" / receipt["raw"]["relative_path"]
            self.assertEqual(hashlib.sha256(raw_path.read_bytes()).hexdigest(), receipt["raw"]["sha256"])
            for ref in receipt["evidence"]:
                evidence_path = root / "state" / ref["relative_path"]
                evidence = json.loads(evidence_path.read_text())
                jsonschema.Draft202012Validator(EVIDENCE_SCHEMA).validate(evidence)
                self.assertEqual(CORE.sha256_value(evidence), ref["sha256"])

            cached = ADAPTER.acquire_search_trends(core)
            self.assertEqual(cached["status"], "CACHE_HIT_FRESH")
            self.assertEqual(fetcher.calls, 1)
            self.assertEqual(cached["raw"]["sha256"], receipt["raw"]["sha256"])
            self.assertEqual(cached["evidence"], receipt["evidence"])

    def test_source_outage_is_honest_and_nonblocking_when_adapter_is_active(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = CORE.AcquisitionCore(
                registry=CORE.SourceCapabilityRegistry(_active_registry(root)),
                state_root=root / "state",
                fetch_fn=Fetcher(fail=True),
            )
            receipt = ADAPTER.acquire_search_trends(core)
            self.assertEqual(receipt["status"], "DEGRADED_NO_EVIDENCE")
            self.assertEqual(receipt["evidence"], [])
            self.assertFalse(receipt["policy"]["source_failure_blocks_production"])
            self.assertFalse(receipt["policy"]["production_authorized"])
            self.assertEqual(receipt["error"]["code"], "E_SOURCE_UNAVAILABLE")

    def test_canonical_disabled_capability_never_calls_network(self):
        with tempfile.TemporaryDirectory() as td:
            fetcher = Fetcher()
            core = CORE.AcquisitionCore(
                registry=CORE.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                fetch_fn=fetcher,
            )
            receipt = ADAPTER.acquire_search_trends(core)
            self.assertEqual(receipt["status"], "DEGRADED_ADAPTER_UNAVAILABLE")
            self.assertEqual(fetcher.calls, 0)
            self.assertEqual(receipt["evidence"], [])
            self.assertFalse(receipt["policy"]["source_failure_blocks_production"])


if __name__ == "__main__":
    unittest.main()
