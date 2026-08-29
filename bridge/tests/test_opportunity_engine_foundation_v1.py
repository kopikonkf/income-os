from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPLEMENT = ROOT / "company" / "atlas" / "human-centric" / "CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md"
ARCH = ROOT / "docs" / "architecture" / "DIE_OPPORTUNITY_ENGINE_ARCHITECTURE_V1.md"
AUDIT = ROOT / "docs" / "architecture" / "DIE_OPPORTUNITY_ENGINE_AUDIT_V1.md"
ORCH = ROOT / "ORCHESTRATOR_CONTRACT.md"
DIV = ROOT / "company" / "division" / "division001" / "IDENTITY.md"
EXEC = ROOT / "company" / "executive" / "IDENTITY.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dual_atlas_complement_separates_demand_primitive_and_expression() -> None:
    text = _read(COMPLEMENT)
    assert "Human-Centric Atlas — demand generator" in text
    assert "Object-Centric Atlas — validated semantic primitive generator" in text
    assert "Object Primitive × Human Demand Context × Product Expression" in text
    assert "No exhaustive Cartesian explosion" in text
    assert "Demand-first" in text and "Supply-first" in text


def test_worth_making_and_blueprint_authority_is_not_hermes() -> None:
    for text in (_read(COMPLEMENT), _read(ARCH), _read(ORCH)):
        assert "Division-01" in text
        assert "Executive" in text
        assert "Hermes" in text
    complement = _read(COMPLEMENT)
    assert "primary domain cognition author" in complement.lower()
    assert "Hermes MUST NOT" in complement
    assert "Executive is the second-line strategic reviewer" in complement


def test_worker_compiler_cannot_invent_prompt_semantics() -> None:
    architecture = _read(ARCH)
    orchestrator = _read(ORCH)
    assert "Compiler MUST fail if it would need to invent missing semantic content" in architecture
    assert "Worker/OpenCode may" in architecture
    assert "must not originate" in orchestrator.lower() or "must not" in orchestrator.lower()


def test_identity_anchors_match_engine_authority_model() -> None:
    division = _read(DIV)
    executive = _read(EXEC)
    assert "semantic AUTHOR" in division
    assert "master prompt" in division
    assert "second-line strategic reviewer" in executive
    assert "MUST NOT directly edit the Division blueprint" in executive


def test_audit_does_not_claim_missing_engines_exist() -> None:
    audit = _read(AUDIT)
    assert "Opportunity Signals | ABSENT" in audit
    assert "Demand Score | PARTIAL / HEURISTIC V0" in audit
    assert "Worth-Making Gate | DOC + VALIDATOR ONLY" in audit
    assert "Blueprint Engine | ARTIFACT + VALIDATOR ONLY" in audit
    assert "Object Longtail Generator | PARTIAL / CURATED V0" in audit
    assert "A legacy Kanban `done` status MUST NOT be sufficient" in audit