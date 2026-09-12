# DIE-H01 Architect Worker Completion / Result Ingestion v1

Status: H01-302 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-302 upgrades the H01-301 browser dispatcher from a checkpoint canary into progress-aware completion supervision. The core rule is simple:

> **Rendered browser text is activity evidence, never completion authority. Mission Control durable state is completion authority.**

This prevents a browser worker from being cut merely because the UI appears idle, a partial answer looks final, a marker appears before protocol reconciliation, or the observer process itself reaches a timeout.

## Completion authority

The supervisor polls the canonical Mission task and accepts terminal truth only from durable Mission state:

- `DONE` -> owner completion accepted;
- `VERIFYING` -> owner completion accepted, independent review still pending;
- `BLOCKED` -> durable block;
- `READY` without owner lease -> attempt ended/requeued, not DONE;
- `FAILED` / `CANCELLED` -> durable unsuccessful terminal state.

For successful `DONE` / `VERIFYING`, result ingestion requires the owner final checkpoint written by `mission.task.complete`: `progress=100` plus payload keys `result` and `artifacts`. A terminal success state without that checkpoint fails closed as `E_DURABLE_RESULT_MISSING`.

The final browser marker `MC005_ARCHITECT_RESULT_<dispatch_id>` remains correlation evidence. A marker while Mission is still `RUNNING` produces `MARKER_AHEAD_OF_PROTOCOL` and the supervisor keeps waiting. Conversely, a durable Mission completion remains authoritative even if the rendered marker is missing or delayed.

## Progress signals

H01-302 deliberately separates **progress** from **completion**.

Durable progress signals:

- new owned Mission checkpoint;
- checkpoint progress change;
- Mission lease heartbeat / expiry update;
- current owner-attempt status/update change.

Browser/UI progress signals are metadata only:

- assistant response node count;
- last assistant response character count;
- visible `Stop generating`/`Stop response` control;
- composer readiness;
- expected marker present / marker candidate IDs;
- auth-required state.

The CDP driver never emits the assistant response text itself. It also never reads cookies, tokens or storage/session credentials.

A visible generating control is positive activity even if response length has not changed yet. This is specifically intended to avoid aggressive cuts while a model is thinking/generating.

## Stall policy

Production defaults:

```text
poll_seconds                 = 2
stall_seconds                = 5400  (90 minutes)
mission_error_grace_seconds  = 300   (5 minutes)
marker_reconcile_seconds     = 30
minimum_stall_seconds        = 300   (5 minutes hard floor)
```

The 5,400-second default reconciles with the live Mission Control Architect adapter, which already treats a fresh Mission heartbeat inside that window as `PROTOCOL_ACTIVE` after observer timeout. H01-302 makes the policy explicit and also considers browser-side progress. The 300-second Mission observer grace is not a kill timer: if the browser is still visibly generating or UI metadata is still changing, the worker remains alive beyond that grace until the actual no-progress stall boundary is reached.

Any configured stall threshold below 300 seconds is rejected as `E_POLICY_STALL_TOO_AGGRESSIVE`.

There is no rendered-chat idle timeout that means DONE. A worker becomes stall-recovery eligible only after the configured interval has no new durable progress **and** no UI progress/generating signal.

## Recovery semantics

The completion supervisor returns `RECOVERY_REQUIRED`—never fake completion—when it observes conditions such as:

- browser process exited while Mission remains active;
- active Mission task has no owner lease;
- owner lease expired;
- owner attempt ended while task still reports active;
- authenticated browser became `AUTH_REQUIRED`;
- no durable or UI progress for the stall interval;
- Mission observer is unavailable beyond its grace window;
- unknown durable task status.

Recovery closes the owned browser and releases the engineering profile lease in `finally`. It does **not** select a replacement task, change providers, reacquire Mission ownership, or mark the task DONE. Those remain Mission Control scheduler/failover decisions.

## Result ingestion

`ResultJournal` provides an optional local idempotent cache of the already-durable Mission result. It is not a second source of truth.

One dispatch writes one `<dispatch_id>.json`. Re-ingesting byte-identical data returns `UNCHANGED`; conflicting bytes fail closed. Persistence rejects known secret-bearing keys including Mission/review lease tokens, access/refresh tokens, authorization, cookies, credentials and raw session bytes.

The ingested record binds:

```text
task_id
principal_id
dispatch_id
durable_status
terminal_checkpoint_id
summary
result
artifacts
marker_correlation
attempt_no
completion_authority = MISSION_CONTROL_DURABLE_STATE
```

## CDP observation upgrade

H01-302 extends `architect_browser_cdp_driver.mjs` to emit metadata-only JSONL `OBSERVATION` records after the initial `SUBMITTED` record. `NodeCdpSession` consumes them asynchronously without blocking the browser.

A deterministic real-Chrome fixture proved:

```text
SUBMITTED
  debug_host=127.0.0.1
        ↓
OBSERVATION
  assistant_nodes=1
  assistant_chars=12
  stop_visible=true
  composer_ready=true
  auth_required=false
        ↓
Browser.close
  exit_code=0
  root_process_gone=true
```

No response body, cookies or session material were emitted.

## Live control-plane reconciliation

The live Windows Mission Control implementation observed during H01-302 already contains two compatible safeguards:

1. `architectProtocolActiveAfterObserverError(..., idleSeconds=5400)` preserves an active protocol after observer timeout when the Mission lease heartbeat remains fresh.
2. `missionTaskComplete` writes a final owner checkpoint with `progress=100` and `{result, artifacts}` before releasing the owner lease and moving the task to `DONE` or `VERIFYING`.

H01-302 does not mutate that separate control-plane repository. It freezes an H01-side executable contract that consumes those durable semantics and can be integrated by the dispatcher/runtime without introducing a second scheduler.

## H01-301 integration standing

H01-301's `dispatch_canary()` remains as the historical bounded canary primitive. Production-safe worker ownership now uses `architect_worker_completion.monitor_worker()`, which holds the browser/profile through intermediate checkpoints and only closes on durable terminal ingestion or a bounded recovery condition.

Therefore the H01 dispatcher is no longer conceptually limited to “close after first checkpoint”; H01-302 supplies the progress-aware lifecycle required before parallel acceptance.

## Non-goals

H01-302 does not implement parallel Git/worktree/repository-write isolation (H01-303), does not run the Founder-gated two-worker parallel canary (H01-304), and does not scale workers by graph width (H01-305).
