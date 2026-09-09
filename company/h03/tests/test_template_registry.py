import copy, importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "h03_factory.py"
spec = importlib.util.spec_from_file_location("h03_factory_templates", P)
h03 = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(h03)

class TemplateRegistryTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "company" / "h03" / "examples" / "mvp"
        self.kp = h03.load_json(base / "knowledge-package.json")
        self.bp = h03.load_json(base / "product-blueprint.json")
        self.ast = h03.compile_document_ast(self.kp, self.bp)

    def test_registry_has_three_reusable_templates_and_no_external_font_files(self):
        reg = h03.load_json(ROOT / "company" / "h03" / "templates" / "pdf-template-registry.v1.json")
        typo = h03.load_json(ROOT / "company" / "h03" / "templates" / "typography-registry.v1.json")
        self.assertEqual(set(reg["templates"]), {"guide.clean.v1", "report.compact.v1", "worksheet.spacious.v1"})
        self.assertFalse(typo["external_font_files_allowed"])
        self.assertEqual(typo["font_policy"], "PDF_CORE_14_NO_EXTERNAL_FONT_FILE")

    def test_default_template_preserves_mvp_canonical_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "default.pdf"
            h03.render_pdf(self.ast, p)
            self.assertEqual(h03.sha256_file(p), "8199048f4a9ee0f70a4e0b62c07c7617ab61b9077cf6700311192617c7eb20ee")

    def test_template_change_does_not_mutate_ast_or_knowledge(self):
        kp_before = copy.deepcopy(self.kp); ast_before = copy.deepcopy(self.ast)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            outputs = {}
            for template_id in ("guide.clean.v1", "report.compact.v1", "worksheet.spacious.v1"):
                out = td / (template_id.replace(".", "-") + ".pdf")
                h03.render_pdf(self.ast, out, template_id)
                validation = h03.validate_pdf(out, self.bp["title"], td / (template_id + "-renders"))
                self.assertGreaterEqual(validation["page_count"], 2)
                outputs[template_id] = h03.sha256_file(out)
            self.assertEqual(len(set(outputs.values())), 3)
        self.assertEqual(self.kp, kp_before)
        self.assertEqual(self.ast, ast_before)

    def test_unknown_template_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "TEMPLATE_NOT_FOUND"):
                h03.render_pdf(self.ast, Path(td) / "x.pdf", "does.not.exist")
