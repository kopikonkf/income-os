import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "source_ingestion.py"
spec = importlib.util.spec_from_file_location("source_ingestion", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class SourceIngestionTests(unittest.TestCase):
    def test_plaintext_snapshot_preserves_identity_and_hashes(self):
        raw = b"Fact alpha.\n\nFact beta."
        snap = mod.ingest_external_bytes(source_id="EXT-001", source_uri="https://example.invalid/a", raw_bytes=raw,
            media_type="text/plain", acquisition_method="WEB_TOOL_SNAPSHOT", rights_state="REVIEWED_REFERENCE_ONLY",
            rights_basis="synthetic test fixture", verbatim_reuse_allowed=False)
        self.assertEqual(snap["raw_sha256"], mod.sha256_bytes(raw))
        self.assertEqual(snap["review_state"], "PENDING_REVIEW")
        self.assertFalse(snap["canonical_truth"])
        self.assertTrue(all(e["source_raw_sha256"] == snap["raw_sha256"] for e in snap["evidence_units"]))

    def test_html_adapter_excludes_script_and_is_deterministic(self):
        raw = b"<html><style>x{}</style><h1>Title</h1><p>Visible fact.</p><script>secret()</script></html>"
        a = mod.ingest_external_bytes(source_id="EXT-HTML", source_uri="https://example.invalid/h", raw_bytes=raw,
            media_type="text/html", acquisition_method="HTTP_CLIENT", rights_state="REVIEWED_REFERENCE_ONLY", rights_basis="fixture")
        b = mod.ingest_external_bytes(source_id="EXT-HTML", source_uri="https://example.invalid/h", raw_bytes=raw,
            media_type="text/html", acquisition_method="HTTP_CLIENT", rights_state="REVIEWED_REFERENCE_ONLY", rights_basis="fixture")
        self.assertEqual(a, b)
        combined = " ".join(x["text"] for x in a["evidence_units"])
        self.assertIn("Visible fact", combined)
        self.assertNotIn("secret", combined)

    def test_llm_and_crawler_cannot_approve(self):
        snap = mod.ingest_external_bytes(source_id="EXT-002", source_uri="https://example.invalid/b", raw_bytes=b"Evidence.",
            media_type="text/plain", acquisition_method="CONNECTOR_EXPORT", rights_state="REVIEWED_REFERENCE_ONLY", rights_basis="fixture")
        for kind in ("LLM", "CRAWLER", "WEB_AI", "PROVIDER_MODEL"):
            with self.assertRaisesRegex(ValueError, "REVIEWER_AUTHORITY_FORBIDDEN"):
                mod.approve_for_knowledge(snap, reviewer_kind=kind, reviewer_id="x", decision_basis="x")

    def test_unknown_rights_fails_closed(self):
        snap = mod.ingest_external_bytes(source_id="EXT-003", source_uri="https://example.invalid/c", raw_bytes=b"Evidence.",
            media_type="text/plain", acquisition_method="USER_FILE")
        with self.assertRaisesRegex(ValueError, "RIGHTS_REVIEW_REQUIRED"):
            mod.approve_for_knowledge(snap, reviewer_kind="ARCHITECT", reviewer_id="chatgpt-architect", decision_basis="bounded test")

    def test_governed_approval_produces_external_source_packet(self):
        snap = mod.ingest_external_bytes(source_id="EXT-004", source_uri="https://example.invalid/d", raw_bytes=b"Evidence one.\nEvidence two.",
            media_type="text/plain", acquisition_method="USER_FILE", rights_state="USER_OWNED_ORIGINAL", rights_basis="synthetic fixture")
        packet = mod.approve_for_knowledge(snap, reviewer_kind="ARCHITECT", reviewer_id="chatgpt-architect", decision_basis="test acceptance")
        self.assertEqual(packet["rights_status"], "GOVERNED_EXTERNAL")
        self.assertEqual(packet["review"]["status"], "ACCEPTED_FOR_KNOWLEDGE")
        self.assertFalse(packet["review"]["crawler_or_llm_authority"])
    def test_approved_external_packet_is_accepted_by_knowledge_validator(self):
        import importlib.util
        hp = ROOT / "company" / "h03" / "lib" / "h03_factory.py"
        hspec = importlib.util.spec_from_file_location("h03_factory_external", hp)
        h03 = importlib.util.module_from_spec(hspec); assert hspec.loader; hspec.loader.exec_module(h03)
        snap = mod.ingest_external_bytes(source_id="EXT-005", source_uri="https://example.invalid/e", raw_bytes=b"Evidence for a governed claim.",
            media_type="text/plain", acquisition_method="USER_FILE", rights_state="USER_OWNED_ORIGINAL", rights_basis="synthetic fixture")
        packet = mod.approve_for_knowledge(snap, reviewer_kind="ARCHITECT", reviewer_id="chatgpt-architect", decision_basis="test acceptance")
        kp = {
            "schema_version":"die.h03.knowledge-package.v1", "knowledge_package_id":"KP-EXT-001", "holding_id":"H03", "version":1,
            "rights_status":"GOVERNED_EXTERNAL", "source_packet":packet,
            "claims":[{"claim_id":"C-EXT-1","text":"A governed external source can support a claim only after review.","evidence_refs":[packet["evidence_units"][0]["evidence_id"]]}]
        }
        h03.validate_knowledge_package(kp)

    def test_unreviewed_external_packet_fails_knowledge_validator(self):
        import importlib.util
        hp = ROOT / "company" / "h03" / "lib" / "h03_factory.py"
        hspec = importlib.util.spec_from_file_location("h03_factory_external_fail", hp)
        h03 = importlib.util.module_from_spec(hspec); assert hspec.loader; hspec.loader.exec_module(h03)
        snap = mod.ingest_external_bytes(source_id="EXT-006", source_uri="https://example.invalid/f", raw_bytes=b"Unreviewed evidence.",
            media_type="text/plain", acquisition_method="USER_FILE", rights_state="REVIEWED_REFERENCE_ONLY", rights_basis="fixture")
        packet = dict(snap); packet["rights_status"] = "GOVERNED_EXTERNAL"
        kp = {"schema_version":"die.h03.knowledge-package.v1","knowledge_package_id":"KP-EXT-FAIL","holding_id":"H03","version":1,
              "rights_status":"GOVERNED_EXTERNAL","source_packet":packet,
              "claims":[{"claim_id":"C1","text":"Claim","evidence_refs":[snap["evidence_units"][0]["evidence_id"]]}]}
        with self.assertRaisesRegex(ValueError, "EXTERNAL_SOURCE_REVIEW_REQUIRED"):
            h03.validate_knowledge_package(kp)

