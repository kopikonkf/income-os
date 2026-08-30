#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
DIE_HOME_FROM_SOURCE = HERE.parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_MODULE_LOAD:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _config_module():
    return _load("oe006e_die_config", DIE_HOME_FROM_SOURCE / "bridge" / "income_os_bridge" / "config.py")


PROJECTION = _load("oe006e_projection", HERE / "project_intelligence_stage.py")
QUARANTINE = _load("oe006e_quarantine", HERE / "quarantine_legacy_kanban.py")
ROUTING = _load("oe006e_routing", HERE / "route_followup.py")
REPLAY = _load("oe006g_replay", HERE / "replay_recovery.py")


def resolve_roots(env: Mapping[str, str] | None = None, *, platform_name: str | None = None):
    return _config_module().resolve_die_path_roots(env, platform_name=platform_name)


def _sha_obj(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def prepare(
    *,
    snapshot_path: Path,
    routing_state_path: Path | None = None,
    dispatch_journal_path: Path | None = None,
    output_dir: Path,
) -> dict[str, Any]:
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"E_SNAPSHOT_MISSING:{snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    projection = PROJECTION.project(snapshot)
    quarantine = QUARANTINE.classify(snapshot, projection)
    state = None
    recovery = None
    routing_state_source = "EMPTY"
    if dispatch_journal_path and dispatch_journal_path.is_file():
        journal = REPLAY.load_journal(dispatch_journal_path)
        recovery = REPLAY.recover(snapshot, journal, now=snapshot["as_of"])
        state = recovery["routing_state"]
        routing = recovery["current_plan"]
        routing_state_source = "DISPATCH_JOURNAL_REPLAY"
    elif routing_state_path and routing_state_path.is_file():
        state = json.loads(routing_state_path.read_text(encoding="utf-8"))
        routing_state_source = "STATE_SNAPSHOT"
    if recovery is None:
        routing = ROUTING.plan(projection, state, now=snapshot["as_of"])
    prepared = {
        "schema": "die.operator-v2.prepared-tick.v1",
        "mission_id": snapshot["mission_id"],
        "subject_id": snapshot["subject_id"],
        "as_of": snapshot["as_of"],
        "snapshot_path": str(snapshot_path.resolve()),
        "snapshot_sha256": _sha_obj(snapshot),
        "projection": projection,
        "legacy_kanban_quarantine": quarantine,
        "routing_plan": routing,
        "routing_state_source": routing_state_source,
        "dispatch_journal_path": str(dispatch_journal_path.resolve()) if dispatch_journal_path else None,
        "replayed_dispatch_claims": recovery["replayed_entry_count"] if recovery else 0,
        "invalidated_dispatch_claims": recovery["invalidated_entry_count"] if recovery else 0,
        "live_kanban_modified": False,
        "semantic_content_authored": False,
        "production_authority_granted": False,
        "network_request_performed": False,
    }
    tick_id = "OPV2-" + _sha_obj({"mission": snapshot["mission_id"], "subject": snapshot["subject_id"], "as_of": snapshot["as_of"]})[:16]
    tick_dir = output_dir / tick_id
    _atomic_json(tick_dir / "projection.json", projection)
    _atomic_json(tick_dir / "legacy-kanban-quarantine.json", quarantine)
    _atomic_json(tick_dir / "routing-plan.json", routing)
    _atomic_json(tick_dir / "prepared.json", prepared)
    return {"tick_id": tick_id, "tick_dir": str(tick_dir.resolve()), "prepared": prepared}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot")
    ap.add_argument("--routing-state")
    ap.add_argument("--dispatch-journal")
    ap.add_argument("--output-dir")
    args = ap.parse_args(argv)
    roots = resolve_roots()
    state_root = Path(roots.die_state_root) / "state" / "operator-v2"
    snapshot = Path(args.snapshot).resolve() if args.snapshot else state_root / "receipt-snapshot.json"
    routing_state = Path(args.routing_state).resolve() if args.routing_state else state_root / "routing-state.json"
    dispatch_journal = Path(args.dispatch_journal).resolve() if args.dispatch_journal else state_root / "dispatch-journal.json"
    output = Path(args.output_dir).resolve() if args.output_dir else state_root / "prepared"
    out = prepare(
        snapshot_path=snapshot,
        routing_state_path=routing_state,
        dispatch_journal_path=dispatch_journal,
        output_dir=output,
    )
    summary = {
        "schema": "die.operator-v2.prepare-result.v1",
        "status": "PASS",
        "tick_id": out["tick_id"],
        "tick_dir": out["tick_dir"],
        "intelligence_stage": out["prepared"]["projection"]["intelligence_stage"],
        "next_required_receipt": out["prepared"]["projection"]["next_required_receipt"],
        "routing_decision": out["prepared"]["routing_plan"]["decision"],
        "action_type": out["prepared"]["routing_plan"]["action_request"]["action_type"],
        "target_principal_id": out["prepared"]["routing_plan"].get("requested_target_principal_id"),
        "kanban_cognition_proof_used": False,
        "semantic_content_authored": False,
        "production_authority_granted": False,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
