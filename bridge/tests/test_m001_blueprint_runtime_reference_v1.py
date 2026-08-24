from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_PATH = ROOT / "docs" / "missions" / "M001_BLUEPRINT_BATCH1_V2.md"
COMPANY_BRAIN_PATH = ROOT / "COMPANY_BRAIN.md"


def test_m001_blueprint_is_founder_ratified_and_uses_canonical_north_star():
    blueprint = BLUEPRINT_PATH.read_text(encoding="utf-8")

    assert "FOUNDER-RATIFIED v2" in blueprint
    assert "net profit and annualized run-rate" in blueprint
    assert "DRAFT v2 — pending Founder review" not in blueprint
    assert "economic metric to be separately defined" not in blueprint


def test_hermes_boot_sequence_requires_the_m001_blueprint():
    company_brain = COMPANY_BRAIN_PATH.read_text(encoding="utf-8")

    assert "for Hermes, before any M-001 planning, delegation, or reporting" in company_brain
    assert "docs/missions/M001_BLUEPRINT_BATCH1_V2.md" in company_brain


def test_blueprint_ratification_does_not_authorize_execution():
    blueprint = BLUEPRINT_PATH.read_text(encoding="utf-8")
    company_brain = COMPANY_BRAIN_PATH.read_text(encoding="utf-8")

    boundary = "No production, upload, publication, account action, or spend is authorized"
    assert boundary in blueprint
    assert "not execution authority" in company_brain


def test_intelligence_director_is_a_division01_function_not_a_new_identity():
    blueprint = BLUEPRINT_PATH.read_text(encoding="utf-8")

    assert "`division-head-division01`" in blueprint
    assert "not a new\nregistered identity, transport lane, or control plane" in blueprint
