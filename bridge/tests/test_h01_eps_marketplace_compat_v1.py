import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'company/factory-asset/lib/vector_postproduction.py'
SPEC = importlib.util.spec_from_file_location('h01_eps_marketplace_v1', LIB)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M10 10 L90 10 L90 90 L10 90 Z" fill="#336699" stroke="#000000" stroke-width="2"/></svg>'''

class H01EpsMarketplaceCompatV1(unittest.TestCase):
    def test_marketplace_eps_common_window_and_vector_purity(self):
        with tempfile.TemporaryDirectory() as td:
            receipt = MODULE.postprocess_vector(SVG, Path(td), 'FASA-H01-EPS-MARKET')
            e = receipt['acceptance_evidence']['validated_eps']
            self.assertEqual(e['result'], 'PASS')
            self.assertTrue(e['marketplace_area_pass'])
            self.assertGreaterEqual(e['bounding_box_area'], 15_000_000)
            self.assertLessEqual(e['bounding_box_area'], 25_000_000)
            self.assertTrue(e['language_level_2'])
            self.assertTrue(e['clean_7bit'])
            self.assertTrue(e['hires_bounding_box'])
            self.assertTrue(e['rgb_only'])
            self.assertFalse(e['contains_raster_operator'])
            self.assertFalse(e['contains_live_font_operator'])
            self.assertFalse(e['contains_transparency_operator'])
            self.assertEqual(e['legacy_illustrator_structural_profile'], 'POSTSCRIPT_LEVEL_2_SIMPLE_PATHS')
            self.assertFalse(e['native_illustrator_save_certified'])
            eps=(Path(td)/'master.eps').read_bytes()
            self.assertIn(b'%%Creator: DIE H01 Vector Postproduction', eps)
            self.assertIn(b'%%LanguageLevel: 2', eps)
            self.assertIn(b'%%DocumentData: Clean7Bit', eps)
            self.assertIn(b'%%HiResBoundingBox:', eps)

if __name__ == '__main__':
    unittest.main()
