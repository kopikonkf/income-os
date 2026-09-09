import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company" / "h03" / "lib" / "h03_factory.py"
spec = importlib.util.spec_from_file_location("h03_factory", LIB)
h03 = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(h03)


class H03FactoryTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "company" / "h03" / "examples" / "mvp"
        self.kp = h03.load_json(self.base / "knowledge-package.json")
        self.bp = h03.load_json(self.base / "product-blueprint.json")

    def test_knowledge_claims_resolve_to_evidence(self):
        h03.validate_knowledge_package(self.kp)

    def test_unresolved_evidence_fails_closed(self):
        broken = json.loads(json.dumps(self.kp))
        broken["claims"][0]["evidence_refs"] = ["MISSING"]
        with self.assertRaisesRegex(ValueError, "UNRESOLVED_EVIDENCE"):
            h03.validate_knowledge_package(broken)

    def test_ast_is_presentation_structured(self):
        ast = h03.compile_document_ast(self.kp, self.bp)
        self.assertEqual(ast["schema_version"], "die.h03.document-ast.v1")
        self.assertTrue(any(b["type"] == "heading" for b in ast["blocks"]))
        self.assertTrue(any(b["type"] == "paragraph" for b in ast["blocks"]))

    def test_pdf_render_is_byte_deterministic_and_reopenable(self):
        ast = h03.compile_document_ast(self.kp, self.bp)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            a = td / "a.pdf"
            b = td / "b.pdf"
            h03.render_pdf(ast, a)
            h03.render_pdf(ast, b)
            self.assertEqual(h03.sha256_file(a), h03.sha256_file(b))
            validation = h03.validate_pdf(a, self.bp["title"], td / "renders")
            self.assertGreaterEqual(validation["page_count"], 2)
            self.assertEqual(validation["metadata_title"], self.bp["title"])
            self.assertTrue(all(v["nonwhite_ratio"] > 0.001 for v in validation["visual_pages"]))

    def test_mvp_build_receipt_preserves_unknown_economics(self):
        receipt = h03.build_mvp(ROOT)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["founder_active_minutes"], "UNKNOWN")
        self.assertEqual(receipt["cash_direct_cost"], "UNKNOWN")
        self.assertEqual(receipt["revenue_state"], "UNPROVEN")
        self.assertEqual(receipt["future_commercial_identity"]["listing_id"], "UNPROVEN")
        self.assertEqual(receipt["future_commercial_identity"]["order_id"], "UNPROVEN")
        self.assertEqual(receipt["future_commercial_identity"]["revenue_event_id"], "UNPROVEN")
        self.assertFalse(receipt["canonical_economics_write"])


if __name__ == "__main__":
    unittest.main()
