# DIE-H01 Architect Browser/CDP Dispatcher v1

Status: H01-301 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-301 implements the browser/CDP dispatch primitive defined by H01-300. It is an engineering execution mechanism, not another scheduler. Mission Control leases the task first; the dispatcher only binds that already-authorized task attempt to one dedicated authenticated ChatGPT Architect browser resource.

## Lifecycle

```text
Mission Control owner lease already granted
        ↓
lease dedicated engineering browser resource
        ↓
spawn one browser/profile
        ↓
attach loopback CDP only
        ↓
verify ChatGPT composer / auth state
        ↓
inject exact H01-300 bootstrap once
        ↓
worker calls Mission MCP and writes durable checkpoint/result
        ↓
dispatcher observes Mission Control durable evidence
        ↓
close browser in finally
        ↓
release profile lease in finally
```

The dispatcher never chooses the next business task. It receives one already-leased task attempt and never advances the graph from chat text.

## Dedicated browser resource

The logical first engineering resource is `h01-eng-architect-a`. Its actual browser executable, UDD path and profile directory are **host-local runtime bindings**, not canonical product truth. Auth cookies/tokens/session bytes are neither copied into Git nor read by the dispatcher.

A host-local atomic profile lease prevents two dispatcher calls from using the same UDD/profile simultaneously. Lease metadata contains only task ID, dispatch ID, principal, timestamps, PID and a random coordination ID. It never contains the Mission owner lease token.

## CDP boundary

`architect_browser_cdp_driver.mjs` directly spawns the browser and binds DevTools to `127.0.0.1` with an ephemeral port. Remote CDP bind is forbidden.

The driver uses only visible-page CDP operations:

- locate the ChatGPT page target;
- inspect URL/composer/login UI;
- populate `#prompt-textarea`, textarea or contenteditable composer;
- submit through the visible Send button, with Enter as fallback;
- close through `Browser.close`.

It does not call ChatGPT private backend APIs and does not request cookies or storage/session credentials through CDP.

Production dispatch is headful. A headless mode exists solely for the deterministic local HTML fixture and is hard-gated by `DIE_H01_CDP_FIXTURE=1` plus an explicit fixture URL.

## Bootstrap

The bootstrap is generated from ephemeral runtime values only:

```text
project_name
task_id
mission_principal_id
mission_lease_token
dispatch_id
completion_marker
```

Its wording enforces Project-context recovery first, current-canon reconciliation, `mission.task.get` intake, supported MCP-only execution, durable checkpoint/complete/block, and the exact dispatch-bound final marker.

The Mission lease token exists only in memory/stdin long enough to populate the browser composer. It is not written to the browser-profile lease, dispatcher receipt, canonical runtime manifest, or normal logs.

## Durable observation

H01-301 does **not** infer progress or completion from the rendered assistant response. It accepts only Mission task state returned by the Mission observer:

- an owned durable checkpoint; or
- terminal `DONE`, `BLOCKED`, or `VERIFYING`.

The bounded H01-301 dispatcher is intentionally marked `CANARY_ONLY_UNTIL_H01_302`. A first durable checkpoint is enough to prove dispatch acceptance and close the H01-301 canary browser. Long-running production worker supervision must wait for H01-302, which owns progress-aware terminal detection, stall recovery and result ingestion.

This distinction prevents H01-301 from recreating the historical failure mode where a worker was cut merely because the UI looked idle or had not produced a final answer quickly enough.

## Cleanup semantics

Browser close and profile-lease release occur in `finally` on:

- successful durable observation;
- Mission evidence timeout;
- bootstrap submission failure;
- identity mismatch;
- caller exception.

The profile lease is not the Mission owner lease and not the repository publication lease. Remote Git publication remains governed separately by `income-os.repo-write + company-os.<task_id>`.

## Live evidence used for H01-301

The currently running H01-301 owner attempt itself was delivered by Mission Control through adapter `architect-browser-cdp-python` with dispatch `AD-MTXX60OV-4289E7`. The bootstrap reached an authenticated ChatGPT Architect session and the worker wrote durable checkpoint `272`, proving live bootstrap injection plus Mission checkpoint observation.

A second authenticated copy of the same leased task was deliberately **not** opened, because doing so would violate H01-300's one task-attempt/session contract.

Browser lifecycle closure was independently exercised against a real Google Chrome process using the hard-gated local fixture: direct spawn → loopback CDP → composer injection → submit → `Browser.close`. The root browser exited with code 0 and its temporary UDD was removed. Unit tests additionally prove close/release on success, timeout and submission failure.

## Acceptance boundary

H01-301 is accepted when canon contains executable dispatcher code, the real CDP UI driver, host-local binding policy, tests, and receipt proving:

1. one dedicated profile can be atomically leased;
2. bootstrap is submitted once through loopback CDP;
3. durable Mission evidence—not chat text—is observed;
4. browser and profile lease close/release deterministically;
5. no Mission/provider/browser secret is persisted;
6. current live Mission adapter evidence is reconciled to the implementation;
7. H01-302 becomes READY for the production-safe completion detector.

H01-301 does not implement H01-302 recovery semantics, H01-303 parallel Git/worktree isolation, or H01-304 two-worker parallel acceptance.
