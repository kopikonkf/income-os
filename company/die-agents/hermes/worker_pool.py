#!/usr/bin/env python3
"""Hermes-owned bounded parallel dispatcher for model-backed Worker-001 jobs.

Hermes remains the sole delegator. The pool does not create nested agents; it
runs multiple independent Worker-001 job executions concurrently. Each job must
have a unique task_id and workspace, and model_worker creates a per-job OpenCode
runtime HOME/evidence directory so TUI/session/database state is never shared.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import threading
from typing import Any

SCHEMA = "die.hermes.worker-pool-request.v1"
RECEIPT_SCHEMA = "die.hermes.worker-pool-receipt.v1"
DEFAULT_MAX_WORKERS = 4
HARD_MAX_WORKERS = 4


class WorkerPoolError(RuntimeError):
    pass


def _load_model_worker(path: Path):
    spec = importlib.util.spec_from_file_location("die_model_worker_pool", path)
    if spec is None or spec.loader is None:
        raise WorkerPoolError("E_MODEL_WORKER_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkerPoolError(f"E_JSON_OBJECT:{path}")
    return value


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_manifest(manifest: dict[str, Any], max_workers: int) -> list[dict[str, Any]]:
    if manifest.get("schema") != SCHEMA or set(manifest) != {"schema", "batch_id", "jobs"}:
        raise WorkerPoolError("E_MANIFEST_SHAPE")
    if not str(manifest.get("batch_id", "")).strip():
        raise WorkerPoolError("E_BATCH_ID")
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise WorkerPoolError("E_JOBS")
    if max_workers < 1 or max_workers > HARD_MAX_WORKERS:
        raise WorkerPoolError("E_PARALLELISM_LIMIT")
    task_ids: set[str] = set()
    workspaces: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise WorkerPoolError("E_JOB_OBJECT")
        task_id = str(job.get("task_id", ""))
        workspace = str(job.get("workspace", ""))
        if not task_id or task_id in task_ids:
            raise WorkerPoolError("E_DUPLICATE_TASK_ID")
        if not workspace or workspace in workspaces:
            raise WorkerPoolError("E_DUPLICATE_WORKSPACE")
        task_ids.add(task_id)
        workspaces.add(workspace)
    return jobs


def execute_pool(
    *, manifest: dict[str, Any], policy: dict[str, Any], workspace_root: Path,
    model_worker_path: Path, max_workers: int = DEFAULT_MAX_WORKERS,
    expected_marker_prefix: str | None = None, timeout_sec: int = 90,
) -> dict[str, Any]:
    jobs = validate_manifest(manifest, max_workers)
    model_worker = _load_model_worker(model_worker_path)
    model_worker.validate_policy(policy)

    lock = threading.Lock()
    active = 0
    peak_active = 0
    started_at = dt.datetime.now(dt.timezone.utc)

    def run_one(job: dict[str, Any]) -> dict[str, Any]:
        nonlocal active, peak_active
        with lock:
            active += 1
            peak_active = max(peak_active, active)
        try:
            marker = None
            if expected_marker_prefix is not None:
                marker = f"{expected_marker_prefix}{job['task_id']}"
            receipt = model_worker.execute(
                job=job,
                policy=policy,
                workspace_root=workspace_root,
                expected_marker=marker,
                timeout_sec=timeout_sec,
            )
            workspace = Path(job["workspace"])
            receipt_path = workspace / ".worker-evidence" / "model-execution-receipt.json"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            return {
                "task_id": job["task_id"],
                "status": receipt["status"],
                "receipt_path": str(receipt_path),
                "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                "runtime_home": receipt.get("runtime_home"),
                "stdout_sha256": receipt.get("stdout_sha256"),
                "stdout_bytes": receipt.get("stdout_bytes", 0),
                "paid_fallback_used": receipt.get("paid_fallback_used"),
                "expected_marker_verified": receipt.get("expected_marker_verified"),
            }
        finally:
            with lock:
                active -= 1

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="worker001") as pool:
        futures = {pool.submit(run_one, job): job["task_id"] for job in jobs}
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                rows.append(future.result())
            except Exception as exc:
                rows.append({"task_id": task_id, "status": "FAILED_POOL_EXECUTION", "error": type(exc).__name__})

    rows.sort(key=lambda row: row["task_id"])
    finished_at = dt.datetime.now(dt.timezone.utc)
    statuses = [row["status"] for row in rows]
    runtime_homes = [row.get("runtime_home") for row in rows if row.get("runtime_home")]
    stdout_hashes = [row.get("stdout_sha256") for row in rows if row.get("stdout_sha256")]
    all_pass = len(rows) == len(jobs) and all(status == "PASS" for status in statuses)
    isolation_pass = len(runtime_homes) == len(set(runtime_homes)) == len(jobs)
    evidence_pass = all(row.get("receipt_sha256") for row in rows)
    no_paid_fallback = all(row.get("paid_fallback_used") is False for row in rows if row.get("status") == "PASS")
    marker_pass = all(row.get("expected_marker_verified") is True for row in rows if row.get("status") == "PASS") if expected_marker_prefix else True

    return {
        "schema": RECEIPT_SCHEMA,
        "batch_id": manifest["batch_id"],
        "status": "PASS" if all_pass and isolation_pass and evidence_pass and no_paid_fallback and marker_pass else "FAIL",
        "manifest_sha256": canonical_sha(manifest),
        "model": policy["model"],
        "provider_id": policy["provider_id"],
        "cost_policy": policy["cost_policy"],
        "requested_jobs": len(jobs),
        "configured_max_workers": max_workers,
        "hard_max_workers": HARD_MAX_WORKERS,
        "peak_active_workers": peak_active,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "checks": {
            "all_jobs_passed": all_pass,
            "unique_runtime_home_per_job": isolation_pass,
            "durable_receipt_per_job": evidence_pass,
            "no_paid_fallback": no_paid_fallback,
            "expected_markers_verified": marker_pass,
            "actual_parallelism_observed": peak_active >= min(len(jobs), max_workers),
        },
        "jobs": rows,
        "authority_boundary": {
            "delegator": "hermes-operator",
            "workers_may_spawn_workers": False,
            "semantic_authority_expanded": False,
            "submission_authorized": False,
            "spend_authorized": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--model-worker", required=True)
    ap.add_argument("--workspace-root", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    ap.add_argument("--expected-marker-prefix")
    ap.add_argument("--timeout-sec", type=int, default=90)
    args = ap.parse_args()
    receipt = execute_pool(
        manifest=load_json(Path(args.manifest)),
        policy=load_json(Path(args.policy)),
        workspace_root=Path(args.workspace_root),
        model_worker_path=Path(args.model_worker),
        max_workers=args.max_workers,
        expected_marker_prefix=args.expected_marker_prefix,
        timeout_sec=args.timeout_sec,
    )
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "jobs": receipt["requested_jobs"], "peak": receipt["peak_active_workers"]}))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
