# MUXIA-B05 — WINDOWS SCALING PROOF

Status: COMPLETE / PASS
Date: 2026-08-27
Execution: `MX-042 -> MX-043`, `STOP_ON_FIRST_FAILURE`

## Scope

Prove that MUXIA can run bounded synthetic workloads across two and four independent browser-profile lanes with correct job/profile lineage, exclusive leases, isolated browser storage/artifacts/logs, captured resource metrics, and clean teardown.

This is a runtime multiplexing proof, not a claim about ChatGPT provider-side throughput, rate limits, or unattended consumer-web output automation.

## Lineage hardening

Before load execution, artifact verification was strengthened so a receipt whose `profileId` differs from `job.profileSelector` fails closed with `ARTIFACT_PROFILE_MISMATCH`.

Regression coverage was added and passes.

## MX-042 — Two-profile bounded concurrency

Participants: `chatgpt-b`, `chatgpt-c`.

Results:

- both lanes overlapped: PASS;
- overlap: 3531 ms;
- duplicate lease attempts rejected: PASS;
- job/profile/receipt lineage: PASS;
- synthetic browser storage cross-contamination: NONE;
- artifact/log contamination: NONE;
- aggregate Edge working set sample: 1,194,856,448 bytes;
- aggregate Edge process count sample: 24;
- teardown: clean;
- task verdict: PASS.

## MX-043 — Four-profile bounded concurrency

Participants: `chatgpt-b`, `chatgpt-c`, `chatgpt-d`, `chatgpt-e`.

Results:

- all four lanes overlapped: PASS;
- overlap: 4756 ms;
- duplicate lease attempts rejected: PASS;
- job/profile/receipt lineage: PASS;
- synthetic browser storage cross-contamination: NONE;
- artifact/log contamination: NONE;
- aggregate Edge working set sample: 2,581,938,176 bytes;
- aggregate Edge process count sample: 55;
- all four jobs reached SUCCEEDED with durable raster receipts.

The initial MX-043 runner wrote a functional PASS receipt but timed out during teardown while Playwright/CDP browser-close shutdown waited. The task was not closed at that point.

## MX-043-R1 — Deterministic four-lane teardown

A single minimal repair child was created under the repair rule.

Recovery:

- owned browser process trees B-E terminated by recorded PID;
- B-E leases released with exact matching owners;
- B-E registry states returned to READY;
- browserPid values cleared;
- residual temporary Edge process count = 0;
- authenticated control profile A remained alive and responsive.

The bounded concurrency runner was patched to use deterministic owned-process termination before lease release instead of awaiting `browser.close()` during teardown.

## Resource envelope

Observed synthetic workload scaling:

- 2 lanes working set: 1,194,856,448 bytes;
- 4 lanes working set: 2,581,938,176 bytes;
- 4/2 working-set ratio: ~2.1609x;
- 2 lanes Edge process count: 24;
- 4 lanes Edge process count: 55;
- 4/2 process-count ratio: ~2.2917x.

These measurements are host/runtime envelope evidence only. Browser subprocess topology is dynamic, so they are not hard production limits.

## Final regression

- TypeScript strict build: PASS;
- core tests: 41/41 PASS;
- parity tests: 5/5 PASS;
- total: 46/46 PASS.

## Runtime preservation

- temporary B-E Edge processes after batch: 0;
- profiles B-E: READY / no lease;
- authenticated profile A Edge PID 21400: preserved/responsive;
- Proxima `127.0.0.1:3211` PID 6892: live/untouched;
- Proxima `127.0.0.1:8501` PID 26508: live/untouched.

No provider credential values were read. No provider prompt/output automation was used. No paid spend occurred.

## Canonical receipts

- `company/muxia/receipts/MX-042-two-profile-bounded-concurrency.receipt.json`
- `company/muxia/receipts/MX-043-four-profile-bounded-concurrency.receipt.json`
- `company/muxia/receipts/MX-043-R1-deterministic-teardown.receipt.json`
- `company/muxia/batches/MUXIA-B05-windows-scaling-proof.receipt.json`

## Verdict

MUXIA-B05 = COMPLETE / PASS.

Next DAG node: `MX-050 — Linux runtime bootstrap`.
