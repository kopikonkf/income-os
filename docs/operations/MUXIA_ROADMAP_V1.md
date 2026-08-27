# MUXIA ROADMAP V1

Status: CANON / EXECUTION NOT STARTED
Date: 2026-08-26
Product: MUXIA
Doctrine: Build > Run > Verify > Refactor > Extend

## Roadmap principle

MUXIA is migrated by **behavioral parity and measured gates**, not by a big-bang rewrite. The existing Proxima path remains live until MUXIA proves equivalent or better reliability on the governed production contract.

Every phase must leave an executable/verifiable artifact. No phase may silently authorize production, marketplace submission, account action, spend, or retirement of the legacy runtime.

## Phase 0 — CANON LOCK

Goal: freeze product identity, scope, architecture, and executable task graph before code changes.

Artifacts:

- `docs/architecture/MUXIA_ADR_V1.md`
- `docs/operations/MUXIA_PRD_V1.md`
- `docs/operations/MUXIA_ROADMAP_V1.md`
- `docs/operations/MUXIA_ATOMIC_TASKS_V1.md`
- `company/muxia-task-graph-v1.json`
- `LASTSTANDINGPOINT.md` handoff

Exit gate:

- documents are self-consistent;
- task graph parses;
- no Proxima/runtime mutation occurred.

## Phase 1 — PROXIMA AUTOPSY + PARITY CONTRACT

Goal: understand only the code paths required to reproduce the already-proven bounded image/text behavior.

Work:

- identify live Proxima repository/runtime revision;
- map Electron ownership vs reusable Node/browser/provider logic;
- record current REST/job/artifact contracts;
- create behavior-parity tests around text canary and durable image export;
- identify Windows/Electron-specific assumptions.

Exit gate:

- one written KEEP / EXTRACT / RETIRE map;
- parity harness fails when current contract is broken and passes on verified legacy baseline;
- no implementation migration yet.

## Phase 2 — MUXIA CORE EXTRACTION ON WINDOWS

Goal: create an OS-neutral core while preserving the existing Windows proof environment.

Work:

- introduce config-driven roots;
- implement Profile Registry;
- implement Job state model;
- implement Artifact Receipt contract;
- define BrowserDriver/ProviderAdapter interfaces;
- isolate legacy Electron behind a compatibility adapter if needed.

Exit gate:

- core tests run without Electron;
- no hard-coded Windows path in core domain logic;
- legacy Proxima remains callable.

## Phase 3 — PLAYWRIGHT/CHROMIUM PARITY ON WINDOWS

Goal: prove Electron is not required for the current bounded Web-AI workflow.

Work:

- Playwright Chromium driver;
- one dedicated `chatgpt-a` persistent profile;
- profile lease + process lifecycle;
- ChatGPT text canary;
- ChatGPT bounded image export;
- durable artifact + hash receipt;
- browser restart/reconnect proof.

Exit gate:

- text canary PASS;
- one bounded image canary PASS;
- artifact receipt parity PASS;
- browser restart preserves allowed authenticated session continuity;
- Electron is not used by the parity path.

## Phase 4 — PROFILE ISOLATION + RECOVERY

Goal: prove the architecture scales by profile, not by shared tabs/windows.

Work:

- `chatgpt-a` + `chatgpt-b` independent directories;
- exclusive lease enforcement;
- crash detection/quarantine/recovery;
- sanitized logs;
- operator-recovery state;
- two-profile concurrency probe;
- four-profile concurrency probe only after two-profile PASS.

Exit gate:

- no cross-profile leakage;
- no duplicate lease;
- crash cannot create false success;
- 2-profile PASS;
- 4-profile PASS.

## Phase 5 — LINUX SPIKE

Goal: prove the Windows GUI is no longer a runtime requirement.

Work:

- provision Linux test target;
- install supported Chromium/Playwright dependencies;
- run headless where compatible;
- use headed Chromium + Xvfb only when needed;
- transfer/create dedicated test profiles through an operator-controlled authentication procedure;
- repeat Windows parity and restart tests.

Exit gate:

- Linux text canary PASS;
- Linux bounded image canary PASS;
- durable artifact/receipt PASS;
- session/profile isolation PASS;
- no Electron/Windows dependency in execution path.

## Phase 6 — SOAK + BOUNDED SCALE

Goal: establish operational reliability before touching mission production routing.

Work:

- 24-hour bounded soak;
- browser crash/restart injection;
- profile lease contention test;
- artifact integrity checks;
- CPU/RAM/disk/process telemetry;
- failure taxonomy and recovery receipts.

Exit gate:

- zero profile corruption;
- zero credential leakage in logs/receipts;
- zero duplicate profile ownership;
- all deliberate crash cases recover or fail closed;
- resource envelope documented.

## Phase 7 — M-001 GOVERNED CANARY

Goal: prove MUXIA is a viable producer under existing DIE governance rather than a standalone demo.

Work:

- compatibility route from current Worker/M-001 producer contract;
- bounded authorized canary only;
- artifact/receipt/QA chain preserved;
- compare export reliability, latency, and resource use with Proxima baseline.

Exit gate:

- durable artifacts resolve inside governed workspace;
- QA/evidence contract passes;
- no authority expansion;
- MUXIA result is >= current Proxima acceptance/export baseline.

## Phase 8 — CUTOVER DECISION

Goal: decide, not assume, whether MUXIA replaces Proxima.

Possible verdicts:

- `PROMOTE_MUXIA`: MUXIA becomes primary; Proxima enters rollback window.
- `EXTEND_CANARY`: more evidence required.
- `REPAIR_MUXIA`: return to failed phase/task.
- `KEEP_PROXIMA`: migration hypothesis rejected for now.

Founder approval is mandatory for `PROMOTE_MUXIA`.

## Phase 9 — LEGACY RETIREMENT / EXTENSION

Only after promotion and rollback evidence:

- retire Electron-specific production path;
- decide whether Windows host is still economically useful;
- add additional provider adapters only when they have a concrete business/job requirement;
- consider dashboard/Tauri/Rust only from measured bottlenecks;
- consider integration into future DIE node/agent fabric without merging responsibility boundaries.

## Anti-drift rules

1. Do not jump to Linux before Windows Playwright parity proves the architecture.
2. Do not add providers before ChatGPT parity/stability is proven.
3. Do not rewrite in Rust before profiling evidence exists.
4. Do not build dashboard before runtime health can be inspected by API/CLI.
5. Do not retire Proxima merely because MUXIA starts successfully.
6. Do not treat browser session memory as DIE canonical state.
7. Do not bypass provider protection or rate-limit mechanisms.
8. A failed task repairs/retries its smallest dependency; it does not restart the entire roadmap.

## License boundary discovered during MX-011

Proxima source is non-commercially licensed. MUXIA phases therefore use independent DIE implementation. Legacy source is read-only reference/evidence unless separate commercial reuse rights are proven. No phase may convert copy/rename Proxima into a migration shortcut.


## 2026-08-27 — Phase 1 parity gate complete

`MX-012` verified the independent DIE-owned MUXIA parity contract against a physically present legacy artifact. Phase 1 (`baseline -> autopsy -> parity contract`) is now COMPLETE. MUXIA core/runtime implementation has not started.

Verified harness: `node --test company\muxia\tests\parity\muxia-parity-contract.test.mjs` -> `5 passed / 0 failed`.

The DAG now has two independently eligible nodes: `MX-020` for provider-neutral core domain modeling and `MX-P03` for the current ChatGPT web execution policy boundary. `MX-P03` must finish before unattended ChatGPT web-adapter execution/output logic; it does not block pure MUXIA core types.

## 2026-08-27 — MX-020 + MX-P03 standing

`MX-020` completed the provider-neutral TypeScript core domain model: Provider, Profile, Job, Artifact Receipt, state transitions, exclusive profile lease, and false-success evidence guard. Verification: TypeScript strict compile PASS, core tests 8/8 PASS, parity regression 5/5 PASS.

`MX-P03` checked current official OpenAI consumer Terms/Usage Policies. Current consumer ChatGPT web may not be used as an unattended automatic/programmatic Output-extraction backend. Phase 3 remains valid but text/image parity is operator-controlled under the current policy gate: browser/session infrastructure may be automated, while provider interaction/output acquisition remains human-controlled unless a later supported interface/agreement explicitly permits programmatic execution/retrieval.

Next single READY node: `MX-021 — Config/path abstraction`.

## 2026-08-27 — Batch MUXIA-B02 complete

`MUXIA-B02 — Core Persistence Foundation` executed as a chained `STOP_ON_FIRST_FAILURE` batch:

`MX-021 Config/path abstraction -> MX-022 Profile Registry -> MX-023 Job + Artifact Registry`.

All three atomic nodes are DONE. Full MUXIA regression: TypeScript strict build PASS, core 21/21 PASS, parity 5/5 PASS (26 total). Persistence remains single-host/local-filesystem using atomic JSON writes and create-exclusive profile lease files; no runtime database dependency was introduced.

Canonical batch receipt: `company/muxia/batches/MUXIA-B02-core-persistence-foundation.receipt.json`.

Completion unlocks `MX-030 Playwright Chromium driver` and `MX-P01 Legacy profile-root metadata probe` as independent READY nodes. No browser/provider task was started by B02.

## 2026-08-27 — Batch MUXIA-B03 complete

`MUXIA-B03 — Browser Foundation` executed as two independent lanes with per-task checkpoints:

- `MX-P01 Legacy profile metadata probe`: DONE. Active Proxima user-data root identified from process metadata only as `C:\Users\aethers\AppData\Roaming\proxima`; provider partition names observed without reading credential/session contents. Default migration rule: do not bulk-import/copy the legacy root.
- `MX-030 Playwright Chromium driver`: DONE. MUXIA now independently launches/supervises Playwright-managed Chrome for Testing with dedicated profile directory, loopback-only ephemeral CDP endpoint, bounded stop/restart, active-run rejection, and profile-root confinement.

Full regression: TypeScript strict build PASS, core 25/25 PASS, parity 5/5 PASS (30 total), orphan MUXIA test Chromium processes after suite = 0.

Canonical batch receipt: `company/muxia/batches/MUXIA-B03-browser-foundation.receipt.json`.

Next single READY node: `MX-031 — ChatGPT provider state detector`.

## 2026-08-27 — MX-031 complete

`MX-031 — ChatGPT provider state detector`: DONE.

MUXIA now has a versioned fail-closed ChatGPT visible-state classifier with state priority `BLOCKED > AUTH_REQUIRED > READY > UNKNOWN`. Targeted tests: 10/10 PASS. Full regression: 40/40 PASS. Acceptance used local fixtures only; live ChatGPT compatibility is deferred to the operator-controlled MX-032 canary.

Next single READY node: `MX-032 — Windows text canary parity`.

## 2026-08-27 — Batch MUXIA-B04 blocked safely at MX-032

`MUXIA-B04 — Provider/Windows Proof` attempted the live Windows provider chain after MX-031.

The dedicated MUXIA profile reached a live ChatGPT protection interstitial (`Just a moment...`). This exposed one detector compatibility gap, repaired as `MX-031-R1`; detector v1.1 now maps the condition to `BLOCKED / PROTECTION_CHALLENGE`.

`MX-032 — Windows text canary parity` is now BLOCKED with blocker `LIVE_CHATGPT_PROTECTION_CHALLENGE`. No prompt was submitted and no Output was extracted. `MX-033` and `MX-034` were not started because their prerequisite remains unsatisfied.

Resume condition: an authorized operator-controlled MUXIA ChatGPT session reaches READY without bypass/circumvention, after which MX-032 may perform a bounded manually confirmed text canary under MX-P03.

Full regression after repair: TypeScript strict PASS, core 36/36 PASS, parity 5/5 PASS, total 41/41 PASS, orphan MUXIA test Chromium processes = 0.

Canonical batch doc: `docs/operations/MUXIA_PROVIDER_WINDOWS_PROOF_B04.md`.
Canonical batch receipt: `company/muxia/batches/MUXIA-B04-provider-windows-proof.receipt.json`.

## 2026-08-27 — MX-033 complete

`MX-033 — Windows durable image parity`: DONE / PASS.

Operator-controlled ChatGPT image acquisition produced a local raster which was manually renamed/moved into the pinned MUXIA artifact path without conversion/editing. MUXIA then validated physical PNG magic, dimensions `1254x1254`, bytes `888599`, SHA-256 `975697da4a72390aab206f59da0dd161400fe3e68764f9809a67c677070a6ef6`, wrote the durable artifact receipt, re-opened/re-verified the physical file, and transitioned job `mx033-image-canary-001` to `SUCCEEDED`.

Full regression after finalize: core 36/36 PASS, parity 5/5 PASS, total 41/41 PASS. Proxima remained live/untouched.

Next READY: `MX-034 — Windows restart persistence proof`.

## 2026-08-27 — MX-034 complete / B04 complete

`MX-034 — Windows restart persistence proof`: DONE / PASS.

Pre-restart authenticated state was `READY / COMPOSER_READY` on Edge PID `21008`, debug port `50898`. The browser process was stopped and the exact same persistent profile `chatgpt-a\edge-auth` was relaunched as Edge PID `21400`, debug port `58494`. Post-restart sanitized detection returned `READY / COMPOSER_READY` without reading credential values, proving persistent profile state survives disposable browser process replacement.

Auth fail-closed targeted regression also passed: auth URL maps to `AUTH_REQUIRED`.

Full regression: core 36/36 PASS, parity 5/5 PASS, total 41/41 PASS.

`MUXIA-B04 — Provider/Windows Proof` is now complete. Historical blocked receipt is preserved; final completion receipt is `company/muxia/batches/MUXIA-B04-provider-windows-proof.complete.receipt.json`.

Next READY: `MX-040 — Two-profile isolation`.

## 2026-08-27 — MX-040 complete

`MX-040 — Two-profile isolation`: DONE / PASS.

`chatgpt-a` and fresh `chatgpt-b` were proven as distinct profile boundaries. Separate leases rejected duplicates and cross-owner release. Synthetic loopback-only cookie/localStorage markers did not cross profiles; artifact and log namespaces remained disjoint. No provider credential/session values were read and no legacy profile was copied.

An initial runner timeout occurred only after the PASS receipt had been written, during teardown. Browser B and both leases were then cleaned deterministically, browser A remained alive, and the runner was patched for deterministic exit. Final regression: 41/41 PASS.

Next READY: `MX-041 — Crash recovery`.

## 2026-08-27 — MX-041 complete

`MX-041 — Crash recovery`: DONE / PASS.

MUXIA now has a core crash-recovery primitive. Real Windows fault injection used fresh profile B as the victim: lease acquired, Edge PID `17568` launched, profile/job marked RUNNING, then the browser process tree was killed. Recovery detected the dead PID, forced job `mx041-crash-job-001` to `FAILED`, released the lease, and returned profile B to `READY`. No artifact receipt was fabricated, and an explicit SUCCEEDED attempt was rejected.

Ambiguous owner/state recovery fails closed to `QUARANTINE_REQUIRED` in unit tests. Authenticated profile A remained alive and untouched.

Targeted crash-recovery tests: 4/4 PASS. Full regression: core 40/40 PASS, parity 5/5 PASS, total 45/45 PASS.

Next READY: `MX-042 — Two-profile bounded concurrency`.

## 2026-08-27 — MUXIA-B05 Windows Scaling Proof complete

Batch `MUXIA-B05 — Windows Scaling Proof` executed `MX-042 -> MX-043` under `STOP_ON_FIRST_FAILURE` and completed PASS after one minimal teardown repair child `MX-043-R1`.

MX-042 proved two-profile bounded concurrency across `chatgpt-b` + `chatgpt-c`: overlapping workloads, correct job/profile/receipt lineage, duplicate lease rejection, storage/artifact/log isolation, resource metrics, and clean teardown. Aggregate Edge working-set sample: 1,194,856,448 bytes across 24 processes.

MX-043 proved four-profile bounded concurrency across `chatgpt-b`..`chatgpt-e`: four overlapping lanes, correct lineage, duplicate lease rejection, no storage/artifact/log contamination, and captured resource envelope. Aggregate Edge working-set sample: 2,581,938,176 bytes across 55 processes.

The initial MX-043 runner wrote a functional PASS receipt but timed out during browser teardown. `MX-043-R1` repaired teardown deterministically by owned PID + exact lease owner. B-E ended READY/no lease/browserPid null with zero residual temporary Edge processes. Runner cleanup was patched accordingly.

Artifact verifier was hardened before B05 with fail-closed `ARTIFACT_PROFILE_MISMATCH` when `receipt.profileId != job.profileSelector`.

Final regression: core 41/41 PASS, parity 5/5 PASS, total 46/46 PASS.

B05 completion receipt: `company/muxia/batches/MUXIA-B05-windows-scaling-proof.receipt.json`.

Next READY: `MX-050 — Linux runtime bootstrap`.

## 2026-08-27 — MUXIA-B06 blocked at MX-050

`MUXIA-B06 — Linux Parity Foundation` started under `STOP_ON_FIRST_FAILURE` and stopped at `MX-050 — Linux runtime bootstrap` because the current Windows VPS has no Linux execution substrate: WSL is not installed and Docker/Podman are unavailable.

Preparation completed before stopping:

- Linux bootstrap script created (`scripts/linux/mx050-bootstrap.sh`);
- Linux-only Chromium smoke created (`scripts/linux/mx050-runtime-smoke.mjs`);
- bootstrap contract regression created (`tests/core/linux-bootstrap-contract.test.mjs`);
- non-Linux false PASS explicitly rejected with `MX050_REQUIRES_LINUX`;
- Electron is not a required dependency;
- full regression after preparation: core 43/43 PASS, parity 5/5 PASS, total 48/48 PASS.

No WSL installation was performed because enabling/installing WSL is an OS-level mutation that may require reboot and needs explicit Founder authorization. The current Architect principal is Administrator, so installation is technically possible once authorized.

MX-051 and MX-052 were not started. Historical blocked receipt: `company/muxia/batches/MUXIA-B06-linux-parity-foundation.blocked.receipt.json`.
