import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'company/factory-asset/fixtures/shopping-bag-blueprint-v2'

def load_module(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

compiler = load_module('factory_asset_blueprint_compiler_fa015', 'company/factory-asset/lib/blueprint_compiler.py')
identity = load_module('factory_asset_identity_fa015', 'company/factory-asset/lib/asset_identity.py')

EXPECTED = {
    'photo.json': ('PHOTO', 'RASTER_GENERATIVE', 'raster-generative-master-v1', ['raster-jpeg-stock-v1', 'raster-webp-preview-v1']),
    'isolated-object.json': ('ISOLATED_OBJECT', 'RASTER_GENERATIVE', 'raster-generative-master-v1', ['raster-jpeg-stock-v1', 'raster-png-export-v1']),
    'icon.json': ('ICON', 'NATIVE_VECTOR', 'native-vector-master-v1', ['vector-eps-export-v1', 'vector-png-preview-v1']),
    'outline.json': ('OUTLINE', 'NATIVE_VECTOR', 'native-vector-master-v1', ['vector-svg-native-v1', 'vector-png-preview-v1']),
    'pattern.json': ('PATTERN', 'PROCEDURAL_VECTOR', 'procedural-vector-master-v1', ['vector-eps-export-v1', 'vector-jpeg-preview-v1']),
    'animation.json': ('ANIMATION', 'MOTION_RENDERER', 'motion-render-master-v1', ['motion-mp4-export-v1', 'motion-jpeg-still-preview-v1']),
}


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def test_manifest_declares_six_semantic_assets_and_twelve_packaging_derivatives():
    manifest = load('manifest.json')
    assert manifest['semantic_asset_count'] == 6
    assert manifest['packaging_derivatives_count'] == 12
    assert set(manifest['fixtures']) == set(EXPECTED)


def test_all_six_positive_fixtures_compile_to_intended_producers_and_recipes():
    for filename, (asset_type, producer, master_recipe, derivative_recipes) in EXPECTED.items():
        blueprint = load(filename)
        plan = compiler.compile_blueprint(blueprint)
        assert plan['asset_type'] == asset_type
        assert plan['producer']['class'] == producer
        assert plan['producer']['recipe_id'] == master_recipe
        assert [row['recipe_id'] for row in plan['derivatives']] == derivative_recipes
        assert all(row['semantic_identity_effect'] == 'NONE' for row in plan['derivatives'])
        assert plan['policy_gate']['submission_blocked'] is False
        assert plan['asset_type_registry_revision'] == '1.0'
        assert plan['marketplace_delivery_profile_revision'] == '1.0'


def test_six_modes_are_six_distinct_semantic_assets():
    blueprints = [load(name) for name in EXPECTED]
    ids = [bp['semantic_identity']['semantic_asset_id'] for bp in blueprints]
    fingerprints = [identity.semantic_fingerprint(bp) for bp in blueprints]
    assert len(set(ids)) == 6
    assert len(set(fingerprints)) == 6


def test_each_fixture_derivatives_keep_same_semantic_asset_id_in_compiled_plan():
    for filename in EXPECTED:
        bp = load(filename)
        plan = compiler.compile_blueprint(bp)
        semantic_id = bp['semantic_identity']['semantic_asset_id']
        assert all(row['semantic_asset_id'] == semantic_id for row in plan['derivatives'])


def test_compilation_is_deterministic_for_every_fixture():
    for filename in EXPECTED:
        bp = load(filename)
        assert compiler.compile_blueprint(bp) == compiler.compile_blueprint(bp)