# DIE H01 Ephemeral Engineering Worktree v1

**Date:** 2026-09-12
**Status:** H01 FOUNDATION CANON after merge
**Scope:** Engineering worktrees for `die-h01`; this policy does not deploy or cut over production.

## Invariants

1. `/srv/die` is legacy live / rollback. Engineering automation must not reset, pull, clean, stash, commit, branch, fetch into, or otherwise mutate `/srv/die` or its Git metadata.
2. Each engineering task receives exactly one path `/home/kopiko/die-sessions/<task>` created from freshly fetched `origin/main`.
3. The worktree is owned by a separate bare engineering anchor at `/home/kopiko/.local/state/die-engineering/income-os.git`. This is deliberate: attaching a new worktree to `/srv/die/.git` would mutate the protected live checkout's shared Git metadata even if the worktree directory were elsewhere.
4. Durable session state is outside both live production and the worktree, under `/home/kopiko/.local/state/die-engineering/sessions/<task>.json`.
5. Closure fails closed while the worktree is dirty or its HEAD is not present on a fetched remote branch. A closed worktree is removed and pruned; its state receipt remains `CLOSED`.
6. Repository publication is still governed by `docs/operations/DIE_ENGINEERING_LEASE_V1.md`: acquire `income-os.repo-write` plus the task-scope lease immediately before remote mutation, release in `finally`, and never infer permission from an absent lease.

## Canonical helper

`bin/die_h01_worktree.py`

Create a task worktree:

```text
python3 bin/die_h01_worktree.py create --task H01-004
```

The helper fetches only into the independent engineering anchor, resolves current `refs/remotes/origin/main`, creates a detached worktree at `/home/kopiko/die-sessions/H01-004`, verifies its HEAD equals the fetched base SHA, then writes an `OPEN` state receipt.

Guard an intended engineering path before a mutating operation:

```text
python3 bin/die_h01_worktree.py guard --path /home/kopiko/die-sessions/H01-004
```

Any path resolving inside `/srv/die`, or outside the configured engineering worktree root, returns `status=ERROR` and exit code `2`.

Close only after the task branch/HEAD is durably published and the worktree is clean:

```text
python3 bin/die_h01_worktree.py close --task H01-004
```

Closure fetches remote refs through the independent anchor, proves the worktree HEAD is contained by a remote ref, removes the worktree, prunes registration, and records `CLOSED`, `head_sha`, `published_refs`, and `closed_at`.

## Failure semantics

The lifecycle is fail-closed. Existing task path/state, invalid task ID, protected/out-of-root path, remote mismatch, fetch/Git failure, base-SHA mismatch, dirty closure, missing state/worktree, or unpublished HEAD aborts without declaring closure. If materialization fails after `git worktree add`, the helper removes the newly-added worktree and prunes the engineering anchor before propagating the failure.

## Acceptance for H01-003

Automated tests must prove at minimum: protected `/srv/die` rejection; outside-root rejection; current-`origin/main` creation; clean published closure/removal; dirty closure refusal; stale state refusal without materializing a worktree; unpublished HEAD refusal; and state-root protection.
