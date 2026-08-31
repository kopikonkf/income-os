#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

PRINCIPALS = {
    "executive": {
        "principal_id": "die-lnx-executive-001",
        "scope": "company_portfolio",
        "authority_capability": "semantic_observation",
        "role_anchor": "company/executive/IDENTITY.md",
        "bootstrap": "company/executive/linux/COGNITION_BOOTSTRAP_V1.md",
    },
    "division01": {
        "principal_id": "die-lnx-division-001",
        "scope": "single_division",
        "authority_capability": "bounded_semantic_observation",
        "role_anchor": "company/division/division001/IDENTITY.md",
        "bootstrap": "company/division/division001/linux/COGNITION_BOOTSTRAP_V1.md",
    },
}


def _utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_envelope(role: str, repo_sha: str, mission_id: str = "M-001") -> dict[str, Any]:
    spec = PRINCIPALS[role]
    briefing = (
        "WAKE-LNX-002 state convergence bootstrap.\n\n"
        f"You are bound as Linux principal `{spec['principal_id']}` to the shared semantic role anchor `{spec['role_anchor']}`. "
        "Before any reasoning, recommendation, review, research, scoring, or decision output, you MUST call your DIE Runtime MCP tool `context_snapshot`. "
        "Conversation/account memory is untrusted and MUST NOT substitute for the snapshot.\n\n"
        "Required convergence checks:\n"
        f"1. principal.principal_id == `{spec['principal_id']}`\n"
        f"2. principal.scope == `{spec['scope']}`\n"
        f"3. authority.capability == `{spec['authority_capability']}`\n"
        "4. freshness.status == `fresh`\n"
        "5. data.canon_context.load_status == `VERIFIED`\n"
        "6. report source_trust/completeness truthfully even when DEGRADED; do not reinterpret DEGRADED as transport failure.\n\n"
        f"After the snapshot succeeds, apply the bounded cognition bootstrap `{spec['bootstrap']}` through projected/canonical facts only; do not request raw filesystem access. "
        "Then return a compact convergence receipt with exactly: principal_id, scope, authority_capability, freshness_status, canon_load_status, source_trust, completeness, repo_sha, bootstrap_status PASS|FAIL. "
        "Do not perform any mutation/control action.\n\n"
        f"Expected repository revision for this convergence cycle: `{repo_sha}`."
    )
    return {
        "schema": "die.wake.envelope.v1",
        "company_instance_id": "DIE-LINUX",
        "principal_id": spec["principal_id"],
        "wake_id": f"WAKE-LNX002-{role.upper()}-{repo_sha[:8]}",
        "mission_id": mission_id,
        "action_type": "WAKE_CONTEXT_CONVERGENCE",
        "briefing": briefing,
        "created_at": _utcnow(),
        "evidence_refs": [spec["role_anchor"], spec["bootstrap"], "company/runtime-instances-v1.json"],
    }


def validate_receipt(role: str, receipt: dict[str, Any], repo_sha: str) -> list[str]:
    spec = PRINCIPALS[role]
    errors: list[str] = []
    expected = {
        "principal_id": spec["principal_id"],
        "scope": spec["scope"],
        "authority_capability": spec["authority_capability"],
        "freshness_status": "fresh",
        "canon_load_status": "VERIFIED",
        "repo_sha": repo_sha,
        "bootstrap_status": "PASS",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"E_CONVERGENCE_FIELD:{key}:{receipt.get(key)!r}")
    for key in ("source_trust", "completeness"):
        if not isinstance(receipt.get(key), str) or not receipt[key]:
            errors.append(f"E_CONVERGENCE_FIELD:{key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("role", choices=sorted(PRINCIPALS))
    build.add_argument("--repo-sha", required=True)
    build.add_argument("--output", required=True)
    accept = sub.add_parser("validate")
    accept.add_argument("role", choices=sorted(PRINCIPALS))
    accept.add_argument("--repo-sha", required=True)
    accept.add_argument("--receipt", required=True)
    args = parser.parse_args()
    if args.command == "build":
        out = build_envelope(args.role, args.repo_sha)
        Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": "PASS", "wake_id": out["wake_id"], "briefing_sha256": hashlib.sha256(out["briefing"].encode()).hexdigest()}))
        return 0
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    errors = validate_receipt(args.role, receipt, args.repo_sha)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
