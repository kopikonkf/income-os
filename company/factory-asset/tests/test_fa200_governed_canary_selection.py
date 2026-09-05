from pathlib import Path
import hashlib
import importlib.util
import json

R = Path(__file__).resolve().parents[3]
PLAN = R / 'company/factory-asset/fixtures/governed-canary/FA-200-shopping-bag-expression-plan.json'
SEL = R / 'company/factory-asset/fixtures/governed-canary/FA-200-shopping-bag-selection.json'
VALIDATOR = R / 'company/factory-asset/lib/asset_expression_plan.py'


def load_validator():
    spec = importlib.util.spec_from_file_location('faep', VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_expression_plan_validates_and_selects_one_static_isolated_raster():
    plan = json.loads(PLAN.read_text())
    load_validator().validate_asset_expression_plan(plan)
    assert plan['decision'] == 'SELECT'
    assert len(plan['expressions']) == 1
    x = plan['expressions'][0]
    assert x['semantic_mode'] == 'ISOLATED_OBJECT'
    assert x['producer_class'] == 'RASTER_GENERATIVE'
    assert x['candidate_marketplace_route'] == {
        'platform_id': 'ADOBE_STOCK',
        'listing_use': 'Unbranded shopping bag isolated object for customer-order fulfillment',
        'state': 'CANDIDATE_REQUIRES_POLICY_CHECK',
    }
    assert plan['policy']['force_all_modes'] is False


def test_all_plan_evidence_hashes_resolve_to_canonical_files():
    plan = json.loads(PLAN.read_text())
    for e in plan['evidence']:
        ref = e['source_ref'].split('#', 1)[0]
        p = R / ref
        assert p.exists(), ref
        assert sha(p) == e['source_sha256']
    assert {e['kind'] for e in plan['evidence']} == {'OBJECT_ATLAS_SEED', 'APPROVED_RESEARCH'}


def test_selection_pins_family_motion_rights_quality_and_no_publication():
    s = json.loads(SEL.read_text())
    assert s['opportunity']['family'] == 'CUSTOMER_ORDER_FULFILLMENT'
    assert s['expression']['semantic_mode'] == 'ISOLATED_OBJECT'
    assert s['expression']['producer_class'] == 'RASTER_GENERATIVE'
    assert s['temporal_motion']['eligibility'] == 'STATIC_ONLY'
    assert s['temporal_motion']['motion_production_authorized'] is False
    assert s['rights_posture']['state'] == 'REVIEW_REQUIRED'
    assert s['rights_posture']['human_rights_clearance'] is False
    assert s['rights_posture']['founder_qc_required'] is True
    assert s['quality_target']['candidate_delivery_format'] == 'JPEG'
    assert s['quality_target']['final_raster_color_space'] == 'sRGB'
    assert s['quality_target']['minimum_final_pixel_count'] == 4_000_000
    assert s['quality_target']['provider_original_immutable'] is True
    assert s['authority']['provider_call'] is False
    assert s['authority']['production_dispatch'] is False
    assert s['authority']['marketplace_upload'] is False
    assert s['authority']['publication'] is False
    assert s['authority']['spend_usd'] == 0


def test_marketplace_and_rights_policy_hashes_are_pinned_and_limits_are_honest():
    s = json.loads(SEL.read_text())
    mr = s['marketplace_route']
    rp = s['rights_posture']
    assert sha(R / mr['delivery_evidence_ref']) == mr['delivery_evidence_sha256']
    assert sha(R / rp['policy_ref']) == rp['policy_sha256']
    limits = s['evidence_limits']
    assert limits['buyer_demand'] == 'OBSERVED_CATEGORY_LEVEL'
    assert limits['exact_candidate_transaction'] == 'UNOBSERVED'
    assert limits['competition_gap'] == 'NOT_PROVEN'
    assert limits['selection_claim'] == 'GOVERNED_CANARY_NOT_MARKET_WINNER'


def test_selected_semantic_identity_matches_plan():
    plan = json.loads(PLAN.read_text())
    s = json.loads(SEL.read_text())
    assert s['opportunity']['semantic_asset_id'] == plan['expressions'][0]['semantic_asset_id']
    assert s['expression']['product_expression'] == plan['expressions'][0]['product_expression']