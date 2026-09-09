import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def load(name):
    p=ROOT/'company'/'h03'/'lib'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
feedback=load('demand_feedback'); analytics=load('analytics'); attr=load('attribution')
E=ROOT/'company'/'h03'/'evidence'

class DemandFeedbackTests(unittest.TestCase):
    def demand(self): return json.loads((E/'H03-ORG-001'/'stages'/'05-demand-wtp.json').read_text(encoding='utf-8'))
    def commerce(self): return json.loads((E/'H03-COM-001'/'commerce-package.json').read_text(encoding='utf-8'))
    def identity(self, channel='x', listing='gumroad'):
        c=self.commerce(); return attr.build_identity(problem_seed_id=c['problem_seed_id'],product_id=c['product_id'],commerce_package_id=c['commerce_package_id'],channel_id=channel,listing_channel_id=listing,campaign_key='feedback-fixture',creative_key='fixture')
    def observation(self, metrics, channel='x', listing='gumroad'):
        return analytics.normalize_snapshot(source_id=listing,source_family='MARKETPLACE',observed_at='2026-09-09T17:30:00Z',identity=self.identity(channel,listing),source_record_ref=f'fixture://{listing}/feedback',metrics=metrics)
    def test_unobserved_baseline_produces_no_calibration_candidate(self):
        baseline=json.loads((E/'H03-ANL-001'/'analytics-baseline-unobserved.json').read_text(encoding='utf-8'))
        product=self.commerce()['product_id']; r=feedback.build_calibration(demand_packet=self.demand(),observations=baseline,product_id=product)
        self.assertEqual(r['calibration_state'],'INSUFFICIENT_OBSERVED_OUTCOMES'); self.assertEqual(r['feedback_signals'],[]); self.assertEqual(r['recommended_wtp_assessment'],'MEDIUM'); self.assertIsNone(r['calibrated_demand_packet_candidate']); self.assertFalse(r['causal_claim']); self.assertFalse(r['canonical_mutation_authorized'])
    def test_engagement_only_never_becomes_wtp(self):
        obs=self.observation({'IMPRESSION':{'state':'OBSERVED','value':1000,'evidence_refs':['fixture://imp']},'CLICK':{'state':'OBSERVED','value':80,'evidence_refs':['fixture://click']},'PRODUCT_VIEW':{'state':'OBSERVED','value':40,'evidence_refs':['fixture://view']}})
        r=feedback.build_calibration(demand_packet=self.demand(),observations=[obs],product_id=self.commerce()['product_id'])
        self.assertEqual(r['calibration_state'],'ENGAGEMENT_ONLY'); self.assertEqual(r['feedback_signals'][0]['signal_type'],'ENGAGEMENT_ONLY'); self.assertEqual(r['recommended_wtp_assessment'],'MEDIUM'); self.assertEqual(r['calibrated_demand_packet_candidate']['wtp_assessment'],'MEDIUM')
    def test_add_to_cart_strengthens_intent_not_spend(self):
        obs=self.observation({'ADD_TO_CART':{'state':'OBSERVED','value':5,'evidence_refs':['fixture://cart']}})
        r=feedback.build_calibration(demand_packet=self.demand(),observations=[obs],product_id=self.commerce()['product_id'])
        self.assertEqual(r['calibration_state'],'PURCHASE_INTENT_OBSERVED'); self.assertEqual(r['feedback_signals'][0]['signal_type'],'PURCHASE_INTENT_SEARCH'); self.assertEqual(r['recommended_buyer_intent_state'],'STRONG'); self.assertEqual(r['recommended_wtp_assessment'],'MEDIUM')
    def test_order_without_revenue_is_sale_proxy_only(self):
        obs=self.observation({'ORDER':{'state':'OBSERVED','value':2,'evidence_refs':['fixture://orders']}})
        r=feedback.build_calibration(demand_packet=self.demand(),observations=[obs],product_id=self.commerce()['product_id'])
        self.assertEqual(r['calibration_state'],'SALE_PROXY_OBSERVED'); self.assertEqual(r['feedback_signals'][0]['signal_type'],'MARKETPLACE_SALE_PROXY'); self.assertEqual(r['recommended_wtp_assessment'],'MEDIUM')
    def test_observed_order_and_revenue_create_revealed_spend_candidate(self):
        obs=self.observation({'ORDER':{'state':'OBSERVED','value':2,'evidence_refs':['fixture://orders']},'REVENUE':{'state':'OBSERVED','value':1800,'currency':'USD','evidence_refs':['fixture://revenue']}})
        r=feedback.build_calibration(demand_packet=self.demand(),observations=[obs],product_id=self.commerce()['product_id'])
        self.assertEqual(r['calibration_state'],'REVEALED_SPEND_OBSERVED'); signal=r['feedback_signals'][0]; self.assertEqual(signal['signal_type'],'REVEALED_SPEND'); self.assertEqual(signal['money'],{'currency':'USD','amount_minor':1800}); self.assertEqual(r['recommended_wtp_assessment'],'STRONG'); self.assertEqual(r['calibrated_demand_packet_candidate']['truth_status'],'CANDIDATE'); self.assertFalse(r['canonical_mutation_authorized'])
    def test_mismatched_problem_seed_fails_closed(self):
        obs=self.observation({'CLICK':{'state':'OBSERVED','value':1,'evidence_refs':['fixture://click']}}); obs['identity']['problem_seed_id']='OTHER'
        with self.assertRaisesRegex(ValueError,'PROBLEM_SEED_MISMATCH'): feedback.build_calibration(demand_packet=self.demand(),observations=[obs],product_id=self.commerce()['product_id'])

if __name__=='__main__': unittest.main()
