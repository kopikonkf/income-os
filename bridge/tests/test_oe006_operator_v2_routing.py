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


F = load("oe006_b12_fixture", ENGINE / "fixtures" / "build_operator_v2_fixture.py")
P = load("oe006_b12_projection", ENGINE / "project_intelligence_stage.py")
Q = load("oe006_b12_quarantine", ENGINE / "quarantine_legacy_kanban.py")
R = load("oe006_b12_route", ENGINE / "route_followup.py")
PREP = load("oe006_b12_prepare", ENGINE / "prepare_operator_v2.py")


def test_oe006d_rule_explicitly_quarantines_historical_cards_and_forbids_grandfathering():
    rule = json.loads((ENGINE / "LEGACY_KANBAN_QUARANTINE_RULE_V1.json").read_text(encoding="utf-8"))
    assert set(rule["legacy_card_ids"]) == {"T1", "T2", "T2-R2"}
    assert rule["kanban_is_cognition_proof"] is False
    assert rule["grandfathering_policy"] == "FORBIDDEN"
    assert rule["legacy_card_effect"] == "NONE_ON_INTELLIGENCE_STAGE"


def test_oe006d_all_done_legacy_cards_without_receipts_remain_signals_and_quarantined():
    snap = F.snapshot_prefix(0, kanban_done=True)
    snap["kanban_metadata"]["legacy_cards"].append({"id": "T2-R2", "status": "done"})
    projection = P.project(snap)
    out = Q.classify(snap, projection)
    assert projection["intelligence_stage"] == "SIGNALS"
    assert projection["next_required_receipt"] == "OPPORTUNITY_SIGNALS"
    assert out["quarantined_count"] == 3
    assert all(row["cognition_effect"] == "NONE" and row["grandfathered"] is False for row in out["cards"])


def test_oe006d_declared_backing_is_only_historical_corroboration_not_progress_source():
    snap = F.snapshot_prefix(1, kanban_done=True)
    snap["kanban_metadata"]["legacy_cards"][0]["backing_receipt_types"] = ["OPPORTUNITY_SIGNALS"]
    projection = P.project(snap)
    out = Q.classify(snap, projection)
    row = next(x for x in out["cards"] if x["card_id"] == "T1")
    assert row["historically_corroborated"] is True
    assert row["corroborated_by_active_receipts"] == ["OPPORTUNITY_SIGNALS"]
    assert row["cognition_effect"] == "NONE"
    assert projection["intelligence_stage"] == "DEMAND_SCORE"


def test_oe006d_full_receipt_chain_does_not_convert_legacy_cards_to_cognition_receipts():
    snap = F.full_snapshot()
    snap["kanban_metadata"]["legacy_cards"].append({"id": "T2-R2", "status": "done"})
    projection = P.project(snap)
    out = Q.classify(snap, projection)
    assert projection["intelligence_stage"] == "READY_FOR_PRODUCTION"
    assert out["cognitive_progress_source"] == "TYPED_PRINCIPAL_RECEIPTS_ONLY"
    assert all(x["grandfathered"] is False for x in out["cards"])


def test_oe006e_path_abstraction_resolves_windows_and_linux_without_profile_paths():
    win = PREP.resolve_roots({"DIE_HOME": r"X:\DIE-CANON", "DIE_STATE_ROOT": r"Y:\DIE-STATE", "MUXIA_ROOT": r"Z:\MUXIA", "DIE_CONFIG_ROOT": r"Y:\CFG", "DIE_INSTALL_ROOT": r"Y:\OPT"}, platform_name="windows")
    lin = PREP.resolve_roots({"DIE_HOME": "/srv/custom-die", "DIE_STATE_ROOT": "/var/lib/custom-die", "MUXIA_ROOT": "/var/lib/custom-muxia", "DIE_CONFIG_ROOT": "/etc/custom-die", "DIE_INSTALL_ROOT": "/opt/custom-die"}, platform_name="linux")
    assert win.die_home == r"X:\DIE-CANON" and win.die_state_root == r"Y:\DIE-STATE"
    assert lin.die_home == "/srv/custom-die" and lin.die_state_root == "/var/lib/custom-die"


def test_oe006e_profile_wrapper_is_path_neutral_and_delegates_to_canonical_entrypoint():
    text = (ENGINE / "hermes_profile_prepare_wrapper.py").read_text(encoding="utf-8")
    assert r"C:\DIE" not in text
    assert "/srv/die" not in text
    assert "DIE_HOME" in text and "Path.cwd()" in text
    assert '"bin" / "die_operator_prepare.py"' in text


def test_oe006e_canonical_entrypoint_has_compat_and_v2_modes_without_machine_root_literal():
    text = (ROOT / "bin" / "die_operator_prepare.py").read_text(encoding="utf-8")
    assert 'choices=["v1-compat", "v2"]' in text
    assert "die_operator_tick.py" in text and "prepare_operator_v2.py" in text
    assert r"C:\DIE" not in text and "/srv/die" not in text


def test_oe006e_v2_prepare_writes_bounded_projection_quarantine_and_route(tmp_path: Path):
    snap = F.snapshot_prefix(2, kanban_done=True)
    snapshot = tmp_path / "receipt-snapshot.json"
    snapshot.write_text(json.dumps(snap), encoding="utf-8")
    out = PREP.prepare(snapshot_path=snapshot, routing_state_path=None, output_dir=tmp_path / "prepared")
    tick = Path(out["tick_dir"])
    assert {p.name for p in tick.iterdir()} == {"projection.json", "legacy-kanban-quarantine.json", "routing-plan.json", "prepared.json"}
    prepared = json.loads((tick / "prepared.json").read_text(encoding="utf-8"))
    assert prepared["projection"]["intelligence_stage"] == "WORTH_MAKING"
    assert prepared["routing_plan"]["requested_target_principal_id"] == "division-head-division01"
    assert prepared["live_kanban_modified"] is False
    assert prepared["semantic_content_authored"] is False
    assert prepared["production_authority_granted"] is False
    assert prepared["network_request_performed"] is False


def test_oe006e_missing_snapshot_fails_closed(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="E_SNAPSHOT_MISSING"):
        PREP.prepare(snapshot_path=tmp_path / "missing.json", routing_state_path=None, output_dir=tmp_path / "out")


def test_oe006f_each_receipt_prefix_routes_to_deterministic_due_principal_or_worker():
    expected = [
        ("OP-CREATE-RESEARCH-CARD", "approved-signal-collector"),
        ("OP-DISPATCH-DEMAND-SCORE", "division001-demand-score-v1"),
        ("OP-REQUEST-DIVISION01-WORTH-MAKING", "division-head-division01"),
        ("OP-REQUEST-EXECUTIVE-WORTH-MAKING-REVIEW", "chatgpt-plus-executive"),
        ("OP-REQUEST-DIVISION01-BLUEPRINT", "division-head-division01"),
        ("OP-REQUEST-EXECUTIVE-BLUEPRINT-REVIEW", "chatgpt-plus-executive"),
        ("OP-CREATE-BLUEPRINT-COMPILE-CARD", "worker-template"),
        ("OP-DRAFT-U1-REQUEST", "founder"),
    ]
    for i, (action, target) in enumerate(expected):
        p = P.project(F.snapshot_prefix(i))
        out = R.plan(p)
        assert out["status"] == "READY" and out["decision"] == "DISPATCH"
        assert out["requested_action_type"] == action
        assert out["requested_target_principal_id"] == target
        assert out["authority_validation"]["status"] == "ALLOW"
        assert out["semantic_content_authored"] is False


def test_oe006f_duplicate_open_intent_is_suppressed_before_followup_threshold():
    p = P.project(F.snapshot_prefix(2))
    first = R.plan(p, now="2026-08-30T07:00:00Z")
    state = R.record(None, first, outcome="DISPATCHED", at="2026-08-30T07:00:00Z")
    again = R.plan(p, state, now="2026-08-30T07:10:00Z")
    assert again["decision"] == "NO_OP_DUPLICATE"
    assert again["action_request"]["action_type"] == "OP-OBSERVE-STATE"
    assert again["dedupe_key"] == first["dedupe_key"]


def test_oe006f_stalled_intent_follows_up_and_counts_only_dispatched_followups():
    p = P.project(F.snapshot_prefix(4))
    first = R.plan(p, now="2026-08-30T07:00:00Z")
    state = R.record(None, first, outcome="DISPATCHED", at="2026-08-30T07:00:00Z")
    follow = R.plan(p, state, now="2026-08-30T07:31:00Z")
    assert follow["decision"] == "FOLLOW_UP"
    assert follow["action_request"]["action_type"] == "OP-FOLLOW-UP-CARD"
    state2 = R.record(state, follow, outcome="DISPATCHED", at="2026-08-30T07:31:00Z")
    assert state2["intents"][first["dedupe_key"]]["follow_up_count"] == 1


def test_oe006f_stall_after_max_followups_blocks_instead_of_inventing_semantics():
    p = P.project(F.snapshot_prefix(5))
    first = R.plan(p, now="2026-08-30T07:00:00Z")
    state = R.record(None, first, outcome="DISPATCHED", at="2026-08-30T07:00:00Z")
    for minute in (31, 62, 93):
        follow = R.plan(p, state, now=f"2026-08-30T{7 + minute // 60:02d}:{minute % 60:02d}:00Z")
        assert follow["decision"] == "FOLLOW_UP"
        state = R.record(state, follow, outcome="DISPATCHED", at=follow["as_of"])
    blocked = R.plan(p, state, now="2026-08-30T09:04:00Z")
    assert blocked["decision"] == "BLOCK_STALLED"
    assert blocked["action_request"]["action_type"] == "OP-BLOCK-CARD"
    assert blocked["semantic_content_authored"] is False


def test_oe006f_founder_request_is_drafted_only_after_compile_hash_lock_is_active():
    auth_stage = P.project(F.snapshot_prefix(7))
    out = R.plan(auth_stage)
    assert out["requested_action_type"] == "OP-DRAFT-U1-REQUEST"
    assert out["requested_target_principal_id"] == "founder"
    assert "BLUEPRINT_COMPILE_HASH_LOCK" in out["action_request"]["evidence_receipt_types"]
    assert out["authority_validation"]["status"] == "ALLOW"


def test_oe006f_ready_chain_routes_runner_only_after_founder_authorization():
    ready = P.project(F.full_snapshot())
    out = R.plan(ready)
    assert out["requested_action_type"] == "OP-INVOKE-M001-RUNNER"
    assert out["requested_target_principal_id"] == "worker-template"
    assert ready["production_authorized"] is True
    assert out["authority_validation"]["status"] == "ALLOW"


def test_oe006f_authority_spoof_or_wrong_due_action_fails_closed():
    projection = P.project(F.snapshot_prefix(0))
    forged = copy.deepcopy(projection)
    forged["next_action_type"] = "F-PRODUCTION-AUTH"
    out = R.plan(forged)
    assert out["status"] == "BLOCKED_AUTHORITY"
    assert out["decision"] == "BLOCK_AUTHORITY"
    assert out["authority_validation"]["status"] == "DENY"
    assert out["production_authority_granted"] is False


def test_oe006f_identical_projection_and_state_produce_identical_routing_plan():
    projection = P.project(F.snapshot_prefix(6))
    assert R.plan(copy.deepcopy(projection)) == R.plan(copy.deepcopy(projection))