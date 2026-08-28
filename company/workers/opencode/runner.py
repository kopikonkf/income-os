#!/usr/bin/env python3
"""Bounded OpenCode Worker-001 runner.

DIE-202 intentionally does not make model/provider calls. The runner validates a
Hermes job envelope, proves the pinned OpenCode executable is present, and
prepares a MUXIA job request inside the assigned workspace. Real model-backed
OpenCode execution requires a separately approved provider/cost policy.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
REQUIRED_FORBIDDEN = {
    "credentials",
    "market submission",
    "spawning workers",
    "writes outside workspace",
    "destructive operations",
}


def fail(code: str, message: str) -> None:
    raise ValueError(f"{code}:{message}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail("E_JOB_SHAPE", "job must be an object")
    return value


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_job(job: dict[str, Any], workspace_root: Path) -> Path:
    allowed_top = {
        "schema", "task_id", "mission_id", "executor", "goal", "context",
        "workspace", "constraints", "acceptance_criteria", "handoff",
    }
    if set(job) != allowed_top:
        fail("E_JOB_FIELDS", f"unexpected/missing fields: {sorted(set(job) ^ allowed_top)}")
    if job["schema"] != "die.worker-job-envelope.v1":
        fail("E_SCHEMA", "unsupported worker job schema")
    for field in ("task_id", "mission_id"):
        if not isinstance(job[field], str) or not SAFE_ID.fullmatch(job[field]):
            fail("E_ID", field)
    if job["executor"] != "opencode":
        fail("E_EXECUTOR", "Worker-001 accepts executor=opencode only")
    if not isinstance(job["goal"], str) or not job["goal"].strip():
        fail("E_GOAL", "goal required")
    if not isinstance(job["context"], str) or len(job["context"]) > 12000:
        fail("E_CONTEXT", "context invalid/too large")

    workspace = Path(job["workspace"])
    if not workspace.is_absolute() or not inside(workspace_root, workspace):
        fail("E_WORKSPACE", "workspace must be absolute and inside DIE_WORKSPACES_ROOT")

    constraints = job["constraints"]
    if not isinstance(constraints, dict):
        fail("E_CONSTRAINTS", "constraints must be object")
    if set(constraints) != {"time_budget_min", "allowed_paths", "network", "forbidden"}:
        fail("E_CONSTRAINTS", "constraints fields mismatch")
    if not isinstance(constraints["time_budget_min"], int) or not (1 <= constraints["time_budget_min"] <= 240):
        fail("E_TIME_BUDGET", "invalid time budget")
    if constraints["network"] != "none":
        fail("E_NETWORK", "DIE-202 synthetic Worker-001 proof requires network=none")
    if not isinstance(constraints["allowed_paths"], list) or not constraints["allowed_paths"]:
        fail("E_ALLOWED_PATHS", "allowed_paths required")
    for raw in constraints["allowed_paths"]:
        p = Path(raw)
        if not p.is_absolute() or not inside(workspace, p):
            fail("E_ALLOWED_PATHS", f"outside workspace: {raw}")
    forbidden = set(constraints["forbidden"] if isinstance(constraints["forbidden"], list) else [])
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        fail("E_FORBIDDEN", "required prohibitions missing")

    criteria = job["acceptance_criteria"]
    if not isinstance(criteria, list) or not criteria:
        fail("E_ACCEPTANCE", "acceptance criteria required")
    seen = set()
    for row in criteria:
        if not isinstance(row, dict) or set(row) != {"id", "statement", "verify_with"}:
            fail("E_ACCEPTANCE", "criterion shape invalid")
        ident = row["id"]
        if not isinstance(ident, str) or not re.fullmatch(r"AC-[1-9][0-9]*", ident) or ident in seen:
            fail("E_ACCEPTANCE", "criterion id invalid/duplicate")
        seen.add(ident)
        if not str(row["statement"]).strip() or not str(row["verify_with"]).strip():
            fail("E_ACCEPTANCE", "criterion statement/verification missing")

    handoff = job["handoff"]
    expected = {"kind", "provider_id", "required_capability", "profile_selector", "timeout_ms"}
    if not isinstance(handoff, dict) or set(handoff) != expected or handoff["kind"] != "muxia_job":
        fail("E_HANDOFF", "MUXIA handoff required")
    if not SAFE_ID.fullmatch(str(handoff["provider_id"])):
        fail("E_HANDOFF", "provider_id invalid")
    if not str(handoff["required_capability"]).strip():
        fail("E_HANDOFF", "required_capability missing")
    selector = handoff["profile_selector"]
    if selector is not None and not SAFE_ID.fullmatch(str(selector)):
        fail("E_HANDOFF", "profile_selector invalid")
    if not isinstance(handoff["timeout_ms"], int) or not (1000 <= handoff["timeout_ms"] <= 3600000):
        fail("E_HANDOFF", "timeout invalid")
    return workspace.resolve()


def probe_opencode(binary: Path, worker_home: Path) -> dict[str, Any]:
    if not binary.is_file():
        fail("E_OPENCODE_MISSING", str(binary))
    worker_home.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(worker_home),
        "XDG_CONFIG_HOME": str(worker_home / ".config"),
        "XDG_CACHE_HOME": str(worker_home / ".cache"),
        "NO_COLOR": "1",
    }
    proc = subprocess.run(
        [str(binary), "--version"],
        cwd=str(worker_home),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        fail("E_OPENCODE_PROBE", (proc.stderr or proc.stdout).strip()[:500])
    version = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if not version:
        fail("E_OPENCODE_VERSION", "empty version")
    return {"binary": str(binary.resolve()), "version": version, "exit_code": proc.returncode}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--workspace-root", default=os.environ.get("DIE_WORKSPACES_ROOT", "/var/lib/die/workspaces"))
    parser.add_argument("--opencode-bin", default=os.environ.get("DIE_OPENCODE_BIN", "/opt/die/workers/opencode/bin/opencode"))
    parser.add_argument("--worker-home", default=os.environ.get("DIE_OPENCODE_HOME", "/var/lib/die/workers/opencode/home"))
    args = parser.parse_args()

    result_path = Path(args.result).resolve()
    try:
        job = load_json(Path(args.job).resolve())
        workspace_root = Path(args.workspace_root).resolve()
        workspace = validate_job(job, workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)
        if not inside(workspace, result_path):
            fail("E_RESULT_PATH", "result must be inside workspace")
        probe = probe_opencode(Path(args.opencode_bin), Path(args.worker_home))

        probe_path = workspace / "opencode-probe.json"
        probe_path.write_text(json.dumps({"schema": "die.opencode-probe.v1", **probe}, indent=2) + "\n", encoding="utf-8")
        handoff = job["handoff"]
        muxia_request = {
            "schema": "die.muxia-job-request.v1",
            "source_task_id": job["task_id"],
            "jobId": f"{job['task_id']}-muxia"[:64],
            "providerId": handoff["provider_id"],
            "requiredCapability": handoff["required_capability"],
            "profileSelector": handoff["profile_selector"],
            "timeoutMs": handoff["timeout_ms"],
        }
        muxia_path = workspace / "muxia-job-request.json"
        muxia_path.write_text(json.dumps(muxia_request, indent=2) + "\n", encoding="utf-8")
        progress_path = workspace / "PROGRESS.md"
        progress_path.write_text(
            f"# {job['task_id']} progress\n\n- OpenCode executable probe: PASS ({probe['version']})\n- MUXIA job request: prepared\n- Provider/model call: NOT PERFORMED\n",
            encoding="utf-8",
        )

        criteria = [row["id"] for row in job["acceptance_criteria"]]
        evidence = [
            {"type": "command_output", "ref": "opencode-probe.json", "claim": criteria[0]},
            {"type": "receipt", "ref": "muxia-job-request.json", "claim": criteria[-1]},
        ]
        payload = {
            "schema": "die.worker-result-envelope.v1",
            "task_id": job["task_id"],
            "executor": "opencode",
            "status": "done",
            "summary": "Bounded Worker-001 synthetic handoff prepared; no model/provider call performed.",
            "artifacts": [
                {"path": "opencode-probe.json", "kind": "file", "description": "Actual OpenCode executable/version probe"},
                {"path": "muxia-job-request.json", "kind": "file", "description": "Validated MUXIA job request"},
                {"path": "PROGRESS.md", "kind": "file", "description": "Resumable worker progress"},
            ],
            "evidence": evidence,
            "tests": [
                {"name": "opencode-cli-probe", "command": "opencode --version", "result": "pass", "output_ref": "opencode-probe.json"},
                {"name": "muxia-job-request-created", "command": "local-envelope-write", "result": "pass", "output_ref": "muxia-job-request.json"},
            ],
            "errors": [],
            "next_action": "handoff muxia-job-request.json to MUXIA",
        }
        result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "task_id": job["task_id"], "opencode_version": probe["version"], "result": str(result_path)}))
        return 0
    except Exception as exc:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "die.worker-result-envelope.v1",
            "task_id": "unknown",
            "executor": "opencode",
            "status": "failed",
            "summary": "Worker-001 runner failed closed.",
            "artifacts": [],
            "evidence": [],
            "tests": [],
            "errors": [{"where": "runner", "message": str(exc), "retryable": False}],
            "next_action": None,
        }
        result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
