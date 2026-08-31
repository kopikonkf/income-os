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


def _outbox_payload_from_claim(entry: dict[str, Any], instance_id: str) -> dict[str, Any]:
    return {
        "schema": "die.operator-v2.outbox-request.v2",
        "company_instance_id": instance_id,
        "claim_sequence": entry["sequence"],
        "claim_entry_sha256": entry["entry_sha256"],
        "created_at": entry["recorded_at"],
        "dedupe_key": entry["dedupe_key"],
        "decision": entry["decision"],
        "action_request": {
            "schema_version": "die.operator-v2.action-request.v1",
            "action_type": entry["action_type"],
            "actor_id": "hermes-operator",
            "projection_stage": entry["projection_stage"],
            "evidence_receipt_types": entry.get("evidence_receipt_types", []),
            "target_principal_id": entry.get("target_principal_id"),
        },
        "next_required_receipt": entry.get("next_required_receipt"),
        "semantic_content_authored": False,
        "production_authority_granted": False,
        "external_side_effect_performed": False,
    }


def _claim_outbox_path(outbox: Path, entry: dict[str, Any]) -> Path:
    return outbox / f"claim-{int(entry['sequence']):06d}-{entry['entry_sha256'][:16]}.json"


def _legacy_outbox_matches(outbox: Path, entry: dict[str, Any]) -> bool:
    legacy = outbox / (entry["dedupe_key"] + ".json")
    if not legacy.exists():
        return False
    try:
        value = json.loads(legacy.read_text(encoding="utf-8"))
    except Exception:
        return False
    action = value.get("action_request") or {}
    return (
        value.get("dedupe_key") == entry["dedupe_key"]
        and action.get("action_type") == entry["action_type"]
        and action.get("target_principal_id") == entry.get("target_principal_id")
        and action.get("projection_stage") == entry["projection_stage"]
    )


def _materialize_claim_outboxes(journal: dict[str, Any], outbox: Path, instance_id: str) -> dict[str, Any]:
    outbox.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    existing: list[str] = []
    for entry in journal.get("entries", []):
        path = _claim_outbox_path(outbox, entry)
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            expected = _outbox_payload_from_claim(entry, instance_id)
            if value != expected:
                raise RuntimeError(f"E_OUTBOX_CLAIM_CONFLICT:{entry['sequence']}")
            existing.append(str(path))
            continue
        if _legacy_outbox_matches(outbox, entry):
            existing.append(str(outbox / (entry["dedupe_key"] + ".json")))
            continue
        _atomic(path, _outbox_payload_from_claim(entry, instance_id))
        written.append(str(path))
    return {"written": written, "existing": existing}


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
    persisted_journal = REPLAY.load_journal(journal_path)
    materialized = _materialize_claim_outboxes(persisted_journal, outbox, instance_id)
    outbox_path = None
    if claim["status"] == "CLAIMED":
        outbox_path = _claim_outbox_path(outbox, claim["claim_entry"])
        if not outbox_path.exists() and not _legacy_outbox_matches(outbox, claim["claim_entry"]):
            raise RuntimeError("E_OUTBOX_MATERIALIZATION_MISSING")
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
        "outbox_recovered_count": len(materialized["written"]) - (1 if claim["status"] == "CLAIMED" and outbox_path is not None and str(outbox_path) in materialized["written"] else 0),
        "outbox_materialized_count": len(materialized["written"]),
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
