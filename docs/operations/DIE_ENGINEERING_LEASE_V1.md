# DIE Engineering Lease v1

**Date:** 2026-09-03
**Status:** CANONICAL OPERATIONAL COORDINATION PRIMITIVE after merge
**Scope:** ChatGPT Architect-controlled repository writers while the Windows Architect MCP remains the active control channel.

## Purpose

Factory Asset and Chapter #4 may execute from separate ChatGPT sessions or scheduled tasks. They may read `origin/main` concurrently, but repository mutation must not race. The Factory graph already requires both a task-scoped lease and a shared `income-os:repo-write` lease; this document defines the exact mechanism that was previously missing.

## Lease implementation

Canonical helper:

`bin/die_engineering_lease.py`

Shared coordination root while Architect MCP remains on Windows:

`D:\mcp-architect\workspace\.engineering-leases`

The helper is OS-neutral, but the coordination root is intentionally bound to the current Architect MCP control host. When Architect MCP is later cut over under the existing `CUT-005 -> MX-053 -> MX-054 -> CUT-006` sequence, the coordination root must be explicitly re-bound; silent dual-root operation is forbidden.

## Required resources

Every Factory Asset repository-mutating run acquires these resources in this exact order:

1. `income-os.repo-write`
2. `factory-asset.<TASK_ID>`

The global resource prevents concurrent Git publication from separate programs. The task resource prevents duplicate execution of the same Factory leaf.

A run that only reads evidence does not need a lease. A run must acquire the pair before the first remote repository mutation such as pushing a branch, creating/updating a PR, merging, or writing canonical state through a repository publication path.

## Atomicity and crash behavior

Each resource is protected by a kernel-held guard lock. The guard is released automatically if the helper process exits. Under that guard, the helper reads/writes one JSON lease record.

Lease records contain only non-secret coordination metadata: resource, random owner token, logical owner, task ID, host, PID, acquisition timestamp, expiry timestamp and TTL.

Default TTL is 5,400 seconds (90 minutes), bounded by the helper to 300..7,200 seconds. A normally completed run must release both leases in `finally`. If a run crashes and leaves records behind, a later acquisition may reclaim them only after expiry while holding the resource guard. Corrupt or unparsable lease state fails closed.

The release path verifies the random token. One runner cannot release another runner's active lease.

## Factory scheduled usage

From a fresh isolated checkout based on current `origin/main`, before repository mutation:

```text
python bin/die_engineering_lease.py acquire-pair \
  --lease-root "D:\mcp-architect\workspace\.engineering-leases" \
  --scope factory-asset \
  --task-id FA-001 \
  --owner factory-asset-hourly \
  --state-file "D:\mcp-architect\workspace\.engineering-leases\factory-asset-FA-001.run.json"
```

Exit semantics:

- `0` + `status=ACQUIRED`: both leases are held; repository mutation may proceed within all other authority rules.
- `3` + `status=BUSY`: another valid writer owns a required lease; make no repository mutation and report the exact owner/task/expiry metadata.
- `2` + `status=ERROR`: lease state/tooling is invalid; fail closed.

Release, always attempted in `finally` after publication/validation or failure:

```text
python bin/die_engineering_lease.py release-pair \
  --state-file "D:\mcp-architect\workspace\.engineering-leases\factory-asset-FA-001.run.json"
```

Inspection is read-only:

```text
python bin/die_engineering_lease.py inspect \
  --lease-root "D:\mcp-architect\workspace\.engineering-leases" \
  --resource income-os.repo-write
```

## Dual-lane rule

Windows `WINDOWS_OAUTH_LAB` tasks and Linux `LINUX_HOURLY_BUILD` tasks may proceed in parallel when they do not mutate the same repository state. Interactive Windows research and provider calls do not hold `income-os.repo-write` merely because they are running.

When either lane publishes canonical repository changes, it must acquire the shared repo-write lease. Unfinished Windows tasks are not a global Linux blocker; only explicit task dependencies and actual lease contention block a Linux leaf.

## Safety invariants

- No lease file contains credentials, cookies, tokens from providers, Git credentials, or secret values.
- The lease root is outside live `C:\DIE`, live `D:\OAUTH`, `/srv/die`, provider profiles and runtime state.
- A lease grants coordination only. It does not grant Founder authority, provider/account authority, spend, submission/publication authority or production cutover authority.
- Absence of a lease never implies permission to mutate; acquisition must return `ACQUIRED`.
- A `BUSY`, corrupt, token-mismatch or helper failure is fail-closed.
- The helper does not reset, stash, clean, deploy, restart or modify production runtime.
