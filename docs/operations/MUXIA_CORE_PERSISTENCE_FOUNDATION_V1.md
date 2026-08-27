# MUXIA CORE PERSISTENCE FOUNDATION V1

Status: BATCH MUXIA-B02 COMPLETE
Date: 2026-08-27
Batch: `MUXIA-B02 — Core Persistence Foundation`
Atomic tasks: `MX-021 -> MX-022 -> MX-023`
Execution policy: `STOP_ON_FIRST_FAILURE`

## Outcome

MUXIA now has an OS-neutral local persistence foundation for configuration paths, profile metadata/leases, jobs, and durable artifact receipts. The implementation remains provider-neutral and contains no browser, Playwright, ChatGPT, credential, or Proxima runtime integration.

## MX-021 — Config/path abstraction

Implemented:

- `company/muxia/src/core/paths.ts`
- `company/muxia/tests/core/paths.test.mjs`

Path contract:

- `MUXIA_ROOT` is the production/runtime override;
- when not configured, development fallback is `<home>/.muxia`;
- logical child paths are derived from the root rather than hard-coded host paths;
- Windows and Linux path semantics are explicitly testable through `path.win32` / `path.posix` fixtures;
- path confinement helper rejects paths escaping their assigned root;
- runtime IDs use a bounded safe identifier contract.

Logical layout:

```text
<MUXIA_ROOT>/
  profiles/
  jobs/
  artifacts/
  state/
    locks/
    receipts/
  logs/
```

Production may later bind the same code to, for example, a Windows or Linux root through configuration; those physical paths are not embedded in core source.

Verification: `4 passed / 0 failed`.

## MX-022 — Profile Registry

Implemented:

- `company/muxia/src/core/storage.ts`
- `company/muxia/src/core/profile-registry.ts`
- `company/muxia/tests/core/profile-registry.test.mjs`

Profile metadata is persisted as sanitized JSON under:

`<MUXIA_ROOT>/state/profiles/<profile_id>.json`

Actual future browser profile data remains separately rooted under:

`<MUXIA_ROOT>/profiles/<profile_id>/...`

Exclusive lease implementation uses filesystem create-exclusive semantics (`wx`) at:

`<MUXIA_ROOT>/state/locks/profile-<profile_id>.lease.json`

This means a second registry/process on the same filesystem cannot silently acquire the same profile while an active lease exists.

Fail-closed rules:

- duplicate lease rejected;
- wrong owner cannot release a lease;
- profile path must remain under configured profile root;
- unknown fields are rejected;
- credential/session-shaped metadata fields are rejected;
- ambiguous/stale lock recovery is not guessed automatically; later recovery work owns that policy.

Verification: `4 passed / 0 failed`.

## MX-023 — Job + Artifact Registry

Implemented:

- `company/muxia/src/core/artifact-registry.ts`
- `company/muxia/src/core/job-registry.ts`
- `company/muxia/tests/core/job-artifact-registry.test.mjs`

Jobs are persisted independently under:

`<MUXIA_ROOT>/jobs/<job_id>.json`

Artifact receipts are persisted under:

`<MUXIA_ROOT>/state/receipts/<job_id>.json`

Job artifact targets are confined beneath the configured MUXIA artifact root.

A job may reach `SUCCEEDED` only after the Artifact Registry re-opens the current physical artifact and confirms:

- artifact exists;
- container is accepted PNG/JPEG/WebP;
- physical SHA-256 matches receipt;
- current byte count matches receipt;
- current detected MIME matches receipt;
- job/provider lineage matches;
- artifact remains inside the job target and MUXIA artifact root.

The receipt is therefore not merely historical text: physical evidence is revalidated at completion time.

Restart safety is demonstrated by destroying/re-instantiating registry objects between persistence and completion. A corrupt artifact after receipt creation blocks `SUCCEEDED` after restart.

Failed jobs may be requeued through the state machine; attempt count increments and survives restart.

Verification: `5 passed / 0 failed`.

## Persistence mechanics

MUXIA V1 local metadata persistence intentionally uses simple filesystem primitives rather than introducing a database before evidence requires one:

- UTF-8 JSON documents;
- temporary file creation;
- file flush (`fsync`);
- atomic rename into the canonical filename;
- create-exclusive lease files.

This is a **single-host/local-filesystem persistence contract**, not a distributed consensus system. Multi-host locking/database semantics are explicitly deferred until MUXIA proves a real need for clustering.

## Dependencies

Runtime npm dependencies: **0**.

Development dependency added:

- `@types/node` — TypeScript type definitions only.

`npm install` audit at installation time: `0 vulnerabilities`.

## Full batch regression

`npm test` from `company/muxia`:

```text
TypeScript strict build: PASS
Core tests:   21 passed / 0 failed
Parity tests:  5 passed / 0 failed
Total:        26 passed / 0 failed
```

Core total includes previously established MX-020 tests plus all B02 path/profile/job/artifact tests.

## Non-goals / untouched boundaries

B02 did not:

- launch Playwright/Chromium;
- create or migrate browser profiles;
- read cookies/tokens/session storage;
- call ChatGPT or another provider;
- modify/restart/stop Proxima;
- migrate Windows to Linux;
- generate a production asset;
- submit/publish/spend;
- create distributed/multi-host persistence.

## Next DAG eligibility

Completion of MX-023 unlocks two independent nodes:

- `MX-030 — Playwright Chromium driver`;
- `MX-P01 — Legacy profile-root metadata probe`.

These are candidates for the next browser-foundation batch, but B02 itself ends here.
