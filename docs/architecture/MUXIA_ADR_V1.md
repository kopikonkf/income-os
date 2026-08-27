# ADR — MUXIA V1: Web-AI Session Runtime

Status: ACCEPTED FOR CANON / NOT IMPLEMENTED
Date: 2026-08-26
Decision owner: Founder Dee
Architecture owner: Chief Executive Architect DEV
Supersedes product naming: Proxima (legacy runtime remains untouched until cutover gate)

## 1. Decision

The successor to Proxima is named **MUXIA**.

MUXIA is the internal canonical product name for a lightweight, scalable Web-AI Session Runtime. The name is derived from **multiplex + AI**: one runtime multiplexes many isolated persistent browser identities/sessions into bounded production lanes.

This is an internal technical name. Public trademark/domain/legal clearance is a separate pre-publication gate; this ADR does not claim exclusivity or registration.

## 2. Problem

Proxima V2 proved that a ChatGPT web session can produce a durable image artifact without BYOK/API inference cost, but the current Electron-coupled design creates unnecessary GUI/Windows dependency, process weight, and scaling fragility.

The economic property to preserve is the authenticated Web-AI session. Electron is not the economic primitive and must not remain the architectural center.

## 3. Decision summary

MUXIA V1 adopts the following architecture:

```text
DIE / Worker / Operator
        |
        v
    MUXIA API
        |
        +-- Job Manager
        +-- Profile Registry
        +-- Session Manager
        +-- Artifact Manager
        +-- Provider Adapters
                |
                v
          Playwright
                |
          Chromium process
                |
      persistent profile dir
```

### Locked decisions

1. **TypeScript + Node.js + Playwright first.** Rust is deferred until profiling proves Node control-plane overhead is material.
2. **Chromium is the browser substrate.** Tauri/WebKitGTK is not the primary runtime because changing browser engines adds compatibility risk. Tauri may later serve only as an optional operator console.
3. **Electron becomes legacy/compatibility only.** MUXIA core must not depend on Electron APIs.
4. **Persistent profile != persistent browser process.** Browser identity/session persists on disk; Chromium processes are disposable and restartable.
5. **One profile has one active owner at a time.** Concurrent use of the same profile is fail-closed.
6. **Provider and profile are separate concepts.** One provider (for example ChatGPT) may own many isolated profiles (`chatgpt-a`, `chatgpt-b`, ...).
7. **Provider-specific behavior is isolated behind adapters.** ChatGPT DOM/session changes may break the ChatGPT adapter without breaking MUXIA core.
8. **Linux is the target production host.** Windows remains the first refactor/proof host and legacy fallback until Linux acceptance passes.
9. **Next.js/UI is optional.** Runtime/API correctness precedes dashboards.
10. **No protective-measure circumvention.** MUXIA must not bypass CAPTCHA, rate limits, account restrictions, or authentication protections. Ambiguous auth/protection states block the job and require operator recovery.
11. **Credentials are credential-equivalent state.** Browser profile directories, cookies, CDP endpoints, and session material are treated as secrets; no cross-profile sharing or raw credential logging.
12. **MUXIA is not the DIE agent runtime.** It is a Web-AI session/production execution substrate. `agentd`, Hermes, Workers, and MUXIA remain separable components.
13. **No live Proxima cutover by inference.** Proxima stays available until the governed MUXIA Linux/canary acceptance gates pass.

## 4. Canonical profile topology

Windows refactor host:

```text
D:\muxia\profiles\
  chatgpt-a\
  chatgpt-b\
  qwen-a\
```

Linux target:

```text
/data/muxia/
  profiles/
    chatgpt-a/
      browser/
      profile.json
    chatgpt-b/
    qwen-a/
  jobs/
  artifacts/
  logs/
  state/
```

Paths are configuration, not hard-coded product contracts.

## 5. State model

Profile lifecycle:

`UNINITIALIZED -> READY -> LEASED -> RUNNING -> READY`

Exceptional states:

`AUTH_REQUIRED | BLOCKED | QUARANTINED | DISABLED`

Job lifecycle:

`QUEUED -> ASSIGNED -> RUNNING -> VERIFYING -> SUCCEEDED`

Exceptional states:

`WAITING_OPERATOR | BLOCKED | FAILED | CANCELLED | TIMED_OUT`

A browser crash does not destroy profile identity. The owner releases or recovers the profile lease only after process termination is verified.

## 6. Security boundaries

- Dedicated profile directory per browser identity/principal.
- CDP/debug endpoints loopback/private only; never public by default.
- No cookie/localStorage/token values in logs, receipts, job payloads, or MCP responses.
- Provider adapters receive the minimum job context needed for execution.
- MUXIA never stores DIE strategic context as browser-session memory.
- Browser output is `done` only after a durable artifact/receipt exists in the assigned artifact boundary.
- Any CAPTCHA, explicit rate-limit, suspicious-login, account-lock, or unknown auth state becomes `WAITING_OPERATOR` or `BLOCKED`; MUXIA does not attempt bypass logic.

## 7. Consequences

### Positive

- Removes Electron from the critical path.
- Makes Linux deployment feasible without changing the economic Web-AI-session primitive.
- Enables multiple isolated session profiles and disposable browser processes.
- Supports provider comparison/fallback without coupling core runtime to one website.
- Allows Windows to become optional after empirical Linux proof.

### Costs / risks

- Web-provider DOM/session behavior remains inherently fragile.
- Browser profiles require strong isolation and lifecycle discipline.
- Headed Linux may still require Xvfb/virtual display for provider compatibility.
- Provider Terms/policies may constrain automation; architecture does not override service rules.

## 8. Rejected alternatives

- **Keep Electron as core:** rejected; preserves unnecessary GUI/OS coupling.
- **Tauri as browser farm:** rejected for V1; Linux WebKitGTK changes browser engine and does not solve the browser-runtime problem better than Playwright/Chromium.
- **Rewrite browser automation in Rust:** rejected for V1; duplicates mature Playwright capability without measured benefit.
- **Next.js as runtime:** rejected; useful only as a control UI/API surface, not browser execution.
- **BYOK API as mandatory producer:** rejected for this migration because it destroys the current zero-incremental-inference-cost economic property.

## 9. Acceptance to supersede Proxima

MUXIA may supersede the live Proxima path only after all of these are evidenced:

1. behavior-parity harness against the current bounded Proxima image export contract;
2. Windows Playwright single-profile PASS;
3. persistent profile survives browser restart without cross-profile leakage;
4. two-profile then four-profile isolation/concurrency PASS;
5. Linux single-profile PASS;
6. Linux four-profile bounded concurrency PASS;
7. crash/restart recovery PASS;
8. 24-hour bounded soak with zero profile corruption/credential leakage;
9. governed M-001 canary produces durable artifacts and receipts with acceptance >= current Proxima canary baseline; and
10. Founder explicitly authorizes cutover.

Until gate 10, `Proxima` is legacy-live and `MUXIA` is successor-under-build.

## 10. Name/IP clearance status

Public-brand status is **HOLD**. MUXIA is currently an internal canonical codename only. Preliminary collision screening and domain findings are recorded in docs/architecture/MUXIA_NAME_CLEARANCE_V1.md. Public trademark/domain promotion requires the separate clearance gate defined there.


## 11. Commercial-license / clean implementation boundary

The inspected Proxima repository is licensed for personal, non-commercial use only. Unless Founder separately proves commercial reuse rights, MUXIA must be independently implemented from DIE-owned requirements, receipts, and observable behavior. Proxima source/tests are reference-only and must not be copied or renamed into MUXIA. See docs/architecture/MUXIA_PROXIMA_AUTOPSY_V1.md.


## 12. ChatGPT consumer-web policy boundary — MX-P03

Current OpenAI consumer Terms checked on 2026-08-27 prohibit automatic/programmatic extraction of data or Output and prohibit circumvention of rate limits/restrictions/protective measures. MUXIA therefore may not treat consumer ChatGPT web as an unattended output-extraction backend under the current agreement.

MUXIA core/profile/session infrastructure remains valid. Under this gate, ChatGPT consumer-web parity tasks use an operator-controlled interaction/output-acquisition step followed by MUXIA local artifact validation. A future supported OpenAI programmatic interface or materially different governing agreement may replace this boundary only after a new policy receipt/ADR update.

Canonical policy artifacts:

- `company/muxia/policies/chatgpt-web-boundary-v1.json`
- `docs/operations/MUXIA_CHATGPT_WEB_POLICY_GATE_V1.md`
