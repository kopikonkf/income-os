"""Mission acceptance reconciliation and fail-closed execution readiness."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

from income_os_bridge import events, projection
from income_os_bridge.hermes_state_reader import ReaderResult

BIN = pathlib.Path(__file__).resolve().parents[2] / "bin"
sys.path.insert(0, str(BIN))
import die_cron  # noqa: E402
import die_event  # noqa: E402


def _rr(rows, trust="VERIFIED"):
    return ReaderResult(rows, "cli", trust, "2026-08-22T18:20:58Z", True)


def _decisions():
    return [
        {
            "decision_id": "D-0020",
            "class": "mission_ratification",
            "choice": "RATIFY_M001_V1",
            "semantic_object": {
                "division_id": "DIVISION-01",
                "mission_id": "M-001",
            },
        },
        {
            "decision_id": "D-0021",
            "class": "propose_mission",
            "choice": "PROPOSE_M001",
            "evidence_ref": "repo:/charters/M-001-v1.md",
            "semantic_object": {
                "division_id": "DIVISION-01",
                "mission_id": "M-001",
                "goal": "First verified AI-stock license",
                "kill_criteria": {"day_45": "first verified license"},
            },
        },
        {
            "decision_id": "D-0022",
            "class": "mission_acceptance",
            "choice": "ACCEPT_M001_OPERATIONALLY",
            "semantic_object": {
                "division_id": "DIVISION-01",
                "mission_id": "M-001",
            },
        },
    ]


def _write_decisions(tmp_path, decisions=None):
    rows = _decisions() if decisions is None else decisions
    (tmp_path / "DECISIONS.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_accepted_decision_is_active_but_not_execution_ready_before_materialization(
    tmp_path,
    monkeypatch,
):
    _write_decisions(tmp_path)
    monkeypatch.setattr(projection.config, "STATE", tmp_path)
    monkeypatch.setattr(projection.reader, "get_kanban_rows", lambda: _rr([]))
    monkeypatch.setattr(projection.events, "read_events", lambda: [])

    any_status = projection.active_missions("any")
    active = projection.active_missions("active")

    assert len(any_status["data"]) == 1
    mission = any_status["data"][0]
    assert mission["mission_id"] == "M-001"
    assert mission["division_id"] == "DIVISION-01"
    assert mission["goal"] == "First verified AI-stock license"
    assert mission["status"] == "active"
    assert mission["lifecycle_state"] == "accepted"
    assert mission["reconcile_required"] is True
    assert mission["execution_ready"] is False
    assert mission["invalid"] is False
    assert mission["last_decision_id"] == "D-0022"
    assert any_status["completeness"] == "degraded"
    assert [row["mission_id"] for row in active["data"]] == ["M-001"]


def test_only_mission_linked_card_activates_and_counts_for_mission(
    tmp_path,
    monkeypatch,
):
    _write_decisions(tmp_path)
    cards = [
        {
            "card_id": "K-M001",
            "mission_id": "M-001",
            "title": "M-001 execution root",
            "status": "open",
            "assignee": "hermes-income-operator",
            "heartbeat_at": None,
        },
        {
            "card_id": "K-OTHER",
            "mission_id": "M-999",
            "title": "Unrelated",
            "status": "open",
            "assignee": "worker",
            "heartbeat_at": None,
        },
    ]
    monkeypatch.setattr(projection.config, "STATE", tmp_path)
    monkeypatch.setattr(projection.reader, "get_kanban_rows", lambda: _rr(cards))
    monkeypatch.setattr(projection.events, "read_events", lambda: [])

    active = projection.active_missions("active")
    detail = projection.mission_get("M-001")

    assert len(active["data"]) == 1
    mission = active["data"][0]
    assert mission["status"] == "active"
    assert mission["lifecycle_state"] == "materialized"
    assert mission["cards_open"] == 1
    assert mission["reconcile_required"] is False
    assert mission["execution_ready"] is True
    assert mission["invalid"] is False
    assert active["completeness"] == "complete"
    assert [card["card_id"] for card in detail["data"]["cards"]] == ["K-M001"]
    assert [row["decision_id"] for row in detail["data"]["decisions"]] == [
        "D-0020",
        "D-0021",
        "D-0022",
    ]


def test_canonical_event_can_link_db_fallback_card_without_guessing(
    tmp_path,
    monkeypatch,
):
    _write_decisions(tmp_path)
    card = {
        "card_id": "K-DB-1",
        "task_id": "K-DB-1",
        "mission_id": None,
        "title": "Title is not used for linkage",
        "status": "open",
        "assignee": "hermes-income-operator",
    }
    event = {
        "seq": 453,
        "event_id": "E-000453",
        "class": "NOTICE",
        "mission_id": "M-001",
        "task_id": "K-DB-1",
        "summary": "mission root materialized",
    }
    monkeypatch.setattr(projection.config, "STATE", tmp_path)
    monkeypatch.setattr(projection.reader, "get_kanban_rows", lambda: _rr([card]))
    monkeypatch.setattr(projection.events, "read_events", lambda: [event])

    mission = projection.active_missions("active")["data"][0]

    assert mission["lifecycle_state"] == "materialized"
    assert mission["reconcile_required"] is False
    assert mission["execution_ready"] is True
    assert mission["last_event_seq"] == 453


def test_blocked_materialized_mission_is_not_execution_ready():
    rows = projection._mission_rows(
        [{
            "card_id": "K-1",
            "mission_id": "M-001",
            "status": "blocked",
        }],
        [],
        _decisions(),
    )

    assert rows[0]["status"] == "blocked"
    assert rows[0]["lifecycle_state"] == "materialized"
    assert rows[0]["execution_ready"] is False


def test_alarm_resolution_is_explicit_and_readiness_fails_closed(monkeypatch):
    event_rows = [
        {
            "seq": 1,
            "event_id": "E-000001",
            "class": "CRITICAL",
            "summary": "provider main 429",
            "source": "provider",
        },
        {
            "seq": 2,
            "event_id": "E-000002",
            "class": "INFO",
            "summary": "provider probe passed",
            "source": "operator",
            "alarm_state": "resolved",
            "resolves_event_id": "E-000001",
        },
        {
            "seq": 3,
            "event_id": "E-000003",
            "class": "CRITICAL",
            "summary": "heartbeat cannot find Hermes",
            "source": "cron",
            "dedupe_key": "health:die-heartbeat:kanban-cli",
            "alarm_state": "open",
        },
    ]
    monkeypatch.setattr(
        projection.reader,
        "get_gateway_status",
        lambda: _rr([{"running": False, "uptime_s": None}]),
    )
    monkeypatch.setattr(projection.reader, "get_cron_jobs", lambda: _rr([]))
    monkeypatch.setattr(projection.events, "read_events", lambda: event_rows)
    monkeypatch.setattr(projection.events, "read_cursor", lambda: 3)

    health = projection.system_health()["data"]

    assert [row["event_id"] for row in health["active_alarms"]] == ["E-000003"]
    assert health["execution_readiness"] == {
        "ready": False,
        "blockers": [
            "gateway_not_running",
            "critical_alarm:E-000003",
        ],
    }


def test_mission_ratification_writer_requires_structured_division_identity(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(die_event, "STATE", tmp_path)

    with pytest.raises(ValueError, match="membutuhkan request_id"):
        die_event.emit_decision(
            "RATIFY",
            "Founder ratified",
            klass="mission_ratification",
            print_record=False,
        )
    with pytest.raises(ValueError, match="division_id"):
        die_event.emit_decision(
            "RATIFY",
            "Founder ratified",
            klass="mission_ratification",
            request_id="REQ-1",
            semantic_object={"mission_id": "M-001"},
            print_record=False,
        )
    assert not (tmp_path / "DECISIONS.jsonl").exists()

    record = die_event.emit_decision(
        "RATIFY",
        "Founder ratified",
        klass="mission_ratification",
        request_id="REQ-2",
        semantic_object={
            "division_id": "DIVISION-01",
            "mission_id": "M-001",
        },
        print_record=False,
    )
    assert record["semantic_object"]["division_id"] == "DIVISION-01"
    assert record["committed_by"] == "die-state-manager"


def test_alarm_writer_and_hermes_executable_override(tmp_path, monkeypatch):
    monkeypatch.setattr(die_event, "STATE", tmp_path)
    alarm = die_event.emit_event(
        "CRITICAL",
        "cron",
        "Kanban unavailable",
        dedupe_key="health:kanban",
        alarm_state="open",
    )
    resolved = die_event.emit_event(
        "INFO",
        "cron",
        "Kanban restored",
        dedupe_key="health:kanban",
        alarm_state="resolved",
    )
    assert alarm["alarm_state"] == "open"
    assert resolved["alarm_state"] == "resolved"

    executable = tmp_path / "hermes.exe"
    executable.write_text("stub", encoding="utf-8")
    found = die_cron.resolve_hermes_executable(
        env={"DIE_HERMES_EXE": str(executable)},
        python_executable=str(tmp_path / "python.exe"),
        which=lambda _name: None,
    )
    assert found == executable


def test_recent_events_preserve_scope_tags_for_division_filtering(
    tmp_path,
    monkeypatch,
):
    event_path = tmp_path / "EVENTS.jsonl"
    event_path.write_text(
        json.dumps({
            "seq": 1,
            "event_id": "E-000001",
            "ts": "2026-08-22T18:20:58Z",
            "class": "NOTICE",
            "source": "hermes-income-operator",
            "division_id": "DIVISION-01",
            "mission_id": "M-001",
            "task_id": "K-1",
            "summary": "mission root materialized",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(events.config, "EVENTS", event_path)

    row = events.recent_events()["events"][0]

    assert row["division_id"] == "DIVISION-01"
    assert row["mission_id"] == "M-001"
    assert row["task_id"] == "K-1"
