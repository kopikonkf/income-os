import importlib.util
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "ai_origin_router", R / "company/factory-asset/lib/ai_origin_router.py"
)
router = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = router
spec.loader.exec_module(router)

POLICY = json.loads(
    (R / "company/factory-asset/registries/marketplace-ai-origin-policy.v1.json").read_text(
        encoding="utf-8"
    )
)

PRIMARY = ["ADOBE_STOCK", "DREAMSTIME", "VECTEEZY", "FREEPIK", "123RF", "MOTIONELEMENTS"]


def test_policy_file_is_valid_json_with_required_keys():
    assert POLICY["schema"] == "die.factory-asset.marketplace-ai-origin-policy.v1"
    assert POLICY["authority"]["automated_compatibility_pass_claimed"] is False
    assert POLICY["authority"]["submission_authorized"] is False
    ids = {p["platform_id"] for p in POLICY["policies"]}
    assert set(PRIMARY) | {"POND5", "SHUTTERSTOCK", "MAGNIFIC"} <= ids


def test_primary_routes_are_manual_only_with_jpg():
    for platform_id in PRIMARY:
        out = router.route(platform_id, ai_origin=True)
        assert out["route"] == "READY_FOR_MANUAL_SUBMISSION"
        assert out["upload"] is True
        assert out["raster_delivery"] == ["JPEG"]
        assert out["disclosure"] not in (None, "N/A")


def test_ai_excluded_platforms_block_even_after_vectorize():
    # Vectorize/PSD does not change AI-origin; router always sees ai_origin=True.
    for platform_id in ("POND5", "SHUTTERSTOCK"):
        out = router.route(platform_id, ai_origin=True)
        assert out["route"] == "BLOCKED_AI_EXCLUDED"
        assert out["upload"] is False


def test_magnific_is_not_a_marketplace():
    assert router.is_marketplace("MAGNIFIC") is False
    out = router.route("MAGNIFIC", ai_origin=True)
    assert out["route"] == "NOT_A_MARKETPLACE"
    assert out["upload"] is False
    assert router.is_marketplace("ADOBE_STOCK") is True


def test_unknown_platform_fails_closed():
    out = router.route("SOME_NEW_SITE", ai_origin=True)
    assert out["route"] == "UNKNOWN_PLATFORM"
    assert out["upload"] is False


def test_router_never_claims_compat_pass():
    raw = json.dumps(
        [router.route(p, ai_origin=True) for p in PRIMARY + ["POND5", "SHUTTERSTOCK"]]
    )
    assert "COMPATIBLE" not in raw
    assert "COMPATIBILITY_PASS" not in raw


def test_motionelements_requires_separate_ai_account():
    out = router.route("MOTIONELEMENTS", ai_origin=True)
    assert out["account_requirement"] == "SEPARATE_AI_CONTRIBUTOR_ACCOUNT"
