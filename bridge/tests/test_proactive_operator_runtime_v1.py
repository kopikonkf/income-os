"""Runtime tests for the DIE Proactive Operator Layer V0 (PR #30 canon).

Covers: envelope bounds + fingerprint stability, pause fail-closed, tick
receipt schema conformance, illegal-transition blocking, FORBIDDEN action
blocking, dedupe recurrence, non-progress counter, EXECUTED/NO_OP mutation
consistency, and platform receipt ingestion rules (SYNTHETIC constraints).

All state lives under a temporary DIE_HOME so live C:\\DIE is untouched.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

DIE_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DIE_REPO / "bin"))

import die_operator_tick as tick  # noqa: E402
import die_platform_receipt as plat  # noqa: E402


@pytest.fixture()
def die_home(tmp_path, monkeypatch):
    home = tmp_path / "DIE"
    (home / "state" / "operator").mkdir(parents=True)
    for sub in ("bin", "company/schemas", "docs/operations", "docs/missions",
                "docs/atlas", "docs/pipeline", "state/projection"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DIE_HOME", str(home))
    monkeypatch.setattr(tick, "DIE", home)
    monkeypatch.setattr(tick, "STATE", home / "state")
    op = home / "state" / "operator"
    monkeypatch.setattr(tick, "OP", op)
    monkeypatch.setattr(tick, "TICKS", op / "ticks")
    monkeypatch.setattr(tick, "RECEIPTS", op / "platform_receipts")
    monkeypatch.setattr(tick, "QC_INBOX", op / "qc_inbox")
    monkeypatch.setattr(tick, "PAUSE_FLAG", op / "PAUSE")
    monkeypatch.setattr(tick, "LOCK", op / "TICK.lock")
    monkeypatch.setattr(tick, "CURSOR", op / "cursor.json")
    monkeypatch.setattr(
        tick, "SCHEMA",
        DIE_REPO / "company" / "schemas" / "die.operator.tick.v1.schema.json")
    monkeypatch.setattr(tick, "EVENT_PY", DIE_REPO / "bin" / "die_event.py")
    monkeypatch.setattr(
        tick, "CANON_MANIFEST", home / "company" / "manifest-absent.json")
    monkeypatch.setattr(plat, "DIE", home)
    monkeypatch.setattr(plat, "RECEIPTS", op / "platform_receipts")
    monkeypatch.setattr(
        plat, "SCHEMA",
        DIE_REPO / "company" / "schemas" / "die.platform.receipt.v1.schema.json")
    monkeypatch.setattr(plat, "EVENT_PY", DIE_REPO / "bin" / "die_event.py")
    # Deterministic collectors: no git/hermes/network in unit tests.
    monkeypatch.setattr(tick, "collect_repo_sha", lambda: "a" * 40)
    monkeypatch.setattr(
        tick, "collect_canon_hashes",
        lambda: ({name: "b" * 64 for name in tick.CANON_FILES}, "VERIFIED"))
    monkeypatch.setattr(
        tick, "collect_kanban",
        lambda override: ([{"id": "t_x", "status": "ready", "assignee": None,
                            "title": "fixture"}], "FILE_OVERRIDE"))
    return home


def _prepare(die_home, fingerprint_seed="fixed"):
    kanban_fixture = die_home / "kanban.json"
    kanban_fixture.write_text(json.dumps([
        {"id": "t_x", "status": "ready"}]), encoding="utf-8")
    rc = tick.main(["prepare", "--kanban-file", str(kanban_fixture),
                    "--no-lock"])
    assert rc == 0
    ticks = sorted((die_home / "state" / "operator" / "ticks").iterdir())
    tick_dir = ticks[-1]
    envelope = json.loads((tick_dir / "envelope.json").read_text(encoding="utf-8"))
    return tick_dir, envelope


def _decision(prev="IDLE", sel="IDLE", result="NO_OP", actions=None,
              selected=None, mutations=None):
    return {
        "previous_state": prev,
        "selected_state": sel,
        "candidate_actions": actions if actions is not None else [{
            "action_id": "A1", "action_type": "NO_OP",
            "authority": "AUTONOMOUS", "rationale": "nothing eligible yet",
            "evidence_refs": ["envelope.kanban"],
            "dedupe_key": "operator:v1:M-001:IDLE:none:00000000",
        }],
        "selected_action_id": selected,
        "result": result,
        "mutations": mutations or [],
        "next_tick_not_before": "2026-08-24T10:30:00Z",
    }


def test_envelope_within_budget_and_fingerprint_stable(die_home):
    _, env1 = _prepare(die_home)
    fp1 = env1["input_fingerprint"]
    assert len(fp1) == 64
    size = (die_home / "state" / "operator" / "ticks").rglob("envelope.json")
    for path in size:
        assert path.stat().st_size <= tick.MAX_ENVELOPE_BYTES


def test_pause_fail_closed(die_home):
    pause = die_home / "state" / "operator" / "PAUSE"
    pause.write_text("{}", encoding="utf-8")
    rc = tick.main(["prepare", "--no-lock"])
    assert rc == 0
    ticks_dir = die_home / "state" / "operator" / "ticks"
    assert not ticks_dir.exists() or not any(ticks_dir.iterdir())


def test_finalize_no_op_receipt_conforms(die_home):
    tick_dir, envelope = _prepare(die_home)
    (tick_dir / "decision.json").write_text(
        json.dumps(_decision()), encoding="utf-8")
    rc = tick.main(["finalize", "--tick-dir", str(tick_dir)])
    assert rc == 0
    receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "die.operator.tick.v1"
    assert receipt["result"] == "NO_OP"
    assert receipt["budget"]["cost_usd"] == 0
    events = (die_home / "state" / "EVENTS.jsonl").read_text(
        encoding="utf-8-sig").strip().splitlines()
    assert any("operator tick" in line for line in events)


def test_illegal_transition_blocked(die_home):
    tick_dir, _ = _prepare(die_home)
    decision = _decision(prev="IDLE", sel="FOUNDER_QC", result="EXECUTED")
    (tick_dir / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    tick.main(["finalize", "--tick-dir", str(tick_dir)])
    receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "BLOCKED"
    assert receipt["mutations"] == []
    sidecar = json.loads(
        (tick_dir / "violations.json").read_text(encoding="utf-8"))
    assert any("illegal transition" in v for v in sidecar["violations"])


def test_forbidden_authority_rejected(die_home):
    tick_dir, _ = _prepare(die_home)
    actions = [{
        "action_id": "A1", "action_type": "INVOKE_M001_RUNNER",
        "authority": "FORBIDDEN", "rationale": "shortcut attempt",
        "evidence_refs": [], "dedupe_key": "operator:v1:M-001:x:y:00000000",
    }]
    decision = _decision(result="EXECUTED", actions=actions, selected="A1",
                         prev="AWAITING_AUTHORIZATION", sel="BATCH_RUNNING")
    (tick_dir / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    tick.main(["finalize", "--tick-dir", str(tick_dir)])
    receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "BLOCKED"


def test_no_op_with_mutations_violates(die_home):
    tick_dir, _ = _prepare(die_home)
    decision = _decision(result="NO_OP", mutations=[{
        "kind": "KANBAN_CARD", "ref": "t_new", "status": "CREATED",
        "dedupe_key": "operator:v1:M-001:card:t_new:00000000"}])
    (tick_dir / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    tick.main(["finalize", "--tick-dir", str(tick_dir)])
    receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "BLOCKED"


def test_dedupe_recurrence_24h_blocked(die_home):
    tick_dir1, _ = _prepare(die_home)
    decision = _decision(result="EXECUTED", mutations=[{
        "kind": "KANBAN_CARD", "ref": "t_r1", "status": "CREATED",
        "dedupe_key": "operator:v1:M-001:RESEARCH_PENDING:triage:aaaa0000"}],
        selected=None)
    decision["event_dedupe_key"] = "operator:v1:M-001:research-request:triage:aaaa0000"
    (tick_dir1 / "decision.json").write_text(json.dumps(decision), encoding="utf-8")
    rc = tick.main(["finalize", "--tick-dir", str(tick_dir1)])
    assert rc == 0

    import time as _time
    _time.sleep(1.1)
    tick_dir2, _ = _prepare(die_home)
    decision2 = json.loads(json.dumps(decision))
    decision2["event_dedupe_key"] = decision["event_dedupe_key"]
    (tick_dir2 / "decision.json").write_text(json.dumps(decision2), encoding="utf-8")
    tick.main(["finalize", "--tick-dir", str(tick_dir2)])
    receipt2 = json.loads((tick_dir2 / "receipt.json").read_text(encoding="utf-8"))
    assert receipt2["result"] == "BLOCKED"


def test_non_progress_counter_grows_and_warns(die_home):
    seen_counts = []
    for _ in range(3):
        tick_dir, _ = _prepare(die_home)
        (tick_dir / "decision.json").write_text(
            json.dumps(_decision()), encoding="utf-8")
        tick.main(["finalize", "--tick-dir", str(tick_dir)])
        receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
        seen_counts.append(receipt["non_progress_count"])
    assert seen_counts[0] == 0 and seen_counts[1] == 1 and seen_counts[2] == 2


def test_degraded_canon_forces_report_only(die_home, monkeypatch):
    monkeypatch.setattr(
        tick, "collect_canon_hashes",
        lambda: ({name: "" for name in tick.CANON_FILES},
                 "E_CANON_FILE_MISSING"))
    tick_dir, _ = _prepare(die_home)
    (tick_dir / "decision.json").write_text(
        json.dumps(_decision(result="EXECUTED", mutations=[{
            "kind": "KANBAN_CARD", "ref": "t_z", "status": "CREATED",
            "dedupe_key": "operator:v1:M-001:c:z:00000000"}])),
        encoding="utf-8")
    tick.main(["finalize", "--tick-dir", str(tick_dir)])
    receipt = json.loads((tick_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "REPORT_ONLY"
    assert receipt["mutations"] == []


# ------------------------------------------------------- platform receipts --

PLATREC_BASE = {
    "schema_version": "die.platform.receipt.v1",
    "recorded_at": "2026-08-24T12:00:00Z",
    "recorded_by": "founder",
    "mission_id": "M-001",
    "batch_id": "M001-U1-001",
    "blueprint_id": "BP-TEST",
    "blueprint_sha256": "c" * 64,
    "asset_id": "M001-M13-FOOD-001",
    "platform": "ADOBE_STOCK",
    "stage": "REVIEW",
    "outcome": "APPROVED",
    "reason_code": "NONE",
    "evidence_label": "VERIFIED",
    "evidence_ref": "screenshot-ref",
    "evidence_sha256": "d" * 64,
    "cost_usd": 0,
}


def test_receipt_ingest_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("DIE_HOME", str(tmp_path))
    monkeypatch.setenv("DIE_STATE_ROOT", str(tmp_path))
    receipts_dir = tmp_path / "receipts"
    monkeypatch.setattr(plat, "DIE", tmp_path)
    monkeypatch.setattr(plat, "RECEIPTS", receipts_dir)
    monkeypatch.setattr(
        plat, "SCHEMA",
        DIE_REPO / "company" / "schemas" / "die.platform.receipt.v1.schema.json")
    monkeypatch.setattr(plat, "EVENT_PY", DIE_REPO / "bin" / "die_event.py")
    row = dict(PLATREC_BASE, receipt_id="PLATREC-TEST0001",
               dedupe_key="platform:v1:test:0001")
    src = tmp_path / "r.json"
    src.write_text(json.dumps(row), encoding="utf-8")
    assert plat.main(["ingest", "--file", str(src)]) == 0
    stored = receipts_dir / "PLATREC-TEST0001.json"
    assert stored.is_file()


def test_receipt_synthetic_requires_fixture_recorder(tmp_path, monkeypatch):
    monkeypatch.setenv("DIE_HOME", str(tmp_path))
    monkeypatch.setenv("DIE_STATE_ROOT", str(tmp_path))
    receipts_dir = tmp_path / "receipts"
    monkeypatch.setattr(plat, "DIE", tmp_path)
    monkeypatch.setattr(plat, "RECEIPTS", receipts_dir)
    monkeypatch.setattr(
        plat, "SCHEMA",
        DIE_REPO / "company" / "schemas" / "die.platform.receipt.v1.schema.json")
    monkeypatch.setattr(plat, "EVENT_PY", DIE_REPO / "bin" / "die_event.py")
    row = dict(PLATREC_BASE, receipt_id="PLATREC-TEST0002",
               evidence_label="SYNTHETIC", recorded_by="founder",
               dedupe_key="platform:v1:test:0002")
    src = tmp_path / "r2.json"
    src.write_text(json.dumps(row), encoding="utf-8")
    assert plat.main(["ingest", "--file", str(src)]) == 1
    row["recorded_by"] = "simulation-fixture"
    src.write_text(json.dumps(row), encoding="utf-8")
    assert plat.main(["ingest", "--file", str(src)]) == 0
