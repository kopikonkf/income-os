import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def load(name):
    p=ROOT/'company'/'h03'/'lib'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
release=load('product_release_gate'); boundary=load('runtime_boundary')
E=ROOT/'company'/'h03'/'evidence'

class GovernanceBoundaryTests(unittest.TestCase):
    def review(self):
        return json.loads((E/'H03-REV-001'/'founder-review-card.json').read_text(encoding='utf-8'))
    def test_independent_review_pass_is_not_founder_qc(self):
        r=self.review(); self.assertEqual(r['decision'],'PASS'); self.assertEqual(r['decision_authority'],'INDEPENDENT_REVIEWER_NOT_FOUNDER'); self.assertTrue(r['founder_action_required']); self.assertFalse(r['external_publication_authorized'])
        gate=release.evaluate_release_gate(review_card=r,founder_qc=None)
        self.assertEqual(gate['state'],'WAITING_FOUNDER_QC'); self.assertFalse(gate['publication_authorized'])
    def test_founder_qc_pass_without_publication_auth_still_blocks_release(self):
        r=self.review(); qc={'schema_version':'die.h03.founder-product-qc.v1','holding_id':'H03','founder_qc_id':'QC-1','product_id':r['product_id'],'review_card_id':r['review_card_id'],'reviewed_artifacts':['artifact://product/pdf'],'decision':'PASS','rights_release':'APPROVED','publication_authorized':False,'reviewed_at':'2026-09-09T18:30:00Z','notes':'reviewed'}
        gate=release.evaluate_release_gate(review_card=r,founder_qc=qc); self.assertEqual(gate['state'],'QC_PASS_PUBLICATION_NOT_AUTHORIZED')
    def test_founder_qc_pass_and_explicit_release_opens_preflight(self):
        r=self.review(); qc={'schema_version':'die.h03.founder-product-qc.v1','holding_id':'H03','founder_qc_id':'QC-2','product_id':r['product_id'],'review_card_id':r['review_card_id'],'reviewed_artifacts':['artifact://product/pdf'],'decision':'PASS','rights_release':'APPROVED','publication_authorized':True,'reviewed_at':'2026-09-09T18:30:00Z','notes':'approved'}
        gate=release.evaluate_release_gate(review_card=r,founder_qc=qc); self.assertEqual(gate['state'],'READY_FOR_PUBLICATION_PREFLIGHT'); self.assertTrue(gate['publication_authorized'])
    def test_mission_control_principal_profile_cannot_be_h03_operational_pool(self):
        bad={'schema_version':'die.h03.operational-browser-binding.v1','holding_id':'H03','pool_owner':'H03','purpose':'GROWTH_WORKFORCE','profile_class':'MISSION_CONTROL_PRINCIPAL_PRIMARY','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','transport_family':'BROWSER_CDP'}
        with self.assertRaisesRegex(ValueError,'CROSS_BOUNDARY_PROFILE_FORBIDDEN'): boundary.validate_operational_binding(bad)
    def test_h03_dedicated_binding_is_allowed_without_machine_paths(self):
        good={'schema_version':'die.h03.operational-browser-binding.v1','holding_id':'H03','pool_owner':'H03','purpose':'GROWTH_WORKFORCE','profile_class':'H03_DEDICATED_OPERATIONAL','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','transport_family':'BROWSER_CDP'}
        self.assertEqual(boundary.validate_operational_binding(good),good)
    def test_independent_review_dedicated_binding_is_allowed(self):
        good={'schema_version':'die.h03.operational-browser-binding.v1','holding_id':'H03','pool_owner':'H03','purpose':'INDEPENDENT_REVIEW_WORKFORCE','profile_class':'H03_DEDICATED_OPERATIONAL','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','transport_family':'BROWSER_CDP'}
        self.assertEqual(boundary.validate_operational_binding(good),good)

    def test_foreign_profile_preflight_is_invalidated(self):
        x=boundary.invalidate_foreign_preflight(source_profile_class='MISSION_CONTROL_PRINCIPAL_PRIMARY',observation_ref='company/h03/evidence/H03-FIRST-DOLLAR-001/live-readiness-preflight.json')
        self.assertFalse(x['valid_for_h03_runtime_readiness'])

if __name__=='__main__': unittest.main()
