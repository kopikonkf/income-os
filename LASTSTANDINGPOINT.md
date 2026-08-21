# LASTSTANDINGPOINT.md

Date: 2026-08-21
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: P3 — EXECUTIVE MCP ACTIVATION GATE v1.1 (DRAFT PR #7 OPEN)
Canonical runtime: `C:\DIE`
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: `architect/executive-mcp-activation-gate-v1-1`
Base branch: `main`
Base/merge commit: `290f64a1eae218b59c3ce0bae67f6d0b8023d740`
Package commit: `6c1ce91a477373a215149b0df7f001f93feff726`
Draft PR: https://github.com/kopikonkf/income-os/pull/7

## Verified merge and synchronization

PR #6 — Executive MCP Activation Readiness v1 is merged and closed:

https://github.com/kopikonkf/income-os/pull/6

- merged: TRUE;
- merged at: `2026-08-21T07:25:39Z`;
- PR head: `6aebdd9323034cb17442db269eb7e839e84c1382`;
- merge commit: `290f64a1eae218b59c3ce0bae67f6d0b8023d740`;
- `C:\DIE\main`, `origin/main`, and the verified merge commit are identical;
- Company Brain validator after merge: PASS;
- full bridge regression after merge: 68 passed;
- all live runtime state changes survived synchronization.

## Canonical runtime boundary

```text
GitHub main
  = canonical code + governed documents

C:\DIE\state
  = live append-only state + generated runtime projections
```

Runtime-owned paths currently preserved and excluded:

- `state/EVENTS.jsonl` — modified;
- `state/projection/.cursor` — modified;
- `state/projection/BRIEFING.md` — modified;
- `state/projection/EVENTS.jsonl` — modified;
- `state/projection/WAKE.flag` — currently absent/deleted by runtime;
- `state/organism-test/groundtruth-20260821.txt` — untracked runtime/test ground truth;
- `state/DECISIONS.jsonl` — unmodified.

These paths must not be staged, discarded, restored, rewritten, or included in an
architecture PR without a separate state-governance decision.

## Corrected P0–P9 standing

| Stage | Actual status | Canonical standing |
| --- | --- | --- |
| P0 — Autopsy/Salvage | COMPLETE | KEEP/MODIFY/RETIRE and salvage boundary complete. |
| P1 — Company Brain | COMPLETE | Constitution, identity package, registry, agency contract, and validator merged in PR #2. |
| P2 — Architect MCP | FUNCTIONALLY COMPLETE | Live `C:\DIE` inspection/write/test/Git cycle works; security-hardening debt remains. |
| P3 — Plus Line 1/2 | CODE COMPLETE v1; GATE v1.1 IN DRAFT PR #7; ACTIVATION PENDING | Line 1 read plane, Line 2 decision plane, and readiness v1 are merged through PR #6. The official control-plane gate hardening is published for Founder review. |
| P4 — Division Line 1/2 | TEMPLATE FOUNDATION ONLY | Keep inactive until one real division and scoped projection exist. |
| P5 — State Layer | COMPLETE v1 | Signed bounded snapshots, typed evidence, replay-safe commit, and State Manager boundary merged in PR #3. |
| P6 — Decision Gateway | COMPLETE v1 | Stateless validation/router and Hermes-ready route merged in PR #4. |
| P7 — Hermes/Worker/Proxima | PARTIAL EXISTING | Hermes integration waits until Executive MCP activation is verified. Proxima remains Worker ↔ Web Chat AI only. |
| P8 — Dashboard | BLOCKED BY DESIGN | Start only after one real division and one economic loop are alive. |
| P9 — Genome/Bootstrap/etc. | DEFERRED | Classify after the current decision/execution loop is operational. |

## Why Activation Gate v1.1 is required

Post-merge verification against current official OpenAI documentation found that
Secure MCP Tunnel requires more than tunnel-client, tunnel IDs, and the DIE
snapshot HMAC key.

The current OpenAI contract also requires:

- a runtime control-plane API key for `tunnel-client`;
- Tunnels Read + Use permissions;
- association with the target Platform organization and ChatGPT workspace;
- ChatGPT Developer Mode as a separate permission;
- outbound HTTPS and local MCP reachability.

Official source:

https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

Readiness v1 could produce a false-positive under injected test prerequisites
without proving these control-plane facts. v1.1 closes that path before any
deployment occurs.

## Executive MCP Activation Gate v1.1

Schema:

```text
die.executive.mcp.activation.readiness.v1.1
```

New fail-closed prerequisites:

- `CONTROL_PLANE_API_KEY` is present with a safe minimum length;
- `DIE_OPENAI_TUNNELS_READ_USE_GRANTED` is explicitly attested;
- `DIE_OPENAI_TUNNEL_WORKSPACE_ASSOCIATED` is explicitly attested;
- `DIE_CHATGPT_DEVELOPER_MODE_ENABLED` is explicitly attested.

Only `1`, `true`, `yes`, or `on` are accepted as affirmative attestations.

The checker returns only booleans and blocker names. It never returns the
control-plane API key, snapshot HMAC key, tunnel IDs, or raw configuration.

## Verification evidence

```text
targeted activation-gate tests
7 passed

full bridge regression
69 passed

live readiness
schema=die.executive.mcp.activation.readiness.v1.1
code_ready=true
activation_ready=false
exit=2
secret_values_returned=false
deployment_performed=false
registration_performed=false
```

Expected live control-plane blockers:

- control-plane API key absent;
- Tunnels Read + Use not attested;
- target ChatGPT workspace association not attested;
- ChatGPT Developer Mode not attested.

Production/runtime standing remains:

- snapshot HMAC key and key ID: ABSENT;
- control-plane API key: ABSENT;
- tunnel-client: ABSENT;
- Line 1/Line 2 tunnel IDs: ABSENT;
- Executive MCP services: NOT RUNNING / NOT INSTALLED;
- ChatGPT Executive registrations: NOT PERFORMED.

## Exact local manifest for draft PR #7

Modified:

- `LASTSTANDINGPOINT.md`
- `bridge/income_os_bridge/activation_readiness.py`
- `bridge/tests/test_executive_activation_readiness_v1.py`
- `docs/architecture/EXECUTIVE_MCP_ACTIVATION_READINESS_V1.md`

Explicit exclusions:

- `state/EVENTS.jsonl`;
- `state/DECISIONS.jsonl`;
- every file under `state/projection/`;
- every file under `state/organism-test/`;
- all runtime secrets and credential values;
- temporary files and cache artifacts;
- tunnel-client installation/configuration;
- OpenAI tunnel creation/modification;
- HMAC or control-plane key generation/provisioning;
- process/service start, deployment, exposure, or registration;
- firewall, DNS, TLS, Cloudflare, or Windows service changes;
- Hermes, Worker, or MCP Proxima changes.

The exact four-path manifest was committed and pushed in package commit `6c1ce91a477373a215149b0df7f001f93feff726`. Runtime-owned `state/` artifacts remain unstaged and excluded.

## Publication state

Draft PR #7:

https://github.com/kopikonkf/income-os/pull/7

- state: OPEN;
- draft: TRUE;
- mergeable: MERGEABLE;
- merge state: CLEAN;
- base: `main`;
- head: `architect/executive-mcp-activation-gate-v1-1`;
- package commit: `6c1ce91a477373a215149b0df7f001f93feff726`;
- changed files: 4 exact manifest paths;
- external check count at creation: 0;
- targeted activation-gate tests: 7 passed;
- full bridge regression: 69 passed;
- readiness: `code_ready=true`, `activation_ready=false` (expected fail-closed);
- production HMAC/control-plane keys: ABSENT;
- tunnel installation/configuration and OpenAI tunnel mutation: NOT PERFORMED;
- service start/deployment/exposure/registration: NOT PERFORMED;
- all state/projection/organism runtime artifacts: EXCLUDED.

PR #7 is for Founder review and manual merge only. It must not be merged automatically.

After PR #7 merge, activation requires a new explicit authorization and prior
confirmation that the Founder can access Platform tunnel settings with Tunnels
Read + Use, associate the target ChatGPT workspace, and enable Developer Mode.
Credential provisioning, tunnel creation, service lifecycle, ChatGPT
registration, and the first real canonical decision remain separately gated.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repository.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not merge Line 2 mutation into Line 1.
Do not reuse Architect DEV trust for runtime cognition.
Do not expose raw paths, credentials, tunnel IDs, or DEV capability.
Do not stage, discard, or rewrite live state/projection/organism artifacts.
Do not write synthetic decisions to live canonical state.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.
