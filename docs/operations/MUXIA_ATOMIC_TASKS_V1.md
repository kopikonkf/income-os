# MUXIA ATOMIC TASKS V1

Status: CANON TASK GRAPH / EXECUTION ACTIVE
Date: 2026-08-26
Product: MUXIA
Machine graph: `company/muxia-task-graph-v1.json`

## Execution doctrine

Each task is intentionally small enough for one focused worker/session. A task is not `DONE` unless its declared artifact and acceptance evidence exist. Failure returns to the smallest failed dependency; do not restart the whole roadmap.

State set:

`BLOCKED | READY | RUNNING | VERIFYING | DONE | FAILED | DEFERRED`

Initial state rule: only tasks with all dependencies `DONE` are `READY`.

No task below authorizes production, marketplace submission, account action, spend, protective-measure circumvention, or live Proxima retirement unless its own acceptance explicitly names that gate and Founder authorization exists.

## DAG overview

```text
MX-000
  |
  v
MX-010 -> MX-011 -> MX-012
                    |
                    v
                  MX-020 -> MX-021 -> MX-022 -> MX-023
                                              |
                                              v
                  MX-030 -> MX-031 -> MX-032 -> MX-033 -> MX-034
                                                        |
                                                        v
                  MX-040 -> MX-041 -> MX-042 -> MX-043
                                                        |
                                                        v
                  MX-050 -> MX-051 -> MX-052
                                      |
                                      v
                  MX-060 -> MX-061 -> MX-062
                                      |
                                      v
                  MX-070 -> MX-071 -> MX-072
                                      |
                                      v
                                   MX-080
```

## MX-000 — Canon lock

**Goal:** Freeze MUXIA name, scope, architecture, roadmap, and machine-readable task graph.

Artifacts:

- ADR, PRD, ROADMAP, ATOMIC TASKS;
- machine JSON graph;
- LASTSTANDINGPOINT handoff.

Acceptance:

- JSON graph parses;
- docs reference the same product name and migration doctrine;
- no runtime/service/session mutation.

Initial status: `RUNNING` during this documentation turn, then `DONE` after verification.

---

## Phase 1 — Legacy autopsy and parity

### MX-010 — Pin live Proxima baseline

**Goal:** Record the exact Proxima repository, branch/SHA, runtime path, listener, and current bounded image/text proof inputs without modifying runtime.

Depends on: `MX-000`

Artifact: `docs/operations/MUXIA_PROXIMA_BASELINE_V1.md`

Acceptance:

- exact repo/SHA/runtime metadata recorded;
- current text and durable-image receipt references identified;
- no secrets/session values read or copied.

### MX-011 — Codebase KEEP/EXTRACT/RETIRE autopsy

**Goal:** Map only the Proxima code paths relevant to session lifecycle, provider UI control, REST contract, artifact export, and Electron coupling.

Depends on: `MX-010`

Artifact: `docs/architecture/MUXIA_PROXIMA_AUTOPSY_V1.md`

Acceptance:

- every relevant module classified `KEEP | EXTRACT | RETIRE | UNKNOWN`;
- Electron dependencies enumerated;
- unknowns converted to explicit probe tasks, not assumptions.

### MX-012 — Build parity contract tests

**Goal:** Encode the current bounded text-canary and durable image-export behavior as tests independent of implementation details.

Depends on: `MX-011`

Artifact: test suite + parity fixture contract.

Acceptance:

- legacy baseline passes;
- deliberately broken artifact hash/path fails;
- tests do not require marketplace or production authorization.

---

## Phase 2 — Core extraction

### MX-020 — Define core domain types

**Goal:** Implement provider/profile/job/artifact state types and schemas with no Electron dependency.

Depends on: `MX-012`

Acceptance:

- schemas/types compile;
- lifecycle transitions validated;
- invalid duplicate lease/false-success transitions rejected.

### MX-021 — Implement config/path abstraction

**Goal:** Remove OS-specific path assumptions from new core code.

Depends on: `MX-020`

Acceptance:

- Windows and Linux path fixtures pass;
- no `C:\`/`D:\` literals in core except tests/legacy adapter fixtures;
- profile/artifact/state roots are config-driven.

### MX-022 — Implement Profile Registry

**Goal:** Persist sanitized profile metadata and enforce one active lease owner per profile.

Depends on: `MX-021`

Acceptance:

- create/read/update profile metadata;
- simultaneous second lease rejected;
- no cookie/token/session content stored in registry.

### MX-023 — Implement Job + Artifact Registry

**Goal:** Persist resumable job state and hash-addressed artifact receipts.

Depends on: `MX-022`

Acceptance:

- restart-safe job lifecycle tests pass;
- `SUCCEEDED` rejected without durable matching artifact receipt;
- receipt carries path/hash/size/type/provider/profile/job linkage.

---

## Phase 3 — Playwright parity on Windows

### MX-030 — Implement Playwright Chromium driver

**Goal:** Launch/stop/restart Chromium against a dedicated test profile without Electron.

Depends on: `MX-023`

Acceptance:

- process lifecycle tests pass;
- dedicated user-data directory used;
- debug endpoint is loopback/private only.

### MX-031 — Implement ChatGPT provider state detector

**Goal:** Detect bounded states needed for safe operation: ready, auth-required, protection/rate-limit/unknown, and failed.

Depends on: `MX-030`

Acceptance:

- state detector fixtures/tests pass;
- protection/auth ambiguity maps to `WAITING_OPERATOR|BLOCKED`;
- no bypass behavior exists.

### MX-032 — Windows text canary parity

**Goal:** Reproduce the known bounded ChatGPT text canary through Playwright/Chromium.

Depends on: `MX-031`

Acceptance:

- expected bounded canary response observed;
- no Electron process participates;
- sanitized execution receipt exists.

### MX-033 — Windows durable image parity

**Goal:** Reproduce one bounded durable ChatGPT image artifact and receipt through the MUXIA path.

Depends on: `MX-032`

Acceptance:

- raster artifact exists;
- hash/bytes/container match receipt;
- no transient-only result is accepted;
- result meets parity contract from `MX-012`.

### MX-034 — Windows restart persistence proof

**Goal:** Prove the dedicated profile survives controlled Chromium restart without silently changing identity.

Depends on: `MX-033`

Acceptance:

- close/relaunch cycle succeeds where provider session policy permits;
- same profile ID/path retained;
- auth-required state fails closed rather than inventing success.

---

## Phase 4 — Isolation and recovery

### MX-040 — Two-profile isolation

**Goal:** Run `chatgpt-a` and `chatgpt-b` from separate profile directories and prove no shared profile state.

Depends on: `MX-034`

Acceptance:

- distinct process/profile ownership;
- no cross-profile cookie/session/log/artifact contamination;
- independent shutdown/restart works.

### MX-041 — Crash recovery

**Goal:** Inject browser termination during a job and prove deterministic failure/recovery.

Depends on: `MX-040`

Acceptance:

- interrupted job is never marked success;
- lease is recovered or profile quarantined;
- next safe action is machine-readable.

### MX-042 — Two-profile bounded concurrency

**Goal:** Execute two independent bounded canaries concurrently.

Depends on: `MX-041`

Acceptance:

- both jobs retain correct profile/artifact lineage;
- no duplicate lease;
- resource measurements captured.

### MX-043 — Four-profile bounded concurrency

**Goal:** Expand only after two-profile PASS and measure four independent session lanes.

Depends on: `MX-042`

Acceptance:

- four isolated leases/processes/jobs pass or fail independently;
- no cross-profile contamination;
- measured CPU/RAM/process envelope recorded;
- failure does not trigger automatic higher concurrency.

---

## Phase 5 — Linux proof

### MX-050 — Linux runtime bootstrap

**Goal:** Provision a Linux test target with only required MUXIA/Playwright/Chromium dependencies.

Depends on: `MX-043`

Acceptance:

- reproducible bootstrap/runbook;
- no Electron dependency;
- headless/headed-Xvfb mode explicitly selected by evidence.

### MX-051 — Linux single-profile parity

**Goal:** Repeat text + bounded image + restart proof on Linux with one dedicated profile.

Depends on: `MX-050`

Acceptance:

- text parity PASS;
- durable image parity PASS;
- restart/session-state handling PASS/fail-closed;
- receipts match core contracts.

### MX-052 — Linux four-profile isolation

**Goal:** Repeat bounded four-profile isolation/concurrency on Linux.

Depends on: `MX-051`

Acceptance:

- independent profile ownership;
- no cross-profile leakage;
- resource envelope documented;
- no Windows GUI dependency in execution path.

---

## Phase 6 — Reliability

### MX-060 — Sanitized observability

Status: `DONE`

**Goal:** Expose runtime/profile/job/artifact health without session credentials.

Depends on: `MX-052`

Acceptance:

- health output contains no cookies/tokens/auth bodies;
- profile/job state is sufficient to diagnose common failures;
- logs redact credential-equivalent fields.

### MX-061 — Fault-injection suite

Status: `DONE`

**Goal:** Test timeout, browser crash, lease contention, disk/artifact failure, and auth-required transitions.

Depends on: `MX-060`

Acceptance:

- each injected fault maps to deterministic state;
- false success count = 0;
- recovery/escalation path documented.

### MX-062 — 24-hour soak

Status: `READY`

**Goal:** Run bounded non-production soak against approved test canaries/profile health loops.

Depends on: `MX-061`

Acceptance:

- zero profile corruption;
- zero credential leakage;
- zero duplicate ownership;
- browser/process recovery behaves as specified;
- complete resource/failure receipt.

---

## Phase 7 — DIE integration and cutover evidence

### MX-070 — Legacy compatibility adapter

**Goal:** Map current governed Worker/Proxima invocation contract to MUXIA without rewriting the mission runner.

Depends on: `MX-062`

Acceptance:

- same bounded input produces equivalent artifact/receipt contract;
- no authority expansion;
- legacy path remains available for rollback.

### MX-071 — M-001 governed MUXIA canary

**Goal:** Execute only an explicitly authorized bounded M-001 producer canary through MUXIA.

Depends on: `MX-070`

Acceptance:

- durable workspace artifact;
- QA/evidence chain PASS;
- no submission/publication/spend expansion;
- comparison metrics against Proxima baseline captured.

### MX-072 — Cutover evidence package

**Goal:** Compile all parity, Linux, isolation, reliability, and M-001 receipts into one Founder decision package.

Depends on: `MX-071`

Acceptance:

- every ADR cutover criterion mapped to evidence;
- gaps are explicit;
- recommendation is `PROMOTE | EXTEND | REPAIR | KEEP_PROXIMA`.

---

## Phase 8 — Founder decision

### MX-080 — Founder cutover decision

**Goal:** Record the Founder decision on whether MUXIA becomes primary.

Depends on: `MX-072`

Authority: Founder only.

Possible outcomes:

- `PROMOTE_MUXIA`
- `EXTEND_CANARY`
- `REPAIR_MUXIA`
- `KEEP_PROXIMA`

Acceptance:

- explicit decision receipt exists;
- no implied retirement from silence;
- legacy retirement is a separate post-promotion task.

## Recovery rule

If a task fails, create at most one repair task beneath that failed node, e.g. `MX-033-R1`. The repair must name the observed defect, minimal change, and exact re-verification. Do not create a new roadmap unless an ADR assumption is falsified.

## Autopsy-discovered probe nodes — added by MX-011

These probes were created because MX-011 found facts that must be measured rather than assumed. They do not authorize credential reads or runtime mutation.

### MX-P01 — Legacy profile-root metadata probe

Depends on: `MX-023`

Goal: identify active Proxima browser profile/user-data roots using metadata only; never read/export cookies, tokens, or session values.

### MX-P02 — Legacy support-tree provenance probe

Depends on: `MX-072`

Goal: classify `D:\proximav2-setup` items before any cleanup as artifact, receipt, runtime, copied source, stale, or sensitive-log.

### MX-P03 — ChatGPT web execution policy gate

Depends on: `MX-012`

Goal: re-check current provider terms/product rules and lock the allowed MUXIA ChatGPT adapter boundary before any unattended web execution/output implementation.

Machine graph total after MX-011: **30 nodes**.

## 2026-08-27 — MX-012 completion standing

- `MX-012 — Parity contract tests`: **DONE**.
- New independent contract: `company/muxia/contracts/muxia.parity-contract.v1.json`.
- New fixture: `company/muxia/tests/parity/fixtures/legacy-proxima-postfix-v1.json`.
- New test suite: `company/muxia/tests/parity/muxia-parity-contract.test.mjs`.
- Verification: **5 passed / 0 failed**.
- `MX-020 — Core domain types`: **READY**.
- `MX-P03 — ChatGPT web execution policy gate`: **READY**.

The physical artifact is authoritative over historical success text. A missing artifact, corrupted hash, or success state without durable artifact+receipt evidence is rejected.

## 2026-08-27 — MX-020 and MX-P03 completion

- `MX-020 — Core domain types`: **DONE**. Strict TypeScript compile PASS; 8 core tests PASS; MX-012 parity regression remains 5 PASS.
- `MX-P03 — ChatGPT web execution policy gate`: **DONE**. Current consumer-web autonomous Output extraction is blocked; operator-controlled acquisition is the canonical V1 ChatGPT path.
- `MX-021 — Config/path abstraction`: **READY** and is the only currently eligible node.

Policy-adjusted future acceptance:

- MX-032 text canary must use operator-controlled confirmation/acquisition or a later supported programmatic interface; no automated consumer-web Output extraction.
- MX-033 durable image parity must validate a local artifact obtained through an operator-controlled acquisition step or later supported programmatic interface.

## Batch receipt — MUXIA-B02

Batch: `MUXIA-B02 — Core Persistence Foundation`
Policy: `STOP_ON_FIRST_FAILURE`
Result: **PASS**

- `MX-021 — Config/path abstraction`: DONE — 4/4 targeted tests PASS.
- `MX-022 — Profile Registry`: DONE — 4/4 targeted tests PASS.
- `MX-023 — Job + Artifact Registry`: DONE — 5/5 targeted tests PASS.
- Full regression: 21 core + 5 parity = **26/26 PASS**.

Receipt: `company/muxia/batches/MUXIA-B02-core-persistence-foundation.receipt.json`.

Next READY nodes after B02: `MX-030`, `MX-P01`.

## Batch receipt — MUXIA-B03

Batch: `MUXIA-B03 — Browser Foundation`
Result: **PASS**

- `MX-P01 — Legacy profile metadata probe`: DONE — metadata-only proof; no credential/session contents read.
- `MX-030 — Playwright Chromium driver`: DONE — 4/4 targeted tests PASS.
- Full regression: 25 core + 5 parity = **30/30 PASS**.
- Orphan MUXIA test Chromium processes after suite: **0**.

Browser dependency: `playwright ^1.62.1` using Playwright-managed Chrome for Testing `151.0.7922.34` on the Windows proof host.

Receipt: `company/muxia/batches/MUXIA-B03-browser-foundation.receipt.json`.

Next READY node: `MX-031`.

## MX-031 completion receipt

- `MX-031 — ChatGPT provider state detector`: **DONE**.
- Detector version: `chatgpt-state-detector-v1`.
- States: `READY | AUTH_REQUIRED | BLOCKED | UNKNOWN`.
- Priority: `BLOCKED > AUTH_REQUIRED > READY > UNKNOWN`.
- Targeted verification: 10/10 PASS.
- Full regression: 35 core + 5 parity = **40/40 PASS**.
- Live ChatGPT provider access during acceptance: NO.
- Next READY: `MX-032`.

Receipt: `company/muxia/receipts/MX-031-chatgpt-state-detector.receipt.json`.

## MUXIA-B04 standing — blocked at MX-032

- `MX-031`: DONE before batch.
- `MX-031-R1 — Repair ChatGPT protection-title detection`: DONE, 11/11 targeted PASS.
- `MX-032 — Windows text canary parity`: **BLOCKED** by `LIVE_CHATGPT_PROTECTION_CHALLENGE`.
- `MX-033`: NOT STARTED / dependency-blocked.
- `MX-034`: NOT STARTED / dependency-blocked.

Live probe result after repair: `BLOCKED / PROTECTION_CHALLENGE / protection-title` on `https://chatgpt.com/`; no prompt, no Output extraction, no bypass.

Resume condition: authorized operator-controlled MUXIA ChatGPT session reaches READY without circumvention.

Batch receipt: `company/muxia/batches/MUXIA-B04-provider-windows-proof.receipt.json`.

## MX-033 completion receipt

- `MX-033 — Windows durable image parity`: **DONE**.
- Job: `mx033-image-canary-001` -> `SUCCEEDED`.
- Artifact: `C:\DIE\workspaces\MUXIA-B04\muxia-root\artifacts\mx033-image-canary-001\mx033-canary.png`.
- SHA-256: `975697da4a72390aab206f59da0dd161400fe3e68764f9809a67c677070a6ef6`.
- Bytes: `888599`.
- MIME: `image/png`.
- Dimensions: `1254x1254`.
- Operator acquisition: manual download, rename/move only, no reported conversion/editing.
- Full regression: 41/41 PASS.
- Next READY: `MX-034`.

Receipt: `company/muxia/receipts/MX-033-image-canary.receipt.json`.

## MX-034 completion receipt

- `MX-034 — Windows restart persistence proof`: **DONE**.
- Same persistent profile: `chatgpt-a\edge-auth`.
- Old Edge PID: `21008`.
- New Edge PID: `21400`.
- Old debug port: `50898`.
- New debug port: `58494`.
- Pre-restart: `READY / COMPOSER_READY`.
- Post-restart: `READY / COMPOSER_READY`.
- Credential values read: NO.
- Auth fail-closed targeted regression: PASS.
- Full regression: 41/41 PASS.
- B04 final status: PASS / COMPLETE.
- Next READY: `MX-040`.

Receipt: `company/muxia/receipts/MX-034-restart-persistence.receipt.json`.

## MX-040 completion receipt

- `MX-040 — Two-profile isolation`: **DONE**.
- Profiles: `chatgpt-a`, fresh `chatgpt-b`.
- Duplicate lease A/B: rejected.
- Cross-owner release: rejected.
- Synthetic cookie/localStorage cross-contamination: NONE.
- Artifact namespace contamination: NONE.
- Log namespace contamination: NONE.
- Provider credential values read: NO.
- Legacy profile copy/import: NO.
- Profile B processes after cleanup: 0.
- Profile A preserved/responsive: YES.
- Full regression: 41/41 PASS.
- Next READY: `MX-041`.

Receipt: `company/muxia/receipts/MX-040-two-profile-isolation.receipt.json`.

## MX-041 completion receipt

- `MX-041 — Crash recovery`: **DONE**.
- Victim: `chatgpt-b`.
- Crash PID: `17568`.
- Pre-crash profile/job: RUNNING / RUNNING.
- Post-recovery job: `FAILED`.
- Post-recovery profile: `READY`, lease null, browserPid null.
- B browser process count: 0.
- Fabricated artifact receipt: NO.
- False-success attempt: rejected.
- Ambiguous owner path: `QUARANTINE_REQUIRED` in unit test.
- Targeted tests: 4/4 PASS.
- Full regression: 45/45 PASS.
- Profile A preserved: YES.
- Next READY: `MX-042`.

Receipt: `company/muxia/receipts/MX-041-crash-recovery.receipt.json`.

## MUXIA-B05 completion

- `MX-042 — Two-profile bounded concurrency`: DONE / PASS.
- `MX-043 — Four-profile bounded concurrency`: DONE / PASS.
- `MX-043-R1 — Deterministic four-lane teardown`: DONE / PASS.
- Correct profile lineage enforced in core via `ARTIFACT_PROFILE_MISMATCH`.
- 2-lane overlap: 3531 ms; working set 1,194,856,448 bytes; process count 24.
- 4-lane overlap: 4756 ms; working set 2,581,938,176 bytes; process count 55.
- B-E post-batch: READY / no lease / zero temporary Edge processes.
- Profile A preserved: YES, Edge PID 21400.
- Full regression: 46/46 PASS.
- Batch receipt: `company/muxia/batches/MUXIA-B05-windows-scaling-proof.receipt.json`.
- Next READY: `MX-050`.

## MUXIA-B06 current standing

- `MX-050 — Linux runtime bootstrap`: BLOCKED (`LINUX_RUNTIME_UNAVAILABLE_ON_HOST`).
- Bootstrap/runbook/static contract prepared and tested.
- Actual Linux Playwright/Chromium runtime proof: NOT YET EXECUTED.
- `MX-051`: not started.
- `MX-052`: not started.
- Full regression: 48/48 PASS.
- Resume requires explicit Founder authorization for WSL2/Linux installation on current VPS or another reachable Linux target.
- Blocked receipt: `company/muxia/batches/MUXIA-B06-linux-parity-foundation.blocked.receipt.json`.
