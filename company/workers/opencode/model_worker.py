#!/usr/bin/env python3
"""WRK-001 bounded model-backed OpenCode Worker execution.

A job owns an isolated OpenCode runtime HOME/session DB/evidence directory.
Completion is based on durable OpenCode JSONL evidence (step_finish + optional
marker), not on the OpenCode process exiting; current OpenCode can keep runtime
cleanup/network handles alive after the assistant result is already complete.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
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


def _completion_from_jsonl(data: bytes, expected_marker: str | None) -> tuple[bool, bool, dict[str, Any] | None]:
    marker_ok = expected_marker is None
    finish: dict[str, Any] | None = None
    for raw in data.splitlines():
        try:
            event = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if event.get("type") == "text":
            text = str((event.get("part") or {}).get("text", ""))
            if expected_marker is not None and expected_marker in text:
                marker_ok = True
        if event.get("type") == "step_finish":
            part = event.get("part") or {}
            if part.get("reason") == "stop":
                finish = event
    return finish is not None and marker_ok, marker_ok, finish


def _stop_process(proc: subprocess.Popen[bytes]) -> str:
    if proc.poll() is not None:
        return "EXITED_NATURALLY"
    proc.terminate()
    try:
        proc.wait(timeout=5)
        return "TERMINATED_AFTER_COMPLETION"
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
        return "KILLED_AFTER_COMPLETION"


def execute(
    *, job: dict[str, Any], policy: dict[str, Any], workspace_root: Path,
    expected_marker: str | None = None, timeout_sec: int = 60,
) -> dict[str, Any]:
    validate_policy(policy)
    workspace = validate_job(job, workspace_root)
    workspace.mkdir(parents=True, exist_ok=True)
    binary = Path(policy["binary"])
    config_path = Path(policy["config_path"])
    if not binary.is_file() or not config_path.is_file():
        return {"schema": RECEIPT_SCHEMA, "status": "BLOCKED_RUNTIME", "task_id": job.get("task_id"), "reason": "binary_or_config_missing"}
    validate_runtime_config(config_path)

    prompt = str(job["goal"]).strip()
    prompt_hash = sha256_bytes(prompt.encode("utf-8"))
    runtime_home = workspace / ".opencode-runtime-home"
    runtime_home.mkdir(parents=True, exist_ok=True)
    try:
        runtime_home.chmod(0o700)
    except OSError:
        pass
    runtime_config = runtime_home / ".config" / "opencode" / "opencode.jsonc"
    runtime_config.parent.mkdir(parents=True, exist_ok=True)
    config_bytes = config_path.read_bytes()
    runtime_config.write_bytes(config_bytes)
    try:
        runtime_config.chmod(0o600)
    except OSError:
        pass
    if runtime_config.read_bytes() != config_bytes:
        raise ModelWorkerError("E_RUNTIME_CONFIG_COPY")

    env = os.environ.copy()
    env.update({
        "HOME": str(runtime_home),
        "XDG_CONFIG_HOME": str(runtime_home / ".config"),
        "XDG_CACHE_HOME": str(runtime_home / ".cache"),
        "OPENCODE_CONFIG": str(runtime_config),
        "NO_COLOR": "1",
    })
    argv = [str(binary), "run", "--pure", "--format", "json", "--model", MODEL, prompt]
    evidence_dir = workspace / ".worker-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = evidence_dir / "opencode.stdout.jsonl"
    stderr_path = evidence_dir / "opencode.stderr.log"
    started = time.monotonic()
    completion_observed = False
    marker_ok = expected_marker is None
    finish_event: dict[str, Any] | None = None
    cleanup = "NOT_STARTED"

    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        proc = subprocess.Popen(argv, cwd=workspace, env=env, stdin=subprocess.DEVNULL, stdout=stdout_handle, stderr=stderr_handle)
        while time.monotonic() - started < timeout_sec:
            stdout_handle.flush()
            data = stdout_path.read_bytes() if stdout_path.exists() else b""
            completion_observed, marker_ok, finish_event = _completion_from_jsonl(data, expected_marker)
            if completion_observed:
                cleanup = _stop_process(proc)
                break
            if proc.poll() is not None:
                cleanup = "EXITED_NATURALLY"
                break
            time.sleep(0.1)
        else:
            cleanup = _stop_process(proc)

    stdout = stdout_path.read_bytes() if stdout_path.exists() else b""
    stderr = stderr_path.read_bytes() if stderr_path.exists() else b""
    completion_observed, marker_ok, finish_event = _completion_from_jsonl(stdout, expected_marker)
    duration_ms = int((time.monotonic() - started) * 1000)
    returncode = proc.poll()

    if not completion_observed:
        return {
            "schema": RECEIPT_SCHEMA, "status": "BLOCKED_RUNTIME", "task_id": job.get("task_id"),
            "provider_id": "opencode", "model": MODEL, "cost_policy": "ZERO_USD_ONLY",
            "paid_fallback_used": False, "prompt_sha256": prompt_hash,
            "reason": "model_completion_not_observed",
            "runtime_home": str(runtime_home), "runtime_config_sha256": sha256_bytes(config_bytes),
            "stdout_sha256": sha256_bytes(stdout), "stdout_bytes": len(stdout),
            "stderr_sha256": sha256_bytes(stderr), "stderr_bytes": len(stderr),
            "returncode_after_cleanup": returncode, "process_cleanup": cleanup, "duration_ms": duration_ms,
            "completion_event_observed": False, "expected_marker_verified": marker_ok,
            "evidence_refs": {"stdout": str(stdout_path), "stderr": str(stderr_path)},
            "authority_boundary": {"semantic_authority_expanded": False, "submission_authorized": False, "spend_authorized": False},
        }

    finish_part = (finish_event or {}).get("part") or {}
    tokens = finish_part.get("tokens") or {}
    cost = finish_part.get("cost")
    cost_zero = cost in (0, 0.0, None)
    status = "PASS" if marker_ok and cost_zero else "FAILED_MODEL_EXECUTION"
    return {
        "schema": RECEIPT_SCHEMA,
        "status": status,
        "task_id": job.get("task_id"),
        "provider_id": "opencode",
        "model": MODEL,
        "cost_policy": "ZERO_USD_ONLY",
        "observed_cost": cost,
        "paid_fallback_used": False,
        "prompt_sha256": prompt_hash,
        "stdout_sha256": sha256_bytes(stdout),
        "stdout_bytes": len(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stderr_bytes": len(stderr),
        "returncode_after_cleanup": returncode,
        "expected_marker_verified": marker_ok,
        "completion_event_observed": True,
        "completion_reason": finish_part.get("reason"),
        "tokens": tokens,
        "duration_ms": duration_ms,
        "process_cleanup": cleanup,
        "runtime_home": str(runtime_home),
        "runtime_config_sha256": sha256_bytes(config_bytes),
        "evidence_refs": {"stdout": str(stdout_path), "stderr": str(stderr_path)},
        "authority_boundary": {"semantic_authority_expanded": False, "submission_authorized": False, "spend_authorized": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--workspace-root", default="/var/lib/die/workspaces")
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--expected-marker")
    ap.add_argument("--timeout-sec", type=int, default=60)
    args = ap.parse_args()
    receipt = execute(
        job=load_json(Path(args.job)), policy=load_json(Path(args.policy)),
        workspace_root=Path(args.workspace_root), expected_marker=args.expected_marker,
        timeout_sec=args.timeout_sec,
    )
    Path(args.receipt).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "model": receipt.get("model")}))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
