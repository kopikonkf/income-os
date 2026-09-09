import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def load(name):
    p=ROOT/'company'/'h03'/'lib'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
social=load('social_distribution'); analytics=load('analytics'); attr=load('attribution')
E=ROOT/'company'/'h03'/'evidence'

class SocialDistributionAnalyticsTests(unittest.TestCase):
    def commerce(self): return json.loads((E/'H03-COM-001'/'commerce-package.json').read_text(encoding='utf-8'))
    def identity(self, channel='facebook_page', listing='gumroad'):
        c=self.commerce(); return attr.build_identity(problem_seed_id=c['problem_seed_id'],product_id=c['product_id'],commerce_package_id=c['commerce_package_id'],channel_id=channel,listing_channel_id=listing,campaign_key='organic-v1',creative_key='test')
    def atom(self, channel='facebook_page', surface='FACEBOOK_PAGE_POST'):
        i=self.identity(channel=channel)
        return {'atom_id':f'H03-ATOM-{channel}','channel_id':channel,'surface':surface,'campaign_id':i['campaign_id'],'creative_id':i['creative_id'],'publication_authorized':False,'paid_ads':False}
    def test_growth_pool_is_separate_and_currently_unprovisioned(self):
        pool=social.load_growth_pool(); social.validate_growth_pool(pool)
        self.assertEqual(pool['purpose'],'GROWTH_WORKFORCE'); self.assertEqual(pool['pool_id'],'h03-growth-social-pool-v1')
        status=load('profile_pool').aggregate_runtime_status(pool)
        self.assertTrue(all(x['available_slots']==0 for x in status.values()))
        intents=social.build_distribution_intents(atoms=[self.atom()],pool=pool)
        self.assertEqual(intents[0]['distribution_state'],'WAITING_ACCOUNT_PREFLIGHT'); self.assertFalse(intents[0]['publication_authorized'])
    def test_ready_browser_slot_still_stops_at_founder_gate(self):
        pool=social.load_growth_pool(); pool['shards'][0]['state']='READY'
        target=next(p for p in pool['shards'][0]['providers'] if p['provider_id']=='facebook_page'); target['state']='READY'; target['available_slots']=1
        intent=social.build_distribution_intents(atoms=[self.atom()],pool=pool)[0]
        self.assertEqual(intent['distribution_state'],'READY_FOR_FOUNDER_GATE'); self.assertEqual(intent['transport_family'],'BROWSER_CDP'); self.assertTrue(intent['founder_gate_required']); self.assertFalse(intent['publication_authorized']); self.assertFalse(intent['session_material_persisted'])
    def test_facebook_page_and_group_are_distinct_adapters(self):
        reg=social.load_adapter_registry(); social.validate_adapter_registry(reg); ids={a['channel_id'] for a in reg['adapters']}
        self.assertIn('facebook_page',ids); self.assertIn('facebook_group',ids); self.assertEqual(len(ids),9)
    def test_analytics_unknown_metrics_stay_unknown(self):
        i=self.identity(); obs=analytics.build_unknown_observation(source_id='facebook_page',source_family='SOCIAL',observed_at='2026-09-09T17:05:00Z',identity=i,source_record_ref='social://facebook/page/pending')
        self.assertTrue(all(m['state']=='UNKNOWN' and m['value'] is None for m in obs['metrics'].values())); self.assertEqual(obs['referrer']['state'],'UNKNOWN')
    def test_analytics_normalizes_and_aggregates_evidence_only_metrics(self):
        i=self.identity(channel='x',listing='gumroad')
        obs=analytics.normalize_snapshot(source_id='gumroad',source_family='MARKETPLACE',observed_at='2026-09-09T17:06:00Z',identity=i,source_record_ref='gumroad://snapshot/1',metrics={
            'PRODUCT_VIEW':{'state':'OBSERVED','value':20,'evidence_refs':['gumroad://snapshot/1#views']},
            'ORDER':{'state':'OBSERVED','value':2,'evidence_refs':['gumroad://snapshot/1#orders']},
            'REVENUE':{'state':'OBSERVED','value':1800,'currency':'USD','evidence_refs':['gumroad://snapshot/1#revenue']}
        },referrer={'state':'OBSERVED','value':'x','evidence_refs':['gumroad://snapshot/1#referrer']})
        group=analytics.aggregate([obs],group_by='listing_channel_id')[0]
        self.assertEqual(group['metrics']['ORDER']['value'],2); self.assertEqual(group['metrics']['REVENUE']['value'],1800); self.assertEqual(group['conversion']['state'],'OBSERVED'); self.assertAlmostEqual(group['conversion']['value'],0.1); self.assertEqual(group['referrers'],['x'])
        events=analytics.to_attribution_events(obs); self.assertEqual({e['event_type'] for e in events},{'PRODUCT_VIEW','ORDER','REVENUE'})
    def test_partial_or_missing_denominator_does_not_invent_conversion(self):
        i=self.identity(channel='facebook_group',listing='payhip')
        obs=analytics.normalize_snapshot(source_id='facebook_group',source_family='SOCIAL',observed_at='2026-09-09T17:07:00Z',identity=i,source_record_ref='facebook://group/post/1',metrics={'IMPRESSION':{'state':'OBSERVED','value':100,'evidence_refs':['facebook://group/post/1#impressions']},'CLICK':{'state':'OBSERVED','value':8,'evidence_refs':['facebook://group/post/1#clicks']}})
        group=analytics.aggregate([obs],group_by='channel_id')[0]
        self.assertEqual(group['metrics']['ORDER']['state'],'UNKNOWN'); self.assertEqual(group['conversion']['state'],'UNKNOWN')
    def test_direct_destination_registry_keeps_domain_optional(self):
        d=json.loads((ROOT/'company'/'h03'/'runtime'/'commerce-direct-destination-registry.v1.json').read_text(encoding='utf-8-sig'))
        self.assertFalse(d['domain_policy']['custom_domain_required_to_start']); self.assertTrue(d['domain_policy']['custom_domain_recommended_for_scale'])
        ids={x['destination_id']:x for x in d['destinations']}
        self.assertEqual(ids['lynk_id']['market_scope'],'INDONESIA_PRIMARY'); self.assertIn('QRIS',ids['lynk_id']['payment_methods_observed']); self.assertEqual(ids['lemon_squeezy']['checkout_role'],'MERCHANT_OF_RECORD'); self.assertEqual(ids['paddle']['checkout_role'],'MERCHANT_OF_RECORD')

if __name__=='__main__': unittest.main()
