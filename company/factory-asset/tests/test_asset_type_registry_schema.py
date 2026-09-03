import copy
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / 'company/factory-asset/schemas/asset-type-registry.schema.json').read_text(encoding='utf-8'))

BASE = {
    'schema': 'die.factory-asset.asset-type-registry.v1',
    'revision': '1.0',
    'asset_types': [
        {
            'asset_type': 'PHOTO',
            'family': 'RASTER',
            'native_representation': 'RASTER_PIXELS',
            'producer_classes': ['RASTER_GENERATIVE'],
            'master_formats': ['PNG'],
            'delivery_formats': ['JPEG', 'WEBP', 'TIFF', 'PDF'],
            'vectorizability': {'mode': 'NOT_VECTORIZABLE', 'raster_trace_allowed': False},
            'rights': {'commercial_use_required': True, 'trademark_free_required': True, 'release_policy': 'RELEASE_IF_RECOGNIZABLE_PERSON_OR_PROPERTY'},
            'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['RASTER_DIMENSIONS', 'COLOR_SPACE']},
            'maturity': {'state': 'EXPERIMENTAL', 'evidence_required': True},
            'distinctness': {'semantic_identity_rule': 'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT', 'packaging_variants_create_new_semantic_asset': False, 'near_duplicate_action': 'QUARANTINE'}
        },
        {
            'asset_type': 'ICON',
            'family': 'VECTOR',
            'native_representation': 'VECTOR_PATHS',
            'producer_classes': ['NATIVE_VECTOR'],
            'master_formats': ['SVG'],
            'delivery_formats': ['SVG', 'EPS', 'PNG'],
            'vectorizability': {'mode': 'NATIVE_VECTOR', 'raster_trace_allowed': False},
            'rights': {'commercial_use_required': True, 'trademark_free_required': True, 'release_policy': 'NONE_EXPECTED'},
            'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['VECTOR_PATHS_PRESENT', 'NO_EMBEDDED_RASTER_ONLY', 'VIEWBOX_BOUNDS']},
            'maturity': {'state': 'CANARY', 'evidence_required': True},
            'distinctness': {'semantic_identity_rule': 'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT', 'packaging_variants_create_new_semantic_asset': False, 'near_duplicate_action': 'QUARANTINE'}
        },
        {
            'asset_type': 'ANIMATION',
            'family': 'MOTION',
            'native_representation': 'TIMED_FRAMES',
            'producer_classes': ['MOTION_RENDERER'],
            'master_formats': ['MP4'],
            'delivery_formats': ['MP4', 'MOV'],
            'vectorizability': {'mode': 'NOT_APPLICABLE', 'raster_trace_allowed': False},
            'rights': {'commercial_use_required': True, 'trademark_free_required': True, 'release_policy': 'NONE_EXPECTED'},
            'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['MOTION_DURATION', 'MOTION_CODEC', 'MOTION_FRAME_INTEGRITY']},
            'maturity': {'state': 'EXPERIMENTAL', 'evidence_required': True},
            'distinctness': {'semantic_identity_rule': 'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT', 'packaging_variants_create_new_semantic_asset': False, 'near_duplicate_action': 'QUARANTINE'}
        }
    ]
}


def validate(doc):
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)


def test_valid_registry_passes():
    validate(BASE)


def test_vector_cannot_be_embedded_raster_only():
    bad = copy.deepcopy(BASE)
    bad['asset_types'][1]['quality']['family_checks'] = ['VECTOR_PATHS_PRESENT']
    try:
        validate(bad)
    except jsonschema.ValidationError:
        return
    raise AssertionError('invalid vector quality unexpectedly passed')


def test_packaging_variant_cannot_create_semantic_asset():
    bad = copy.deepcopy(BASE)
    bad['asset_types'][0]['distinctness']['packaging_variants_create_new_semantic_asset'] = True
    try:
        validate(bad)
    except jsonschema.ValidationError:
        return
    raise AssertionError('distinctness invariant unexpectedly passed')


def test_trace_eligible_requires_guard_and_raster_family():
    bad = copy.deepcopy(BASE)
    bad['asset_types'][0]['vectorizability'] = {'mode': 'TRACE_ELIGIBLE', 'raster_trace_allowed': True, 'complexity_guard_required': False}
    try:
        validate(bad)
    except jsonschema.ValidationError:
        return
    raise AssertionError('unguarded raster trace unexpectedly passed')


def test_motion_requires_frame_integrity():
    bad = copy.deepcopy(BASE)
    bad['asset_types'][2]['quality']['family_checks'] = ['MOTION_DURATION', 'MOTION_CODEC']
    try:
        validate(bad)
    except jsonschema.ValidationError:
        return
    raise AssertionError('invalid motion quality unexpectedly passed')
