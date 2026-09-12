"""Read-only dependency-ready graph-width planning for H01 engineering workers.

This module deliberately stops at a deterministic plan.  It does not acquire a
Mission Control lease, create a task, change a task status, claim a worktree, or
write a repository.  The caller must submit the returned task IDs to Mission
Control, which remains the durable scheduler and task authority.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "die.h01.architect-graph-width-planner.v1"
DEFAULT_CANONICAL_REF = "refs/remotes/origin/main"
DEFAULT_TASK_GRAPH = "company/company-os/die-h01/die-h01-task-graph.v1.json"
DEFAULT_WORKTREE_ROOT = "/home/kopiko/die-sessions"
FOUNDER_GATED_AUTHORITIES = {"FOUNDER", "FOUNDER_GATED", "FOUNDER_REQUIRED"}
KNOWN_STATES = {"READY", "LEASED", "RUNNING", "VERIFYING", "DONE", "BLOCKED", "DEFERRED", "WAITING_FOUNDER"}


class GraphWidthPlanningError(RuntimeError):
    """Raised when the canonical graph or coordination snapshot is malformed."""


def _as_list(value: Any, *, field: str, task_id: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        raise GraphWidthPlanningError(f"E_INVALID_{field.upper()}:{task_id}")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GraphWidthPlanningError(f"E_INVALID_{field.upper()}:{task_id}")
        result.append(item.strip())
    return result


def _task_map(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = graph.get("tasks")
    if not isinstance(rows, list):
        raise GraphWidthPlanningError("E_TASK_GRAPH_TASKS_NOT_LIST")
    tasks: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise GraphWidthPlanningError("E_TASK_GRAPH_TASK_ID_INVALID")
        task_id = row["id"].strip()
        if task_id in tasks:
            raise GraphWidthPlanningError(f"E_TASK_GRAPH_DUPLICATE_TASK:{task_id}")
        tasks[task_id] = row
    return tasks


def _resource_declaration(task_id: str, task: Mapping[str, Any]) -> tuple[list[str], bool, str | None]:
    values: list[str] = []
    for field in ("resources", "required_resources", "exclusive_resources"):
        if field in task:
            values.extend(_as_list(task.get(field), field=field, task_id=task_id))
    for field in ("browser_resource", "resource"):
        value = task.get(field)
        if value is not None:
            values.extend(_as_list(value, field=field, task_id=task_id))

    mutable_repo_write = bool(task.get("mutable_repo_write", False))
    owner = task.get("mutable_repo_write_owner", task.get("repo_write_owner"))
    if mutable_repo_write:
        if not isinstance(owner, str) or not owner.strip():
            raise GraphWidthPlanningError(f"E_AMBIGUOUS_MUTABLE_REPO_WRITE_OWNERSHIP:{task_id}")
        values.append(str(task.get("repo_write_resource") or "income-os.repo-write"))
    return sorted(set(values)), mutable_repo_write, owner.strip() if isinstance(owner, str) else None


def _worktree(task_id: str, task: Mapping[str, Any], worktree_root: str) -> str:
    value = task.get("worktree")
    if value is None:
        return str(Path(worktree_root) / task_id)
    if not isinstance(value, str) or not value.strip():
        raise GraphWidthPlanningError(f"E_INVALID_WORKTREE:{task_id}")
    return str(Path(value).expanduser().resolve(strict=False))


def _active_leases(rows: Iterable[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    active: dict[str, Mapping[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping) or not isinstance(row.get("resource"), str) or not row["resource"].strip():
            raise GraphWidthPlanningError("E_ACTIVE_LEASE_RESOURCE_UNKNOWN")
        status = row.get("status")
        if status is None:
            raise GraphWidthPlanningError(f"E_ACTIVE_LEASE_STATE_UNKNOWN:{row['resource']}")
        if status not in {"FREE", "EXPIRED", "ACTIVE"}:
            raise GraphWidthPlanningError(f"E_ACTIVE_LEASE_STATE_UNKNOWN:{row['resource']}={status}")
        if status == "ACTIVE":
            resource = row["resource"].strip()
            if resource in active:
                raise GraphWidthPlanningError(f"E_ACTIVE_LEASE_DUPLICATE:{resource}")
            active[resource] = row
    return active


def _active_worktrees(rows: Iterable[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    active: dict[str, Mapping[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping) or not isinstance(row.get("worktree"), str) or not row["worktree"].strip():
            raise GraphWidthPlanningError("E_ACTIVE_WORKTREE_UNKNOWN")
        status = row.get("status")
        if status is None:
            raise GraphWidthPlanningError(f"E_ACTIVE_WORKTREE_STATE_UNKNOWN:{row['worktree']}")
        if status not in {"FREE", "RELEASED", "EXPIRED", "ACTIVE", "OPEN", "CLAIMED"}:
            raise GraphWidthPlanningError(f"E_ACTIVE_WORKTREE_STATE_UNKNOWN:{row['worktree']}={status}")
        if status in {"ACTIVE", "OPEN", "CLAIMED"}:
            path = str(Path(row["worktree"]).expanduser().resolve(strict=False))
            if path in active:
                raise GraphWidthPlanningError(f"E_ACTIVE_WORKTREE_DUPLICATE:{path}")
            active[path] = row
    return active


def _authorization_set(value: Iterable[str] | Mapping[str, Any] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, Mapping):
        return {str(key) for key, allowed in value.items() if allowed is True}
    return {str(item) for item in value}


def _graph_digest(graph: Mapping[str, Any]) -> str:
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_graph_width(
    graph: Mapping[str, Any],
    *,
    active_leases: Iterable[Mapping[str, Any]] | None = None,
    active_worktrees: Iterable[Mapping[str, Any]] | None = None,
    founder_authorized_tasks: Iterable[str] | Mapping[str, Any] | None = None,
    max_workers: int | None = None,
    worktree_root: str = DEFAULT_WORKTREE_ROOT,
    canonical_ref: str = DEFAULT_CANONICAL_REF,
    canonical_ref_sha: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic, resource-safe dependency-ready worker set.

    ``graph`` and coordination rows are treated as immutable observations.  A
    malformed coordination snapshot raises instead of being guessed around;
    an individual task with an unknown dependency or missing Founder approval
    is excluded from the returned set.
    """
    if not isinstance(graph, Mapping):
        raise GraphWidthPlanningError("E_TASK_GRAPH_NOT_OBJECT")
    if max_workers is not None and (not isinstance(max_workers, int) or max_workers < 0):
        raise GraphWidthPlanningError("E_MAX_WORKERS_INVALID")
    tasks = _task_map(graph)
    leases = _active_leases(active_leases)
    worktrees = _active_worktrees(active_worktrees)
    authorized = _authorization_set(founder_authorized_tasks)
    ordered = sorted(tasks.values(), key=lambda row: (-int(row.get("priority", 0)), str(row["id"])))
    exclusions: dict[str, dict[str, Any]] = {}
    eligible: list[dict[str, Any]] = []

    def exclude(task_id: str, code: str, detail: str = "") -> None:
        exclusions[task_id] = {"code": code, **({"detail": detail} if detail else {})}

    for task in ordered:
        task_id = str(task["id"])
        status = task.get("status")
        if status not in KNOWN_STATES:
            exclude(task_id, "UNKNOWN_TASK_STATE", str(status))
            continue
        if status != "READY":
            exclude(task_id, "TASK_NOT_READY", str(status))
            continue
        dependencies = _as_list(task.get("depends_on"), field="depends_on", task_id=task_id)
        dependency_status: dict[str, Any] = {}
        unknown = []
        blocked = []
        for dependency in dependencies:
            upstream = tasks.get(dependency)
            dep_status = upstream.get("status") if upstream else None
            dependency_status[dependency] = dep_status
            if dep_status not in KNOWN_STATES:
                unknown.append(dependency)
            elif dep_status != "DONE":
                blocked.append(dependency)
        if unknown:
            exclude(task_id, "UNKNOWN_DEPENDENCY_STATE", ",".join(unknown))
            continue
        if blocked:
            exclude(task_id, "DEPENDENCY_NOT_DONE", ",".join(f"{dep}={dependency_status[dep]}" for dep in blocked))
            continue
        authority = str(task.get("authority") or "")
        if authority in FOUNDER_GATED_AUTHORITIES and task_id not in authorized:
            exclude(task_id, "FOUNDER_AUTHORIZATION_REQUIRED")
            continue
        try:
            resources, mutable_repo_write, repo_write_owner = _resource_declaration(task_id, task)
            target_worktree = _worktree(task_id, task, worktree_root)
        except GraphWidthPlanningError as exc:
            code, _, detail = str(exc).partition(":")
            code = code.removeprefix("E_")
            exclude(task_id, code, detail)
            continue
        active_resource_conflicts = []
        for resource in resources:
            lease = leases.get(resource)
            if lease is not None:
                active_resource_conflicts.append(resource)
        active_worktree = worktrees.get(target_worktree)
        if active_resource_conflicts:
            exclude(task_id, "ACTIVE_LEASE_CONFLICT", ",".join(active_resource_conflicts))
            continue
        if active_worktree is not None:
            owner = active_worktree.get("task_id")
            code = "ACTIVE_WORKTREE_CONFLICT" if isinstance(owner, str) and owner else "AMBIGUOUS_WORKTREE_OWNERSHIP"
            exclude(task_id, code, str(owner or target_worktree))
            continue
        eligible.append({
            "task_id": task_id,
            "priority": int(task.get("priority", 0)),
            "dependencies": dependencies,
            "dependency_status": dependency_status,
            "authority": authority,
            "resources": resources,
            "worktree": target_worktree,
            "mutable_repo_write": mutable_repo_write,
            "repo_write_owner": repo_write_owner,
        })

    selected: list[dict[str, Any]] = []
    selected_resources: set[str] = set()
    selected_worktrees: set[str] = set()
    for candidate in eligible:
        if max_workers is not None and len(selected) >= max_workers:
            exclude(candidate["task_id"], "WIDTH_LIMIT")
            continue
        resource_conflicts = sorted(selected_resources.intersection(candidate["resources"]))
        if resource_conflicts:
            exclude(candidate["task_id"], "RESOURCE_COLLISION", ",".join(resource_conflicts))
            continue
        if candidate["worktree"] in selected_worktrees:
            exclude(candidate["task_id"], "WORKTREE_COLLISION", candidate["worktree"])
            continue
        selected.append(candidate)
        selected_resources.update(candidate["resources"])
        selected_worktrees.add(candidate["worktree"])

    return {
        "schema": SCHEMA,
        "status": "PLANNED" if selected else "EMPTY",
        "canonical_ref": canonical_ref,
        "canonical_ref_sha": canonical_ref_sha,
        "graph_sha256": _graph_digest(graph),
        "ordered_candidate_task_ids": [row["task_id"] for row in eligible],
        "dependency_ready_task_ids": [row["task_id"] for row in eligible],
        "selected_task_ids": [row["task_id"] for row in selected],
        "selected": selected,
        "excluded": exclusions,
        "max_workers": max_workers,
        "mission_control_is_scheduler": True,
        "read_only": True,
        "scheduler_action_taken": False,
        "durable_state_mutated": False,
        "canonical_graph_mutated": False,
    }


def load_canonical_graph(
    repo: str | Path,
    *,
    canonical_ref: str = DEFAULT_CANONICAL_REF,
    task_graph_path: str = DEFAULT_TASK_GRAPH,
) -> tuple[dict[str, Any], str]:
    """Read graph JSON and commit identity from canonical Git only."""
    root = Path(repo).expanduser().resolve(strict=False)
    sha_proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{canonical_ref}^{{commit}}"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if sha_proc.returncode:
        raise GraphWidthPlanningError("E_CANONICAL_REF_UNAVAILABLE")
    raw_proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{canonical_ref}:{task_graph_path}"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if raw_proc.returncode:
        raise GraphWidthPlanningError("E_CANONICAL_TASK_GRAPH_UNAVAILABLE")
    try:
        graph = json.loads(raw_proc.stdout)
    except json.JSONDecodeError as exc:
        raise GraphWidthPlanningError("E_CANONICAL_TASK_GRAPH_JSON") from exc
    if not isinstance(graph, dict):
        raise GraphWidthPlanningError("E_TASK_GRAPH_NOT_OBJECT")
    return graph, sha_proc.stdout.strip()


def plan_canonical_graph_width(repo: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Plan from the canonical Git ref; this helper performs no Git writes."""
    graph, sha = load_canonical_graph(
        repo,
        canonical_ref=kwargs.pop("canonical_ref", DEFAULT_CANONICAL_REF),
        task_graph_path=kwargs.pop("task_graph_path", DEFAULT_TASK_GRAPH),
    )
    return plan_graph_width(graph, canonical_ref_sha=sha, **kwargs)


# Descriptive alias for callers that prefer the policy term over the helper name.
plan_dependency_ready_set = plan_graph_width
