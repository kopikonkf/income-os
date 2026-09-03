import copy
import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / 'company/factory-asset/lib/blueprint_compiler.py'
spec = importlib.util.spec_from_file_location('factory_asset_blueprint_compiler', MODULE_PATH)
compiler = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = compiler
spec.loader.exec_module(compiler)

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


def test_concrete_asset_registry_validates_against_fa010_schema():
    registry = json.loads((ROOT / 'company/factory-asset/registries/asset-types.v1.json').read_text(encoding='utf-8'))
    schema = json.loads((ROOT / 'company/factory-asset/schemas/asset-type-registry.schema.json').read_text(encoding='utf-8-sig'))
    jsonschema.Draft202012Validator(schema).validate(registry)
    assert [x['asset_type'] for x in registry['asset_types']] == ['PHOTO', 'ISOLATED_OBJECT', 'ICON', 'OUTLINE', 'PATTERN', 'ANIMATION']


def test_photo_compiles_deterministically_to_raster_master_and_jpeg_recipe():
    one = compiler.compile_blueprint(copy.deepcopy(BASE))
    two = compiler.compile_blueprint(copy.deepcopy(BASE))
    assert one == two
    assert one['producer'] == {'class': 'RASTER_GENERATIVE', 'recipe_id': 'raster-generative-master-v1', 'maturity': 'PRODUCTION_READY'}
    assert one['master']['format'] == 'PNG'
    assert one['derivatives'][0]['recipe_id'] == 'raster-jpeg-stock-v1'
    assert one['derivatives'][0]['semantic_asset_id'] == 'FASA-SHOPPING_BAG_PHOTO'
    assert one['derivatives'][0]['semantic_identity_effect'] == 'NONE'
    assert one['policy_gate']['submission_blocked'] is False


def test_unknown_asset_type_rejected_before_dispatch():
    bp = copy.deepcopy(BASE)
    bp['asset_type'] = 'MAGIC_THING'
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code == 'ASSET_TYPE_UNKNOWN'


def test_asset_registry_producer_mismatch_rejected():
    bp = copy.deepcopy(BASE)
    bp['producer_class'] = 'NATIVE_VECTOR'
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code in {'BLUEPRINT_SCHEMA_INVALID', 'PRODUCER_CLASS_MISMATCH'}


def test_raster_to_vector_derivative_rejected_before_dispatch():
    bp = copy.deepcopy(BASE)
    bp['derivatives'] = [{'derivative_id': 'FAKE_SVG', 'purpose': 'COMPATIBILITY_EXPORT', 'format': 'SVG', 'semantic_identity_effect': 'NONE'}]
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code in {'DELIVERY_FORMAT_NOT_ALLOWED', 'RASTER_TO_VECTOR_FORBIDDEN'}


def test_isolated_object_requires_alpha_quality_contract():
    bp = copy.deepcopy(BASE)
    bp['asset_type'] = 'ISOLATED_OBJECT'
    bp['blueprint_id'] = 'FABP-SHOPPING_BAG_ISOLATED'
    bp['semantic_identity']['semantic_asset_id'] = 'FASA-SHOPPING_BAG_ISOLATED'
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code == 'QUALITY_CONTRACT_INCOMPLETE'
    assert 'ALPHA_POLICY' in str(exc.value)


def test_pattern_compiles_to_procedural_vector_with_native_eps_export():
    bp = copy.deepcopy(BASE)
    bp.update({
        'blueprint_id': 'FABP-SHOPPING_BAG_PATTERN',
        'asset_type': 'PATTERN',
        'native_representation': 'VECTOR_PATHS',
        'producer_class': 'PROCEDURAL_VECTOR',
        'master_spec': {'format': 'SVG', 'color_space': 'SRGB', 'lineage_sha256_required': True},
        'derivatives': [
            {'derivative_id': 'ADOBE_EPS', 'purpose': 'MARKETPLACE_DELIVERY', 'format': 'EPS', 'semantic_identity_effect': 'NONE'},
            {'derivative_id': 'PREVIEW_PNG', 'purpose': 'PREVIEW', 'format': 'PNG', 'semantic_identity_effect': 'NONE'},
        ],
        'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['VECTOR_PATHS_PRESENT', 'NO_EMBEDDED_RASTER_ONLY', 'VIEWBOX_BOUNDS', 'PATH_COMPLEXITY']},
    })
    bp['semantic_identity'].update({
        'semantic_asset_id': 'FASA-SHOPPING_BAG_PATTERN',
        'commercial_use_case': 'repeating shopping bag pattern for packaging backgrounds',
        'intent': 'DECORATIVE_BACKGROUND',
    })
    plan = compiler.compile_blueprint(bp)
    assert plan['producer']['class'] == 'PROCEDURAL_VECTOR'
    assert plan['producer']['recipe_id'] == 'procedural-vector-master-v1'
    assert [x['recipe_id'] for x in plan['derivatives']] == ['vector-eps-export-v1', 'vector-png-preview-v1']


def test_motion_compiles_mp4_delivery_and_still_preview_only():
    bp = copy.deepcopy(BASE)
    bp.update({
        'blueprint_id': 'FABP-SHOPPING_BAG_ANIMATION',
        'asset_type': 'ANIMATION',
        'native_representation': 'TIMED_FRAMES',
        'producer_class': 'MOTION_RENDERER',
        'master_spec': {'format': 'MP4', 'duration_seconds': 6, 'fps': 30, 'color_space': 'SRGB', 'lineage_sha256_required': True},
        'derivatives': [
            {'derivative_id': 'ADOBE_MP4', 'purpose': 'MARKETPLACE_DELIVERY', 'format': 'MP4', 'semantic_identity_effect': 'NONE'},
            {'derivative_id': 'PREVIEW_JPEG', 'purpose': 'PREVIEW', 'format': 'JPEG', 'semantic_identity_effect': 'NONE'},
        ],
        'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['MOTION_DURATION', 'MOTION_CODEC', 'MOTION_FRAME_INTEGRITY']},
    })
    bp['semantic_identity'].update({
        'semantic_asset_id': 'FASA-SHOPPING_BAG_ANIMATION',
        'commercial_use_case': 'short animated shopping bag motion graphic',
        'intent': 'MOTION_ASSET',
    })
    plan = compiler.compile_blueprint(bp)
    assert [x['recipe_id'] for x in plan['derivatives']] == ['motion-mp4-export-v1', 'motion-jpeg-still-preview-v1']


def test_motion_still_cannot_claim_marketplace_delivery():
    bp = copy.deepcopy(BASE)
    bp.update({
        'blueprint_id': 'FABP-SHOPPING_BAG_ANIMATION',
        'asset_type': 'ANIMATION',
        'native_representation': 'TIMED_FRAMES',
        'producer_class': 'MOTION_RENDERER',
        'master_spec': {'format': 'MP4', 'duration_seconds': 6, 'fps': 30, 'color_space': 'SRGB', 'lineage_sha256_required': True},
        'derivatives': [{'derivative_id': 'BAD_JPEG', 'purpose': 'MARKETPLACE_DELIVERY', 'format': 'JPEG', 'semantic_identity_effect': 'NONE'}],
        'quality': {'magic_mime_match': True, 'decode_reopen': True, 'lineage_sha256': True, 'family_checks': ['MOTION_DURATION', 'MOTION_CODEC', 'MOTION_FRAME_INTEGRITY']},
    })
    bp['semantic_identity'].update({'semantic_asset_id': 'FASA-SHOPPING_BAG_ANIMATION', 'commercial_use_case': 'short animated shopping bag motion graphic', 'intent': 'MOTION_ASSET'})
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code == 'MOTION_STILL_DELIVERY_FORBIDDEN'


def test_unknown_marketplace_evidence_cannot_be_claimed_compatible():
    bp = copy.deepcopy(BASE)
    bp['policy']['marketplace_profiles'] = ['DREAMSTIME']
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code == 'COMPATIBILITY_CLAIM_EXCEEDS_EVIDENCE'


def test_unknown_marketplace_evidence_compiles_but_blocks_submission():
    bp = copy.deepcopy(BASE)
    bp['policy']['marketplace_profiles'] = ['DREAMSTIME']
    bp['policy']['compatibility_state'] = 'COMPATIBILITY_UNKNOWN'
    plan = compiler.compile_blueprint(bp)
    assert plan['policy_gate']['submission_blocked'] is True


def test_pinned_marketplace_rejects_unsupported_delivery_format():
    bp = copy.deepcopy(BASE)
    bp['derivatives'] = [{'derivative_id': 'ADOBE_TIFF', 'purpose': 'MARKETPLACE_DELIVERY', 'format': 'TIFF', 'semantic_identity_effect': 'NONE'}]
    with pytest.raises(compiler.BlueprintCompileError) as exc:
        compiler.compile_blueprint(bp)
    assert exc.value.code == 'MARKETPLACE_FORMAT_UNSUPPORTED'

def test_cli_compiles_blueprint_file(tmp_path):
    import subprocess
    source = tmp_path / "blueprint.json"
    output = tmp_path / "plan.json"
    source.write_text(json.dumps(BASE), encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(ROOT / "company/factory-asset/bin/compile_asset_blueprint.py"), str(source), "--output", str(output)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert cp.returncode == 0, cp.stderr
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert plan["schema"] == "die.factory-asset.production-plan.v1"
    assert plan["producer"]["recipe_id"] == "raster-generative-master-v1"
