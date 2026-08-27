# MUXIA PRD V1 — Lightweight Web-AI Session Runtime

Status: CANON DRAFT ACCEPTED / IMPLEMENTATION NOT STARTED
Date: 2026-08-26
Product: MUXIA
Legacy predecessor: Proxima V2

## 1. Product thesis

MUXIA turns isolated authenticated Web-AI browser sessions into a durable, observable, profile-isolated production runtime without requiring Electron as the core process model.

The product preserves the economically valuable primitive already proven by Proxima: using existing authenticated Web-AI product sessions to perform bounded creative work, while making browser lifecycle, profile isolation, artifact handling, recovery, and scale explicit.

## 2. Primary users

1. **DIE Worker/Hermes** — submits bounded production jobs and receives durable artifacts/receipts.
2. **Founder/operator** — owns authentication, manual recovery/takeover, and authorization gates.
3. **Chief Architect** — inspects health/capability through bounded MCP/control surfaces; does not receive raw browser credentials.
4. **Provider adapter maintainer** — repairs provider-specific UI behavior without changing MUXIA core.

## 3. V1 goals

- Run without Electron as a core dependency.
- Run on Windows during refactor and target Linux for production.
- Manage multiple isolated persistent browser profiles.
- Treat Chromium processes as disposable workers.
- Preserve authenticated session continuity across browser restart where the provider permits it.
- Allocate exactly one active owner/lease per profile.
- Expose provider-neutral jobs and provider-specific adapters.
- Produce durable artifacts plus receipts before a job can be `SUCCEEDED`.
- Recover cleanly from browser crash, timeout, and restart.
- Provide enough telemetry to diagnose failures without logging credentials/session secrets.
- Support bounded concurrency expansion from 1 -> 2 -> 4 profiles before larger scale is considered.
- Preserve the existing Proxima path as fallback until explicit cutover.

## 4. Non-goals V1

- No attempt to bypass CAPTCHA, rate limits, account protections, or service restrictions.
- No autonomous account creation or credential acquisition.
- No 1k-5k/day scale claim in V1.
- No generic DIE agent framework (`agentd` is separate).
- No dashboard requirement.
- No Rust rewrite merely for performance aesthetics.
- No multi-host clustering until one Linux host proves the runtime contract.
- No retirement of Proxima/Windows before empirical acceptance.

## 5. Core domain objects

### Provider

Defines a website/product family and adapter capabilities.

Minimum fields:

- `provider_id`
- `adapter_version`
- `capabilities[]`
- `health`

### Profile

Persistent browser identity/session boundary.

Minimum fields:

- `profile_id`
- `provider_id`
- `profile_path`
- `state`
- `lease_owner`
- `browser_pid`
- `last_health_at`
- `last_success_at`
- `failure_count`

### Job

One bounded execution unit.

Minimum fields:

- `job_id`
- `provider_id`
- `required_capability`
- `profile_selector`
- `workspace/artifact_target`
- `timeout`
- `status`
- `attempt`
- `created_at`

### Artifact receipt

Minimum fields:

- `job_id`
- `profile_id`
- `provider_id`
- `artifact_path`
- `sha256`
- `bytes`
- `mime/container`
- `created_at`
- `adapter_version`
- `status`

## 6. Functional requirements

### FR-01 Profile registry

MUXIA must create/read/update profile metadata without exposing secret session contents. Each profile maps to exactly one provider and one dedicated browser data directory.

### FR-02 Exclusive profile lease

A profile cannot be used by two active browser owners simultaneously. Lease acquisition must fail closed if ownership is ambiguous.

### FR-03 Browser lifecycle

MUXIA can launch, detect, stop, and restart Chromium for a leased profile. A process restart must not silently create a new identity.

### FR-04 Provider adapter

Core runtime calls provider-neutral operations. Provider-specific selectors/navigation/state detection remain in versioned adapters.

V1 provider priority:

1. ChatGPT image producer;
2. ChatGPT text canary;
3. additional providers only after ChatGPT parity is stable.

### FR-05 Operator recovery

When authentication, CAPTCHA, explicit rate limit, suspicious login, or an unknown protection state is detected, the job becomes `WAITING_OPERATOR`/`BLOCKED`. MUXIA exposes sanitized recovery context but no bypass automation.

### FR-06 Artifact durability

A generated browser result is not `SUCCEEDED` until the expected artifact exists in the assigned artifact boundary and its receipt contains matching hash/size/type evidence.

### FR-07 Crash recovery

Browser/process crash must release or quarantine the profile deterministically. Restart may resume only from durable job/profile state.

### FR-08 Concurrency

Concurrency is capacity-controlled, not tab-count-controlled. Initial capacity progression is 1 -> 2 -> 4 leased profiles. More is a later evidence-based decision.

### FR-09 Observability

Required health surfaces:

- runtime health;
- profile states;
- active leases;
- job states;
- browser PID/process state;
- sanitized provider state;
- artifact receipt status;
- failure category/count;
- resource use.

### FR-10 Compatibility

During migration, MUXIA must provide either a compatibility adapter or bounded command/API mapping so governed DIE production does not require a simultaneous mission-runner rewrite.

## 7. Non-functional requirements

### Reliability

- no cross-profile cookie/session contamination in acceptance tests;
- no duplicate active lease for one profile;
- browser crash cannot mark a job successful;
- process restart cannot erase durable job state;
- 24-hour soak must complete with zero profile corruption or credential leakage before cutover consideration.

### Security

- profile directories are credential-equivalent and access-controlled;
- CDP/debug exposure is loopback/private only by default;
- credentials/cookies/tokens are redacted from logs and receipts;
- raw browser-session state is never returned through Architect/Runtime MCP;
- no provider protection bypass logic is implemented.

### Portability

- no hard-coded Windows-only paths in core;
- path roots are environment/config driven;
- browser adapter must support Windows proof host and Linux target host;
- Linux headed mode may use Xvfb only when empirical provider behavior requires it.

### Resource efficiency

- no permanent browser process required for an idle profile;
- idle profiles occupy disk state, not an always-on Electron window;
- browser process count is bounded by configured concurrency.

## 8. V1 success metrics

MUXIA V1 is technically successful when:

1. current Proxima bounded image-export behavior is reproduced through Playwright/Chromium;
2. persistent authentication/session continuity survives controlled browser restart where provider permits;
3. two then four profile-isolated sessions operate without contamination;
4. Linux target reproduces the same bounded contract;
5. crash/restart recovery is deterministic;
6. 24-hour soak passes;
7. M-001 canary artifacts meet or exceed the current Proxima artifact/export baseline; and
8. no additional BYOK inference dependency is introduced by the migration itself.

## 9. Cutover rule

`MUXIA_READY_FOR_CUTOVER` is false by default.

It may become true only when the acceptance evidence listed in `MUXIA_ADR_V1.md` and `MUXIA_ROADMAP_V1.md` is complete and Founder explicitly approves the switch. Naming canon does not imply runtime cutover.

## 10. Provider-policy constraint — 2026-08-27

MUXIA V1 remains a browser/profile/session runtime, but current ChatGPT consumer-web output acquisition is **operator-controlled**, not unattended extraction. Provider-neutral infrastructure may automate profile leases, browser lifecycle, health, job preparation, local artifact ingestion, hashing, receipts, and recovery states. It must not automatically/programmatically extract ChatGPT consumer-web Output, bypass provider protections/rate limits, reverse-engineer private backend transports, or export browser credential/session values.

Accordingly, the V1 ChatGPT path is:

`job prepared -> dedicated profile -> operator-controlled provider interaction/acquisition -> local artifact -> MUXIA verify/hash/receipt`.

If OpenAI later provides a supported programmatic interface/agreement for this workflow, the provider adapter can evolve without changing MUXIA core.
