#!/usr/bin/env python3
"""Enforced ephemeral engineering worktree lifecycle for DIE H01."""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, subprocess
from pathlib import Path

SCHEMA = "die.h01.ephemeral-worktree.v1"
DEFAULT_REPO_URL = "https://github.com/kopikonkf/income-os.git"
DEFAULT_ANCHOR = Path("/home/kopiko/.local/state/die-engineering/income-os.git")
DEFAULT_WORKTREE_ROOT = Path("/home/kopiko/die-sessions")
DEFAULT_STATE_ROOT = Path("/home/kopiko/.local/state/die-engineering/sessions")
PROTECTED_ROOT = Path("/srv/die")
TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

class LifecycleError(RuntimeError): pass

def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def resolve(path): return Path(path).expanduser().resolve(strict=False)
def inside(path, root): return path == root or root in path.parents

def reject_protected(path):
    p, protected = resolve(path), resolve(PROTECTED_ROOT)
    if inside(p, protected):
        raise LifecycleError(f"E_PROTECTED_LIVE_PATH path={p} protected={protected}")
    return p

def assert_engineering_path(path, worktree_root=DEFAULT_WORKTREE_ROOT):
    p, root = reject_protected(path), reject_protected(worktree_root)
    if p == root or not inside(p, root):
        raise LifecycleError(f"E_OUTSIDE_ENGINEERING_WORKTREE path={p} root={root}")
    return p

def valid_task(task):
    if not TASK_RE.fullmatch(task): raise LifecycleError(f"E_INVALID_TASK_ID task={task!r}")
    return task

def git(args, check=True):
    cp = subprocess.run(["git", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and cp.returncode:
        raise LifecycleError(f"E_GIT rc={cp.returncode} cmd={' '.join(args)} stderr={cp.stderr.strip()[:1200]}")
    return cp

def state_path(root, task): return reject_protected(root) / f"{valid_task(task)}.json"
def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def ensure_anchor(anchor, repo_url):
    anchor = reject_protected(anchor); anchor.parent.mkdir(parents=True, exist_ok=True)
    if not anchor.exists():
        git(["init", "--bare", str(anchor)])
        git(["-C", str(anchor), "remote", "add", "origin", repo_url])
    if git(["-C", str(anchor), "rev-parse", "--is-bare-repository"]).stdout.strip() != "true":
        raise LifecycleError(f"E_ANCHOR_NOT_BARE path={anchor}")
    actual = git(["-C", str(anchor), "remote", "get-url", "origin"]).stdout.strip()
    if actual.rstrip("/") != repo_url.rstrip("/"):
        raise LifecycleError(f"E_REMOTE_MISMATCH expected={repo_url} actual={actual}")
    git(["-C", str(anchor), "fetch", "--prune", "origin", "+refs/heads/main:refs/remotes/origin/main"])
    sha = git(["-C", str(anchor), "rev-parse", "refs/remotes/origin/main^{commit}"]).stdout.strip()
    return anchor, sha

def create_worktree(task, anchor, worktree_root, state_root, repo_url):
    task = valid_task(task); root = reject_protected(worktree_root)
    target = assert_engineering_path(root / task, root)
    sp = state_path(state_root, task)
    if target.exists(): raise LifecycleError(f"E_WORKTREE_PATH_EXISTS path={target}")
    if sp.exists(): raise LifecycleError(f"E_SESSION_STATE_EXISTS path={sp}")
    anchor, base_sha = ensure_anchor(anchor, repo_url)
    registry = git(["-C", str(anchor), "worktree", "list", "--porcelain"]).stdout
    if f"worktree {target}\n" in registry: raise LifecycleError(f"E_WORKTREE_ALREADY_REGISTERED path={target}")
    root.mkdir(parents=True, exist_ok=True)
    added = False
    try:
        git(["-C", str(anchor), "worktree", "add", "--detach", str(target), "refs/remotes/origin/main"])
        added = True
        head = git(["-C", str(target), "rev-parse", "HEAD"]).stdout.strip()
        if head != base_sha: raise LifecycleError(f"E_BASE_SHA_MISMATCH expected={base_sha} actual={head}")
        data = {"schema": SCHEMA, "task_id": task, "status": "OPEN", "anchor": str(anchor),
                "worktree": str(target), "base_ref": "refs/remotes/origin/main", "base_sha": base_sha,
                "created_at": now()}
        write_json(sp, data)
        return data
    except Exception:
        if added:
            git(["-C", str(anchor), "worktree", "remove", "--force", str(target)], check=False)
            git(["-C", str(anchor), "worktree", "prune"], check=False)
        raise

def published_refs(anchor, head):
    git(["-C", str(anchor), "fetch", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*"])
    out = git(["-C", str(anchor), "for-each-ref", "--format=%(refname)", "--contains", head,
               "refs/remotes/origin/"]).stdout
    return [x.strip() for x in out.splitlines() if x.strip()]

def close_worktree(task, worktree_root, state_root):
    task = valid_task(task); root = reject_protected(worktree_root)
    target = assert_engineering_path(root / task, root); sp = state_path(state_root, task)
    if not sp.exists(): raise LifecycleError(f"E_SESSION_STATE_MISSING path={sp}")
    state = json.loads(sp.read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA or state.get("task_id") != task or resolve(state.get("worktree", "")) != target:
        raise LifecycleError(f"E_SESSION_STATE_MISMATCH path={sp}")
    anchor = reject_protected(state.get("anchor", ""))
    if not target.exists(): raise LifecycleError(f"E_WORKTREE_MISSING path={target}")
    if git(["-C", str(target), "status", "--porcelain"]).stdout.strip():
        raise LifecycleError("E_WORKTREE_DIRTY closure refused")
    head = git(["-C", str(target), "rev-parse", "HEAD"]).stdout.strip()
    refs = published_refs(anchor, head)
    if not refs: raise LifecycleError(f"E_UNPUBLISHED_HEAD sha={head} closure refused")
    git(["-C", str(anchor), "worktree", "remove", str(target)])
    git(["-C", str(anchor), "worktree", "prune"])
    state.update({"status": "CLOSED", "head_sha": head, "published_refs": refs, "closed_at": now()})
    write_json(sp, state); return state

def parser():
    p = argparse.ArgumentParser(description="DIE H01 ephemeral engineering worktree lifecycle")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create"); c.add_argument("--task", required=True)
    c.add_argument("--anchor", default=str(DEFAULT_ANCHOR)); c.add_argument("--worktree-root", default=str(DEFAULT_WORKTREE_ROOT))
    c.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT)); c.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    x = sub.add_parser("close"); x.add_argument("--task", required=True)
    x.add_argument("--worktree-root", default=str(DEFAULT_WORKTREE_ROOT)); x.add_argument("--state-root", default=str(DEFAULT_STATE_ROOT))
    g = sub.add_parser("guard"); g.add_argument("--path", required=True); g.add_argument("--worktree-root", default=str(DEFAULT_WORKTREE_ROOT))
    return p

def main():
    a = parser().parse_args()
    try:
        if a.command == "create": result = create_worktree(a.task, a.anchor, a.worktree_root, a.state_root, a.repo_url)
        elif a.command == "close": result = close_worktree(a.task, a.worktree_root, a.state_root)
        else: result = {"schema": SCHEMA, "status": "SAFE", "path": str(assert_engineering_path(a.path, a.worktree_root))}
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "ERROR", "error": str(exc)}, sort_keys=True)); return 2
    print(json.dumps(result, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
