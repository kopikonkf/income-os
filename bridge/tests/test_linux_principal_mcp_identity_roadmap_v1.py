from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"
ROADMAP = ROOT / "docs" / "architecture" / "DIE_LINUX_PRINCIPAL_MCP_IDENTITY_ROADMAP_V1.md"
AUDIT = ROOT / "company" / "muxia" / "receipts" / "ID-LNX-000-windows-principal-reference-audit.receipt.json"


def _tasks() -> dict[str, dict]:
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data["tasks"]}


def test_windows_reference_audit_is_done_and_first_linux_tasks_are_ready() -> None:
    tasks = _tasks()
    assert tasks["ID-LNX-000"]["status"] == "DONE"
    assert tasks["MCP-LNX-001"]["status"] == "DONE"
    assert tasks["MCP-LNX-002"]["status"] == "DONE"
    assert tasks["MCP-LNX-003"]["status"] == "READY"
    assert tasks["ID-LNX-001"]["status"] == "READY"
    assert AUDIT.is_file()
    receipt = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert receipt["audit_mode"] == "READ_ONLY"
    assert receipt["windows_unchanged"] is True
    assert receipt["windows_reference"]["executive"]["tool_count"] == 18
    assert receipt["windows_reference"]["division01"]["tool_count"] == 6


def test_exec_div_mcp_wake_identity_chain_is_explicit() -> None:
    tasks = _tasks()
    assert tasks["MCP-LNX-002"]["depends_on"] == ["MCP-LNX-001"]
    assert tasks["MCP-LNX-003"]["depends_on"] == ["MCP-LNX-002", "IDENTITY-LNX-REKEY-004"]
    assert tasks["WAKE-LNX-001"]["depends_on"] == ["ID-LNX-000", "DIE-200", "DIE-201", "IDENTITY-LNX-REKEY-004"]
    assert tasks["WAKE-LNX-002"]["depends_on"] == ["WAKE-LNX-001", "MCP-LNX-003"]
    assert tasks["ID-LNX-003"]["depends_on"] == ["WAKE-LNX-002"]
    assert tasks["ID-LNX-004"]["depends_on"] == ["WAKE-LNX-002"]
    assert tasks["ID-LNX-005"]["depends_on"] == ["ID-LNX-002", "ID-LNX-003", "ID-LNX-004"]
    assert tasks["MCP-LNX-004"]["depends_on"] == ["MCP-LNX-003", "WAKE-LNX-002", "ID-LNX-005"]
    assert tasks["MCP-LNX-005"]["depends_on"] == ["MCP-LNX-004"]


def test_non_architect_acceptance_is_required_before_connector_handoff() -> None:
    tasks = _tasks()
    assert tasks["CUT-004A"]["depends_on"] == ["CUT-003", "MCP-LNX-005"]
    assert tasks["CUT-004B"]["depends_on"] == ["CUT-003", "MCP-LNX-005"]
    assert tasks["MX-053"]["depends_on"] == ["CUT-005"]
    assert tasks["MX-054"]["depends_on"] == ["MX-053"]
    assert tasks["CUT-006"]["depends_on"] == ["MX-054"]


def test_roadmap_preserves_two_lines_and_architect_last() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    assert "WAKE / COGNITION LINE" in text
    assert "RUNTIME MCP / STATE LINE" in text
    assert "Wake may trigger cognition but never substitutes for `context_snapshot`" in text
    assert "Architect migration is intentionally last" in text
    assert "executive-mcp.aethers.biz.id" in text
    assert "division01-mcp.aethers.biz.id" in text
