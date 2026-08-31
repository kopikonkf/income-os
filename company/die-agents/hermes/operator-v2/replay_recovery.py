#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parent
JOURNAL_SCHEMA = ROOT / "die.operator-v2.dispatch-journal.v1.schema.json"
PROJECTION_MODULE = ROOT / "project_intelligence_stage.py"
ROUTING_MODULE = ROOT / "route_followup.py"
ZERO_SHA256 = "0" * 64
CLAIMABLE_DECISIONS = {"DISPATCH", "FOLLOW_UP", "BLOCK_STALLED"}


class ReplayError(RuntimeError):
    pass


class InjectedCrash(RuntimeError):
    """Test-only crash boundary after the durable journal commit."""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReplayError(f"E_MODULE_LOAD:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROJECTION = _load("oe006g_projection", PROJECTION_MODULE)
ROUTING = _load("oe006g_routing", ROUTING_MODULE)


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def snapshot_sha256(snapshot: dict[str, Any]) -> str:
    return _sha(snapshot)


def receipt_chain_sha256(snapshot: dict[str, Any]) -> str:
    """Bind cognition evidence, never mutable Kanban or observation time."""
    return _sha(
        {
            "company_instance_id": snapshot.get("company_instance_id"),
            "mission_id": snapshot.get("mission_id"),
            "subject_id": snapshot.get("subject_id"),
            "receipts": snapshot.get("receipts", []),
        }
    )


def empty_journal() -> dict[str, Any]:
    return {"schema": "die.operator-v2.dispatch-journal.v1", "entries": []}


def _entry_hash(entry: dict[str, Any]) -> str:
    material = {key: value for key, value in entry.items() if key != "entry_sha256"}
    return _sha(material)


def validate_journal(journal: dict[str, Any]) -> None:
    schema = json.loads(JOURNAL_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(journal),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise ReplayError("E_JOURNAL_SCHEMA:" + errors[0].message)

    previous = ZERO_SHA256
    for sequence, entry in enumerate(journal["entries"], start=1):
        if entry["sequence"] != sequence:
            raise ReplayError(f"E_JOURNAL_SEQUENCE:{sequence}")
        if entry["previous_entry_sha256"] != previous:
            raise ReplayError(f"E_JOURNAL_PREVIOUS_HASH:{sequence}")
        expected = _entry_hash(entry)
        if entry["entry_sha256"] != expected:
            raise ReplayError(f"E_JOURNAL_ENTRY_HASH:{sequence}")
        previous = expected


def load_journal(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_journal()
    journal = json.loads(path.read_text(encoding="utf-8"))
    validate_journal(journal)
    return journal


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def _entry_matches_plan(entry: dict[str, Any], plan: dict[str, Any]) -> bool:
    expected_outcome = "BLOCKED" if plan["decision"] == "BLOCK_STALLED" else "DISPATCHED"
    return all(
        [
            entry["dedupe_key"] == plan["dedupe_key"],
            entry["plan_sha256"] == _sha(plan),
            entry["projection_stage"] == plan["projection_stage"],
            entry["decision"] == plan["decision"],
            entry["action_type"] == plan["action_request"]["action_type"],
            entry["target_principal_id"]
            == plan["action_request"].get("target_principal_id"),
            entry["outcome"] == expected_outcome,
            entry["follow_up_count"] == plan["follow_up_count"],
            entry["authority_status"]
            == plan["authority_validation"]["status"]
            == "ALLOW",
            plan["semantic_content_authored"] is False,
            plan["production_authority_granted"] is False,
        ]
    )


def recover(
    snapshot: dict[str, Any],
    journal: dict[str, Any] | None = None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    journal = copy.deepcopy(journal or empty_journal())
    validate_journal(journal)
    projection = PROJECTION.project(snapshot)
    observation_time = now or snapshot["as_of"]
    chain_sha = receipt_chain_sha256(snapshot)

    if projection["registry_status"] != "PASS":
        blocked_plan = ROUTING.plan(projection, None, now=observation_time)
        return {
            "schema": "die.operator-v2.recovery-result.v1",
            "status": "BLOCKED_INVALID_RECEIPTS",
            "projection": projection,
            "routing_state": ROUTING.empty_state(),
            "current_plan": blocked_plan,
            "replayed_entry_count": 0,
            "invalidated_entry_count": len(journal["entries"]),
            "journal_entry_count": len(journal["entries"]),
            "receipt_chain_sha256": chain_sha,
        }

    initial_plan = ROUTING.plan(projection, None, now=observation_time)
    current_dedupe_key = initial_plan["dedupe_key"]
    state = ROUTING.empty_state()
    replayed = 0
    invalidated = 0

    for entry in journal["entries"]:
        if (
            entry["receipt_chain_sha256"] != chain_sha
            or entry["dedupe_key"] != current_dedupe_key
        ):
            invalidated += 1
            continue
        expected_plan = ROUTING.plan(projection, state, now=entry["recorded_at"])
        if not _entry_matches_plan(entry, expected_plan):
            raise ReplayError(f"E_JOURNAL_PLAN_MISMATCH:{entry['sequence']}")
        state = ROUTING.record(
            state,
            expected_plan,
            outcome=entry["outcome"],
            at=entry["recorded_at"],
        )
        replayed += 1

    current_plan = ROUTING.plan(projection, state, now=observation_time)
    return {
        "schema": "die.operator-v2.recovery-result.v1",
        "status": "PASS",
        "projection": projection,
        "routing_state": state,
        "current_plan": current_plan,
        "replayed_entry_count": replayed,
        "invalidated_entry_count": invalidated,
        "journal_entry_count": len(journal["entries"]),
        "receipt_chain_sha256": chain_sha,
    }


def claim(
    snapshot: dict[str, Any],
    journal: dict[str, Any] | None = None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    journal = copy.deepcopy(journal or empty_journal())
    recovery = recover(snapshot, journal, now=now)
    if recovery["status"] != "PASS":
        return {
            "status": recovery["status"],
            "journal": journal,
            "routing_state": recovery["routing_state"],
            "routing_plan": recovery["current_plan"],
            "recovery": recovery,
        }

    plan = recovery["current_plan"]
    if (
        plan["status"] != "READY"
        or plan["authority_validation"]["status"] != "ALLOW"
        or plan["decision"] not in CLAIMABLE_DECISIONS
    ):
        return {
            "status": "SUPPRESSED",
            "journal": journal,
            "routing_state": recovery["routing_state"],
            "routing_plan": plan,
            "recovery": recovery,
        }

    recorded_at = now or snapshot["as_of"]
    outcome = "BLOCKED" if plan["decision"] == "BLOCK_STALLED" else "DISPATCHED"
    previous = journal["entries"][-1]["entry_sha256"] if journal["entries"] else ZERO_SHA256
    entry = {
        "sequence": len(journal["entries"]) + 1,
        "record_kind": "DISPATCH_CLAIM",
        "recorded_at": recorded_at,
        "recorded_before_side_effect": True,
        "mission_id": plan["mission_id"],
        "subject_id": plan["subject_id"],
        "snapshot_sha256": snapshot_sha256(snapshot),
        "receipt_chain_sha256": recovery["receipt_chain_sha256"],
        "dedupe_key": plan["dedupe_key"],
        "plan_sha256": _sha(plan),
        "projection_stage": plan["projection_stage"],
        "decision": plan["decision"],
        "action_type": plan["action_request"]["action_type"],
        "target_principal_id": plan["action_request"].get("target_principal_id"),
        "outcome": outcome,
        "follow_up_count": plan["follow_up_count"],
        "authority_status": plan["authority_validation"]["status"],
        "semantic_content_authored": False,
        "production_authority_granted": False,
        "previous_entry_sha256": previous,
    }
    entry["entry_sha256"] = _entry_hash(entry)
    journal["entries"].append(entry)
    validate_journal(journal)
    state = ROUTING.record(
        recovery["routing_state"],
        plan,
        outcome=outcome,
        at=recorded_at,
    )
    return {
        "status": "CLAIMED",
        "journal": journal,
        "routing_state": state,
        "routing_plan": plan,
        "claim_entry": entry,
        "recovery": recovery,
    }


def persist_claim(
    *,
    snapshot_path: Path,
    journal_path: Path,
    routing_state_path: Path,
    now: str | None = None,
    crash_after_journal_for_test: bool = False,
) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    journal = load_journal(journal_path)
    result = claim(snapshot, journal, now=now)

    if result["status"] == "CLAIMED":
        _atomic_json(journal_path, result["journal"])
        if crash_after_journal_for_test:
            raise InjectedCrash("E_INJECTED_CRASH_AFTER_JOURNAL")

    # The journal is authoritative. This projection is recoverable and may be
    # safely repaired even when a claim was suppressed or receipts were blocked.
    _atomic_json(routing_state_path, result["routing_state"])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "claim", "recover"):
        sub = subparsers.add_parser(command)
        sub.add_argument("snapshot")
        sub.add_argument("--journal", required=True)
        sub.add_argument("--routing-state")
        sub.add_argument("--now")
    args = parser.parse_args(argv)
    snapshot_path = Path(args.snapshot).resolve()
    journal_path = Path(args.journal).resolve()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    journal = load_journal(journal_path)

    if args.command in {"preview", "recover"}:
        result = recover(snapshot, journal, now=args.now)
        if args.command == "recover" and args.routing_state:
            _atomic_json(Path(args.routing_state).resolve(), result["routing_state"])
    else:
        if not args.routing_state:
            parser.error("claim requires --routing-state")
        result = persist_claim(
            snapshot_path=snapshot_path,
            journal_path=journal_path,
            routing_state_path=Path(args.routing_state).resolve(),
            now=args.now,
        )

    public = {key: value for key, value in result.items() if key != "journal"}
    print(json.dumps(public, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "CLAIMED", "SUPPRESSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
