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
LIB = H01 / "lib/market_signal_acquisition.py"
CONNECTORS = H01 / "lib/market_signal_connectors.py"
REGISTRY_DIR = H01 / "runtime/market-signal-sources"
CAP_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-source-capability.v1.schema.json").read_text())
REC_SCHEMA = json.loads((H01 / "contracts/h01-market-signal-acquisition-receipt.v1.schema.json").read_text())

spec = importlib.util.spec_from_file_location("h01_131a_acquisition", LIB)
M = importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name] = M; spec.loader.exec_module(M)
spec2 = importlib.util.spec_from_file_location("h01_131_connectors_for_acq", CONNECTORS)
C = importlib.util.module_from_spec(spec2); assert spec2 and spec2.loader; sys.modules[spec2.name] = C; spec2.loader.exec_module(C)


def wiki_request():
    return C.build_wikimedia_pageviews_request("shopping bag", "2026090100", "2026091200")


def wiki_normalizer(payload, retrieved_at, source_url):
    return C.normalize_wikimedia_pageviews("shopping bag", payload, retrieved_at=retrieved_at, source_url=source_url)


class Clock:
    def __init__(self, value=1_800_000_000.0): self.value = float(value); self.sleeps = []
    def now(self): return self.value
    def sleep(self, seconds): self.sleeps.append(seconds); self.value += seconds


class Fetcher:
    def __init__(self, *, fail=False): self.calls = 0; self.fail = fail
    def __call__(self, request, capability):
        self.calls += 1
        if self.fail: raise RuntimeError("simulated source outage")
        body = json.dumps({"items": [{"views": 10}, {"views": 20}]}).encode()
        return M.PublicHttpResponse(body=body, content_type="application/json", final_url=request["url"])


class H01131AAcquisitionCore(unittest.TestCase):
    def test_registry_is_per_source_schema_valid_and_parallel_friendly(self):
        registry = M.SourceCapabilityRegistry(REGISTRY_DIR)
        snap = registry.snapshot()
        self.assertEqual(set(snap), {"wikimedia_pageviews_v1", "google_ads_keyword_historical_v1"})
        for source_id, row in snap.items():
            jsonschema.Draft202012Validator(CAP_SCHEMA).validate(row)
            self.assertEqual((REGISTRY_DIR / f"{source_id}.json").name, f"{source_id}.json")
            self.assertFalse(row["production_blocking"])
            self.assertFalse(row["authority"]["credential_read_authorized"])
        self.assertEqual(snap["wikimedia_pageviews_v1"]["adapter_state"], "ACTIVE")
        self.assertEqual(snap["google_ads_keyword_historical_v1"]["adapter_state"], "AUTH_CONTEXT_REQUIRED")

    def test_public_request_rejects_off_host_and_secret_headers(self):
        cap = M.SourceCapabilityRegistry(REGISTRY_DIR).get("wikimedia_pageviews_v1")
        with self.assertRaisesRegex(ValueError, "E_PUBLIC_URL_SCOPE"):
            M.sanitize_request({"method": "GET", "url": "https://example.com/x", "headers": {}}, cap)
        with self.assertRaisesRegex(ValueError, "E_SECRET_HEADER"):
            M.sanitize_request({"method": "GET", "url": "https://wikimedia.org/x", "headers": {"Authorization": "secret"}}, cap)

    def test_acquire_persists_immutable_raw_evidence_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td); clock = Clock(); fetch = Fetcher(); registry = M.SourceCapabilityRegistry(REGISTRY_DIR)
            core = M.AcquisitionCore(registry=registry, state_root=state, now_fn=clock.now, sleep_fn=clock.sleep, fetch_fn=fetch)
            receipt = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:shopping-bag:window", request=wiki_request(), normalizer=wiki_normalizer)
            jsonschema.Draft202012Validator(REC_SCHEMA).validate(receipt)
            self.assertEqual(receipt["status"], "ACQUIRED")
            self.assertEqual(receipt["effective_freshness"], "FRESH")
            self.assertEqual(fetch.calls, 1)
            raw_path = state / receipt["raw"]["relative_path"]
            self.assertTrue(raw_path.is_file())
            self.assertEqual(hashlib.sha256(raw_path.read_bytes()).hexdigest(), receipt["raw"]["sha256"])
            self.assertEqual(len(receipt["evidence"]), 1)
            evidence_path = state / receipt["evidence"][0]["relative_path"]
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(evidence["normalized_metrics"]["pageviews_total"], 30)
            self.assertEqual(M.sha256_value(evidence), receipt["evidence"][0]["sha256"])
            acquisitions = list((evidence_path.parents[1] / "acquisitions").glob("*.json"))
            self.assertEqual(len(acquisitions), 1)

    def test_fresh_cache_hit_avoids_second_network_call(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(); fetch = Fetcher(); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), now_fn=clock.now, sleep_fn=clock.sleep, fetch_fn=fetch)
            first = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:cache", request=wiki_request(), normalizer=wiki_normalizer)
            clock.value += 60
            second = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:cache", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(first["status"], "ACQUIRED")
            self.assertEqual(second["status"], "CACHE_HIT_FRESH")
            self.assertTrue(second["cache"]["hit"])
            self.assertEqual(fetch.calls, 1)
            self.assertEqual(second["raw"]["sha256"], first["raw"]["sha256"])
            self.assertEqual(second["evidence"], first["evidence"])

    def test_stale_cache_survives_source_outage_without_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(); fetch = Fetcher(); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), now_fn=clock.now, sleep_fn=clock.sleep, fetch_fn=fetch)
            first = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:stale", request=wiki_request(), normalizer=wiki_normalizer)
            clock.value += 86401
            fetch.fail = True
            second = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:stale", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(second["status"], "DEGRADED_STALE_CACHE")
            self.assertEqual(second["effective_freshness"], "STALE")
            self.assertEqual(second["evidence"], first["evidence"])
            self.assertFalse(second["policy"]["source_failure_blocks_production"])
            self.assertEqual(second["error"]["code"], "E_SOURCE_UNAVAILABLE")

    def test_outage_without_cache_is_honest_no_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(); fetch = Fetcher(fail=True); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), now_fn=clock.now, sleep_fn=clock.sleep, fetch_fn=fetch)
            receipt = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:none", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(receipt["status"], "DEGRADED_NO_EVIDENCE")
            self.assertEqual(receipt["effective_freshness"], "UNKNOWN")
            self.assertEqual(receipt["evidence"], [])
            self.assertFalse(receipt["policy"]["production_authorized"])

    def test_source_content_type_drift_degrades_fail_soft(self):
        with tempfile.TemporaryDirectory() as td:
            class HtmlFetcher:
                def __call__(self, request, capability):
                    return M.PublicHttpResponse(body=b"<html>changed</html>", content_type="text/html", final_url=request["url"])
            core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), fetch_fn=HtmlFetcher())
            receipt = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:drift", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(receipt["status"], "DEGRADED_NO_EVIDENCE")
            self.assertEqual(receipt["error"]["code"], "E_SOURCE_UNAVAILABLE")
            self.assertFalse(receipt["policy"]["source_failure_blocks_production"])

    def test_auth_required_source_never_reads_credentials_or_calls_network(self):
        with tempfile.TemporaryDirectory() as td:
            fetch = Fetcher(); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), fetch_fn=fetch)
            receipt = core.acquire(source_id="google_ads_keyword_historical_v1", query_key="gads:shopping bag", request={"method":"GET","url":"https://googleads.googleapis.com/external-context","headers":{"User-Agent":"DIE-H01/1.0"}}, normalizer=lambda *args: [])
            self.assertEqual(receipt["status"], "DEGRADED_AUTH_REQUIRED")
            self.assertEqual(fetch.calls, 0)
            self.assertFalse(receipt["policy"]["credential_values_read"])
            self.assertFalse(receipt["policy"]["cookies_or_tokens_read"])

    def test_source_lease_busy_degrades_instead_of_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td); lock = state / "sources/wikimedia_pageviews_v1/source.lock"; lock.parent.mkdir(parents=True); lock.write_text("busy")
            fetch = Fetcher(); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=state, fetch_fn=fetch)
            receipt = core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:busy", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(receipt["status"], "DEGRADED_SOURCE_BUSY")
            self.assertEqual(fetch.calls, 0)

    def test_persistent_min_interval_is_enforced_across_queries(self):
        with tempfile.TemporaryDirectory() as td:
            clock = Clock(); fetch = Fetcher(); core = M.AcquisitionCore(registry=M.SourceCapabilityRegistry(REGISTRY_DIR), state_root=Path(td), now_fn=clock.now, sleep_fn=clock.sleep, fetch_fn=fetch)
            core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:q1", request=wiki_request(), normalizer=wiki_normalizer)
            clock.value += 0.2
            core.acquire(source_id="wikimedia_pageviews_v1", query_key="wiki:q2", request=wiki_request(), normalizer=wiki_normalizer)
            self.assertEqual(fetch.calls, 2)
            self.assertEqual(len(clock.sleeps), 1)
            self.assertAlmostEqual(clock.sleeps[0], 0.8, places=5)


if __name__ == "__main__":
    unittest.main()
