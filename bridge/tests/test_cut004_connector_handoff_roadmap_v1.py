from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def test_cut004_chatgpt_connector_handoffs_are_first_class_atomic_tasks() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    tasks = {row["id"]: row for row in graph["tasks"]}
    exec_cut = tasks["CUT-004A"]
    div_cut = tasks["CUT-004B"]
    umbrella = tasks["CUT-004"]
    assert exec_cut["status"] == "BLOCKED"
    assert div_cut["status"] == "BLOCKED"
    assert exec_cut["depends_on"] == ["CUT-003", "MCP-LNX-005"]
    assert div_cut["depends_on"] == ["CUT-003", "MCP-LNX-005"]
    assert "Executive ChatGPT MCP connector" in exec_cut["title"]
    assert "Division01 ChatGPT MCP connector" in div_cut["title"]
    assert "Windows endpoint" in exec_cut["acceptance"]
    assert "Linux Executive endpoint" in exec_cut["acceptance"]
    assert "Windows endpoint" in div_cut["acceptance"]
    assert "Linux Division01 endpoint" in div_cut["acceptance"]
    assert "rollback until CUT-005" in exec_cut["acceptance"]
    assert "rollback until CUT-005" in div_cut["acceptance"]
    assert umbrella["depends_on"] == ["CUT-004A", "CUT-004B"]


def test_cut004_connector_handoffs_do_not_move_architect_ordering() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    tasks = {row["id"]: row for row in graph["tasks"]}
    assert tasks["CUT-005"]["depends_on"] == ["CUT-004"]
    assert tasks["MX-053"]["depends_on"] == ["CUT-005"]
    assert tasks["CUT-006"]["depends_on"] == ["MX-054"]