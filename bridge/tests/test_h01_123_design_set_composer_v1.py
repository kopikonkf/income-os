import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'company/company-os/die-h01/lib/design_set_composer_v1.py'
S=importlib.util.spec_from_file_location('h01_123_set',LIB); M=importlib.util.module_from_spec(S); sys.modules[S.name]=M; S.loader.exec_module(M)
SAMPLE=json.loads((ROOT/'company/company-os/die-h01/fixtures/h01-121-taxonomy-family-map.sample.json').read_text())['families']

class H01123DesignSet(unittest.TestCase):
    def setUp(self): self.family=copy.deepcopy(SAMPLE[0])
    def test_compose_is_deterministic_and_preserves_semantic_members(self):
        a=M.compose_design_set(self.family); b=M.compose_design_set(self.family)
        self.assertEqual(a,b); self.assertTrue(a['set_id'].startswith('DSET-V1-'))
        self.assertEqual([m['member_id'] for m in a['members']],[m['member_id'] for m in self.family['members']])
        self.assertTrue(all(m['identity_effect']=='NONE' for m in a['members']))
    def test_derivatives_never_become_set_members(self):
        d=M.compose_design_set(self.family)
        self.assertTrue(d['boundary']['is_design_set']); self.assertFalse(d['boundary']['is_derivative_bundle'])
        self.assertFalse(d['boundary']['is_listing_package']); self.assertTrue(d['boundary']['set_members_are_semantic_members'])
        self.assertFalse(d['boundary']['derivatives_create_set_members'])
        self.assertTrue(all(m['blueprint']['form']=='SINGLE' for m in d['members']))
    def test_review_required_family_stays_on_rights_hold(self):
        d=M.compose_design_set(self.family)
        self.assertEqual(d['rights_class'],'REVIEW_REQUIRED'); self.assertEqual(d['rights_gate']['decision'],'REVIEW_REQUIRED')
        self.assertEqual(d['rights_gate']['next_route'],'RIGHTS_REVIEW_HOLD'); self.assertFalse(d['rights_gate']['normal_stock_route_allowed'])
        self.assertFalse(any(d['authority'].values()))
    def test_brand_restricted_family_is_blocked(self):
        f=copy.deepcopy(self.family); f['rights_class']='BRAND_RESTRICTED'
        f['source']['evidence'].append({'evidence_id':'rights:test','kind':'RIGHTS_EVIDENCE','ref':'fixture://brand-restriction'})
        d=M.compose_design_set(f)
        self.assertEqual(d['rights_gate']['decision'],'BLOCK_NORMAL_STOCK'); self.assertEqual(d['rights_gate']['next_route'],'RESTRICTED_RIGHTS_REVIEW')
    def test_member_limit_is_bounded(self):
        f=max(SAMPLE,key=lambda x:len(x['members']))
        if len(f['members']) < 3: self.skipTest('sample has no family above two members')
        d=M.compose_design_set(copy.deepcopy(f),max_members=2); self.assertEqual(len(d['members']),2)
        with self.assertRaisesRegex(M.DesignSetError,'E_MAX_MEMBERS'): M.compose_design_set(copy.deepcopy(f),max_members=25)

if __name__=='__main__': unittest.main()
