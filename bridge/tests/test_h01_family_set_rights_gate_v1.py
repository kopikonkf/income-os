import copy
import importlib.util
import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / 'company' / 'company-os' / 'die-h01'
SCHEMA = json.loads((H01 / 'contracts' / 'h01-family-set-rights-candidate.v1.schema.json').read_text())
FIX = json.loads((H01 / 'fixtures' / 'h01-family-set-rights-gate-v1.cases.json').read_text())
FAMILY_FIX = json.loads((H01 / 'fixtures' / 'h01-semantic-family-v1.examples.json').read_text())['examples']
DOC = (H01 / 'DIE_H01_FAMILY_SET_RIGHTS_GATE_V1.md').read_text()
spec = importlib.util.spec_from_file_location('h01_family_set_rights_gate', H01 / 'lib' / 'family_set_rights_gate.py')
gate = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(gate)


class H01FamilySetRightsGateV1Tests(unittest.TestCase):
    def setUp(self):
        self.cases = {x['name']: x for x in FIX['cases']}

    def test_schema_is_valid_draft_202012(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)

    def test_all_fixture_routes_match_expected(self):
        for case in FIX['cases']:
            result = gate.evaluate_family_set_rights(copy.deepcopy(case['candidate']))
            self.assertEqual(result['decision'], case['expected_decision'])
            self.assertEqual(result['next_route'], case['expected_route'])
            self.assertFalse(result['legal_clearance_claimed'])
            self.assertFalse(result['authority']['production_authorized'])
            self.assertFalse(result['authority']['submission_authorized'])
            self.assertFalse(result['authority']['publication_authorized'])
            self.assertFalse(result['authority']['rights_gate_bypass_allowed'])

    def test_brand_restricted_system_is_discoverable_but_normal_stock_blocked(self):
        result = gate.evaluate_family_set_rights(copy.deepcopy(self.cases['brand-restricted-system-blocked-from-normal-stock']['candidate']))
        self.assertTrue(result['discovery_preserved'])
        self.assertEqual(result['rights_class'], 'BRAND_RESTRICTED')
        self.assertEqual(result['decision'], 'BLOCK_NORMAL_STOCK')
        self.assertEqual(result['next_route'], 'RESTRICTED_RIGHTS_REVIEW')
        self.assertFalse(result['normal_stock_route_allowed'])

    def test_design_set_inherits_strongest_constituent_rights(self):
        result = gate.evaluate_family_set_rights(copy.deepcopy(self.cases['design-set-with-brand-family-blocked']['candidate']))
        self.assertEqual(result['candidate_kind'], 'DESIGN_SET')
        self.assertEqual(result['rights_class'], 'BRAND_RESTRICTED')
        self.assertFalse(result['normal_stock_route_allowed'])

    def test_caller_cannot_downgrade_brand_constituent_to_generic(self):
        bad = copy.deepcopy(self.cases['design-set-with-brand-family-blocked']['candidate'])
        bad['declared_rights_class'] = 'GENERIC_UNRESTRICTED'
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_RIGHTS_CLASS_DRIFT'):
            gate.evaluate_family_set_rights(bad)

    def test_brand_restriction_requires_explicit_rights_evidence(self):
        bad = copy.deepcopy(self.cases['brand-restricted-system-blocked-from-normal-stock']['candidate'])
        bad['evidence'][0]['kind'] = 'CURATED_RELATION'
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_BRAND_RESTRICTION_EVIDENCE_REQUIRED'):
            gate.evaluate_family_set_rights(bad)

    def test_unknown_and_review_required_fail_closed(self):
        for name in ('unknown-rights-held', 'review-required-family-held'):
            result = gate.evaluate_family_set_rights(copy.deepcopy(self.cases[name]['candidate']))
            self.assertEqual(result['decision'], 'REVIEW_REQUIRED')
            self.assertEqual(result['next_route'], 'RIGHTS_REVIEW_HOLD')
            self.assertFalse(result['normal_stock_route_allowed'])

    def test_generic_unrestricted_only_passes_to_next_gate_not_production(self):
        result = gate.evaluate_family_set_rights(copy.deepcopy(self.cases['generic-family-normal-stock-candidate']['candidate']))
        self.assertEqual(result['decision'], 'PASS_TO_NEXT_GATE')
        self.assertTrue(result['normal_stock_route_allowed'])
        self.assertFalse(result['authority']['production_authorized'])
        self.assertIn('candidate only', DOC)

    def test_missing_evidence_reference_fails_closed(self):
        bad = copy.deepcopy(self.cases['generic-family-normal-stock-candidate']['candidate'])
        bad['constituents'][0]['evidence_refs'] = ['EVID-MISSING']
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_EVIDENCE_REF_UNKNOWN'):
            gate.evaluate_family_set_rights(bad)

    def test_duplicate_constituents_and_evidence_fail_closed(self):
        bad = copy.deepcopy(self.cases['generic-family-normal-stock-candidate']['candidate'])
        bad['constituents'][1]['ref_id'] = bad['constituents'][0]['ref_id']
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_DUPLICATE_CONSTITUENT'):
            gate.evaluate_family_set_rights(bad)
        bad = copy.deepcopy(self.cases['design-set-with-brand-family-blocked']['candidate'])
        bad['evidence'][1]['evidence_id'] = bad['evidence'][0]['evidence_id']
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_DUPLICATE_EVIDENCE'):
            gate.evaluate_family_set_rights(bad)

    def test_derivative_bundle_or_listing_package_cannot_enter_gate(self):
        for kind in ('DERIVATIVE_BUNDLE', 'LISTING_PACKAGE'):
            bad = copy.deepcopy(self.cases['generic-family-normal-stock-candidate']['candidate'])
            bad['candidate_kind'] = kind
            with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_SCHEMA'):
                gate.evaluate_family_set_rights(bad)

    def test_h01_120_generic_and_brand_families_adapt_without_identity_rewrite(self):
        by_class = {x['family_class']: x for x in FAMILY_FIX}
        generic = gate.candidate_from_semantic_family(copy.deepcopy(by_class['TAXONOMIC']))
        restricted = gate.candidate_from_semantic_family(copy.deepcopy(by_class['SYSTEM']))
        self.assertEqual(generic['candidate_id'], by_class['TAXONOMIC']['family_id'])
        self.assertEqual(restricted['candidate_id'], by_class['SYSTEM']['family_id'])
        self.assertEqual(gate.evaluate_family_set_rights(generic)['decision'], 'PASS_TO_NEXT_GATE')
        self.assertEqual(gate.evaluate_family_set_rights(restricted)['decision'], 'BLOCK_NORMAL_STOCK')
        self.assertEqual([x['ref_id'] for x in restricted['constituents']], [x['member_id'] for x in by_class['SYSTEM']['members']])

    def test_requested_route_is_fixed_to_normal_stock_production(self):
        bad = copy.deepcopy(self.cases['generic-family-normal-stock-candidate']['candidate'])
        bad['requested_route'] = 'AUTO_PUBLISH'
        with self.assertRaisesRegex(gate.FamilySetRightsGateError, 'E_SCHEMA'):
            gate.evaluate_family_set_rights(bad)

    def test_doctrine_separates_preproduction_gate_from_fa136(self):
        self.assertIn('pre-production semantic rights-routing gate', DOC)
        self.assertIn('complements, rather than replaces', DOC)
        self.assertIn('FA-136', DOC)
        self.assertIn('cannot silently route into normal stock production', DOC)


if __name__ == '__main__':
    unittest.main()
