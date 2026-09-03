import copy
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / 'company/factory-asset/schemas/asset-blueprint-v2.schema.json').read_text(encoding='utf-8-sig'))

BASE = {
    'schema': 'die.factory-asset.asset-blueprint.v2',
    'blueprint_id': 'FABP-SHOPPING_BAG_PHOTO',
    'semantic_identity': {
        'semantic_asset_id': 'FASA-SHOPPING_BAG_PHOTO',
        'commercial_use_case': 'generic reusable retail shopping-bag stock image',
        'subject': 'shopping bag',
        'intent': 'COMMERCIAL_STOCK',
    },
    'asset_type': 'PHOTO',
    'native_representation': 'RASTER_PIXELS',
    'producer_class': 'RASTER_GENERATIVE',
    'master_spec': {'format': 'PNG', 'width_px': 4096, 'height_px': 4096, 'color_space': 'SRGB', 'lineage_sha256_required': True},
    'derivatives': [{'derivative_id': 'ADOBE_JPEG', 'purpose': 'MARKETPLACE_DELIVERY', 'format': 'JPEG', 'semantic_identity_effect': 'NONE'}],
    'distinctness': {'identity_rule': 'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT', 'packaging_variants_create_new_semantic_asset': False, 'near_duplicate_action': 'QUARANTINE'},
    'rights': {'commercial_use_cleared': True, 'trademark_free': True, 'recognizable_person_or_property': False, 'release_state': 'NOT_REQUIRED'},
    'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['RASTER_DIMENSIONS', 'COLOR_SPACE']},
    'policy': {'compatibility_state': 'COMPATIBLE', 'marketplace_profiles': ['ADOBE_STOCK'], 'unknown_policy_action': 'BLOCK_SUBMISSION', 'submission_authority': 'FOUNDER_CONTROLLED'},
}

def validate(doc):
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)

def must_fail(doc):
    try:
        validate(doc)
    except jsonschema.ValidationError:
        return
    raise AssertionError('invalid blueprint unexpectedly passed')

def test_valid_raster_blueprint_passes():
    validate(BASE)

def test_packaging_derivative_never_mints_identity():
    bad = copy.deepcopy(BASE)
    bad['derivatives'][0]['semantic_identity_effect'] = 'NEW_SEMANTIC_ASSET'
    must_fail(bad)

def test_vector_requires_native_vector_producer_and_quality():
    bad = copy.deepcopy(BASE)
    bad['native_representation'] = 'VECTOR_PATHS'
    bad['producer_class'] = 'RASTER_GENERATIVE'
    bad['master_spec'] = {'format': 'SVG', 'lineage_sha256_required': True}
    bad['quality']['family_checks'] = ['VECTOR_PATHS_PRESENT', 'NO_EMBEDDED_RASTER_ONLY']
    must_fail(bad)

def test_motion_requires_duration_fps_and_integrity():
    bad = copy.deepcopy(BASE)
    bad['native_representation'] = 'TIMED_FRAMES'
    bad['producer_class'] = 'MOTION_RENDERER'
    bad['master_spec'] = {'format': 'MP4', 'lineage_sha256_required': True}
    bad['quality']['family_checks'] = ['MOTION_DURATION']
    must_fail(bad)

def test_recognizable_subject_requires_release_or_editorial_state():
    bad = copy.deepcopy(BASE)
    bad['rights']['recognizable_person_or_property'] = True
    bad['rights']['release_state'] = 'NOT_REQUIRED'
    must_fail(bad)

def test_policy_unknown_is_fail_closed():
    good = copy.deepcopy(BASE)
    good['policy']['compatibility_state'] = 'COMPATIBILITY_UNKNOWN'
    validate(good)
    bad = copy.deepcopy(good)
    bad['policy']['unknown_policy_action'] = 'ALLOW_SUBMISSION'
    must_fail(bad)

def test_submission_authority_remains_founder_controlled():
    bad = copy.deepcopy(BASE)
    bad['policy']['submission_authority'] = 'AUTONOMOUS'
    must_fail(bad)
