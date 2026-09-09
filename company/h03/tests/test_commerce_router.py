import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'commerce_router.py'
spec=importlib.util.spec_from_file_location('commerce_router',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
E=ROOT/'company'/'h03'/'evidence'

class CommerceRouterTests(unittest.TestCase):
    def data(self):
        return {
            'review':json.loads((E/'H03-REV-001'/'founder-review-card.json').read_text(encoding='utf-8')),
            'bp':json.loads((E/'H03-ORG-001'/'stages'/'18-product-blueprint.json').read_text(encoding='utf-8')),
            'package':json.loads((E/'H03-ORG-001'/'stages'/'21-package-receipt.json').read_text(encoding='utf-8')),
            'seed':json.loads((E/'H03-ORG-001'/'stages'/'03-problem-seed-batch.json').read_text(encoding='utf-8'))['candidates'][0],
        }
    def package(self):
        d=self.data()
        return mod.build_commerce_package(review_card=d['review'],blueprint=d['bp'],package_receipt=d['package'],problem_seed_id=d['seed']['problem_seed_id'],delivery_base_ref='artifact://H03-ORG-001/package/H03-PROD-ORG001-001')
    def test_registry_has_broad_multichannel_pool(self):
        r=mod.load_registry(); mod.validate_registry(r)
        self.assertGreaterEqual(len(r['channels']),18)
        ids={c['channel_id'] for c in r['channels']}
        for cid in {'etsy','gumroad','payhip','ko_fi','lemon_squeezy','amazon_kdp','google_play_books','apple_books','draft2digital','notion_marketplace','creative_market','creative_fabrica'}:
            self.assertIn(cid,ids)
    def test_guide_routes_to_multiple_current_income_surfaces(self):
        p=self.package(); routes={r['channel_id']:r for r in p['route_matrix']}
        for cid in ('gumroad','payhip','ko_fi','lemon_squeezy','google_play_books','leanpub','etsy'):
            self.assertEqual(routes[cid]['content_readiness'],'CONTENT_READY')
            self.assertEqual(routes[cid]['account_gate'],'PREFLIGHT_REQUIRED')
        self.assertEqual(routes['amazon_kdp']['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertEqual(routes['apple_books']['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertEqual(routes['draft2digital']['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertEqual(routes['notion_marketplace']['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertEqual(routes['teachers_pay_teachers']['content_readiness'],'NOT_ELIGIBLE')
        self.assertEqual(routes['envato']['content_readiness'],'PAUSED_INTAKE')
    def test_derivative_opportunities_are_deduplicated(self):
        p=self.package(); values=[x['derivative_type'] for x in p['derivative_opportunities']]
        self.assertEqual(len(values),len(set(values)))
        self.assertIn('epub_book',values)
        self.assertIn('notion_template',values)
    def test_package_is_channel_neutral_and_founder_locked(self):
        p=self.package()
        self.assertEqual(p['schema_version'],'die.h03.commerce-package.v1')
        self.assertTrue(p['publication_authority']['founder_required'])
        self.assertFalse(p['publication_authority']['external_publication_authorized'])
        self.assertFalse(p['pricing_hypothesis']['observed_sales'])
        self.assertEqual(p['pricing_hypothesis']['state'],'UNTESTED')
        self.assertNotIn('platform_account',json.dumps(p).lower())
    def test_channel_drafts_are_transforms_not_publication_actions(self):
        p=self.package()
        etsy=mod.build_channel_listing_draft(package=p,channel_id='etsy')
        google=mod.build_channel_listing_draft(package=p,channel_id='google_play_books')
        kdp=mod.build_channel_listing_draft(package=p,channel_id='amazon_kdp')
        notion=mod.build_channel_listing_draft(package=p,channel_id='notion_marketplace')
        self.assertFalse(etsy['publication_authorized'])
        self.assertEqual(len(etsy['listing_fields']['tags']),13)
        self.assertTrue(google['listing_fields']['content_files'])
        self.assertEqual(kdp['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertIn('epub_book',kdp['required_derivatives'])
        self.assertEqual(notion['content_readiness'],'DERIVATIVE_REQUIRED')
        self.assertIn('notion_template',notion['required_derivatives'])
    def test_review_must_pass_before_commerce(self):
        d=self.data(); d['review']['decision']='REVISE'
        with self.assertRaisesRegex(ValueError,'COMMERCE_REVIEW_PASS_REQUIRED'):
            mod.build_commerce_package(review_card=d['review'],blueprint=d['bp'],package_receipt=d['package'],problem_seed_id=d['seed']['problem_seed_id'],delivery_base_ref='artifact://x')
