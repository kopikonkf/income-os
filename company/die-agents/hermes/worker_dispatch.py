#!/usr/bin/env python3
"""Hermes -> Worker-001 bounded dispatch adapter for DIE-202.

This is orchestration glue, not a second agent. It invokes exactly one configured
worker runner, then enforces Worker Contract acceptance before returning control
to Hermes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def verify_result(job: dict[str, Any], result: dict[str, Any], workspace: Path) -> dict[str, Any]:
    if result.get("schema") != "die.worker-result-envelope.v1":
        raise ValueError("WORKER_RESULT_SCHEMA_INVALID")
    if result.get("task_id") != job.get("task_id") or result.get("executor") != "opencode":
        raise ValueError("WORKER_RESULT_IDENTITY_MISMATCH")

    artifacts = result.get("artifacts")
    evidence = result.get("evidence")
    tests = result.get("tests")
    if not isinstance(artifacts, list) or not isinstance(evidence, list) or not isinstance(tests, list):
        raise ValueError("WORKER_RESULT_COLLECTION_INVALID")

    artifact_paths = []
    for row in artifacts:
        rel = Path(str(row.get("path", "")))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("WORKER_ARTIFACT_PATH_UNSAFE")
        path = (workspace / rel).resolve()
        if not inside(workspace, path) or not path.exists():
            raise ValueError(f"WORKER_ARTIFACT_MISSING:{rel}")
        artifact_paths.append(rel.as_posix())

    criterion_ids = {row["id"] for row in job.get("acceptance_criteria", [])}
    evidence_claims = {str(row.get("claim", "")) for row in evidence}
    failing_tests = [row for row in tests if row.get("result") != "pass"]

    accepted_status = result.get("status")
    reasons: list[str] = []
    if accepted_status == "done" and not evidence:
        accepted_status = "blocked"
        reasons.append("DONE_WITHOUT_EVIDENCE")
    missing = sorted(criterion_ids - evidence_claims)
    if accepted_status == "done" and missing:
        accepted_status = "partial"
        reasons.append("AC_WITHOUT_EVIDENCE:" + ",".join(missing))
    if accepted_status == "done" and failing_tests:
        accepted_status = "partial"
        reasons.append("FAILING_TEST")

    return {
        "schema": "die.hermes-worker-acceptance.v1",
        "task_id": job["task_id"],
        "worker": "opencode",
        "worker_claimed_status": result.get("status"),
        "accepted_status": accepted_status,
        "artifacts_verified": artifact_paths,
        "acceptance_criteria": sorted(criterion_ids),
        "evidence_claims": sorted(evidence_claims),
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--worker-result", required=True)
    parser.add_argument("--dispatch-receipt", required=True)
    parser.add_argument("--worker-runner", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--opencode-bin", required=True)
    parser.add_argument("--worker-home", required=True)
    parser.add_argument("--timeout-sec", type=int, default=60)
    args = parser.parse_args()

    job_path = Path(args.job).resolve()
    result_path = Path(args.worker_result).resolve()
    receipt_path = Path(args.dispatch_receipt).resolve()
    job = load(job_path)
    workspace = Path(str(job.get("workspace", ""))).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    if not inside(workspace_root, workspace):
        raise SystemExit("WORKSPACE_OUTSIDE_ROOT")
    if not inside(workspace, result_path) or not inside(workspace, receipt_path):
        raise SystemExit("RESULT_OR_RECEIPT_OUTSIDE_WORKSPACE")

    command = [
        sys.executable,
        str(Path(args.worker_runner).resolve()),
        "--job", str(job_path),
        "--result", str(result_path),
        "--workspace-root", str(workspace_root),
        "--opencode-bin", str(Path(args.opencode_bin).resolve()),
        "--worker-home", str(Path(args.worker_home).resolve()),
    ]
    proc = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=args.timeout_sec, check=False)
    if proc.returncode != 0:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps({
            "schema": "die.hermes-worker-acceptance.v1",
            "task_id": job.get("task_id"),
            "worker": "opencode",
            "worker_claimed_status": "failed",
            "accepted_status": "failed",
            "artifacts_verified": [],
            "acceptance_criteria": [row.get("id") for row in job.get("acceptance_criteria", [])],
            "evidence_claims": [],
            "reasons": ["WORKER_PROCESS_FAILED"],
            "worker_exit_code": proc.returncode,
        }, indent=2) + "\n", encoding="utf-8")
        print(proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
        return 2

    result = load(result_path)
    acceptance = verify_result(job, result, workspace)
    acceptance["worker_exit_code"] = proc.returncode
    receipt_path.write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")
    if acceptance["accepted_status"] != "done":
        print(json.dumps(acceptance), file=sys.stderr)
        return 3
    print(json.dumps(acceptance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
