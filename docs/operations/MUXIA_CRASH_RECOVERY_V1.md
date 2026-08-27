# MUXIA MX-041 — CRASH RECOVERY V1

Status: VERIFIED / COMPLETE
Date: 2026-08-27
Task: `MX-041 — Crash recovery`

## Purpose

Prove that an interrupted browser-backed assignment never becomes a false success and that a crashed profile lease is recovered deterministically when ownership is unambiguous.

## Recovery policy

MUXIA core now includes `src/core/crash-recovery.ts`.

Recovery rules:

- if the recorded browser PID is still alive -> no recovery action;
- if the profile is RUNNING, lease owner matches the expected owner, and the PID is dead -> RUNNING/VERIFYING job becomes FAILED, then the lease is released and profile returns to READY;
- if owner/state/PID metadata is ambiguous -> fail closed with `QUARANTINE_REQUIRED`; do not guess ownership;
- a recovered interrupted job must never become SUCCEEDED without durable artifact evidence.

## Unit verification

`tests/core/crash-recovery.test.mjs` verifies:

1. crashed RUNNING assignment -> FAILED + profile READY;
2. live process -> NOOP, no premature recovery;
3. owner ambiguity -> QUARANTINE_REQUIRED with no mutation;
4. recovered FAILED job cannot be promoted to SUCCEEDED.

Targeted suite: 4/4 PASS.

## Real Windows fault injection

Victim profile: `chatgpt-b`.

Control profile: authenticated `chatgpt-a` remained alive and was not modified.

Injected sequence:

```text
chatgpt-b READY
  -> acquire lease mx041-worker-b
  -> launch Edge PID 17568
  -> mark profile RUNNING
  -> create job mx041-crash-job-001
  -> job RUNNING
  -> taskkill process tree
  -> PID dead
  -> recoverCrashedAssignment()
  -> job FAILED
  -> lease released
  -> profile READY
```

Post-recovery:

- browser B process count: 0;
- job: `FAILED`;
- profile B: `READY`, `leaseOwner = null`, `browserPid = null`;
- lease file absent;
- artifact receipt absent;
- explicit false-success attempt rejected with `ARTIFACT_RECEIPT_NOT_FOUND`.

Acceptance:

- interrupted job never succeeded: PASS;
- crashed process dead: PASS;
- lease recovered: PASS;
- no fabricated artifact receipt: PASS.

## Full regression

- TypeScript strict build: PASS;
- core tests: 40/40 PASS;
- parity tests: 5/5 PASS;
- total: 45/45 PASS.

## Runtime preservation

Authenticated profile A remained alive on Edge PID `21400` in RDP session 2.

Proxima remained live/untouched:

- `127.0.0.1:3211` -> Electron provider/session API;
- `127.0.0.1:8501` -> Python `proxima_agent.web` dashboard.

## Canonical artifacts

- `company/muxia/src/core/crash-recovery.ts`
- `company/muxia/tests/core/crash-recovery.test.mjs`
- `company/muxia/scripts/mx041-crash-injection.mjs`
- `company/muxia/receipts/MX-041-crash-recovery.receipt.json`

## Verdict

MX-041 PASS.

Next DAG node: `MX-042 — Two-profile bounded concurrency`.
