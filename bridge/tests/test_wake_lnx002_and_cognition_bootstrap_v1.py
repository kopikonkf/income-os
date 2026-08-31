from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAKE = ROOT / "company" / "browser" / "linux" / "wake_convergence.py"
EXEC = ROOT / "company" / "executive" / "linux" / "COGNITION_BOOTSTRAP_V1.md"
DIV = ROOT / "company" / "division" / "division001" / "linux" / "COGNITION_BOOTSTRAP_V1.md"
SOCIETY = ROOT / "company" / "die-agents" / "hermes" / "linux" / "PRINCIPAL_SOCIETY_AUTHORITY_V1.md"


def _load():
    spec = importlib.util.spec_from_file_location("wake_convergence", WAKE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wake_convergence_envelopes_require_fresh_context_before_reasoning() -> None:
    module = _load()
    sha = "a" * 40
    for role, principal, scope in [
        ("executive", "die-lnx-executive-001", "company_portfolio"),
        ("division01", "die-lnx-division-001", "single_division"),
    ]:
        env = module.build_envelope(role, sha)
        assert env["company_instance_id"] == "DIE-LINUX"
        assert env["principal_id"] == principal
        assert "MUST call your DIE Runtime MCP tool `context_snapshot`" in env["briefing"]
        assert f"principal.scope == `{scope}`" in env["briefing"]
        assert "freshness.status == `fresh`" in env["briefing"]
        assert "data.canon_context.load_status == `VERIFIED`" in env["briefing"]
        assert "do not perform any mutation/control action" in env["briefing"].lower()


def test_convergence_receipt_validation_is_principal_and_repo_pinned() -> None:
    module = _load()
    sha = "b" * 40
    good = {
        "principal_id": "die-lnx-executive-001",
        "scope": "company_portfolio",
        "authority_capability": "semantic_observation",
        "freshness_status": "fresh",
        "canon_load_status": "VERIFIED",
        "source_trust": "DEGRADED",
        "completeness": "degraded",
        "repo_sha": sha,
        "bootstrap_status": "PASS",
    }
    assert module.validate_receipt("executive", good, sha) == []
    bad = dict(good, principal_id="chatgpt-plus-executive")
    assert any(x.startswith("E_CONVERGENCE_FIELD:principal_id") for x in module.validate_receipt("executive", bad, sha))


def test_linux_cognition_bootstraps_preserve_role_vs_principal_separation() -> None:
    executive = EXEC.read_text(encoding="utf-8")
    division = DIV.read_text(encoding="utf-8")
    assert "die-lnx-executive-001" in executive and "company/executive/IDENTITY.md" in executive
    assert "die-lnx-division-001" in division and "company/division/division001/IDENTITY.md" in division
    assert "context_snapshot" in executive and "context_snapshot" in division
    assert "command Workers/MUXIA" in executive and "command Workers/MUXIA" in division
    for token in ["OE-001", "OE-002", "OE-003", "OE-004", "OE-005"]:
        assert token in division


def test_society_authority_keeps_orchestration_cognition_execution_separate() -> None:
    text = SOCIETY.read_text(encoding="utf-8")
    for token in ["Hermes income-operator", "Division01", "Executive", "Worker", "MUXIA", "State Manager", "Founder"]:
        assert token in text
    assert "Hermes routes cognition and execution but does not manufacture" in text
    assert "MUXIA is an engine/provider boundary, never an authority-bearing actor" in text
    assert "Linux principal presenting a Windows principal as issuer MUST be rejected" in text
