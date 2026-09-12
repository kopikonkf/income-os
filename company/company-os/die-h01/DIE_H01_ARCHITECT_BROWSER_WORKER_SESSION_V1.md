# DIE-H01 ChatGPT Architect Browser-Worker Session Contract v1

Status: H01-300 ACCEPTANCE CANDIDATE
Date: 2026-09-12
Scope: engineering-worker sessions executed through authenticated ChatGPT Architect browser sessions. This contract defines the session boundary; H01-301/302/303 implement dispatch, completion detection and parallel isolation enforcement.

## 1. Authority model

Mission Control is the sole durable task/graph authority. A ChatGPT Architect browser session is an execution worker, not a scheduler and not a source of task truth.

Each browser worker MUST own exactly one Mission Control task attempt at a time:

```text
one browser session
  -> one task_id
  -> one mission_principal_id
  -> one active task-scoped owner lease capability
  -> one dispatch_id / attempt
  -> one isolated /home/kopiko/die-sessions/<task_id> worktree when repository work is required
  -> bounded checkpoints
  -> one durable terminal Mission outcome
  -> one final result marker only after durable completion succeeds
```

A worker MUST NOT multiplex unrelated Mission tasks inside one chat session, self-select another task, advance the graph from chat memory, or treat visible assistant prose as canonical task state. This is the explicit **no chat-memory-only completion** rule.

## 2. Bootstrap contract

The dispatcher gives the browser worker only enough authority to recover context and fetch the authoritative Work Card. The bootstrap is transport text, not task truth.

Required ephemeral bootstrap values:

- `project_name`
- `task_id`
- `mission_principal_id`
- `mission_lease_token`
- `dispatch_id`
- `completion_marker = MC005_ARCHITECT_RESULT_<dispatch_id>`

The lease token is an ephemeral capability. It MUST NOT be committed to Git, persisted in canonical receipts, copied into ordinary logs, included in final result artifacts, or reused for another task.

Normative bootstrap instructions are:

1. recover relevant cross-session context from the named ChatGPT Project;
2. reconcile recovered context with current Git canon;
3. call `mission.task.get` with the supplied task/principal/owner lease before task execution;
4. do not rely on bootstrap prose for task details;
5. use only supported ChatGPT Architect MCP / Universal MCP execution paths and never simulate Mission calls;
6. use `mission.task.checkpoint`, `mission.task.complete`, or `mission.task.block` for durable state;
7. emit the exact completion marker on the final line only after `mission.task.complete` returns durable success.

The Work Card returned by `mission.task.get`, plus current canon, overrides stale chat memory or an older source SHA embedded in dispatch metadata.

## 3. Session phases

### Phase A — context recovery

The worker reads Project sources/prior session context relevant to the task. Context helps continuity but never grants readiness, authority, mutation permission or completion.

### Phase B — authoritative intake

The worker calls `mission.task.get`. Invalid/expired/mismatched lease capability is fail-closed: do not execute from guessed task details and do not simulate a reacquire.

The worker reconciles the returned source node/acceptance with current `origin/main`. If current canon materially conflicts with the leased task, checkpoint/block rather than silently inventing a new scope.

### Phase C — durable start/checkpoint

Before substantial mutation the worker writes a Mission checkpoint summarizing recovered context, reconciled canon, locked scope and safety boundaries. Long tasks heartbeat/checkpoint sufficiently to retain the owner lease.

### Phase D — isolated engineering workspace

Repository engineering uses the H01-003 lifecycle:

```text
/home/kopiko/die-sessions/<task_id>
```

created from freshly fetched `origin/main` through `bin/die_h01_worktree.py`. `/srv/die` remains protected legacy-live/rollback. A worker does not share a mutable engineering worktree with another task.

Read-only/cognition tasks need not manufacture repository mutation, but any repository write must occur only in the task's isolated worktree.

### Phase E — execution

The worker executes only Work Card scope. It may use current canon and approved tools, but may not expand business scope, infer Founder approval, fabricate tool calls, or declare success from chat text.

Repository publication is separately serialized by `docs/operations/DIE_ENGINEERING_LEASE_V1.md`. `income-os.repo-write` plus the task-scope engineering lease is acquired immediately before remote Git mutation and released in `finally`; it is not held for the whole browser session.

### Phase F — durable terminal state

Successful work calls `mission.task.complete` with bounded summary/result/artifacts. Failure that cannot safely complete calls `mission.task.block` with the real reason. A worker that loses its owner capability cannot mark itself DONE from chat.

For reviewed tasks, `mission.task.complete` may move to VERIFYING rather than DONE; the worker reports the returned durable state honestly.

## 4. Completion marker contract

The exact completion marker is:

```text
MC005_ARCHITECT_RESULT_<dispatch_id>
```

Example shape only:

```text
MC005_ARCHITECT_RESULT_AD-EXAMPLE-123456
```

Rules:

- marker MUST be the final non-whitespace line of the worker's final response;
- marker MUST equal the bootstrap marker exactly;
- marker MUST NOT be emitted before a successful `mission.task.complete` response;
- `mission.task.block`, lease loss, tool failure or ordinary chat completion MUST NOT emit the success marker;
- marker is correlation evidence for H01-302/result ingestion, not completion authority by itself;
- Mission Control durable state/result remains authoritative even if rendered chat text is missing, duplicated or delayed.

## 5. Machine-readable result contract

The worker's durable `mission.task.complete` result SHOULD contain bounded non-secret fields sufficient for audit and recovery:

```json
{
  "status": "PASS",
  "task_id": "H01-NNN",
  "dispatch_id": "AD-...",
  "origin_main": "<published canon sha when applicable>",
  "validation": {},
  "worktree_closed": true,
  "repo_write_lease_released": true
}
```

Artifacts are logical paths/URLs/hashes, never lease tokens, cookies, provider credentials or browser session material. `origin_main`, worktree and repo-write fields may be null/not-applicable for cognition-only tasks that do not publish repository changes.

## 6. No chat-memory-only completion

These are explicitly insufficient to mark work DONE:

- assistant says "done";
- final marker appears without durable Mission completion;
- browser tab closes;
- repository commit exists locally but is unpublished;
- PR exists but acceptance requires merge and merge has not occurred;
- worktree has files but no durable receipt;
- previous conversation claims a dependency is complete while current canon/Mission state disagrees.

H01-302 must therefore use Mission Control durable state as primary completion evidence. Rendered chat/marker is only a bounded correlation signal.

## 7. Parallel-worker invariants

This contract permits multiple Architect browser workers only when Mission Control has leased different dependency-safe tasks. H01-303 is responsible for enforcement, but the contract already forbids:

- two workers owning the same task attempt/owner lease;
- two tasks sharing one mutable worktree;
- concurrent remote Git mutation without the shared `income-os.repo-write` lease;
- bypassing dependency/merge gates because another chat claims progress;
- sharing Mission lease tokens between workers.

The dispatcher may observe task/lease state; it does not become a second scheduler. Mission Control decides which task is ready and who owns it.

## 8. Session closure

After durable publication/completion, the worker closes its H01 worktree through the H01-003 helper only when clean and published. Publication lease is released in `finally`. Browser lifecycle closure belongs to H01-301/302; closing the browser before durable terminal state is never equivalent to task completion.

## 9. Non-goals

H01-300 does not implement browser/CDP dispatch, progress detection, stalled-session recovery, parallel canary execution, UDD/profile leasing or production asset generation. Those remain H01-301..305 or other task tracks.

## 10. Acceptance invariants

Canon must state and machine-check that:

1. one browser worker maps to exactly one Mission task/principal/owner lease/dispatch attempt;
2. Work Card is fetched from Mission Control after Project-context recovery;
3. one isolated H01 worktree is used for repository engineering;
4. `/srv/die` remains forbidden for engineering mutation;
5. remote Git writes require the canonical repo-write + task-scope engineering lease pair;
6. durable Mission checkpoint/complete/block are authoritative;
7. success marker is exactly dispatch-bound and emitted only after durable completion success;
8. no lease/session secret is persisted in canon/result artifacts;
9. chat memory/rendered text alone can never mark a task DONE.
