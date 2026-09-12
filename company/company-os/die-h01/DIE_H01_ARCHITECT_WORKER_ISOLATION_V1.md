# DIE-H01 Architect Worker Isolation v1

Status: H01-303 ACCEPTANCE CANDIDATE
Date: 2026-09-12
Scope: parallel ChatGPT Architect engineering workers only. Mission Control remains the sole scheduler and durable task authority.

## Purpose

H01-303 closes the gap between the H01-300 session contract and parallel execution. A worker may mutate repository state only from its exact task worktree, while a host-local claim prevents a second worker from concurrently mutating that same worktree. Remote Git publication remains separately serialized by the existing global engineering lease protocol.

The implementation is `company/company-os/die-h01/engineering/architect_worker_isolation.py`.

## Canonical dependency and merge gate

Before a worker claims a mutable workspace, the isolation layer reads the H01 task graph from `refs/remotes/origin/main`, not from the worker branch. Every declared dependency must be `DONE`, and the target task must be in a dispatchable canonical status.

This rule is intentionally conservative. A worker branch may locally mark an upstream task `DONE`, but that unmerged branch cannot unlock a downstream task. The downstream gate changes only after the corresponding task-graph state is visible on canonical `origin/main`. The guard is a preflight only: it does not lease Mission work, choose the next task, mutate the graph, or bypass Founder authority.

## Mutable worktree gate

Repository mutation is allowed only when all of the following are true:

- path resolves exactly to `/home/kopiko/die-sessions/<task_id>`;
- the Git top-level is exactly that path;
- the H01-003 lifecycle receipt exists, matches the same task/path, and is `OPEN`;
- neither the Git dir nor common Git dir resolves inside protected `/srv/die`;
- the resolved worktree has one exclusive active mutation claim.

The claim is keyed by the resolved worktree path and records only task/principal/dispatch coordination metadata plus a random release token. A second claim fails closed with `E_MUTABLE_WORKTREE_BUSY`. Corrupt claim state also fails closed.

Claims deliberately do not auto-expire. A timeout must not silently hand a mutable worktree to a second worker while the first worker may still be alive. Crash/stale-claim recovery therefore belongs to durable Mission reconciliation before cleanup.

Different tasks may use different worktrees that share a safe non-live Git common directory. Sharing Git object/ref storage is not the same as sharing a mutable checkout.

## Repository publication lease

H01-303 does not create a Linux shadow repo-write lock. Publication continues to use the one canonical control-plane lease root defined by `DIE_ENGINEERING_LEASE_V1.md`:

```text
income-os.repo-write
company-os.<task_id>
```

The pair is acquired immediately before remote Git mutation and released in `finally`. An active `income-os.repo-write` held by another task makes the second publisher fail closed. The Mission owner lease is task authority, not repository-write coordination.

Creating a second Linux lease root would split coordination and permit two writers to believe they are exclusive, so it is explicitly forbidden.

## Lifecycle

```text
Mission task already leased by control plane
        -> read canonical origin/main dependency gate
        -> validate exact H01-003 worktree + OPEN lifecycle receipt
        -> acquire exclusive mutable-worktree claim
        -> execute local edits/tests/commit
        -> acquire control-plane repo-write + company-os.<task_id> pair only for publication
        -> publish under existing authority rules
        -> release publication pair in finally
        -> release mutable-worktree claim
```

A local commit does not unlock downstream work. A local task-graph edit does not unlock downstream work. A PR existing does not unlock downstream work. Canonical `origin/main` plus Mission Control remain the merge/dependency truth.

## H01-303 acceptance

Acceptance requires machine evidence that:

1. one task is bound to its exact task worktree and OPEN lifecycle state;
2. a second parallel worker cannot claim the same mutable worktree;
3. distinct task worktrees can be claimed independently;
4. corrupt/stale coordination cannot be silently bypassed;
5. Git metadata under `/srv/die` is rejected;
6. an unmerged worker branch cannot unlock a downstream dependency gate;
7. conflicting `income-os.repo-write` acquisition across tasks fails closed;
8. the publication lease pair remains exactly `income-os.repo-write + company-os.<task_id>` with no Linux shadow root;
9. H01-304 becomes dependency-ready only after H01-302 and H01-303 are canonically `DONE`, while its `FOUNDER_REQUIRED` authority remains unchanged.

H01-303 does not run the two-worker browser canary; that remains H01-304.
