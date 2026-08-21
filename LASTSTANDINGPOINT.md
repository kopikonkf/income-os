# LASTSTANDINGPOINT.md

Date: 2026-08-21
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: P3 — EXECUTIVE MCP ACTIVATION READINESS v1 (IMPLEMENTED LOCALLY; PUBLICATION AUTHORIZATION PENDING)
Canonical runtime: `C:\DIE`
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: `architect/executive-mcp-activation-readiness-v1`
Base branch: `main`
Base commit: `bbfaaf8778d32b1d0cc96e260968323ce0c78abf`

## Verified merge standing

PR #5 — Executive Line 2 MCP v1 was merged and closed:

https://github.com/kopikonkf/income-os/pull/5

- merged: TRUE;
- merged at: `2026-08-21T06:59:09Z`;
- merge commit: `bbfaaf8778d32b1d0cc96e260968323ce0c78abf`;
- PR head: `f3b11f1258f1fa0f79847b7887f438364a0e19ba`;
- `C:\DIE\main` fast-forwarded to the same merge commit;
- Company Brain validator after merge: PASS;
- bridge regression after merge: 62 passed;
- all live runtime state changes were preserved across synchronization.

P5 State Context v1, P6 Decision Gateway v1, and Executive Line 2 MCP v1 are merged foundations.

## Canonical synchronization and runtime exclusions

```text
GitHub main
  = canonical code + constitutional/governed artifacts

C:\DIE\state
  = live append-only state + generated operational projections
```

Live runtime-owned worktree paths observed after PR #5 merge:

- `state/EVENTS.jsonl` — modified by live events/heartbeats;
- `state/projection/.cursor` — modified by projection advancement;
- `state/projection/BRIEFING.md` — modified by projection briefing;
- `state/projection/EVENTS.jsonl` — modified by projection output;
- `state/projection/WAKE.flag` — currently removed by the runtime gate;
- `state/organism-test/groundtruth-20260821.txt` — new runtime/test ground truth;
- `state/DECISIONS.jsonl` — unmodified.

All of these are operational truth or runtime output. They must not be staged, discarded, restored, rewritten, or included in an architecture PR without a separate explicit state-governance decision.

Production credential standing:

- `DIE_SNAPSHOT_HMAC_KEY`: ABSENT;
- `DIE_SNAPSHOT_HMAC_KEY_ID`: ABSENT;
- Secure MCP Tunnel client: ABSENT;
- Line 1 tunnel ID: ABSENT;
- Line 2 tunnel ID: ABSENT;
- DIE Executive MCP process/service: NOT RUNNING / NOT INSTALLED;
- ChatGPT Executive MCP registration: NOT PERFORMED.

## Corrected P0–P9 standing

| Stage | Actual status | Canonical standing |
| --- | --- | --- |
| P0 — Autopsy/Salvage | COMPLETE | KEEP/MODIFY/RETIRE and salvage boundary complete. |
| P1 — Company Brain | COMPLETE | Constitution, State boundary, agency contract, identity package, registry, and validator complete; PR #2 merged. |
| P2 — Architect MCP | FUNCTIONALLY COMPLETE | `C:\DIE` inspection/write/test/Git cycle works; security hardening debt remains. Architect DEV stays separate from runtime cognition. |
| P3 — Plus Line 1/2 | CODE COMPLETE v1; ACTIVATION PENDING | Line 1 bounded read MCP exists; Line 2 `decision_submit` exists and PR #5 merged. Activation-readiness package is local; no tunnel, production key, process, deployment, or ChatGPT registration yet. |
| P4 — Division Line 1/2 | TEMPLATE FOUNDATION ONLY | `division-head-template` exists but is intentionally inactive until one real division and scoped projection exist. |
| P5 — State Layer | COMPLETE v1 | One physical State Manager writer, JSONL substrate, authority/freshness request contract, signed bounded context snapshots, typed evidence, and replay-safe decision commit exist; PR #3 merged. |
| P6 — Decision Gateway | COMPLETE v1 | Stateless P5→State Manager commit router, typed receipt, evidence/HMAC revalidation, and Hermes-ready route exist; PR #4 merged. |
| P7 — Hermes/Worker/Proxima | PARTIAL EXISTING | Hermes/Worker/Proxima pipeline exists partly on VPS. Hermes decision acceptance/acknowledgment remains after Executive MCP activation. Proxima stays Worker ↔ Web Chat AI only. |
| P8 — Dashboard | BLOCKED BY DESIGN | Start only after one real division and one economic loop are alive. |
| P9 — Genome/Bootstrap/etc. | DEFERRED / READY FOR CLASSIFICATION | Review as ADOPT/ADAPT/MERGE/REJECT after current decision/execution loop is operational. |

The table supplied in chat was an early standing point and is now superseded by this canonical audit.

## Activation-readiness architectural decision

The post-PR #5 handoff originally placed production HMAC provisioning before the service boundary. Live audit found no DIE MCP service, tunnel client, or tunnel IDs. Provisioning first would create an orphaned credential.

Corrected principle:

```text
code contract
  -> activation readiness
  -> tunnel/service boundary
  -> credential provisioning
  -> activation verification
  -> ChatGPT registration
  -> first authorized live decision
```

No deployment action is performed by the current package.

## Current OpenAI transport baseline

Official OpenAI documentation currently establishes:

- ChatGPT Developer mode is available to Plus;
- supported remote MCP protocols include SSE and streaming HTTP;
- write tools are treated as writes and require confirmation by default;
- `readOnlyHint` is used to distinguish read-only tools;
- private MCP servers can be reached in developer mode through Secure MCP Tunnel;
- the tunnel can reach configured stdio or HTTP MCP servers;
- private/write capabilities require authentication and server-side authorization.

Official references:

- https://developers.openai.com/api/docs/guides/developer-mode
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/deploy/connect-chatgpt

For the internal Founder/Executive lane, this package selects private Secure MCP Tunnel rather than public plugin submission or a new public OAuth service.

## Executive MCP Activation Readiness v1 outcome

Implemented:

- dedicated Line 1 bootstrap: `bin/die_executive_line1_mcp.py`;
- existing Line 2 bootstrap preserved: `bin/die_executive_mcp.py`;
- Line 1 server version `0.4.0`;
- Line 2 server version `1.1.0`;
- bounded server instructions for both lanes;
- every Line 1 tool explicitly advertises `readOnlyHint: true`;
- Line 2 exposes only `decision_submit` with `readOnlyHint: false`;
- Line 2 remains `idempotentHint: true`;
- malformed Line 1 JSON-RPC params now fail closed with `-32602`;
- separate server names and entrypoints;
- non-secret readiness schema `die.executive.mcp.activation.readiness.v1`;
- readiness checker: `bin/die_executive_activation_check.py`;
- two distinct tunnel IDs required;
- shared HMAC key/key-ID presence validated without returning values;
- no secret, tunnel ID, credential value, or raw config returned.

Preserved:

- Line 1 and Line 2 remain separate connections;
- Line 1 remains read-only;
- Line 2 remains the only Executive mutation surface;
- State Manager remains the sole physical writer;
- Hermes remains the sole operational control plane;
- Architect MCP is not reused for runtime cognition;
- MCP Proxima is not changed or conflated with DIE MCP;
- no process, service, port, firewall, DNS, Cloudflare, TLS, tunnel, secret, or ChatGPT registration is mutated.

## Executable readiness check

```powershell
python bin/die_executive_activation_check.py
```

Live audit result:

```json
{
  "schema_version": "die.executive.mcp.activation.readiness.v1",
  "activation_mode": "secure_mcp_tunnel",
  "code_ready": true,
  "activation_ready": false,
  "line1_tool_count": 12,
  "line2_tools": ["decision_submit"],
  "secret_values_returned": false,
  "deployment_performed": false,
  "registration_performed": false
}
```

Expected blockers before explicit deployment authorization:

- activation mode not configured in the runtime environment;
- production snapshot HMAC key absent;
- production HMAC key ID absent;
- tunnel client absent;
- Line 1 tunnel ID absent;
- Line 2 tunnel ID absent;
- distinct-tunnel proof unavailable.

This is a correct fail-closed result, not a test failure.

## Verification evidence

```text
python bin/die_company_brain_check.py
PASS — identity_count=5, runtime_identity_count=4

python -m py_compile <activation-readiness Python paths>
PASS

python -m pytest bridge/tests -q
68 passed

python bin/die_executive_activation_check.py
code_ready=true
activation_ready=false
exit=2 (expected until deployment prerequisites exist)

git diff --check
PASS

live DECISIONS mutation
NONE

production credential provisioning
NONE

MCP deployment/registration
NONE
```

Coverage includes:

- Line 1 read-only annotations;
- Line 2 write/idempotency annotations;
- bounded server instructions;
- malformed Line 1 JSON-RPC rejection;
- code-ready result without credentials;
- no secret or tunnel-ID value leakage;
- readiness success with injected test-only prerequisites;
- duplicate tunnel-ID rejection;
- real Line 1 stdio initialize/tools-list round-trip;
- all prior P0–P6 regression behavior.

## Exact publication manifest for draft PR #6

Modified:

- `LASTSTANDINGPOINT.md`
- `bridge/income_os_bridge/mcp_server.py`
- `bridge/income_os_bridge/executive_mcp_server.py`

New:

- `bin/die_executive_line1_mcp.py`
- `bin/die_executive_activation_check.py`
- `bridge/income_os_bridge/activation_readiness.py`
- `bridge/tests/test_executive_activation_readiness_v1.py`
- `docs/architecture/EXECUTIVE_MCP_ACTIVATION_READINESS_V1.md`

Explicit exclusions:

- `state/EVENTS.jsonl`;
- `state/DECISIONS.jsonl`;
- every file under `state/projection/`;
- every file under `state/organism-test/`;
- runtime secrets and credential values;
- temporary files and test state;
- `__pycache__`, `.pytest_cache`, and all cache artifacts;
- tunnel installation/configuration;
- HMAC generation/provisioning;
- process/service start;
- firewall, DNS, Cloudflare, or TLS changes;
- ChatGPT registration;
- Hermes integration;
- MCP Proxima changes.

No path is staged at this standing point.

## Next authorized publication action

Required Founder authorization:

```text
AUTHORIZED: stage the exact Executive MCP Activation Readiness v1 manifest only,
commit, push architect/executive-mcp-activation-readiness-v1,
and create draft PR #6.
Exclude state/EVENTS.jsonl, state/DECISIONS.jsonl,
all state/projection and state/organism-test runtime artifacts,
all runtime secrets, temporary files, and cache artifacts.
Do not install or configure the tunnel client.
Do not generate or provision the production HMAC key.
Do not start, deploy, expose, or register either MCP service.
```

After PR #6 merge, the next action requires a new explicit deployment-and-credential authorization defining:

1. permission to install/configure the Secure MCP Tunnel client;
2. permission to create/use two distinct tunnel IDs;
3. permission to generate and provision the production HMAC key and rotation ID without disclosing values;
4. permission to start the two dedicated MCP processes/tunnels;
5. whether ChatGPT registration will be performed by the Founder in UI or delegated through an available authorized control surface.

The first real canonical decision remains a separate authorization after activation verification.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repo.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not merge Line 2 mutation into Line 1.
Do not reuse Architect DEV trust for runtime cognition.
Do not expose raw paths, credentials, or DEV capability.
Do not stage, discard, or rewrite live state/projection/organism artifacts.
Do not write synthetic decisions to live canonical state.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.
