import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / 'company/factory-asset/fixtures/shopping-bag-blueprint-v2'
NEGATIVE = FIXTURES / 'negative'

def load_module(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

compiler = load_module('factory_asset_blueprint_compiler_fa019', 'company/factory-asset/lib/blueprint_compiler.py')
identity = load_module('factory_asset_identity_fa019', 'company/factory-asset/lib/asset_identity.py')


def test_fa019_positive_fixture_set_compiles_green_and_pins_versions():
    manifest = json.loads((FIXTURES / 'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['fixtures']) == 6
    plans = []
    for filename in manifest['fixtures']:
        bp = json.loads((FIXTURES / filename).read_text(encoding='utf-8'))
        plan = compiler.compile_blueprint(bp)
        plans.append(plan)
        assert plan['asset_type_registry_revision'] == '1.0'
        assert plan['marketplace_delivery_profile_revision'] == '1.0'
        assert plan['policy_gate']['submission_blocked'] is False
    assert len({plan['semantic_asset_id'] for plan in plans}) == 6


def test_fa019_negative_cross_family_fixture_set_fails_with_typed_errors():
    manifest = json.loads((NEGATIVE / 'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['fixtures']) == 6
    observed = {}
    for row in manifest['fixtures']:
        bp = json.loads((NEGATIVE / row['file']).read_text(encoding='utf-8'))
        with pytest.raises(compiler.BlueprintCompileError) as exc:
            compiler.compile_blueprint(bp)
        observed[row['file']] = exc.value.code
        assert exc.value.code == row['expected_error']
    assert set(observed.values()) == {
        'NATIVE_REPRESENTATION_MISMATCH',
        'DELIVERY_FORMAT_NOT_ALLOWED',
        'MOTION_STILL_DELIVERY_FORBIDDEN',
    }


def test_fa019_positive_semantic_fingerprints_are_unique():
    manifest = json.loads((FIXTURES / 'manifest.json').read_text(encoding='utf-8'))
    fingerprints = []
    for filename in manifest['fixtures']:
        bp = json.loads((FIXTURES / filename).read_text(encoding='utf-8'))
        fingerprints.append(identity.semantic_fingerprint(bp))
    assert len(set(fingerprints)) == 6


def test_fa019_no_positive_packaging_derivative_mints_identity():
    manifest = json.loads((FIXTURES / 'manifest.json').read_text(encoding='utf-8'))
    for filename in manifest['fixtures']:
        bp = json.loads((FIXTURES / filename).read_text(encoding='utf-8'))
        plan = compiler.compile_blueprint(bp)
        assert all(row['semantic_asset_id'] == plan['semantic_asset_id'] for row in plan['derivatives'])
        assert all(row['semantic_identity_effect'] == 'NONE' for row in plan['derivatives'])


def test_fa019_registry_and_delivery_profile_catalogs_are_exactly_pinned():
    catalog = compiler.CompilerCatalog.load_default()
    assert catalog.asset_registry['revision'] == '1.0'
    assert catalog.delivery_profiles['revision'] == '1.0'
    assert set(catalog.asset_types) >= {'PHOTO','ISOLATED_OBJECT','ICON','OUTLINE','PATTERN','ANIMATION'}
    assert catalog.profiles['ADOBE_STOCK']['profile_state'] == 'EVIDENCE_PINNED'