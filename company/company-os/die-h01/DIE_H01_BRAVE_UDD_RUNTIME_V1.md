# DIE H01 Brave UDD Runtime v1

Status: H01-025 IMPLEMENTED / LIVE ACCEPTED
Date: 2026-09-12

## Purpose

H01-025 owns the host-local Brave lifecycle for one selected H01 profile/job. It does not schedule work, choose providers, mutate Mission Control, or read/export browser authentication state.

```text
selected profile + provider/job
        -> canonical host manifest binding
        -> existing /opt/die/h01/bin/h01-brave-profile launcher
        -> UDD-level flock enforces one sibling owner
        -> loopback CDP only
        -> enforce exactly one provider page
        -> wait for durable terminal result
        -> Browser.close
        -> verify browser/CDP gone and UDD lock released
```

H01-026 later chooses sibling profiles/providers fairly. H01-107 later performs real SVG provider canaries. H01-025 only guarantees the execution envelope.

## Runtime ownership

The runtime reuses the already accepted launcher and 20-UDD/100-profile manifest. It does not create a second browser manager. Profile mapping is deterministic: p001..p005 -> s01, p006..p010 -> s02, through p096..p100 -> s20; CDP ports are 9201..9300 and must bind to 127.0.0.1.

The launcher owns the UDD `flock`. If any sibling is active, a second sibling launch fails closed with exit code 73 / `UDD_BUSY`.

## One committed provider page/job

After browser startup, the controller selects the requested provider origin, closes restored/extraneous page targets, and fails unless exactly one provider page remains. Service workers and browser internals are not counted as committed page jobs.

The runtime supports two terminal modes:

- `probe`: writes a durable readiness result itself; used only for H01-025 acceptance.
- `wait-result`: waits for an external terminal receipt whose `job_id`, `provider_id`, `profile_id`, and terminal state match the committed job. This is the production handoff used by H01-107/H01-104A.

A terminal result must exist durably before Brave is closed. Terminal states accepted by the lifecycle gate are SUCCEEDED, FAILED, TIMEOUT, CANCELLED, UNSUPPORTED, AMBIGUOUS, and EMPTY.

## Safety boundary

H01-025 never reads browser cookies, tokens, Local Storage, IndexedDB, session databases, or profile bytes. It does not submit provider generation in its acceptance probe and has no submission/publication authority. Mission Control remains upstream authority/scheduler and is not modified by this task.

## Live acceptance

Canary `H01-025-CANARY-002` used p001/s01/9201 and ChatGPT without prompt submission. During the active job, exactly one ChatGPT page existed. A concurrent p005 launch on sibling s01 failed with RC=73 / `UDD_BUSY h01-web-s01`. The durable SUCCEEDED job receipt was written before Browser.close; afterward process and CDP 9201 were gone and the UDD lock was free.

Canary `H01-025-CANARY-003` proved production `wait-result` semantics: the runtime held one ChatGPT page while no result existed, consumed an external H01-104A-compatible terminal result, then closed Brave and released the UDD lock.

Implementation: `engineering/brave_udd_runtime.mjs`.
