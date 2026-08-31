from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "company" / "browser" / "linux" / "cognition_acceptance.py"
EXEC_TEMPLATE = ROOT / "company" / "muxia" / "receipts" / "templates" / "ID-LNX-003-executive-cognition.template.json"
DIV_TEMPLATE = ROOT / "company" / "muxia" / "receipts" / "templates" / "ID-LNX-004-division01-cognition.template.json"
OPERATOR_RECEIPT = ROOT / "company" / "muxia" / "receipts" / "ID-LNX-002-operator-v2-linux.acceptance.receipt.json"


def _load():
    spec = importlib.util.spec_from_file_location("cognition_acceptance", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _receipt(path: Path, sha: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["repo_sha"] = sha
    return data


def test_role_templates_pass_when_repo_sha_is_exact() -> None:
    module = _load()
    sha = "c" * 40
    executive = _receipt(EXEC_TEMPLATE, sha)
    division = _receipt(DIV_TEMPLATE, sha)
    assert module.validate_assimilation("executive", executive, sha) == []
    assert module.validate_assimilation("division01", division, sha) == []


def test_role_acceptance_rejects_memory_authority_and_missing_responsibility() -> None:
    module = _load()
    sha = "d" * 40
    executive = _receipt(EXEC_TEMPLATE, sha)
    executive["account_memory_used_as_authority"] = True
    executive["responsibilities_ack"].remove("strategic_challenge")
    errors = module.validate_assimilation("executive", executive, sha)
    assert "E_ACCOUNT_MEMORY_AUTHORITY" in errors
    assert any(x.startswith("E_RESPONSIBILITY_ACK:strategic_challenge") for x in errors)


def test_society_acceptance_requires_distinct_principals_scopes_and_operator_done() -> None:
    module = _load()
    sha = "e" * 40
    executive = _receipt(EXEC_TEMPLATE, sha)
    division = _receipt(DIV_TEMPLATE, sha)
    operator = json.loads(OPERATOR_RECEIPT.read_text(encoding="utf-8"))
    assert module.validate_society(executive, division, operator, sha) == []

    collapsed = dict(division, principal_id=executive["principal_id"], scope=executive["scope"])
    errors = module.validate_society(executive, collapsed, operator, sha)
    assert "E_ROLE_COLLAPSE_PRINCIPAL" in errors
    assert "E_ROLE_COLLAPSE_SCOPE" in errors


def test_templates_are_linux_principal_specific_not_shared_role_ids() -> None:
    executive = json.loads(EXEC_TEMPLATE.read_text(encoding="utf-8"))
    division = json.loads(DIV_TEMPLATE.read_text(encoding="utf-8"))
    assert executive["principal_id"] == "die-lnx-executive-001"
    assert division["principal_id"] == "die-lnx-division-001"
    assert executive["role_anchor"] == "company/executive/IDENTITY.md"
    assert division["role_anchor"] == "company/division/division001/IDENTITY.md"
    assert executive["principal_id"] != "chatgpt-plus-executive"
    assert division["principal_id"] != "division-head-division01"
