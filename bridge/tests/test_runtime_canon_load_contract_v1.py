from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPANY_BRAIN = ROOT / "COMPANY_BRAIN.md"
EXECUTIVE = ROOT / "company" / "executive" / "IDENTITY.md"
DIVISION01 = ROOT / "company" / "division" / "division001" / "IDENTITY.md"

PIPELINE = "docs/pipeline/DIGITAL_INCOME_PIPELINE_CANON.md"
ATLAS = "company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md"
COMPLEMENT = "company/atlas/human-centric/CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md"
BLUEPRINT = "docs/missions/M001_BLUEPRINT_BATCH1_V2.md"
MATRIX = "docs/pipeline/MATRIX_6_PLATFORM_TOS_STRICTNESS.md"
WORKBOOK = "docs/atlas/SCENARIO_1B_QUANTITY_GAME.xlsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_company_brain_routes_blueprint_to_both_runtime_cognitive_principals():
    brain = _read(COMPANY_BRAIN)

    assert "for Division-01 cognition, before any M-001 research, scoring" in brain
    assert "for Executive cognition, before any M-001 assessment, challenge" in brain
    assert BLUEPRINT in brain


def test_executive_has_conditional_m001_canon_contract_without_new_authority():
    executive = _read(EXECUTIVE)

    for path in (PIPELINE, ATLAS, COMPLEMENT, BLUEPRINT, MATRIX, WORKBOOK):
        assert path in executive
    assert "gross-revenue hypothesis model" in executive
    assert "grants no repository, filesystem, shell, new MCP" in executive


def test_division01_loads_full_m001_canon_before_worth_making():
    division = _read(DIVISION01)

    for path in (PIPELINE, ATLAS, COMPLEMENT, BLUEPRINT, MATRIX, WORKBOOK):
        assert path in division
    assert "before any\nresearch, scoring, Worth-Making Gate" in division
    assert "not observed ERVA or net-profit evidence" in division
    assert "grants no raw repository/filesystem access, new MCP tools" in division


def test_each_principal_requires_independent_fresh_context_receipt():
    for anchor, principal in (
        (_read(EXECUTIVE), "Executive"),
        (_read(DIVISION01), "Division-01"),
    ):
        assert "fresh-context assimilation" in anchor, principal
        assert "receipt" in anchor, principal
        assert "repository SHA" in anchor, principal
        assert "snapshot ID/as-of" in anchor, principal
        assert "probe results" in anchor, principal
        assert "A live wake or port" in anchor, principal
