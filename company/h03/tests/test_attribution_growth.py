import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def load(name):
    p=ROOT/'company'/'h03'/'lib'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
attr=load('attribution'); growth=load('growth_atomizer')
E=ROOT/'company'/'h03'/'evidence'

class AttributionGrowthTests(unittest.TestCase):
    def data(self):
        return {
            'commerce':json.loads((E/'H03-COM-001'/'commerce-package.json').read_text(encoding='utf-8')),
            'kp':json.loads((E/'H03-ORG-001'/'stages'/'16-knowledge-package.json').read_text(encoding='utf-8')),
        }
    def test_identity_separates_acquisition_and_listing_channel(self):
        d=self.data(); i=attr.build_identity(problem_seed_id=d['commerce']['problem_seed_id'],product_id=d['commerce']['product_id'],commerce_package_id=d['commerce']['commerce_package_id'],channel_id='x',listing_channel_id='payhip',campaign_key='organic-v1',creative_key='short-text')
        self.assertEqual(i['channel_id'],'x'); self.assertEqual(i['listing_channel_id'],'payhip'); self.assertIn('payhip',i['listing_id']); self.assertEqual(i['destination_state'],'UNPUBLISHED'); self.assertIsNone(i['destination_url']); self.assertEqual(i['utm']['utm_source'],'x')
    def test_unobserved_funnel_does_not_invent_zero_conversion(self):
        d=self.data(); i=attr.build_identity(problem_seed_id=d['commerce']['problem_seed_id'],product_id=d['commerce']['product_id'],commerce_package_id=d['commerce']['commerce_package_id'],channel_id='threads',listing_channel_id='gumroad',campaign_key='organic-v1',creative_key='conversation')
        f=attr.build_unobserved_funnel_state(identity=i); self.assertTrue(all(v=='UNOBSERVED' for v in f['states'].values())); self.assertNotIn('0',json.dumps(f['states']))
    def test_observed_events_require_evidence_and_revenue_money(self):
        d=self.data(); i=attr.build_identity(problem_seed_id=d['commerce']['problem_seed_id'],product_id=d['commerce']['product_id'],commerce_package_id=d['commerce']['commerce_package_id'],channel_id='x',listing_channel_id='gumroad',campaign_key='organic-v1',creative_key='short')
        e=attr.build_observed_event(event_type='CLICK',identity=i,observed_at='2026-09-09T16:20:00Z',source_event_id='CLICK-1',evidence_refs=['analytics://click/1']); self.assertEqual(e['identity']['problem_seed_id'],d['commerce']['problem_seed_id'])
        with self.assertRaisesRegex(ValueError,'ATTR_ORDER_ID_REQUIRED'): attr.build_observed_event(event_type='REVENUE',identity=i,observed_at='2026-09-09T16:21:00Z',source_event_id='REV-1',evidence_refs=['order://1'],money={'currency':'USD','amount_minor':900})
        with self.assertRaisesRegex(ValueError,'ATTR_EVENT_EVIDENCE_REQUIRED'): attr.build_observed_event(event_type='CLICK',identity=i,observed_at='2026-09-09T16:20:00Z',source_event_id='CLICK-2',evidence_refs=[])
    def fixture_outputs(self):
        return {
            'x':{'claim_ids':['C4','C5'],'content':{'hook':'Opting out once is not the finish line.','body':'People-search listings can reappear, and opting out reduces exposure rather than deleting public records. Recheck periodically.','cta':'Save the workflow for your next privacy cleanup.'}},
            'threads':{'claim_ids':['C1','C2','C3'],'content':{'opening':'A practical way to start a people-search cleanup:','body':'Search for your listing, follow the site opt-out instructions, then repeat across other relevant sites. The repetitive part is exactly why a checklist helps.','cta':'Use a repeatable sequence instead of starting from scratch.'}},
            'instagram':{'claim_ids':['C1','C2','C4','C5'],'content':{'carousel_slides':['Find your listing','Follow the opt-out steps','Recheck later','Remember: exposure reduction is not total erasure'],'caption':'A simple four-part privacy cleanup sequence grounded in consumer guidance.','cta':'Save this carousel for your next recheck.'}},
            'facebook_page':{'claim_ids':['C1','C2','C4'],'content':{'post':'A practical people-search cleanup loop: find your listing, follow the site opt-out steps, and set a reminder to recheck later.','cta':'Keep the workflow handy for your next privacy cleanup.'}},
            'facebook_group':{'claim_ids':['C3','C4','C5'],'content':{'post':'For anyone doing people-search opt-outs manually: expect repetitive site-by-site work and plan to recheck later. Also, treat removal as exposure reduction rather than permanent erasure of public records.','cta':'NONE'}},
            'tiktok':{'claim_ids':['C1','C2','C4'],'content':{'hook':'Your people-search opt-out should be a loop, not a one-time task.','script_beats':['Find the listing','Follow the site opt-out flow','Set a reminder to recheck'],'cta':'Keep the sequence handy.'}},
            'youtube':{'claim_ids':['C1','C2','C3','C4','C5','C6'],'content':{'title':'How a DIY people-search opt-out workflow actually works','outline':['Find exposed listings','Submit site opt-outs','Repeat across sites','Recheck periodically','Understand what opt-out cannot erase','DIY versus paid-service choice'],'cta':'Use the guide as a repeatable checklist for the process.'}},
            'pinterest':{'claim_ids':['C1','C2','C4'],'content':{'pin_title':'DIY People-Search Opt-Out Workflow','pin_description':'Find the listing, follow the opt-out instructions, and schedule periodic rechecks. A compact evergreen privacy-cleanup reference.','cta':'Save for later.'}},
            'reddit':{'claim_ids':['C3','C4','C5'],'content':{'title':'A useful mental model for people-search opt-outs: maintenance, not permanent erasure','body':'The frustrating part is that removal is repetitive: you may need to opt out site by site and check again later. Also, removing a people-search listing is not the same as deleting underlying public records. Treat it as exposure reduction and maintenance.','cta':'NONE'}}
        }
    def test_growth_builds_nine_standard_work_cards_and_evidence_bound_atoms(self):
        d=self.data(); cards=growth.build_work_cards(commerce_package=d['commerce'],knowledge_package=d['kp'],campaign_key='organic-education-v1',listing_channel_id='gumroad'); self.assertEqual(len(cards),9); self.assertTrue(all(c['role']=='GROWTH_PRODUCER' for c in cards)); self.assertTrue(all(c['capability_requirements']=={'web_ai':True,'mcp':False,'shell':False,'local_filesystem':False} for c in cards))
        reg={c['channel_id']:c for c in growth.load_registry()['channels']}; outputs=self.fixture_outputs(); atoms=[]
        destinations=['google_play_books','gumroad','leanpub','fourthwall','ko_fi','lemon_squeezy','payhip','etsy','sellfy']
        for card,dest in zip(cards,destinations):
            cid=card['work_card_id'].rsplit('-',1)[-1]; atoms.append(growth.normalize_atom(card=card,channel=reg[cid],commerce_package=d['commerce'],knowledge_package=d['kp'],campaign_key='organic-education-v1',listing_channel_id=dest,model_output=outputs[cid]))
        self.assertEqual({a['channel_id'] for a in atoms},{'x','threads','instagram','facebook_page','facebook_group','tiktok','youtube','pinterest','reddit'}); self.assertEqual(len({a['campaign_id'] for a in atoms}),1); self.assertEqual(len({a['attribution_identity']['listing_channel_id'] for a in atoms}),9); self.assertTrue(all(a['evidence_refs'] for a in atoms)); self.assertTrue(all(a['paid_ads'] is False and a['publication_authorized'] is False for a in atoms)); self.assertEqual(next(a for a in atoms if a['channel_id']=='facebook_group')['content']['cta'],'NONE'); self.assertEqual(atoms[-1]['content']['cta'],'NONE')
        bp=growth.build_blueprint(commerce_package=d['commerce'],atoms=atoms,objective='organic education and demand capture'); self.assertEqual(len(bp['channels']),9); self.assertFalse(bp['paid_ads_enabled']); self.assertFalse(bp['publication_authorized'])
    def test_growth_rejects_unknown_claim(self):
        d=self.data(); cards=growth.build_work_cards(commerce_package=d['commerce'],knowledge_package=d['kp'],campaign_key='organic-v1',listing_channel_id='gumroad'); ch=growth.load_registry()['channels'][0]
        with self.assertRaisesRegex(ValueError,'GROWTH_CLAIM_SCOPE_INVALID'): growth.normalize_atom(card=cards[0],channel=ch,commerce_package=d['commerce'],knowledge_package=d['kp'],campaign_key='organic-v1',listing_channel_id='gumroad',model_output={'claim_ids':['C999'],'content':{'body':'bad'}})
