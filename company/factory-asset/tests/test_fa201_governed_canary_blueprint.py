from pathlib import Path
import hashlib
import importlib.util
import json
import sys

R = Path(__file__).resolve().parents[3]
ROOT = R / 'company/factory-asset/fixtures/governed-canary'
PLAN = ROOT / 'FA-200-shopping-bag-expression-plan.json'
SELECTION = ROOT / 'FA-200-shopping-bag-selection.json'
BLUEPRINT = ROOT / 'FA-201-shopping-bag-blueprint-v2.json'
PRODUCTION = ROOT / 'FA-201-shopping-bag-production-plan.json'
LOCK = ROOT / 'FA-201-shopping-bag-blueprint-lock.json'
COMPILER = R / 'company/factory-asset/lib/blueprint_compiler.py'


def load_compiler():
    spec = importlib.util.spec_from_file_location('compiler', COMPILER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_blueprint_validates_and_compiles_deterministically():
    mod = load_compiler()
    bp = json.loads(BLUEPRINT.read_text())
    expected = json.loads(PRODUCTION.read_text())
    mod.validate_blueprint(bp)
    actual = mod.compile_blueprint(bp)
    assert actual == expected
    assert actual['blueprint_sha256'] == 'd66654c5031f5c36aebfeb348124f9fedd17685c9362fdf6b8dbd39cd0a2e31c'
    assert actual['producer'] == {'class': 'RASTER_GENERATIVE', 'recipe_id': 'raster-generative-master-v1', 'maturity': 'PRODUCTION_READY'}


def test_frozen_semantic_identity_matches_fa200_selection_exactly():
    plan = json.loads(PLAN.read_text())
    sel = json.loads(SELECTION.read_text())
    bp = json.loads(BLUEPRINT.read_text())
    lock = json.loads(LOCK.read_text())
    expr = plan['expressions'][0]
    assert expr['semantic_asset_id'] == sel['opportunity']['semantic_asset_id'] == bp['semantic_identity']['semantic_asset_id'] == lock['semantic_lock']['semantic_asset_id']
    assert expr['product_expression'] == sel['expression']['product_expression'] == lock['semantic_lock']['product_expression']
    assert expr['commercial_use_case'] == bp['semantic_identity']['commercial_use_case'] == lock['semantic_lock']['commercial_use_case']
    assert expr['semantic_mode'] == lock['semantic_lock']['semantic_mode'] == 'ISOLATED_OBJECT'
    assert bp['asset_type'] == 'ISOLATED_OBJECT'


def test_master_and_delivery_plan_pin_quality_and_versions():
    prod = json.loads(PRODUCTION.read_text())
    lock = json.loads(LOCK.read_text())
    assert prod['master'] == {'format': 'PNG', 'width_px': 4096, 'height_px': 4096, 'color_space': 'SRGB', 'lineage_sha256_required': True}
    assert lock['master_spec']['pixel_count'] == 4096 * 4096
    assert lock['master_spec']['pixel_count'] >= 4_000_000
    assert prod['asset_type_registry_revision'] == lock['versions']['asset_type_registry_revision'] == '1.0'
    assert prod['marketplace_delivery_profile_revision'] == lock['versions']['marketplace_delivery_profile_revision'] == '1.0'
    by = {d['derivative_id']: d for d in prod['derivatives']}
    assert by['ADOBE_JPEG']['recipe_id'] == 'raster-jpeg-stock-v1'
    assert by['ADOBE_JPEG']['marketplace_profiles'] == ['ADOBE_STOCK']
    assert all(d['semantic_identity_effect'] == 'NONE' for d in prod['derivatives'])


def test_distinctness_and_cognition_are_fail_closed_without_extra_calls():
    lock = json.loads(LOCK.read_text())
    d = lock['distinctness']
    assert d['identity_rule'] == 'DISTINCT_COMMERCIAL_USE_CASE_AND_BLUEPRINT'
    assert d['packaging_variants_create_new_semantic_asset'] is False
    assert d['near_duplicate_action'] == 'QUARANTINE'
    c = lock['cognition_routing']
    assert c['decision'] == 'NOT_REQUIRED_DETERMINISTIC_COMPILE_OF_FROZEN_FA200_SELECTION'
    assert c['division01_called'] is False
    assert c['executive_called'] is False
    assert sha(R / c['policy_evidence_ref']) == c['policy_evidence_sha256']


def test_technical_compatibility_never_becomes_submission_authority():
    prod = json.loads(PRODUCTION.read_text())
    lock = json.loads(LOCK.read_text())
    assert prod['policy_gate']['compatibility_state'] == 'COMPATIBLE'
    assert prod['policy_gate']['submission_blocked'] is False
    assert prod['policy_gate']['submission_authority'] == 'FOUNDER_CONTROLLED'
    g = lock['governance']
    assert g['rights_runtime_state'] == 'REVIEW_REQUIRED'
    assert g['founder_qc_complete'] is False
    assert g['effective_submission_blocked'] is True
    assert g['marketplace_acceptance'] is False
    assert g['publication_authority'] is False
    assert g['provider_call_authorized_by_this_task'] is False


def test_all_lock_hashes_match_current_canon_inputs():
    lock = json.loads(LOCK.read_text())
    assert sha(PLAN) == lock['inputs']['fa200_expression_plan_sha256']
    assert sha(SELECTION) == lock['inputs']['fa200_selection_sha256']
    assert sha(BLUEPRINT) == lock['blueprint']['file_sha256']
    assert sha(PRODUCTION) == lock['production_plan_file_sha256']
    assert sha(R / 'company/factory-asset/registries/asset-types.v1.json') == lock['versions']['asset_type_registry_sha256']
    assert sha(R / 'company/factory-asset/registries/marketplace-delivery-profiles.v1.json') == lock['versions']['marketplace_delivery_profile_sha256']