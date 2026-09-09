import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'first_dollar_canary.py'
spec=importlib.util.spec_from_file_location('first_dollar_canary',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
E=ROOT/'company'/'h03'/'evidence'

class FirstDollarCanaryTests(unittest.TestCase):
    def price(self): return json.loads((E/'H03-COM-001'/'commerce-package.json').read_text(encoding='utf-8'))['pricing_hypothesis']
    def social(self,state='AUTH_REQUIRED'): return {k:state for k in ['facebook_page','facebook_group','pinterest','reddit','youtube','x','threads']}
    def base(self,**kw):
        args=dict(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTH_REQUIRED','payhip':'CHALLENGE'},social_preflight=self.social(),phase_authorized=True,founder_qc_state='PENDING',product_release_authorized=False,runtime_boundary_state='UNPROVEN')
        args.update(kw); return mod.build_canary(**args)
    def test_phase_authorization_does_not_bypass_founder_product_qc(self):
        c=self.base(); self.assertTrue(c['phase_authorized']); self.assertEqual(c['distribution_state'],'BLOCKED_FOUNDER_QC'); self.assertEqual(c['growth_state'],'BLOCKED_FOUNDER_QC'); self.assertFalse(c['product_release_authorized']); self.assertFalse(c['external_publication_occurred'])
    def test_qc_pass_without_release_auth_still_blocks(self):
        c=self.base(founder_qc_state='PASS'); self.assertEqual(c['distribution_state'],'BLOCKED_PRODUCT_RELEASE_AUTH')
    def test_release_auth_requires_qc_pass(self):
        with self.assertRaisesRegex(ValueError,'RELEASE_REQUIRES_FOUNDER_QC_PASS'): self.base(product_release_authorized=True)
    def test_foreign_or_unproven_runtime_boundary_blocks_account_preflight(self):
        c=self.base(founder_qc_state='PASS',product_release_authorized=True,runtime_boundary_state='INVALID_FOREIGN_PROFILE_EVIDENCE'); self.assertEqual(c['distribution_state'],'BLOCKED_RUNTIME_BOUNDARY')
    def test_dedicated_runtime_then_seller_readiness_controls_distribution(self):
        c=self.base(founder_qc_state='PASS',product_release_authorized=True,runtime_boundary_state='VALID_H03_DEDICATED'); self.assertEqual(c['distribution_state'],'BLOCKED_SELLER_ACCOUNT_PREFLIGHT')
        c=self.base(founder_qc_state='PASS',product_release_authorized=True,runtime_boundary_state='VALID_H03_DEDICATED',seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTH_REQUIRED'}); self.assertEqual(c['distribution_state'],'READY_FOR_BOUNDED_PUBLICATION')
    def test_publication_without_release_auth_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'PUBLICATION_WITHOUT_PRODUCT_RELEASE_AUTH'): self.base(listing_published=True)

if __name__=='__main__': unittest.main()
