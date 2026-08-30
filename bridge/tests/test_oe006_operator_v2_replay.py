from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "die-agents" / "hermes" / "operator-v2"


def load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


F = load("oe006g_fixture_test", ENGINE / "fixtures" / "build_operator_v2_fixture.py")
R = load("oe006g_replay_test", ENGINE / "replay_recovery.py")
PREP = load("oe006g_prepare_test", ENGINE / "prepare_operator_v2.py")


def _write_snapshot(path: Path, snapshot: dict) -> None:
    path.write_text(json.dumps(snapshot), encoding="utf-8")


def test_oe006g_restart_replay_is_deterministic_for_identical_evidence_and_time():
    snapshot = F.snapshot_prefix(4)
    first = R.claim(snapshot, now="2026-08-30T07:00:00Z")
    assert first["status"] == "CLAIMED"
    serialized = json.loads(json.dumps(first["journal"]))
    a = R.recover(copy.deepcopy(snapshot), serialized, now="2026-08-30T07:10:00Z")
    b = R.recover(copy.deepcopy(snapshot), serialized, now="2026-08-30T07:10:00Z")
    assert a == b
    assert a["replayed_entry_count"] == 1
    assert a["current_plan"]["decision"] == "NO_OP_DUPLICATE"


def test_oe006g_write_ahead_claim_suppresses_duplicate_dispatch():
    snapshot = F.snapshot_prefix(2)
    first = R.claim(snapshot, now="2026-08-30T07:00:00Z")
    entry = first["claim_entry"]
    assert entry["recorded_before_side_effect"] is True
    assert entry["decision"] == "DISPATCH"
    assert entry["outcome"] == "DISPATCHED"
    duplicate = R.claim(snapshot, first["journal"], now="2026-08-30T07:05:00Z")
    assert duplicate["status"] == "SUPPRESSED"
    assert duplicate["routing_plan"]["decision"] == "NO_OP_DUPLICATE"
    assert len(duplicate["journal"]["entries"]) == 1


def test_oe006g_stale_receipts_cannot_replay_ready_for_production():
    ready = F.full_snapshot()
    claimed = R.claim(ready, now=ready["as_of"])
    stale = copy.deepcopy(ready)
    stale["as_of"] = "2026-09-01T07:00:00Z"
    recovered = R.recover(stale, claimed["journal"], now=stale["as_of"])
    assert recovered["projection"]["intelligence_stage"] != "READY_FOR_PRODUCTION"
    assert recovered["current_plan"]["action_request"]["action_type"] != "OP-INVOKE-M001-RUNNER"
    assert recovered["invalidated_entry_count"] == 1


@pytest.mark.parametrize("receipt_type", ["WORTH_MAKING_EXEC_REVIEW", "BLUEPRINT_EXEC_REVIEW"])
def test_oe006g_forged_semantic_review_principal_blocks_without_claim(receipt_type: str):
    snapshot = F.full_snapshot()
    receipt = next(row for row in snapshot["receipts"] if row["receipt_type"] == receipt_type)
    receipt["issuer_id"] = "hermes-operator"
    out = R.claim(snapshot, now=snapshot["as_of"])
    assert out["status"] == "BLOCKED_INVALID_RECEIPTS"
    assert out["recovery"]["projection"]["intelligence_stage"] == "BLOCKED_INVALID_RECEIPTS"
    assert out["routing_plan"]["action_request"]["action_type"] == "OP-BLOCK-CARD"
    assert out["journal"]["entries"] == []


def test_oe006g_legacy_kanban_replay_is_metadata_only_and_cannot_reset_dedupe():
    snapshot = F.snapshot_prefix(1, kanban_done=False)
    first = R.claim(snapshot, now="2026-08-30T07:00:00Z")
    changed = copy.deepcopy(snapshot)
    changed["kanban_metadata"]["legacy_cards"] = [
        {"id": "T1", "status": "done"},
        {"id": "T2", "status": "done"},
        {"id": "T2-R2", "status": "done"},
    ]
    recovered = R.recover(changed, first["journal"], now="2026-08-30T07:05:00Z")
    assert recovered["projection"]["intelligence_stage"] == "DEMAND_SCORE"
    assert recovered["projection"]["kanban_cognition_proof_used"] is False
    assert recovered["replayed_entry_count"] == 1
    assert recovered["current_plan"]["decision"] == "NO_OP_DUPLICATE"


def test_oe006g_routing_state_is_recovered_from_journal_after_state_loss(tmp_path: Path):
    snapshot_path = tmp_path / "receipt-snapshot.json"
    journal_path = tmp_path / "dispatch-journal.json"
    state_path = tmp_path / "routing-state.json"
    _write_snapshot(snapshot_path, F.snapshot_prefix(3))
    R.persist_claim(
        snapshot_path=snapshot_path,
        journal_path=journal_path,
        routing_state_path=state_path,
        now="2026-08-30T07:00:00Z",
    )
    state_path.unlink()
    repaired = R.persist_claim(
        snapshot_path=snapshot_path,
        journal_path=journal_path,
        routing_state_path=state_path,
        now="2026-08-30T07:05:00Z",
    )
    assert repaired["status"] == "SUPPRESSED"
    assert state_path.is_file()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert next(iter(state["intents"].values()))["status"] == "OPEN"


def test_oe006g_crash_between_plan_and_record_has_no_durable_dispatch(tmp_path: Path):
    snapshot = F.snapshot_prefix(5)
    preview = R.recover(snapshot, now="2026-08-30T07:00:00Z")
    assert preview["current_plan"]["decision"] == "DISPATCH"
    journal_path = tmp_path / "dispatch-journal.json"
    assert not journal_path.exists()

    snapshot_path = tmp_path / "receipt-snapshot.json"
    state_path = tmp_path / "routing-state.json"
    _write_snapshot(snapshot_path, snapshot)
    claimed = R.persist_claim(
        snapshot_path=snapshot_path,
        journal_path=journal_path,
        routing_state_path=state_path,
        now="2026-08-30T07:00:00Z",
    )
    assert claimed["status"] == "CLAIMED"
    assert len(R.load_journal(journal_path)["entries"]) == 1


def test_oe006g_crash_after_dispatch_record_recovers_and_suppresses_duplicate(tmp_path: Path):
    snapshot_path = tmp_path / "receipt-snapshot.json"
    journal_path = tmp_path / "dispatch-journal.json"
    state_path = tmp_path / "routing-state.json"
    _write_snapshot(snapshot_path, F.snapshot_prefix(6))
    with pytest.raises(R.InjectedCrash, match="E_INJECTED_CRASH_AFTER_JOURNAL"):
        R.persist_claim(
            snapshot_path=snapshot_path,
            journal_path=journal_path,
            routing_state_path=state_path,
            now="2026-08-30T07:00:00Z",
            crash_after_journal_for_test=True,
        )
    assert journal_path.is_file()
    assert not state_path.exists()

    recovered = R.persist_claim(
        snapshot_path=snapshot_path,
        journal_path=journal_path,
        routing_state_path=state_path,
        now="2026-08-30T07:05:00Z",
    )
    assert recovered["status"] == "SUPPRESSED"
    assert recovered["routing_plan"]["decision"] == "NO_OP_DUPLICATE"
    assert len(R.load_journal(journal_path)["entries"]) == 1


def test_oe006g_follow_up_counter_persists_across_multiple_restarts():
    snapshot = F.snapshot_prefix(4)
    first = R.claim(snapshot, now="2026-08-30T07:00:00Z")
    follow1 = R.claim(snapshot, json.loads(json.dumps(first["journal"])), now="2026-08-30T07:31:00Z")
    follow2 = R.claim(snapshot, json.loads(json.dumps(follow1["journal"])), now="2026-08-30T08:02:00Z")
    state = follow2["routing_state"]
    intent = next(iter(state["intents"].values()))
    assert follow1["claim_entry"]["decision"] == "FOLLOW_UP"
    assert follow2["claim_entry"]["decision"] == "FOLLOW_UP"
    assert intent["follow_up_count"] == 2
    replayed = R.recover(snapshot, follow2["journal"], now="2026-08-30T08:03:00Z")
    assert next(iter(replayed["routing_state"]["intents"].values()))["follow_up_count"] == 2


def test_oe006g_founder_gate_cannot_be_created_by_replaying_ready_journal():
    ready = F.full_snapshot()
    runner_claim = R.claim(ready, now=ready["as_of"])
    without_founder = F.snapshot_prefix(7)
    recovered = R.recover(without_founder, runner_claim["journal"], now=without_founder["as_of"])
    assert recovered["projection"]["intelligence_stage"] == "AUTHORIZATION"
    assert recovered["projection"]["production_authorized"] is False
    assert recovered["current_plan"]["action_request"]["action_type"] == "OP-DRAFT-U1-REQUEST"
    assert recovered["current_plan"]["requested_target_principal_id"] == "founder"
    assert recovered["invalidated_entry_count"] == 1


def test_oe006g_ready_for_production_cannot_survive_invalidated_authorization():
    ready = F.full_snapshot()
    runner_claim = R.claim(ready, now=ready["as_of"])
    invalidated = copy.deepcopy(ready)
    invalidated["receipts"][-1]["status"] = "INVALID"
    recovered = R.recover(invalidated, runner_claim["journal"], now=invalidated["as_of"])
    assert recovered["status"] == "PASS"
    assert recovered["projection"]["intelligence_stage"] == "AUTHORIZATION"
    assert recovered["projection"]["can_invoke_production_runner"] is False
    assert recovered["current_plan"]["action_request"]["action_type"] == "OP-DRAFT-U1-REQUEST"


def test_oe006g_tampered_journal_hash_fails_closed():
    claimed = R.claim(F.snapshot_prefix(2), now="2026-08-30T07:00:00Z")
    forged = copy.deepcopy(claimed["journal"])
    forged["entries"][0]["target_principal_id"] = "hermes-operator"
    with pytest.raises(R.ReplayError, match="E_JOURNAL_ENTRY_HASH"):
        R.recover(F.snapshot_prefix(2), forged, now="2026-08-30T07:05:00Z")


def test_oe006g_prepare_replays_journal_instead_of_trusting_lost_state(tmp_path: Path):
    snapshot = F.snapshot_prefix(2)
    snapshot_path = tmp_path / "receipt-snapshot.json"
    journal_path = tmp_path / "dispatch-journal.json"
    _write_snapshot(snapshot_path, snapshot)
    claimed = R.claim(snapshot, now="2026-08-30T07:00:00Z")
    journal_path.write_text(json.dumps(claimed["journal"]), encoding="utf-8")

    out = PREP.prepare(
        snapshot_path=snapshot_path,
        routing_state_path=tmp_path / "missing-routing-state.json",
        dispatch_journal_path=journal_path,
        output_dir=tmp_path / "prepared",
    )
    prepared = out["prepared"]
    assert prepared["routing_state_source"] == "DISPATCH_JOURNAL_REPLAY"
    assert prepared["replayed_dispatch_claims"] == 1
    assert prepared["routing_plan"]["decision"] == "NO_OP_DUPLICATE"


def test_oe006g_terminal_block_survives_replay_instead_of_redispatching():
    snapshot = F.snapshot_prefix(3)
    journal = R.claim(snapshot, now="2026-08-30T07:00:00Z")["journal"]
    for now in ("2026-08-30T07:31:00Z", "2026-08-30T08:02:00Z", "2026-08-30T08:33:00Z"):
        journal = R.claim(snapshot, journal, now=now)["journal"]
    blocked = R.claim(snapshot, journal, now="2026-08-30T09:04:00Z")
    assert blocked["claim_entry"]["decision"] == "BLOCK_STALLED"
    replayed = R.recover(snapshot, blocked["journal"], now="2026-08-30T09:35:00Z")
    assert replayed["current_plan"]["decision"] == "NO_OP_TERMINAL"
    assert replayed["current_plan"]["action_request"]["action_type"] == "OP-OBSERVE-STATE"
