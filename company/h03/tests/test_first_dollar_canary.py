import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'first_dollar_canary.py'
spec=importlib.util.spec_from_file_location('first_dollar_canary',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
E=ROOT/'company'/'h03'/'evidence'

class FirstDollarCanaryTests(unittest.TestCase):
    def price(self):
        return json.loads((E/'H03-COM-001'/'commerce-package.json').read_text(encoding='utf-8'))['pricing_hypothesis']
    def social(self, state='AUTH_REQUIRED'):
        return {k:state for k in ['facebook_page','facebook_group','pinterest','reddit','youtube','x','threads']}
    def test_founder_authorized_but_accounts_missing_blocks_live_action(self):
        c=mod.build_canary(product_id='H03-PROD-ORG001-001',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTH_REQUIRED','payhip':'CHALLENGE'},social_preflight=self.social())
        self.assertTrue(c['founder_authorized']); self.assertEqual(c['distribution_state'],'BLOCKED_SELLER_ACCOUNT_PREFLIGHT'); self.assertEqual(c['growth_state'],'BLOCKED_DISTRIBUTION_NOT_LIVE'); self.assertFalse(c['external_publication_occurred']); self.assertFalse(c['paid_ads'])
    def test_ready_seller_advances_only_to_publication_gate(self):
        c=mod.build_canary(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTH_REQUIRED'},social_preflight=self.social())
        self.assertEqual(c['distribution_state'],'READY_FOR_BOUNDED_PUBLICATION'); self.assertEqual(c['growth_state'],'BLOCKED_DISTRIBUTION_NOT_LIVE'); self.assertFalse(c['external_publication_occurred'])
    def test_published_listing_but_no_social_session_blocks_growth(self):
        c=mod.build_canary(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTH_REQUIRED'},social_preflight=self.social(),listing_published=True)
        self.assertEqual(c['distribution_state'],'PUBLISHED'); self.assertEqual(c['growth_state'],'BLOCKED_SOCIAL_ACCOUNT_PREFLIGHT'); self.assertTrue(c['external_publication_occurred'])
    def test_one_social_session_is_enough_for_bounded_growth(self):
        s=self.social(); s['pinterest']='AUTHENTICATED'
        c=mod.build_canary(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTH_REQUIRED'},social_preflight=s,listing_published=True)
        self.assertEqual(c['growth_state'],'READY_FOR_BOUNDED_ORGANIC_PROMOTION')
    def test_first_dollar_signal_requires_observed_revenue(self):
        s=self.social('AUTHENTICATED')
        c=mod.build_canary(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTHENTICATED'},social_preflight=s,listing_published=True,promotions_published=True,observed_revenue_minor=100)
        self.assertEqual(c['growth_state'],'PROMOTED'); self.assertIn('FIRST_DOLLAR_MILESTONE_OBSERVED',c['next_required_action'])
    def test_authorization_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError,'FOUNDER_AUTH_REQUIRED'):
            mod.build_canary(product_id='P',price_hypothesis=self.price(),seller_preflight={'gumroad':'AUTHENTICATED','payhip':'AUTH_REQUIRED'},social_preflight=self.social(),founder_authorized=False)

if __name__=='__main__': unittest.main()
