from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[2]
POOL_PATH = ROOT / "company" / "die-agents" / "hermes" / "worker_pool.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


POOL = load("wrk001_pool_test", POOL_PATH)


def make_job(task_id: str, workspace: Path) -> dict:
    return {
        "schema": "die.worker-job-envelope.v1",
        "task_id": task_id,
        "mission_id": "M-001",
        "executor": "opencode",
        "goal": f"Return exactly WRK001_POOL_OK_{task_id}",
        "context": "Synthetic bounded parallelism proof.",
        "workspace": str(workspace),
        "constraints": {
            "time_budget_min": 5,
            "allowed_paths": [str(workspace)],
            "network": "allowlist",
            "forbidden": ["credentials", "market submission", "spawning workers", "writes outside workspace", "destructive operations"],
        },
        "acceptance_criteria": [{"id": "AC-1", "statement": "marker", "verify_with": "receipt"}],
        "handoff": {"kind": "muxia_job", "provider_id": "chatgpt", "required_capability": "image_generation", "profile_selector": None, "timeout_ms": 60000},
    }


def test_pool_rejects_duplicate_task_or_workspace(tmp_path: Path) -> None:
    w = tmp_path / "w"
    j1 = make_job("J1", w)
    j2 = make_job("J1", tmp_path / "w2")
    with pytest.raises(POOL.WorkerPoolError, match="E_DUPLICATE_TASK_ID"):
        POOL.validate_manifest({"schema": POOL.SCHEMA, "batch_id": "B1", "jobs": [j1, j2]}, 2)
    j2 = make_job("J2", w)
    with pytest.raises(POOL.WorkerPoolError, match="E_DUPLICATE_WORKSPACE"):
        POOL.validate_manifest({"schema": POOL.SCHEMA, "batch_id": "B1", "jobs": [j1, j2]}, 2)


def test_pool_enforces_hard_parallel_ceiling(tmp_path: Path) -> None:
    manifest = {"schema": POOL.SCHEMA, "batch_id": "B1", "jobs": [make_job("J1", tmp_path / "w1")]}
    with pytest.raises(POOL.WorkerPoolError, match="E_PARALLELISM_LIMIT"):
        POOL.validate_manifest(manifest, POOL.HARD_MAX_WORKERS + 1)


def test_pool_runs_jobs_with_unique_runtime_homes_and_durable_receipts(tmp_path: Path) -> None:
    fake = tmp_path / "fake_model_worker.py"
    fake.write_text(textwrap.dedent('''
        from pathlib import Path
        def validate_policy(policy):
            assert policy["model"] == "opencode/muse-spark-1.2-contributor-free"
        def execute(*, job, policy, workspace_root, expected_marker=None, timeout_sec=90):
            workspace = Path(job["workspace"])
            runtime = workspace / ".opencode-runtime-home"
            evidence = workspace / ".worker-evidence"
            runtime.mkdir(parents=True, exist_ok=True)
            evidence.mkdir(parents=True, exist_ok=True)
            out = evidence / "opencode.stdout.jsonl"
            out.write_text(expected_marker or "ok")
            return {
                "schema": "die.worker.model-execution-receipt.v1",
                "status": "PASS",
                "task_id": job["task_id"],
                "provider_id": "opencode",
                "model": policy["model"],
                "cost_policy": "ZERO_USD_ONLY",
                "paid_fallback_used": False,
                "stdout_sha256": job["task_id"] * 8,
                "stdout_bytes": out.stat().st_size,
                "expected_marker_verified": True,
                "runtime_home": str(runtime),
            }
    '''), encoding="utf-8")
    root = tmp_path / "workspaces"
    jobs = [make_job(f"J{i}", root / f"J{i}") for i in range(1, 5)]
    policy = {"model": "opencode/muse-spark-1.2-contributor-free", "provider_id": "opencode", "cost_policy": "ZERO_USD_ONLY"}
    receipt = POOL.execute_pool(
        manifest={"schema": POOL.SCHEMA, "batch_id": "B1", "jobs": jobs},
        policy=policy,
        workspace_root=root,
        model_worker_path=fake,
        max_workers=4,
        expected_marker_prefix="WRK001_POOL_OK_",
    )
    assert receipt["status"] == "PASS"
    assert receipt["requested_jobs"] == 4
    assert receipt["peak_active_workers"] >= 1
    assert receipt["checks"]["all_jobs_passed"] is True
    assert receipt["checks"]["unique_runtime_home_per_job"] is True
    assert receipt["checks"]["durable_receipt_per_job"] is True
    assert receipt["checks"]["no_paid_fallback"] is True
    assert receipt["authority_boundary"]["workers_may_spawn_workers"] is False
