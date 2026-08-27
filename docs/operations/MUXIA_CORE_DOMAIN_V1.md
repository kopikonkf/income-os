# MUXIA CORE DOMAIN V1

Status: MX-020 VERIFIED / COMPLETE
Date: 2026-08-27
Product: MUXIA
Scope: provider-neutral core modeling only; no browser/provider execution

## Outcome

MX-020 establishes the first DIE-owned MUXIA implementation code. It is independent of Proxima source and contains no Electron, Playwright, browser, provider, credential, or session implementation.

Artifacts:

- `company/muxia/package.json`
- `company/muxia/tsconfig.json`
- `company/muxia/src/core/domain.ts`
- `company/muxia/contracts/muxia.core-domain.v1.schema.json`
- `company/muxia/tests/core/domain.test.mjs`

## Domain contracts

### Provider

Fields: provider ID, adapter version, capabilities, health.

Health states:

`UNKNOWN | HEALTHY | DEGRADED | BLOCKED`

### Profile

Fields include profile ID, provider ID, configurable profile path, lifecycle state, lease owner, browser PID metadata, health/success timestamps, and failure count.

Lifecycle:

`UNINITIALIZED -> READY -> LEASED -> RUNNING`

with fail-safe exceptional states:

`AUTH_REQUIRED | BLOCKED | QUARANTINED | DISABLED`

A profile may have only one active lease owner.

### Job

States:

`QUEUED | ASSIGNED | RUNNING | VERIFYING | SUCCEEDED | WAITING_OPERATOR | BLOCKED | FAILED | CANCELLED | TIMED_OUT`

`SUCCEEDED` is reachable only from `VERIFYING`, never directly from queued/running states.

### Artifact receipt

The core type binds job/profile/provider lineage, path, SHA-256, bytes, MIME, adapter version, creation time, and `VERIFIED` status.

## Fail-closed invariants

1. duplicate profile lease -> rejected;
2. wrong lease owner cannot run/release profile;
3. READY cannot skip directly to RUNNING;
4. disabled profile cannot silently reactivate;
5. QUEUED cannot skip to SUCCEEDED;
6. terminal SUCCEEDED cannot return to RUNNING;
7. transition to SUCCEEDED requires completion evidence proving artifact existence, receipt existence, hash agreement, byte-count agreement, and MIME agreement.

These rules implement the MX-012 physical-evidence doctrine at the domain state-machine level.

## Verification

TypeScript:

`tsc -p company/muxia/tsconfig.json` -> PASS under strict mode.

Core tests:

`node --test company/muxia/tests/core/domain.test.mjs`

Result: `8 passed / 0 failed`.

Parity regression:

`node --test company/muxia/tests/parity/muxia-parity-contract.test.mjs`

Result: `5 passed / 0 failed`.

No new npm dependency was installed. The host already provides Node.js, npm, and TypeScript.

## Boundary

MX-020 did not:

- launch Chromium/Playwright;
- inspect or mutate browser profiles;
- call ChatGPT or another provider;
- alter Proxima;
- touch credentials/session values;
- generate assets;
- submit/publish/spend.

## Next dependency

Completion of MX-020 makes `MX-021 — Config/path abstraction` eligible. `MX-P03` remains an independent policy gate that must complete before unattended ChatGPT web-adapter execution/output logic.
