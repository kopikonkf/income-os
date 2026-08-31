#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DIE_HOME = HERE.parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"E_MODULE_LOAD:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREPARE = _load("id_lnx002_prepare", HERE / "prepare_operator_v2.py")
REPLAY = _load("id_lnx002_replay", HERE / "replay_recovery.py")


def _utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(temp, path)


def _load_receipts(inbox: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not inbox.exists():
        return rows
    for path in sorted(inbox.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"E_RECEIPT_NOT_OBJECT:{path.name}")
        rows.append(value)
    if len(rows) > 100:
        raise RuntimeError("E_RECEIPT_LIMIT")
    return rows


def run() -> dict[str, Any]:
    state_root = Path(os.environ.get("DIE_STATE_ROOT", "/var/lib/die")) / "state" / "operator-v2"
    instance_id = os.environ.get("DIE_COMPANY_INSTANCE", "")
    if instance_id != "DIE-LINUX":
        raise RuntimeError("E_LINUX_INSTANCE_REQUIRED")
    inbox = state_root / "receipt-inbox"
    snapshot_path = state_root / "receipt-snapshot.json"
    journal_path = state_root / "dispatch-journal.json"
    output_dir = state_root / "prepared"
    outbox = state_root / "outbox"
    now = _utcnow()
    snapshot = {
        "schema_version": "die.operator-v2.receipt-snapshot.v1",
        "company_instance_id": instance_id,
        "mission_id": "M-001",
        "subject_id": os.environ.get("DIE_OPERATOR_V2_SUBJECT_ID", "M001-ACTIVE"),
        "as_of": now,
        "receipts": _load_receipts(inbox),
        "kanban_metadata": {"source": "typed-receipt-first", "cognition_proof_used": False},
    }
    _atomic(snapshot_path, snapshot)
    prepared = PREPARE.prepare(snapshot_path=snapshot_path, dispatch_journal_path=journal_path, output_dir=output_dir)
    routing_state_path = state_root / "routing-state.json"
    claim = REPLAY.persist_claim(
        snapshot_path=snapshot_path,
        journal_path=journal_path,
        routing_state_path=routing_state_path,
        now=now,
    )
    plan = claim["routing_plan"]
    outbox_path = None
    if claim["status"] == "CLAIMED":
        request = {
            "schema": "die.operator-v2.outbox-request.v1",
            "company_instance_id": instance_id,
            "created_at": now,
            "dedupe_key": plan["dedupe_key"],
            "decision": plan["decision"],
            "action_request": plan["action_request"],
            "next_required_receipt": plan.get("next_required_receipt"),
            "semantic_content_authored": False,
            "production_authority_granted": False,
        }
        outbox.mkdir(parents=True, exist_ok=True)
        outbox_path = outbox / (plan["dedupe_key"] + ".json")
        if outbox_path.exists():
            existing = json.loads(outbox_path.read_text(encoding="utf-8"))
            if existing.get("dedupe_key") != request["dedupe_key"] or existing.get("action_request") != request["action_request"]:
                raise RuntimeError("E_OUTBOX_CONFLICT")
        else:
            _atomic(outbox_path, request)
    summary = {
        "schema": "die.operator-v2.linux-scheduler-tick.v1",
        "status": "PASS",
        "company_instance_id": instance_id,
        "tick_id": prepared["tick_id"],
        "intelligence_stage": prepared["prepared"]["projection"]["intelligence_stage"],
        "next_required_receipt": prepared["prepared"]["projection"]["next_required_receipt"],
        "routing_decision": plan["decision"],
        "action_type": plan["action_request"]["action_type"],
        "target_principal_id": plan["action_request"].get("target_principal_id"),
        "claim_status": claim["status"],
        "outbox_written": outbox_path is not None,
        "outbox_ref": str(outbox_path) if outbox_path else None,
        "semantic_content_authored": False,
        "production_authority_granted": False,
        "network_request_performed": False,
    }
    return summary


def main() -> int:
    try:
        print(json.dumps(run(), indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "die.operator-v2.linux-scheduler-tick.v1", "status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
