#!/usr/bin/env python3
"""WRK-001 bounded model-backed OpenCode Worker execution.

Uses the existing Worker job envelope and an explicit zero-cost model policy.
The runner never falls back to another model/provider and emits a fail-closed
receipt on timeout, unavailable model, policy mismatch, or missing evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

POLICY_SCHEMA = "die.worker.model-policy.v1"
RECEIPT_SCHEMA = "die.worker.model-execution-receipt.v1"
MODEL = "opencode/muse-spark-1.2-contributor-free"


class ModelWorkerError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ModelWorkerError("E_JSON_OBJECT")
    return value


def validate_policy(policy: dict[str, Any]) -> None:
    required = {
        "schema", "provider_id", "model", "small_model", "cost_policy",
        "free_badge_required", "paid_fallback_allowed", "network_policy",
        "worker_home", "config_path", "binary", "semantic_authority",
    }
    if set(policy) != required or policy.get("schema") != POLICY_SCHEMA:
        raise ModelWorkerError("E_POLICY_SHAPE")
    if policy["provider_id"] != "opencode" or policy["model"] != MODEL or policy["small_model"] != MODEL:
        raise ModelWorkerError("E_MODEL_NOT_PINNED")
    if policy["cost_policy"] != "ZERO_USD_ONLY" or policy["free_badge_required"] is not True:
        raise ModelWorkerError("E_COST_POLICY")
    if policy["paid_fallback_allowed"] is not False:
        raise ModelWorkerError("E_PAID_FALLBACK")
    if policy["network_policy"] != "OPENCODE_PROVIDER_ONLY":
        raise ModelWorkerError("E_NETWORK_POLICY")
    if policy["semantic_authority"] != "BOUNDED_EXECUTION_ONLY":
        raise ModelWorkerError("E_AUTHORITY_POLICY")


def validate_runtime_config(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("model") != MODEL or config.get("small_model") != MODEL:
        raise ModelWorkerError("E_RUNTIME_MODEL_MISMATCH")
    provider = config.get("provider", {}).get("opencode", {})
    if provider.get("whitelist") != ["muse-spark-1.2-contributor-free"]:
        raise ModelWorkerError("E_RUNTIME_WHITELIST")
    return config


def validate_job(job: dict[str, Any], workspace_root: Path) -> Path:
    if job.get("schema") != "die.worker-job-envelope.v1" or job.get("executor") != "opencode":
        raise ModelWorkerError("E_JOB_SCHEMA")
    workspace = Path(str(job.get("workspace", ""))).resolve()
    root = workspace_root.resolve()
    try:
        workspace.relative_to(root)
    except ValueError as exc:
        raise ModelWorkerError("E_WORKSPACE_ESCAPE") from exc
    constraints = job.get("constraints")
    if not isinstance(constraints, dict) or constraints.get("network") != "allowlist":
        raise ModelWorkerError("E_NETWORK_NOT_GOVERNED")
    forbidden = set(constraints.get("forbidden") or [])
    if "credentials" not in forbidden or "market submission" not in forbidden or "spawning workers" not in forbidden:
        raise ModelWorkerError("E_REQUIRED_PROHIBITIONS")
    if not str(job.get("goal", "")).strip():
        raise ModelWorkerError("E_GOAL")
    return workspace


def execute(*, job: dict[str, Any], policy: dict[str, Any], workspace_root: Path, expected_marker: str | None = None, timeout_sec: int = 60) -> dict[str, Any]:
    validate_policy(policy)
    workspace = validate_job(job, workspace_root)
    workspace.mkdir(parents=True, exist_ok=True)
    binary = Path(policy["binary"])
    worker_home = Path(policy["worker_home"])
    config_path = Path(policy["config_path"])
    if not binary.is_file() or not config_path.is_file():
        return {"schema": RECEIPT_SCHEMA, "status": "BLOCKED_RUNTIME", "task_id": job.get("task_id"), "reason": "binary_or_config_missing"}
    validate_runtime_config(config_path)

    prompt = str(job["goal"]).strip()
    prompt_hash = sha256_bytes(prompt.encode("utf-8"))
    env = os.environ.copy()
    env.update({
        "HOME": str(worker_home),
        "XDG_CONFIG_HOME": str(worker_home / ".config"),
        "XDG_CACHE_HOME": str(worker_home / ".cache"),
        "OPENCODE_CONFIG": str(config_path),
        "NO_COLOR": "1",
    })
    argv = [str(binary), "run", "--pure", "--format", "json", "--model", MODEL, prompt]
    try:
        completed = subprocess.run(argv, cwd=workspace, env=env, capture_output=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired:
        return {
            "schema": RECEIPT_SCHEMA, "status": "BLOCKED_RUNTIME", "task_id": job.get("task_id"),
            "provider_id": "opencode", "model": MODEL, "cost_policy": "ZERO_USD_ONLY",
            "paid_fallback_used": False, "prompt_sha256": prompt_hash, "reason": "model_call_timeout",
            "authority_boundary": {"semantic_authority_expanded": False, "submission_authorized": False, "spend_authorized": False},
        }
    stdout = completed.stdout or b""
    stderr = completed.stderr or b""
    marker_ok = expected_marker is None or expected_marker.encode("utf-8") in stdout
    status = "PASS" if completed.returncode == 0 and stdout and marker_ok else "FAILED_MODEL_EXECUTION"
    return {
        "schema": RECEIPT_SCHEMA,
        "status": status,
        "task_id": job.get("task_id"),
        "provider_id": "opencode",
        "model": MODEL,
        "cost_policy": "ZERO_USD_ONLY",
        "paid_fallback_used": False,
        "prompt_sha256": prompt_hash,
        "stdout_sha256": sha256_bytes(stdout),
        "stdout_bytes": len(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stderr_bytes": len(stderr),
        "returncode": completed.returncode,
        "expected_marker_verified": marker_ok,
        "authority_boundary": {"semantic_authority_expanded": False, "submission_authorized": False, "spend_authorized": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--workspace-root", default="/var/lib/die/workspaces")
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--expected-marker")
    args = ap.parse_args()
    receipt = execute(job=load_json(Path(args.job)), policy=load_json(Path(args.policy)), workspace_root=Path(args.workspace_root), expected_marker=args.expected_marker)
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "model": receipt.get("model")}))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
