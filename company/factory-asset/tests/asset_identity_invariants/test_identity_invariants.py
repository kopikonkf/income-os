import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / 'company/factory-asset/lib/asset_identity.py'
spec = importlib.util.spec_from_file_location('factory_asset_identity', MODULE_PATH)
identity = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = identity
spec.loader.exec_module(identity)

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


def test_identical_blueprint_is_identical_transition():
    receipt = identity.assert_identity_invariants(BASE, copy.deepcopy(BASE))
    assert receipt['transition'] == 'IDENTICAL'
    assert receipt['before']['semantic_fingerprint'] == receipt['after']['semantic_fingerprint']


def test_format_and_resolution_changes_are_packaging_only():
    after = copy.deepcopy(BASE)
    after['master_spec']['format'] = 'TIFF'
    after['master_spec']['width_px'] = 8192
    after['master_spec']['height_px'] = 8192
    receipt = identity.assert_identity_invariants(BASE, after)
    assert receipt['transition'] == 'PACKAGING_VARIANT'
    assert receipt['before']['semantic_asset_id'] == receipt['after']['semantic_asset_id']
    assert receipt['before']['semantic_fingerprint'] == receipt['after']['semantic_fingerprint']
    assert receipt['before']['packaging_fingerprint'] != receipt['after']['packaging_fingerprint']


def test_preview_and_delivery_format_changes_are_packaging_only():
    after = copy.deepcopy(BASE)
    after['derivatives'] = [
        {'derivative_id': 'WEB_PREVIEW', 'purpose': 'PREVIEW', 'format': 'WEBP', 'semantic_identity_effect': 'NONE'},
        {'derivative_id': 'TIFF_COMPAT', 'purpose': 'COMPATIBILITY_EXPORT', 'format': 'TIFF', 'semantic_identity_effect': 'NONE'},
    ]
    assert identity.classify_identity_transition(BASE, after) == 'PACKAGING_VARIANT'
    identity.assert_identity_invariants(BASE, after)


def test_marketplace_route_change_is_packaging_not_semantic():
    after = copy.deepcopy(BASE)
    after['policy']['marketplace_profiles'] = ['DREAMSTIME']
    after['policy']['compatibility_state'] = 'COMPATIBILITY_UNKNOWN'
    receipt = identity.assert_identity_invariants(BASE, after)
    assert receipt['transition'] == 'PACKAGING_VARIANT'
    assert after['semantic_identity']['semantic_asset_id'] == BASE['semantic_identity']['semantic_asset_id']


def test_packaging_only_change_cannot_mint_new_semantic_id():
    after = copy.deepcopy(BASE)
    after['master_spec']['width_px'] = 8192
    after['semantic_identity']['semantic_asset_id'] = 'FASA-SHOPPING_BAG_PHOTO_8K'
    with pytest.raises(identity.AssetIdentityInvariantError) as exc:
        identity.assert_identity_invariants(BASE, after)
    assert exc.value.code == 'PACKAGING_MINTED_SEMANTIC_ID'


def test_commercial_use_case_change_requires_new_semantic_id():
    after = copy.deepcopy(BASE)
    after['semantic_identity']['commercial_use_case'] = 'shopping bag outline component for interface iconography'
    with pytest.raises(identity.AssetIdentityInvariantError) as exc:
        identity.assert_identity_invariants(BASE, after)
    assert exc.value.code == 'SEMANTIC_ID_REUSED_FOR_DISTINCT_WORK'


def test_commercial_use_case_change_requires_new_blueprint_too():
    after = copy.deepcopy(BASE)
    after['semantic_identity']['commercial_use_case'] = 'shopping bag outline component for interface iconography'
    after['semantic_identity']['semantic_asset_id'] = 'FASA-SHOPPING_BAG_OUTLINE'
    with pytest.raises(identity.AssetIdentityInvariantError) as exc:
        identity.assert_identity_invariants(BASE, after)
    assert exc.value.code == 'DISTINCT_USE_CASE_REQUIRES_SEPARATE_BLUEPRINT'


def test_distinct_use_case_with_new_semantic_and_blueprint_ids_is_valid():
    after = copy.deepcopy(BASE)
    after['blueprint_id'] = 'FABP-SHOPPING_BAG_OUTLINE'
    after['semantic_identity'].update({
        'semantic_asset_id': 'FASA-SHOPPING_BAG_OUTLINE',
        'commercial_use_case': 'shopping bag outline component for interface iconography',
        'intent': 'DESIGN_COMPONENT',
    })
    after['asset_type'] = 'OUTLINE'
    receipt = identity.assert_identity_invariants(BASE, after)
    assert receipt['transition'] == 'SEMANTIC_VARIANT'
    assert receipt['before']['semantic_fingerprint'] != receipt['after']['semantic_fingerprint']


def test_asset_type_change_reusing_semantic_id_is_forbidden():
    after = copy.deepcopy(BASE)
    after['asset_type'] = 'PATTERN'
    with pytest.raises(identity.AssetIdentityInvariantError) as exc:
        identity.assert_identity_invariants(BASE, after)
    assert exc.value.code == 'SEMANTIC_ID_REUSED_FOR_DISTINCT_WORK'


def test_subject_whitespace_and_case_normalization_does_not_mint_semantics():
    after = copy.deepcopy(BASE)
    after['semantic_identity']['subject'] = '  Shopping   Bag  '
    after['semantic_identity']['commercial_use_case'] = 'GENERIC reusable RETAIL shopping-bag stock image'
    assert identity.semantic_fingerprint(BASE) == identity.semantic_fingerprint(after)
    assert identity.classify_identity_transition(BASE, after) == 'IDENTICAL'


def test_derivative_order_does_not_change_packaging_fingerprint():
    one = copy.deepcopy(BASE)
    one['derivatives'] = [
        {'derivative_id': 'A', 'purpose': 'PREVIEW', 'format': 'WEBP', 'semantic_identity_effect': 'NONE'},
        {'derivative_id': 'B', 'purpose': 'COMPATIBILITY_EXPORT', 'format': 'TIFF', 'semantic_identity_effect': 'NONE'},
    ]
    two = copy.deepcopy(one)
    two['derivatives'].reverse()
    assert identity.packaging_fingerprint(one) == identity.packaging_fingerprint(two)


def test_derivative_cannot_claim_semantic_identity_effect():
    after = copy.deepcopy(BASE)
    after['derivatives'][0]['semantic_identity_effect'] = 'NEW_ASSET'
    with pytest.raises(identity.AssetIdentityInvariantError) as exc:
        identity.assert_identity_invariants(BASE, after)
    assert exc.value.code == 'DERIVATIVE_CHANGED_SEMANTIC_IDENTITY'


def test_blueprint_id_may_change_for_packaging_revision_without_new_semantic_asset():
    after = copy.deepcopy(BASE)
    after['blueprint_id'] = 'FABP-SHOPPING_BAG_PHOTO_V2'
    after['master_spec']['width_px'] = 8192
    receipt = identity.assert_identity_invariants(BASE, after)
    assert receipt['transition'] == 'PACKAGING_VARIANT'
    assert receipt['before']['semantic_asset_id'] == receipt['after']['semantic_asset_id']