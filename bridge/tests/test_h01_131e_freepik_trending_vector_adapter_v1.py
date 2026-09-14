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
ADAPTER_PATH = H01 / "lib/market_signal_freepik.py"
REGISTRY_DIR = H01 / "runtime/market-signal-sources"
CAP_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-source-capability.v1.schema.json").read_text())
RECEIPT_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-acquisition-receipt.v1.schema.json").read_text())

core_spec = importlib.util.spec_from_file_location("h01_131e_core", CORE_PATH)
CORE = importlib.util.module_from_spec(core_spec)
assert core_spec and core_spec.loader
sys.modules[core_spec.name] = CORE
core_spec.loader.exec_module(CORE)

adapter_spec = importlib.util.spec_from_file_location("h01_131e_freepik", ADAPTER_PATH)
ADAPTER = importlib.util.module_from_spec(adapter_spec)
assert adapter_spec and adapter_spec.loader
sys.modules[adapter_spec.name] = ADAPTER
adapter_spec.loader.exec_module(ADAPTER)


class NoNetworkFetcher:
    def __init__(self):
        self.calls = 0

    def __call__(self, request, capability):
        self.calls += 1
        raise AssertionError("network must not be called while Freepik/Magnific adapter is compliance-gated")


class H01131EFreepikTrendingVectorAdapter(unittest.TestCase):
    def capability(self):
        return CORE.SourceCapabilityRegistry(REGISTRY_DIR).get(ADAPTER.SOURCE_ID)

    def test_source_capability_is_valid_optional_and_compliance_gated(self):
        cap = self.capability()
        jsonschema.Draft202012Validator(CAP_SCHEMA).validate(cap)
        self.assertEqual(cap["adapter_state"], "ADAPTER_PENDING")
        self.assertEqual(cap["acquisition_mode"], "PUBLIC_HTTPS_TEXT")
        self.assertEqual(cap["commercial_intent_tier"], "MARKETPLACE_POPULAR_QUERY")
        self.assertEqual(cap["signal_classes"], ["TREND"])
        self.assertEqual(cap["max_requests_per_run"], 1)
        self.assertGreaterEqual(cap["min_interval_seconds"], 1)
        self.assertFalse(cap["production_blocking"])
        self.assertFalse(cap["authority"]["credential_read_authorized"])
        self.assertFalse(cap["authority"]["production_authorized"])
        self.assertFalse(cap["authority"]["submission_authorized"])
        self.assertFalse(cap["authority"]["publication_authorized"])
        self.assertFalse(cap["authority"]["spend_authorized"])

    def test_request_is_first_party_get_and_contains_no_secret_headers(self):
        request = ADAPTER.build_freepik_trending_vector_request()
        cap = self.capability()
        sanitized = CORE.sanitize_request(request, cap)
        self.assertEqual(sanitized["method"], "GET")
        self.assertTrue(CORE.host_allowed(sanitized["url"], cap["allowed_hosts"]))
        secret_names = {"authorization", "cookie", "proxy-authorization", "x-api-key", "x-goog-api-key"}
        self.assertFalse(secret_names.intersection({key.casefold() for key in sanitized["headers"]}))

    def test_evidence_semantics_are_popular_query_not_direct_telemetry_or_volume(self):
        semantics = ADAPTER.evidence_semantics()
        self.assertEqual(semantics["evidence_class"], "MARKETPLACE_POPULAR_QUERY")
        self.assertEqual(semantics["media_type"], "VECTOR")
        self.assertFalse(semantics["direct_customer_search_telemetry"])
        self.assertTrue(semantics["popular_query_ranking"])
        self.assertFalse(semantics["popularity_content_needs_proxy"])
        self.assertFalse(semantics["macro_trend"])
        self.assertFalse(semantics["query_volume_available"])
        self.assertFalse(semantics["visitor_query_count_available"])
        self.assertEqual(semantics["quantitative_confidence"], "NONE")
        self.assertEqual(semantics["adapter_state"], "ADAPTER_PENDING")
        self.assertEqual(
            semantics["block_reason_code"],
            "E_FREEPIK_AUTOMATED_TREND_ACQUISITION_NOT_COMPLIANT",
        )

    def test_core_fail_softs_without_network_io_or_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            fetcher = NoNetworkFetcher()
            core = CORE.AcquisitionCore(
                registry=CORE.SourceCapabilityRegistry(REGISTRY_DIR),
                state_root=Path(td),
                fetch_fn=fetcher,
            )
            receipt = ADAPTER.acquire_freepik_trending_vectors(core)
            jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(receipt)
            self.assertEqual(receipt["status"], "DEGRADED_ADAPTER_UNAVAILABLE")
            self.assertEqual(receipt["effective_freshness"], "UNKNOWN")
            self.assertEqual(receipt["evidence"], [])
            self.assertEqual(fetcher.calls, 0)
            self.assertEqual(receipt["error"]["code"], "E_ADAPTER_UNAVAILABLE")
            self.assertFalse(receipt["policy"]["source_failure_blocks_production"])
            self.assertFalse(receipt["policy"]["credential_values_read"])
            self.assertFalse(receipt["policy"]["cookies_or_tokens_read"])
            self.assertFalse(receipt["policy"]["production_authorized"])
            self.assertFalse(receipt["policy"]["submission_authorized"])
            self.assertFalse(receipt["policy"]["publication_authorized"])
            self.assertFalse(receipt["policy"]["spend_authorized"])

    def test_no_parser_or_automated_extraction_surface_is_shipped(self):
        self.assertFalse(hasattr(ADAPTER, "parse_freepik_trending_vector_searches"))
        self.assertFalse(hasattr(ADAPTER, "normalize_freepik_trending_vectors"))


if __name__ == "__main__":
    unittest.main()
