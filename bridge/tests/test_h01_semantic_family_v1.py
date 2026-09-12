import copy
import hashlib
import json
import unittest
from pathlib import Path

import importlib.util
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / 'company' / 'company-os' / 'die-h01'
SCHEMA = json.loads((H01 / 'contracts' / 'h01-semantic-family.v1.schema.json').read_text(encoding='utf-8'))
FIXTURES = json.loads((H01 / 'fixtures' / 'h01-semantic-family-v1.examples.json').read_text(encoding='utf-8'))
DOC = (H01 / 'DIE_H01_SEMANTIC_FAMILY_V1.md').read_text(encoding='utf-8')
TASK_GRAPH = H01 / 'die-h01-task-graph.v1.json'
LIB = H01 / 'lib' / 'semantic_family_v1.py'
SPEC = importlib.util.spec_from_file_location('h01_family_lib', LIB)
FAMILY = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(FAMILY)
LEGACY = json.loads((ROOT / 'company' / 'die-agents' / 'hermes' / 'production-cognition' / 'die.production.family-blueprint.v1.schema.json').read_text(encoding='utf-8'))


def validate(doc):
    FAMILY.validate_semantic_family(doc)


def must_fail(doc):
    with unittest.TestCase().assertRaises(FAMILY.SemanticFamilyError):
        validate(doc)


def expected_family_id(doc):
    payload = {
        'family_version': doc['family_version'],
        'family_class': doc['family_class'],
        'semantic_key': doc['semantic_identity']['semantic_key'],
        'canonical_subject_ids': sorted(m['canonical_subject_ref']['subject_id'] for m in doc['members']),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return f"FAM-V1-{doc['family_class']}-{hashlib.sha256(raw).hexdigest()[:24].upper()}"


class SemanticFamilyV1Tests(unittest.TestCase):
    def setUp(self):
        self.examples = FIXTURES['examples']
        self.by_class = {x['family_class']: x for x in self.examples}

    def test_schema_is_valid_draft_2020_12(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)

    def test_exactly_five_required_family_classes_validate(self):
        expected = {'TAXONOMIC', 'FUNCTIONAL', 'CONTEXTUAL', 'VARIANT', 'SYSTEM'}
        self.assertEqual(set(self.by_class), expected)
        self.assertEqual(len(self.examples), 5)
        for example in self.examples:
            validate(example)

    def test_family_id_is_deterministic_and_members_are_sorted_unique(self):
        for example in self.examples:
            ids = [m['canonical_subject_ref']['subject_id'] for m in example['members']]
            self.assertEqual(ids, sorted(ids))
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(example['family_id'], expected_family_id(example))
            self.assertEqual(example['family_id'], FAMILY.canonical_family_id(example))
            self.assertEqual(example['determinism']['member_order'], 'CANONICAL_SUBJECT_ID_ASC')

    def test_member_identity_and_object_atlas_linkage_are_preserved(self):
        for example in self.examples:
            self.assertFalse(example['semantic_identity']['family_membership_creates_new_asset_identity'])
            self.assertEqual(example['semantic_identity']['member_identity_policy'], 'PRESERVE_CANONICAL_SUBJECT')
            for member in example['members']:
                self.assertEqual(member['member_kind'], 'CANONICAL_SEMANTIC_MEMBER')
                self.assertEqual(member['canonical_subject_ref']['source'], 'OBJECT_ATLAS')
                self.assertEqual(member['identity_effect'], 'NONE')

    def test_validator_rejects_subject_id_order_duplicates_and_member_id_drift(self):
        bad = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad['members'] = list(reversed(bad['members']))
        with self.assertRaisesRegex(FAMILY.SemanticFamilyError, 'E_MEMBER_ORDER'):
            validate(bad)
        bad = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad['members'][1]['canonical_subject_ref']['subject_id'] = bad['members'][0]['canonical_subject_ref']['subject_id']
        bad['members'][1]['member_id'] = bad['members'][0]['member_id']
        with self.assertRaisesRegex(FAMILY.SemanticFamilyError, 'E_DUPLICATE_CANONICAL_SUBJECT'):
            validate(bad)
        bad = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad['members'][0]['member_id'] = 'OA-DRIFTED-MEMBER'
        with self.assertRaisesRegex(FAMILY.SemanticFamilyError, 'E_MEMBER_ID_DRIFT'):
            validate(bad)

    def test_validator_rejects_family_id_mismatch(self):
        bad = copy.deepcopy(self.by_class['FUNCTIONAL'])
        bad['family_id'] = 'FAM-V1-FUNCTIONAL-000000000000000000000000'
        with self.assertRaisesRegex(FAMILY.SemanticFamilyError, 'E_FAMILY_ID_MISMATCH'):
            validate(bad)

    def test_single_asset_with_derivatives_cannot_be_a_family(self):
        bad = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad['members'] = bad['members'][:1]
        must_fail(bad)

    def test_derivative_bundle_conflation_is_rejected(self):
        bad = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad['artifact_kind'] = 'DERIVATIVE_BUNDLE'
        bad['members'][0]['member_kind'] = 'DERIVATIVE_FILE'
        must_fail(bad)
        bad2 = copy.deepcopy(self.by_class['TAXONOMIC'])
        bad2['boundary']['is_derivative_bundle'] = True
        must_fail(bad2)

    def test_listing_package_conflation_is_rejected(self):
        bad = copy.deepcopy(self.by_class['FUNCTIONAL'])
        bad['artifact_kind'] = 'LISTING_PACKAGE'
        must_fail(bad)
        bad2 = copy.deepcopy(self.by_class['FUNCTIONAL'])
        bad2['boundary']['is_listing_package'] = True
        must_fail(bad2)

    def test_design_set_conflation_is_rejected(self):
        bad = copy.deepcopy(self.by_class['CONTEXTUAL'])
        bad['boundary']['is_design_set'] = True
        must_fail(bad)

    def test_source_evidence_and_rights_class_are_required(self):
        bad = copy.deepcopy(self.by_class['VARIANT'])
        bad['source']['evidence'] = []
        must_fail(bad)
        bad2 = copy.deepcopy(self.by_class['VARIANT'])
        del bad2['rights_class']
        must_fail(bad2)

    def test_brand_restricted_system_is_representable_but_not_authorized(self):
        system = self.by_class['SYSTEM']
        validate(system)
        self.assertEqual(system['rights_class'], 'BRAND_RESTRICTED')
        self.assertFalse(system['authority']['production_authorized'])
        self.assertFalse(system['authority']['submission_authorized'])
        self.assertFalse(system['authority']['publication_authorized'])
        self.assertFalse(system['authority']['restricted_family_auto_eligible'])

    def test_legacy_family_blueprint_is_not_semantic_family_v1(self):
        self.assertNotEqual(LEGACY.get('$id'), SCHEMA.get('$id'))
        self.assertIn('Older Division01 / production-cognition artifacts', DOC)
        self.assertIn('artifact_kind=SEMANTIC_FAMILY', DOC)

    def test_boundary_vocabulary_is_explicit_in_doctrine(self):
        for term in ('SEMANTIC FAMILY', 'DESIGN SET', 'DERIVATIVE BUNDLE', 'LISTING PACKAGE'):
            self.assertIn(term, DOC)
        self.assertIn('one semantic asset with derivatives', DOC.lower())


    def test_task_graph_opens_only_direct_h01_120_descendants(self):
        graph = json.loads(TASK_GRAPH.read_text(encoding='utf-8'))
        tasks = {x['id']: x for x in graph['tasks']}
        self.assertEqual(tasks['H01-120']['status'], 'DONE')
        self.assertEqual(tasks['H01-121']['status'], 'READY')
        self.assertEqual(tasks['H01-122']['status'], 'READY')
        self.assertEqual(tasks['H01-123']['status'], 'BLOCKED')
        self.assertEqual(tasks['H01-123']['depends_on'], ['H01-111', 'H01-121', 'H01-122'])

if __name__ == '__main__':
    unittest.main()
