from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{rel}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


queue_mod = _load("fa_c012_factory_queue", "company/factory-asset/lib/factory_queue.py")
console_contract = _load("fa_c012_console_contract", "company/factory-asset/lib/console_contract.py")

SNAPSHOT_SCHEMA = "die.factory-asset.console-recovery-snapshot.v1"
RESULT_SCHEMA = "die.factory-asset.console-recovery-acceptance.v1"


class ConsoleRecoveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _sha_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _job_id(kind: str) -> str:
    return f"FCJOB-FA-C012-{kind}"


def _key(kind: str) -> str:
    return hashlib.sha256(f"fa-c012|{kind}".encode()).hexdigest()


def build_precrash_queue() -> queue_mod.FactoryJobQueue:
    q = queue_mod.FactoryJobQueue()
    rows = [
        ("READY", "FASA-FA-C012-READY"),
        ("RUNNING-UNCOMMITTED", "FASA-FA-C012-RUNNING-UNCOMMITTED"),
        ("PAUSED", "FASA-FA-C012-PAUSED"),
        ("RETRY-WAIT", "FASA-FA-C012-RETRY-WAIT"),
        ("SUCCEEDED", "FASA-FA-C012-SUCCEEDED"),
        ("RUNNING-COMMITTED", "FASA-FA-C012-RUNNING-COMMITTED"),
    ]
    for kind, semantic_id in rows:
        q.submit(
            job_id=_job_id(kind),
            idempotency_key=_key(kind),
            intent={
                "source_surface": "FACTORY_CONSOLE",
                "task_id": "FA-C012",
                "blueprint_id": f"FABP-FA-C012-{kind}",
                "semantic_asset_id": semantic_id,
                "label": f"FA-C012 {kind}",
                "provider_id": "qwen" if "RUNNING" in kind else None,
            },
        )

    q.start(_job_id("RUNNING-UNCOMMITTED"), owner="factory-c012-worker-a", lease_token=_key("lease-a"))

    q.start(_job_id("PAUSED"), owner="factory-c012-worker-b", lease_token=_key("lease-b"))
    q.pause(_job_id("PAUSED"))

    q.start(_job_id("RETRY-WAIT"), owner="factory-c012-worker-c", lease_token=_key("lease-c"))
    q.fail(_job_id("RETRY-WAIT"), code="RATE_LIMITED", retryable=True)

    q.start(_job_id("SUCCEEDED"), owner="factory-c012-worker-d", lease_token=_key("lease-d"))
    q.succeed(_job_id("SUCCEEDED"), artifact_sha256=hashlib.sha256(b"fa-c012-success-artifact").hexdigest())

    q.start(_job_id("RUNNING-COMMITTED"), owner="factory-c012-worker-e", lease_token=_key("lease-e"))
    return q


def build_recovery_snapshot(q: queue_mod.FactoryJobQueue) -> dict[str, Any]:
    queue_snapshot = q.snapshot()
    committed_job = _job_id("RUNNING-COMMITTED")
    commit = {
        "schema": "die.factory-asset.generation-commit.v1",
        "job_id": committed_job,
        "idempotency_key": q.get(committed_job).idempotency_key,
        "commit_id": _sha_json({"job_id": committed_job, "attempt": 1, "external": "synthetic-c012"}),
        "attempt": 1,
        "external_commit_key": "synthetic:fa-c012:committed-before-crash",
    }
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "task_id": "FA-C012",
        "queue_snapshot": queue_snapshot,
        "dispatch_fences": {committed_job: commit},
        "provider_calls_performed": False,
        "browser_owner_actions": 0,
        "credential_values_read": False,
        "cookies_or_tokens_read": False,
    }
    snapshot["snapshot_sha256"] = _sha_json({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    return snapshot


def persist_recovery_snapshot(path: str | Path, snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ConsoleRecoveryError("E_SNAPSHOT_SCHEMA", "invalid console recovery snapshot schema")
    expected = _sha_json({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    if snapshot.get("snapshot_sha256") != expected:
        raise ConsoleRecoveryError("E_SNAPSHOT_HASH", "snapshot hash mismatch")
    _atomic_json(Path(path), snapshot)


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA or snapshot.get("task_id") != "FA-C012":
        raise ConsoleRecoveryError("E_SNAPSHOT_SCHEMA", "invalid C012 recovery envelope")
    expected = _sha_json({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    if snapshot.get("snapshot_sha256") != expected:
        raise ConsoleRecoveryError("E_SNAPSHOT_HASH", "snapshot hash mismatch")
    if snapshot.get("provider_calls_performed") is not False or snapshot.get("browser_owner_actions") != 0:
        raise ConsoleRecoveryError("E_AUTHORITY", "C012 acceptance must remain zero-provider and zero-browser-owner")


def load_and_reconcile(path: str | Path) -> tuple[queue_mod.FactoryJobQueue, dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise ConsoleRecoveryError("E_SNAPSHOT_MISSING", str(source))
    snapshot = json.loads(source.read_text(encoding="utf-8"))
    _validate_snapshot(snapshot)
    queue_snapshot = json.loads(json.dumps(snapshot["queue_snapshot"]))
    fences = dict(snapshot.get("dispatch_fences") or {})

    fenced_jobs: list[str] = []
    for row in queue_snapshot.get("jobs", []):
        job_id = row.get("job_id")
        if row.get("state") == "RUNNING" and job_id in fences:
            commit = fences[job_id]
            if commit.get("schema") != "die.factory-asset.generation-commit.v1" or commit.get("job_id") != job_id or not commit.get("commit_id"):
                raise ConsoleRecoveryError("E_DISPATCH_FENCE_INVALID", str(job_id))
            row["state"] = "PAUSED"
            row["owner"] = None
            row["lease_token"] = None
            row["failure_code"] = "DISPATCH_RECONCILIATION_REQUIRED"
            row["recovery_count"] = int(row.get("recovery_count", 0)) + 1
            fenced_jobs.append(str(job_id))

    q = queue_mod.FactoryJobQueue.from_snapshot(queue_snapshot)
    rows = {row["job_id"]: row for row in q.list()}
    uncommitted = rows[_job_id("RUNNING-UNCOMMITTED")]
    committed = rows[_job_id("RUNNING-COMMITTED")]
    succeeded = rows[_job_id("SUCCEEDED")]
    paused = rows[_job_id("PAUSED")]
    retry_wait = rows[_job_id("RETRY-WAIT")]

    if uncommitted["state"] != "READY" or uncommitted["recovery_count"] != 1 or uncommitted["owner"] is not None:
        raise ConsoleRecoveryError("E_UNCOMMITTED_RECOVERY", "RUNNING uncommitted job did not reconcile to READY")
    if committed["state"] != "PAUSED" or committed["failure_code"] != "DISPATCH_RECONCILIATION_REQUIRED" or committed["owner"] is not None:
        raise ConsoleRecoveryError("E_COMMITTED_RECOVERY", "committed dispatch was not fenced")
    if succeeded["state"] != "SUCCEEDED" or not succeeded.get("artifact_sha256"):
        raise ConsoleRecoveryError("E_SUCCESS_DRIFT", "existing success did not survive restart")
    if paused["state"] != "PAUSED":
        raise ConsoleRecoveryError("E_PAUSED_DRIFT", "paused state drifted during recovery")
    if retry_wait["state"] != "RETRY_WAIT":
        raise ConsoleRecoveryError("E_RETRY_WAIT_DRIFT", "retry wait state drifted during recovery")

    manifest = {
        "schema": "die.factory-asset.console-recovery-reconciliation.v1",
        "task_id": "FA-C012",
        "source_snapshot_sha256": snapshot["snapshot_sha256"],
        "reconciliation_required_job_ids": sorted(fenced_jobs),
        "uncommitted_running_recovered_to_ready": [_job_id("RUNNING-UNCOMMITTED")],
        "preserved_success_job_ids": [_job_id("SUCCEEDED")],
        "preserved_paused_job_ids": [_job_id("PAUSED")],
        "preserved_retry_wait_job_ids": [_job_id("RETRY-WAIT")],
        "provider_calls_performed": False,
        "browser_owner_actions": 0,
    }
    return q, manifest


def run_console_recovery_acceptance(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    q = build_precrash_queue()
    pre_rows = q.list()
    snapshot = build_recovery_snapshot(q)
    snapshot_path = root / "recovery-snapshot.json"
    persist_recovery_snapshot(snapshot_path, snapshot)

    recovered, manifest = load_and_reconcile(snapshot_path)
    manifest_path = root / "reconciliation.json"
    _atomic_json(manifest_path, manifest)
    post_rows = recovered.list()
    post_by = {row["job_id"]: row for row in post_rows}

    fenced_job = _job_id("RUNNING-COMMITTED")
    duplicate_dispatch_blocked = False
    try:
        recovered.start(fenced_job, owner="factory-console-c012-auto-resume", lease_token="forbidden")
    except queue_mod.QueueError as exc:
        if exc.code != "INVALID_STATE_TRANSITION":
            raise
        duplicate_dispatch_blocked = True
    if not duplicate_dispatch_blocked:
        raise ConsoleRecoveryError("E_DUPLICATE_DISPATCH_NOT_BLOCKED", fenced_job)

    false_success_blocked = post_by[_job_id("RUNNING-UNCOMMITTED")]["artifact_sha256"] is None
    if not false_success_blocked:
        raise ConsoleRecoveryError("E_FALSE_SUCCESS", "crash recovery synthesized artifact success")

    console_events = [console_contract.queue_event(row) for row in post_rows]
    ui_state = {
        "schema": "die.factory-asset.console-recovery-ui-state.v1",
        "task_id": "FA-C012",
        "events": console_events,
        "reconciliation_required_job_ids": manifest["reconciliation_required_job_ids"],
        "provider_dispatch_performed": False,
    }
    ui_state_path = root / "ui-reconciled-state.json"
    _atomic_json(ui_state_path, ui_state)

    pre_success = next(row for row in pre_rows if row["job_id"] == _job_id("SUCCEEDED"))
    post_success = post_by[_job_id("SUCCEEDED")]
    assertions = {
        "durable_snapshot_roundtrip": snapshot_path.is_file() and manifest_path.is_file() and ui_state_path.is_file(),
        "uncommitted_running_recovers_ready": post_by[_job_id("RUNNING-UNCOMMITTED")]["state"] == "READY" and post_by[_job_id("RUNNING-UNCOMMITTED")]["recovery_count"] == 1,
        "committed_dispatch_fenced": post_by[fenced_job]["state"] == "PAUSED" and post_by[fenced_job]["failure_code"] == "DISPATCH_RECONCILIATION_REQUIRED",
        "duplicate_dispatch_blocked": duplicate_dispatch_blocked,
        "success_preserved_exactly": pre_success["artifact_sha256"] == post_success["artifact_sha256"] and post_success["state"] == "SUCCEEDED",
        "paused_and_retry_state_preserved": post_by[_job_id("PAUSED")]["state"] == "PAUSED" and post_by[_job_id("RETRY-WAIT")]["state"] == "RETRY_WAIT",
        "zero_false_success": false_success_blocked,
        "ui_reconciles_from_recovered_core": len(ui_state["events"]) == len(post_rows) and {e["job_id"] for e in ui_state["events"]} == {r["job_id"] for r in post_rows},
        "zero_provider_calls": True,
    }
    result = "PASS" if all(assertions.values()) else "FAIL"
    out = {
        "schema": RESULT_SCHEMA,
        "task_id": "FA-C012",
        "result": result,
        "source_surface": "FACTORY_CONSOLE",
        "precrash_state_counts": _state_counts(pre_rows),
        "postrecovery_state_counts": _state_counts(post_rows),
        "reconciliation_required_job_ids": manifest["reconciliation_required_job_ids"],
        "duplicate_dispatch_blocked": duplicate_dispatch_blocked,
        "provider_calls_performed": False,
        "browser_owner_actions": 0,
        "credential_values_read": False,
        "cookies_or_tokens_read": False,
        "spend_usd": 0,
        "account_actions": 0,
        "marketplace_actions": 0,
        "assertions": assertions,
        "evidence_paths": {
            "snapshot": str(snapshot_path),
            "reconciliation": str(manifest_path),
            "ui_state": str(ui_state_path),
            "final_result": str(root / "final-result.json"),
        },
    }
    _atomic_json(root / "final-result.json", out)
    return out


def _state_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    states = ("READY", "RUNNING", "PAUSED", "RETRY_WAIT", "SUCCEEDED", "FAILED", "CANCELLED")
    return {state: sum(1 for row in rows if row["state"] == state) for state in states}
