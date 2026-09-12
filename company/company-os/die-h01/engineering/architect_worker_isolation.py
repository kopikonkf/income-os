from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "die.h01.architect-worker-isolation.v1"
CLAIM_SCHEMA = "die.h01.mutable-worktree-claim.v1"
WORKTREE_SCHEMA = "die.h01.ephemeral-worktree.v1"
DEFAULT_WORKTREE_ROOT = Path("/home/kopiko/die-sessions")
DEFAULT_STATE_ROOT = Path("/home/kopiko/.local/state/die-engineering/sessions")
DEFAULT_CLAIM_ROOT = Path("/home/kopiko/.local/state/die-engineering/worker-claims")
DEFAULT_PROTECTED_ROOT = Path("/srv/die")
DEFAULT_CANONICAL_REF = "refs/remotes/origin/main"
DEFAULT_TASK_GRAPH = "company/company-os/die-h01/die-h01-task-graph.v1.json"
TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
DISPATCHABLE_CANONICAL_STATUSES = {"READY", "LEASED", "RUNNING"}


class IsolationError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _valid_task(task_id: str) -> str:
    if not TASK_RE.fullmatch(task_id):
        raise IsolationError("E_INVALID_TASK_ID", repr(task_id))
    return task_id


def _git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if cp.returncode:
        raise IsolationError("E_GIT", f"cmd={' '.join(args)} stderr={cp.stderr.strip()[:1000]}")
    return cp.stdout.strip()


def canonical_task_gate(
    repo: str | Path,
    task_id: str,
    *,
    canonical_ref: str = DEFAULT_CANONICAL_REF,
    task_graph_path: str = DEFAULT_TASK_GRAPH,
) -> dict[str, Any]:
    """Read dependency readiness from canonical origin/main, never the worker branch."""
    task_id = _valid_task(task_id)
    repo_path = _resolve(repo)
    ref_sha = _git(repo_path, "rev-parse", f"{canonical_ref}^{{commit}}")
    raw = _git(repo_path, "show", f"{canonical_ref}:{task_graph_path}")
    try:
        graph = json.loads(raw)
    except Exception as exc:
        raise IsolationError("E_CANONICAL_TASK_GRAPH_JSON", task_graph_path) from exc
    tasks = {row.get("id"): row for row in graph.get("tasks", []) if isinstance(row, dict) and row.get("id")}
    task = tasks.get(task_id)
    if not task:
        raise IsolationError("E_CANONICAL_TASK_MISSING", task_id)
    dependencies = list(task.get("depends_on") or [])
    dependency_status = {dep: (tasks.get(dep) or {}).get("status") for dep in dependencies}
    unknown = [dep for dep, status in dependency_status.items() if status is None]
    if unknown:
        raise IsolationError("E_CANONICAL_DEPENDENCY_MISSING", ",".join(unknown))
    blocked = [dep for dep, status in dependency_status.items() if status != "DONE"]
    if blocked:
        detail = ",".join(f"{dep}={dependency_status[dep]}" for dep in blocked)
        raise IsolationError("E_CANONICAL_DEPENDENCY_BLOCKED", detail)
    status = str(task.get("status") or "")
    if status not in DISPATCHABLE_CANONICAL_STATUSES:
        raise IsolationError("E_CANONICAL_TASK_NOT_DISPATCHABLE", f"{task_id}={status}")
    return {
        "schema": SCHEMA,
        "task_id": task_id,
        "canonical_ref": canonical_ref,
        "canonical_ref_sha": ref_sha,
        "task_status": status,
        "task_authority": task.get("authority"),
        "dependency_status": dependency_status,
        "scheduler_action_taken": False,
        "canonical_graph_mutated": False,
    }


def validate_worker_worktree(
    task_id: str,
    worktree: str | Path,
    *,
    worktree_root: str | Path = DEFAULT_WORKTREE_ROOT,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    protected_root: str | Path = DEFAULT_PROTECTED_ROOT,
) -> dict[str, Any]:
    """Prove this worker owns the exact task worktree and not live /srv/die metadata."""
    task_id = _valid_task(task_id)
    root = _resolve(worktree_root)
    protected = _resolve(protected_root)
    target = _resolve(worktree)
    expected = _resolve(root / task_id)
    if target != expected:
        raise IsolationError("E_WORKTREE_TASK_PATH_MISMATCH", f"expected={expected} actual={target}")
    if _inside(target, protected):
        raise IsolationError("E_PROTECTED_LIVE_PATH", str(target))
    if not target.is_dir():
        raise IsolationError("E_WORKTREE_MISSING", str(target))

    top = _resolve(_git(target, "rev-parse", "--show-toplevel"))
    if top != target:
        raise IsolationError("E_GIT_TOPLEVEL_MISMATCH", f"expected={target} actual={top}")
    git_dir_raw = _git(target, "rev-parse", "--git-dir")
    git_dir = _resolve(git_dir_raw if Path(git_dir_raw).is_absolute() else target / git_dir_raw)
    common_raw = _git(target, "rev-parse", "--git-common-dir")
    common_dir = _resolve(common_raw if Path(common_raw).is_absolute() else git_dir / common_raw)
    if _inside(git_dir, protected) or _inside(common_dir, protected):
        raise IsolationError("E_PROTECTED_LIVE_GIT_METADATA", f"git_dir={git_dir} common_dir={common_dir}")

    lifecycle_path = _resolve(state_root) / f"{task_id}.json"
    if not lifecycle_path.is_file():
        raise IsolationError("E_WORKTREE_LIFECYCLE_STATE_MISSING", str(lifecycle_path))
    try:
        state = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IsolationError("E_WORKTREE_LIFECYCLE_STATE_INVALID", str(lifecycle_path)) from exc
    if state.get("schema") != WORKTREE_SCHEMA:
        raise IsolationError("E_WORKTREE_LIFECYCLE_SCHEMA", str(state.get("schema")))
    if state.get("task_id") != task_id:
        raise IsolationError("E_WORKTREE_LIFECYCLE_TASK_MISMATCH", str(state.get("task_id")))
    if _resolve(state.get("worktree", "")) != target:
        raise IsolationError("E_WORKTREE_LIFECYCLE_PATH_MISMATCH", str(state.get("worktree")))
    if state.get("status") != "OPEN":
        raise IsolationError("E_WORKTREE_LIFECYCLE_NOT_OPEN", str(state.get("status")))

    return {
        "schema": SCHEMA,
        "task_id": task_id,
        "worktree": str(target),
        "head_sha": _git(target, "rev-parse", "HEAD"),
        "branch": _git(target, "branch", "--show-current"),
        "git_dir": str(git_dir),
        "git_common_dir": str(common_dir),
        "lifecycle_state": str(lifecycle_path),
        "lifecycle_status": "OPEN",
        "protected_live_git_metadata": False,
    }


@dataclass(frozen=True)
class WorkerIdentity:
    task_id: str
    principal_id: str
    dispatch_id: str

    def validate(self) -> None:
        _valid_task(self.task_id)
        if not self.principal_id:
            raise IsolationError("E_PRINCIPAL_REQUIRED")
        if not self.dispatch_id:
            raise IsolationError("E_DISPATCH_REQUIRED")


class MutableWorktreeClaim:
    """Fail-closed host-local claim for one mutable worktree.

    Claims deliberately do not auto-expire. Crash recovery must reconcile durable
    Mission state before stale coordination state is removed; a timeout alone can
    never hand a mutable worktree to a second worker.
    """

    def __init__(self, claim_root: str | Path, worktree: str | Path):
        self.claim_root = _resolve(claim_root)
        self.worktree = _resolve(worktree)
        digest = hashlib.sha256(str(self.worktree).encode("utf-8")).hexdigest()[:24]
        self.lock_dir = self.claim_root / f"worktree-{digest}.lock"
        self.token: str | None = None

    def _state_path(self) -> Path:
        return self.lock_dir / "claim.json"

    def _read_existing(self) -> dict[str, Any]:
        try:
            return json.loads(self._state_path().read_text(encoding="utf-8"))
        except Exception as exc:
            raise IsolationError("E_MUTABLE_WORKTREE_BUSY_CORRUPT", str(self.lock_dir)) from exc

    def acquire(self, identity: WorkerIdentity) -> dict[str, Any]:
        identity.validate()
        self.claim_root.mkdir(parents=True, exist_ok=True)
        try:
            self.lock_dir.mkdir()
        except FileExistsError as exc:
            existing = self._read_existing()
            detail = (
                f"worktree={self.worktree} task_id={existing.get('task_id')} "
                f"principal_id={existing.get('principal_id')} dispatch_id={existing.get('dispatch_id')}"
            )
            raise IsolationError("E_MUTABLE_WORKTREE_BUSY", detail) from exc
        token = uuid.uuid4().hex
        record = {
            "schema": CLAIM_SCHEMA,
            "token": token,
            "task_id": identity.task_id,
            "principal_id": identity.principal_id,
            "dispatch_id": identity.dispatch_id,
            "worktree": str(self.worktree),
            "pid": os.getpid(),
            "acquired_at": _utc_now(),
        }
        try:
            self._state_path().write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        except Exception:
            shutil.rmtree(self.lock_dir, ignore_errors=True)
            raise
        self.token = token
        return record

    def release(self) -> dict[str, Any]:
        if not self.token:
            return {"schema": CLAIM_SCHEMA, "status": "ALREADY_RELEASED", "worktree": str(self.worktree)}
        existing = self._read_existing()
        if existing.get("token") != self.token:
            raise IsolationError("E_MUTABLE_WORKTREE_TOKEN_MISMATCH", str(self.worktree))
        shutil.rmtree(self.lock_dir)
        self.token = None
        return {"schema": CLAIM_SCHEMA, "status": "RELEASED", "worktree": str(self.worktree)}


@dataclass
class IsolationHandle:
    identity: WorkerIdentity
    canonical_gate: dict[str, Any]
    workspace: dict[str, Any]
    claim: MutableWorktreeClaim
    claim_record: dict[str, Any]

    def release(self) -> dict[str, Any]:
        return self.claim.release()


def acquire_worker_isolation(
    identity: WorkerIdentity,
    worktree: str | Path,
    *,
    canonical_ref: str = DEFAULT_CANONICAL_REF,
    task_graph_path: str = DEFAULT_TASK_GRAPH,
    worktree_root: str | Path = DEFAULT_WORKTREE_ROOT,
    state_root: str | Path = DEFAULT_STATE_ROOT,
    claim_root: str | Path = DEFAULT_CLAIM_ROOT,
    protected_root: str | Path = DEFAULT_PROTECTED_ROOT,
) -> IsolationHandle:
    """Gate canonical dependencies, validate workspace, then claim mutation authority."""
    identity.validate()
    workspace = validate_worker_worktree(
        identity.task_id,
        worktree,
        worktree_root=worktree_root,
        state_root=state_root,
        protected_root=protected_root,
    )
    gate = canonical_task_gate(
        worktree,
        identity.task_id,
        canonical_ref=canonical_ref,
        task_graph_path=task_graph_path,
    )
    claim = MutableWorktreeClaim(claim_root, worktree)
    record = claim.acquire(identity)
    return IsolationHandle(identity=identity, canonical_gate=gate, workspace=workspace, claim=claim, claim_record=record)


def publication_resources(task_id: str) -> list[str]:
    """Return the canonical publication lease pair; this function does not acquire it."""
    task_id = _valid_task(task_id)
    return ["income-os.repo-write", f"company-os.{task_id}"]
