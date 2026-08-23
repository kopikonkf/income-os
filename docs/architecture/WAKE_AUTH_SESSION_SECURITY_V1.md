# Wake Auth and Session Security v1

Date: 2026-08-23
Owner: Chief Executive Architect DEV
Decision class: security architecture / control-plane transport
Executive evidence: `evidence/executive-verdict-wake-design-20260823.json`

## Verdict

**APPROVE WITH MANDATORY CONTROLS.**

The Division-01 and Executive wake paths may proceed to canon as outbound
control-plane bridges. The four-part auth/session proposal is directionally
correct, but permanent canon requires the amendments in this document.

This verdict does not authorize new accounts, credential creation, service or
scheduled-task mutation, browser-profile mutation, wake execution, production,
or marketplace submission.

## Evidence classification

The following are empirical implementation facts, not stable public OpenAI API
contracts:

- raw HTTPS and `headless=new` were Cloudflare-challenged in this environment;
- headed browser in-page fetch passed;
- `/api/auth/session` returned the web session token accepted by the observed
  `backend-api/*` path;
- Codex OAuth credentials were accepted only by their Codex audience;
- the observed sentinel challenge required a sha3-512 proof.

The `backend-api/*`, sentinel fields, and response shapes are undocumented web
implementation dependencies. Any provider-side change is an expected failure
mode, not proof that the canonical authority boundary changed.

Official OpenAI documentation establishes the supported distinction: ChatGPT
web keeps its authenticated session in the browser, while Codex may cache its
own credentials in `auth.json` or an OS credential store. OpenAI explicitly
says file-based `auth.json` must be treated like a password. It also labels full
CDP access as elevated risk because it exposes sensitive browser internals.

References:

- https://learn.chatgpt.com/docs/auth
- https://learn.chatgpt.com/docs/browser

## 4.1 Auth/session proposal verdict

| Proposal | Verdict | Canonical amendment |
| --- | --- | --- |
| Web JWT fetched live per wake and not persisted | APPROVE, AMENDED | The Web JWT must remain inside the authenticated page context. It must not cross CDP into Python, enter an evaluated source string as a literal, be returned, logged, or written. The page reacquires it immediately before the request. |
| Codex OAuth refresh token outside repo with user-only ACL | CONDITIONAL APPROVE | This is a separate Codex credential and is not a wake dependency. Prefer the OS credential store/keyring. If file fallback is retained, protect both directory and file, disable broad inheritance, verify ACL without reading content, and remove/revoke it when no Codex consumer exists. |
| `wake.json` contains only non-secret conversation ID | APPROVE, AMENDED | `conversation_id` is non-bearer but sensitive operational metadata. `wake.json` may also carry principal/division binding, lifecycle, generation, and bounded supersession history so the one-active-thread invariant can be enforced. It must never contain cookies, JWTs, refresh tokens, sentinel tokens, proofs, or message bodies. |
| Event receipt contains references only | APPROVE | Receipt allowlist: principal/division, event ID, outcome, latency, error code, thread generation, and evidence reference. No credential value, browser cookie, request/response header, raw backend body, PoW input/output, or full auth/session object. |

## Credential and metadata classes

| Material | Classification | Allowed residence | Persistence |
| --- | --- | --- | --- |
| Browser profile cookies/session | credential-equivalent, highest control | principal-dedicated browser user-data directory | provider/browser managed |
| Web JWT from `/api/auth/session` | secret, short-lived | authenticated page memory only | forbidden |
| Sentinel requirement token | secret-equivalent, ephemeral | page memory only | forbidden |
| PoW seed/environment/proof | ephemeral anti-abuse material | bounded solver memory and page request | forbidden |
| Codex OAuth access/refresh bundle | secret, separate audience | OS credential store preferred; protected `auth.json` fallback | only while a real Codex consumer requires it |
| `conversation_id` | non-bearer sensitive metadata | protected wake state | permitted |
| Wake briefing/reply | company-confidential content | ChatGPT thread and governed operator session | never copied into auth logs |

The wake process must not read `auth.json`. A browser login/session and a Codex
OAuth cache are different credential domains even when they represent the same
human account.

## Highest control point: browser profile plus CDP

CDP access is credential-equivalent because a controller can inspect page
runtime, network state, and authenticated targets. Required controls:

1. Bind every debugging endpoint explicitly to `127.0.0.1`.
2. Never route CDP through Cloudflared, Caddy, public firewall rules, MCP, or a
   remote administration endpoint.
3. Use a principal-dedicated browser user-data directory and OS ACL.
4. Pin principal, wake-state home, and CDP port in the wrapper/operator skill.
5. Fail closed on principal/division mismatch.
6. Do not dump CDP messages, evaluated expressions, headers, cookies, backend
   bodies, or browser storage.
7. On 401/403 or session mismatch, do not blind retry. Emit a sanitized alarm
   and require controlled re-authentication.
8. Treat a compromised CDP controller as a compromised browser session.

## 4.2 Ratified design decisions

### A. Wake boundary

**RATIFIED.** Wake is outbound control-plane transport owned by Hermes/operator
policy. It is not a Runtime MCP tool, capability, or inbound authority path.
Runtime MCP remains bounded Decision Fabric access.

### B. Executive authentication

**RATIFIED WITH CONTROLS.** The existing authenticated BrowserOS neo session is
sufficient for Executive wake. A separate Codex OAuth bundle must not be
created merely for wake. BrowserOS :9110 remains principal-dedicated,
loopback-only, health-probed, and recoverable through the auth/session runbook.

### C. Persistent conversation model

**RATIFIED WITH TERMINOLOGY CORRECTION.** The invariant is:

`division_id -> exactly_one_active_thread`

Lifecycle is `active -> archived/superseded`, with a generation counter and an
explicit `superseded_by` relation. A ChatGPT thread is the canonical
**continuity memory container** for that division identity; it is **not Company Truth**.
Canonical decisions, events, evidence, economics, mission lifecycle,
and authority remain in the DIE State Layer and governed repository.

The same single-active-thread rule applies to the Executive principal without
inventing a division ID.

## 4.3 Multi-division transport correction

The v2.1 pure-OAuth/raw-HTTPS assumption is retired for the measured ChatGPT web
wake path. The canonical transport class is browser-backed in-page fetch over
loopback CDP until a supported provider API replaces it.

However, **one browser process with many profiles is not an authentication
isolation boundary**. A full-CDP controller for that process can enumerate and
attach to its targets; one compromise can therefore collapse every profile in
that process into one trust domain.

The corrected capacity model is:

- one installed browser binary;
- one credential-isolated user-data directory per principal;
- one dedicated loopback CDP port per active principal instance;
- a bounded pool of **on-demand browser slots**, default concurrency one;
- cold/warm start profiles as needed instead of keeping 15 browsers resident;
- never claim cross-division isolation from Chrome/Brave profile names alone.

Thus 15 divisions do not require 15 always-on browsers, but they do require 15
separate credential/session domains. A single shared multi-profile process may
be used only as an explicitly accepted shared-trust pilot; it may not be the
canon for isolated division principals.

Current implementation gap: `wake_brave_health.ps1` still selects `Profile 3`
inside the ordinary Brave `User Data` root. That is accepted only for the
current single-principal pilot, not as proof of principal isolation. Before a
second division is activated, an authorized operator must migrate Division-01
to a principal-dedicated user-data directory, complete controlled re-login, and
verify that its CDP process exposes no other principal's targets. This PR does
not perform that runtime/profile migration.

Current topology remains valid:

| Principal | Implementation | CDP | Standing |
| --- | --- | --- | --- |
| DIVISION-01 | headed Brave, dedicated wake profile | `127.0.0.1:9333` | LIVE pilot |
| Executive | BrowserOS neo | `127.0.0.1:9110` | LIVE, principal-dedicated |

## Resilience and scale gate

Before Division-02 is activated, record at least the first M-001 production
cycle and 20 eligible wake attempts. Required evidence:

- send success rate and response success rate;
- 401/403, Cloudflare, sentinel, CDP, timeout, and thread-binding failures;
- p50/p95 end-to-end latency;
- number of manual re-authentications and browser recoveries;
- zero cross-principal routing;
- zero secret leakage in logs, receipts, events, artifacts, and repository;
- one exercised session-expiry recovery and one thread-rotation proof.

Initial canary gate: at least 95% successful wakes, 100% correct principal and
thread binding, and zero security violations. Failure blocks expansion and
returns the design to Architect/Founder review.

## Acceptance criteria

Canon is complete when:

1. no Web JWT or sentinel requirement token crosses from page to Python;
2. CDP listeners are explicitly loopback-only;
3. wake state fails closed on principal/division mismatch;
4. exactly one active continuity thread is represented per principal/division;
5. auth/session rotation and revocation are executable without exposing a
   credential value;
6. operator skills prohibit blind auth retries and raw token logging;
7. Runtime MCP tool surfaces remain unchanged.
