from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "company" / "muxia-task-graph-v1.json"


def _graph() -> dict:
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def _tasks() -> dict[str, dict]:
    return {row["id"]: row for row in _graph()["tasks"]}


def test_oe_task_ids_unique_dependencies_resolve_and_dag_is_acyclic() -> None:
    graph = _graph()
    rows = graph["tasks"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    tasks = {row["id"]: row for row in rows}
    for row in rows:
        for dep in row["depends_on"]:
            assert dep in tasks, f"{row['id']} -> missing {dep}"

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        assert task_id not in visiting, f"cycle at {task_id}"
        visiting.add(task_id)
        for dep in tasks[task_id]["depends_on"]:
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)


def test_oe_roadmap_has_all_milestones_and_only_first_atomic_task_ready() -> None:
    tasks = _tasks()
    for task_id in ["OE-000", "OE-001", "OE-002", "OE-003", "OE-004", "OE-005", "OE-006", "OE-007"]:
        assert task_id in tasks
    assert tasks["OE-000"]["status"] == "DONE"
    ready = {task_id for task_id, row in tasks.items() if task_id.startswith("OE-") and row["status"] == "READY"}
    assert ready == {"OE-003D"}


def test_oe_milestone_dependency_chain_is_strict() -> None:
    tasks = _tasks()
    assert tasks["OE-001A"]["depends_on"] == ["OE-000"]
    assert tasks["OE-001A"]["status"] == "DONE"
    assert tasks["OE-001B"]["status"] == "DONE"
    assert tasks["OE-001C"]["status"] == "DONE"
    assert tasks["OE-001D"]["status"] == "DONE"
    assert tasks["OE-001E"]["status"] == "DONE"
    assert tasks["OE-001F"]["status"] == "DONE"
    assert tasks["OE-001G"]["status"] == "DONE"
    assert tasks["OE-001"]["status"] == "DONE"
    assert tasks["OE-002A"]["status"] == "DONE"
    assert tasks["OE-002B"]["status"] == "DONE"
    assert tasks["OE-002C"]["status"] == "DONE"
    assert tasks["OE-002D"]["status"] == "DONE"
    assert tasks["OE-002E"]["status"] == "DONE"
    assert tasks["OE-002F"]["status"] == "DONE"
    assert tasks["OE-002"]["status"] == "DONE"
    assert tasks["OE-003A"]["status"] == "DONE"
    assert tasks["OE-003B"]["status"] == "DONE"
    assert tasks["OE-003C"]["status"] == "DONE"
    assert tasks["OE-003D"]["status"] == "READY"
    assert tasks["OE-002A"]["depends_on"] == ["OE-001"]
    assert tasks["OE-003A"]["depends_on"] == ["OE-002"]
    assert tasks["OE-004A"]["depends_on"] == ["OE-003"]
    assert tasks["OE-005A"]["depends_on"] == ["OE-004"]
    assert tasks["OE-006A"]["depends_on"] == ["OE-005"]
    assert tasks["OE-007A"]["depends_on"] == ["OE-006", "DIE-204", "MX-070"]


def test_oe_milestones_cannot_complete_without_terminal_atomic_gate() -> None:
    tasks = _tasks()
    assert tasks["OE-001"]["depends_on"] == ["OE-001G"]
    assert tasks["OE-002"]["depends_on"] == ["OE-002F"]
    assert tasks["OE-003"]["depends_on"] == ["OE-003G"]
    assert tasks["OE-004"]["depends_on"] == ["OE-004F"]
    assert tasks["OE-005"]["depends_on"] == ["OE-005F"]
    assert tasks["OE-006"]["depends_on"] == ["OE-006G"]
    assert tasks["OE-007"]["depends_on"] == ["OE-007G"]


def test_oe_authority_boundaries_are_encoded_in_acceptance_text() -> None:
    tasks = _tasks()
    worth = " ".join(tasks[x]["acceptance"] for x in ["OE-004B", "OE-004C", "OE-004E", "OE-004"])
    blueprint = " ".join(tasks[x]["acceptance"] for x in ["OE-005A", "OE-005B", "OE-005C", "OE-005D", "OE-005"])
    operator = " ".join(tasks[x]["acceptance"] for x in ["OE-006A", "OE-006B", "OE-006D", "OE-006F", "OE-006"])
    canary = " ".join(tasks[x]["acceptance"] for x in ["OE-007C", "OE-007D", "OE-007E", "OE-007F", "OE-007"])

    assert "Division01" in worth and "Executive" in worth and "Hermes is not" in worth
    assert "Division01" in blueprint and "Executive" in blueprint and "Worker/Hermes" in blueprint
    assert "Kanban" in operator and "self-grant" in operator and "never authors" in operator
    assert "Founder" in canary and "exact" in canary and "Worker/MUXIA" in canary


def test_cutover_path_cannot_bypass_oe007() -> None:
    tasks = _tasks()
    assert "OE-007" in tasks["MX-071"]["depends_on"]
    assert "OE-007 governed intelligence lineage" in tasks["MX-071"]["acceptance"]


def test_graph_declares_existing_waiting_states_used_by_migration_overlay() -> None:
    graph = _graph()
    states = set(graph["states"])
    for state in ["WAITING_OPERATOR", "WAITING_OPERATOR_CREDENTIALS", "WAITING_OBJECT_FILTER_COMPLETION"]:
        assert state in states
    for row in graph["tasks"]:
        assert row["status"] in states


def test_oe_atomic_count_is_pinned() -> None:
    tasks = _tasks()
    oe_ids = {task_id for task_id in tasks if task_id.startswith("OE-")}
    assert len(oe_ids) == 54