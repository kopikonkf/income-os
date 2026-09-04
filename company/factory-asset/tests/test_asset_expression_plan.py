import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'fixtures/asset-expression-plan'
spec = importlib.util.spec_from_file_location('asset_expression_plan', ROOT / 'lib/asset_expression_plan.py')
planner = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(planner)


def fixture(name='one'):
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def invalid(plan, code='PLAN_SCHEMA_INVALID'):
    with pytest.raises(planner.AssetExpressionPlanError) as caught:
        planner.validate_asset_expression_plan(plan)
    assert caught.value.code == code


def test_schema_is_valid_draft_202012():
    schema = json.loads(planner.SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(('name', 'count'), [('zero', 0), ('one', 1), ('multiple', 3)])
def test_same_seed_supports_zero_one_and_multiple_decisions(name, count):
    plan = fixture(name)
    original = copy.deepcopy(plan)
    planner.validate_asset_expression_plan(plan)
    assert plan == original
    assert plan['seed']['noun'] == 'shopping bag'
    assert len(plan['expressions']) == count


def test_reject_is_a_valid_zero_expression_outcome():
    plan = fixture('zero')
    plan['decision'] = 'REJECT'
    plan['decision_rationale'] = 'The reviewed seed has no commercially supported buyer use case.'
    planner.validate_asset_expression_plan(plan)


@pytest.mark.parametrize(('name', 'decision'), [('zero', 'SELECT'), ('one', 'RESEARCH'), ('one', 'REJECT')])
def test_decision_and_cardinality_must_agree(name, decision):
    plan = fixture(name)
    plan['decision'] = decision
    invalid(plan)


@pytest.mark.parametrize(('field', 'value'), [
    ('expansion_rule', 'ALL_MODES'), ('force_all_modes', True),
    ('packaging_variants_create_new_semantic_asset', True),
    ('derivative_planning_stage', 'BEFORE_SEMANTIC_SELECTION'),
])
def test_forced_expansion_and_packaging_inflation_are_forbidden(field, value):
    plan = fixture()
    plan['policy'][field] = value
    invalid(plan)


@pytest.mark.parametrize('field', ['derivatives', 'output_format', 'master_sha256'])
def test_delivery_and_existing_master_fields_are_not_semantic_inputs(field):
    plan = fixture()
    plan['expressions'][0][field] = 'PNG'
    invalid(plan)


@pytest.mark.parametrize('field', ['buyer', 'commercial_use_case', 'product_expression', 'semantic_mode',
                                    'producer_class', 'candidate_marketplace_route', 'evidence_refs'])
def test_selected_expression_requires_every_pin(field):
    plan = fixture()
    del plan['expressions'][0][field]
    invalid(plan)


@pytest.mark.parametrize(('mode', 'producer'), [
    ('PHOTO', 'MOTION_RENDERER'), ('PATTERN', 'RASTER_GENERATIVE'),
    ('ANIMATION', 'RASTER_GENERATIVE'), ('JPEG', 'RASTER_GENERATIVE'),
    ('ICON', 'MOTION_RENDERER'), ('OUTLINE', 'RASTER_GENERATIVE'),
])
def test_unknown_modes_and_incompatible_producers_fail_closed(mode, producer):
    plan = fixture()
    plan['expressions'][0].update(semantic_mode=mode, producer_class=producer)
    invalid(plan)


def test_animation_requires_meaningful_temporal_description():
    plan = fixture('multiple')
    del plan['expressions'][2]['temporal_value']
    invalid(plan)


def test_referencing_missing_evidence_fails_closed():
    plan = fixture()
    plan['expressions'][0]['evidence_refs'] = ['missing-evidence']
    invalid(plan, 'EVIDENCE_REFERENCE_UNKNOWN')


def test_each_expression_needs_its_own_supported_scope():
    plan = fixture('multiple')
    plan['expressions'][1]['evidence_refs'] = ['fixture-photo']
    invalid(plan, 'EVIDENCE_SCOPE_MISMATCH')


@pytest.mark.parametrize('field', ['buyer', 'commercial_use_case', 'product_expression'])
def test_commercial_pin_cannot_drift_from_evidence(field):
    plan = fixture()
    plan['expressions'][0][field] = 'Different unsupported commercial interpretation'
    invalid(plan, 'EVIDENCE_SCOPE_MISMATCH')


def test_seed_cannot_drift_from_evidence():
    plan = fixture()
    plan['seed']['noun'] = 'water bottle'
    invalid(plan, 'EVIDENCE_SCOPE_MISMATCH')


def test_route_cannot_drift_or_claim_compatibility():
    plan = fixture()
    plan['expressions'][0]['candidate_marketplace_route']['platform_id'] = 'OTHER_MARKET'
    invalid(plan, 'EVIDENCE_SCOPE_MISMATCH')
    plan = fixture()
    plan['expressions'][0]['candidate_marketplace_route']['state'] = 'COMPATIBLE'
    invalid(plan)


def test_duplicate_evidence_and_semantic_ids_fail():
    plan = fixture('multiple')
    plan['evidence'][1]['evidence_id'] = plan['evidence'][0]['evidence_id']
    invalid(plan, 'DUPLICATE_EVIDENCE_ID')
    plan = fixture('multiple')
    plan['expressions'][1]['semantic_asset_id'] = plan['expressions'][0]['semantic_asset_id']
    invalid(plan, 'DUPLICATE_SEMANTIC_ASSET_ID')


def test_new_id_route_or_case_does_not_mint_duplicate_semantics():
    plan = fixture()
    duplicate = copy.deepcopy(plan['expressions'][0])
    duplicate['semantic_asset_id'] = 'FASA-SHOPPING_BAG_COPY'
    duplicate['candidate_marketplace_route']['platform_id'] = 'OTHER_MARKET'
    duplicate['product_expression'] = '  ' + duplicate['product_expression'].upper() + '  '
    plan['expressions'].append(duplicate)
    invalid(plan, 'DUPLICATE_SEMANTIC_EXPRESSION')


def test_fixture_evidence_sources_are_real_pinned_local_bytes():
    for item in fixture('multiple')['evidence']:
        assert item['kind'] == 'SYNTHETIC_FIXTURE'
        relative, anchor = item['source_ref'].split('#')
        source = ROOT.parents[1] / relative
        assert hashlib.sha256(source.read_bytes()).hexdigest() == item['source_sha256']
        assert anchor in json.loads(source.read_text())


def test_blank_commercial_claim_is_invalid():
    plan = fixture()
    plan['expressions'][0]['commercial_use_case'] = ' ' * 20
    invalid(plan)
