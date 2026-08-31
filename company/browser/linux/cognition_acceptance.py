#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROLE_CONTRACTS = {
    "executive": {
        "task_id": "ID-LNX-003",
        "principal_id": "die-lnx-executive-001",
        "scope": "company_portfolio",
        "authority_capability": "semantic_observation",
        "role_anchor": "company/executive/IDENTITY.md",
        "bootstrap_ref": "company/executive/linux/COGNITION_BOOTSTRAP_V1.md",
        "required_responsibilities": {
            "portfolio_synthesis",
            "strategic_challenge",
            "division01_worth_making_review",
            "division01_blueprint_review",
            "bounded_review_outcomes",
        },
        "required_boundaries": {
            "no_worker_command",
            "no_direct_state_write",
            "no_submission",
            "no_self_authority",
        },
    },
    "division01": {
        "task_id": "ID-LNX-004",
        "principal_id": "die-lnx-division-001",
        "scope": "single_division",
        "authority_capability": "bounded_semantic_observation",
        "role_anchor": "company/division/division001/IDENTITY.md",
        "bootstrap_ref": "company/division/division001/linux/COGNITION_BOOTSTRAP_V1.md",
        "required_responsibilities": {
            "OE-001",
            "OE-002",
            "OE-003",
            "OE-004",
            "OE-005",
            "platform_evidence_doctrine",
        },
        "required_boundaries": {
            "no_worker_command",
            "no_execution_authority",
            "no_direct_state_write",
            "no_submission",
        },
    },
}


def validate_assimilation(role: str, receipt: dict[str, Any], repo_sha: str) -> list[str]:
    contract = ROLE_CONTRACTS[role]
    errors: list[str] = []
    exact = {
        "schema": "die.cognition.assimilation.receipt.v1",
        "task_id": contract["task_id"],
        "company_instance_id": "DIE-LINUX",
        "principal_id": contract["principal_id"],
        "scope": contract["scope"],
        "authority_capability": contract["authority_capability"],
        "freshness_status": "fresh",
        "canon_load_status": "VERIFIED",
        "repo_sha": repo_sha,
        "role_anchor": contract["role_anchor"],
        "bootstrap_ref": contract["bootstrap_ref"],
        "bootstrap_status": "PASS",
    }
    for key, value in exact.items():
        if receipt.get(key) != value:
            errors.append(f"E_ASSIMILATION_FIELD:{key}:{receipt.get(key)!r}")
    for key in ("source_trust", "completeness"):
        if not isinstance(receipt.get(key), str) or not receipt[key]:
            errors.append(f"E_ASSIMILATION_FIELD:{key}")
    responsibilities = set(receipt.get("responsibilities_ack") or [])
    boundaries = set(receipt.get("boundaries_ack") or [])
    missing_responsibilities = sorted(contract["required_responsibilities"] - responsibilities)
    missing_boundaries = sorted(contract["required_boundaries"] - boundaries)
    if missing_responsibilities:
        errors.append("E_RESPONSIBILITY_ACK:" + ",".join(missing_responsibilities))
    if missing_boundaries:
        errors.append("E_BOUNDARY_ACK:" + ",".join(missing_boundaries))
    if receipt.get("account_memory_used_as_authority") is not False:
        errors.append("E_ACCOUNT_MEMORY_AUTHORITY")
    if receipt.get("mutation_performed") is not False:
        errors.append("E_MUTATION_PERFORMED")
    return errors


def validate_society(
    executive: dict[str, Any],
    division01: dict[str, Any],
    operator: dict[str, Any],
    repo_sha: str,
) -> list[str]:
    errors = [
        *("EXEC:" + e for e in validate_assimilation("executive", executive, repo_sha)),
        *("DIV:" + e for e in validate_assimilation("division01", division01, repo_sha)),
    ]
    if operator.get("task_id") != "ID-LNX-002" or operator.get("status") != "DONE":
        errors.append("E_OPERATOR_NOT_DONE")
    runtime = operator.get("live_runtime") or {}
    if runtime.get("profile") != "income-operator":
        errors.append("E_OPERATOR_PROFILE")
    if runtime.get("company_instance_id") != "DIE-LINUX":
        errors.append("E_OPERATOR_INSTANCE")
    if runtime.get("cron_mode") != "no-agent":
        errors.append("E_OPERATOR_SCHEDULER_MODE")
    if executive.get("principal_id") == division01.get("principal_id"):
        errors.append("E_ROLE_COLLAPSE_PRINCIPAL")
    if executive.get("scope") == division01.get("scope"):
        errors.append("E_ROLE_COLLAPSE_SCOPE")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    role_cmd = sub.add_parser("role")
    role_cmd.add_argument("role", choices=sorted(ROLE_CONTRACTS))
    role_cmd.add_argument("--receipt", required=True)
    role_cmd.add_argument("--repo-sha", required=True)
    society_cmd = sub.add_parser("society")
    society_cmd.add_argument("--executive", required=True)
    society_cmd.add_argument("--division01", required=True)
    society_cmd.add_argument("--operator", required=True)
    society_cmd.add_argument("--repo-sha", required=True)
    args = parser.parse_args()
    if args.command == "role":
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        errors = validate_assimilation(args.role, receipt, args.repo_sha)
    else:
        errors = validate_society(
            json.loads(Path(args.executive).read_text(encoding="utf-8")),
            json.loads(Path(args.division01).read_text(encoding="utf-8")),
            json.loads(Path(args.operator).read_text(encoding="utf-8")),
            args.repo_sha,
        )
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
