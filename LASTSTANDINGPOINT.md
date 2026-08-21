# LASTSTANDINGPOINT.md

Date: 2026-08-21
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: P3 — CHATGPT PLUS EXECUTIVE LINE 2 MCP v1 (IMPLEMENTED LOCALLY; PUBLICATION AUTHORIZATION PENDING)
Canonical runtime: `C:\DIE`
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: `architect/executive-line2-mcp-v1`
Base branch: `main`
Base commit: `d5d958f817b8c3bc47a284ccb355d61375389822`

## Verified merge standing

PR #4 — P6 Decision Gateway v1 was merged and closed:

https://github.com/kopikonkf/income-os/pull/4

- merged: TRUE;
- merged at: `2026-08-21T04:40:45Z`;
- merge commit: `d5d958f817b8c3bc47a284ccb355d61375389822`;
- PR head: `04a81132a29745f2533762b95a77559c8abfac98`;
- `C:\DIE\main` fast-forwarded to the merge commit;
- live event ledger preserved across synchronization;
- branch `architect/executive-line2-mcp-v1` created from the merge commit.

P5 State Context v1 and P6 Decision Gateway v1 are now merged foundations.

## Canonical synchronization and exclusions

```text
GitHub main
  = canonical code + constitutional/governed artifacts

C:\DIE\state
  = live append-only operational truth
```

Current live standing:

- `state/EVENTS.jsonl` continues to receive heartbeat events and remains an unstaged local modification;
- `state/DECISIONS.jsonl` is unmodified;
- production `DIE_SNAPSHOT_HMAC_KEY`: ABSENT;
- production `DIE_SNAPSHOT_HMAC_KEY_ID`: ABSENT;
- no production key was generated, written, displayed, or provisioned;
- all mutation tests used temporary isolated state and a temporary test-only key.

Neither live ledger may be staged, discarded, rewritten, or used for synthetic verification.

## Executive Line 2 MCP v1 decision

Line 1 remains the existing read-only observation MCP.

Line 2 is a separate dedicated mutation MCP that exposes exactly one semantic business capability:

`decision_submit`

It deliberately does not expose:

- filesystem read/write;
- raw JSON/file mutation;
- shell or subprocess execution;
- database access;
- Git or repository operations;
- service control;
- credential access;
- worker control;
- Hermes dispatch;
- Constitution or identity mutation.

The transport is separate from the Chief Executive Architect development MCP and separate from MCP Proxima V2. Proxima remains the Worker ↔ Web Chat AI production-engine path.

## Fixed trust boundary

The Line 2 process pins:

- principal: `chatgpt-plus-executive`;
- scope: `company_portfolio`;
- action: `state.decision.submit`;
- object type: `DECISION`.

Runtime cognition cannot override or inherit those values. Caller-supplied identity is rejected rather than treated as authentication.

Accepted semantic input is limited to:

- replay-safe `request_id`;
- fresh signed `die.context.snapshot.v1`;
- one bounded commit-ready decision;
- typed evidence already present in that snapshot;
- bounded assumptions.

The MCP server composes existing contracts rather than bypassing them:

```text
ChatGPT Plus Executive
  -> Line 1 context_snapshot
  -> Line 2 decision_submit
  -> P5 validate_and_normalize
  -> P6 Decision Gateway
  -> DIE State Manager (sole physical writer)
  -> typed committed/rejected receipt
  -> Hermes-ready route
```

## Preserved architectural boundaries

- DIE State Manager remains the sole physical canonical writer.
- Executive Line 2 owns no database, ledger, queue, scheduler, daemon, or durable memory.
- The observation MCP remains read-only.
- P5 authority/freshness normalization remains mandatory.
- P6 trust/authority/evidence revalidation remains mandatory.
- Missing or wrong snapshot HMAC fails closed with `E_SNAPSHOT_UNTRUSTED`.
- `request_id` replay returns the prior decision without a duplicate append.
- A successful result is only `ready_for_operational_acceptance`.
- Line 2 does not deliver to Hermes and does not execute workers.
- Hermes remains the single operational control plane.
- Architect DEV privilege remains Founder-invoked, non-runtime, and non-inheritable.
- Remote hosting, TLS, connection authentication, ChatGPT app registration, and production key provisioning are not performed by this package.

## Executable artifact

Dedicated stdio MCP entrypoint:

```powershell
python bin/die_executive_mcp.py
```

MCP surface:

```text
tools/list
  -> decision_submit only

tools/call decision_submit
  -> exact input validation
  -> fixed Executive identity and scope
  -> P5 normalization
  -> P6 commit/reject
  -> typed MCP content receipt
```

Operational safeguards include:

- exact JSON Schema with `additionalProperties: false`;
- process-local limit of 12 mutation tool calls per hour;
- malformed JSON-RPC params rejected with `-32602`;
- unknown tools rejected with `E_MCP_TOOL_NOT_FOUND`;
- raw paths, traversal, secret-shaped content, stale/unsigned snapshots, forged evidence, unavailable writer, and invalid decisions fail closed;
- serial stdio request handling;
- append-only replay semantics delegated to the canonical State Manager.

## Isolated MCP end-to-end proof

The test suite starts the real `bin/die_executive_mcp.py` process with:

- a temporary `DIE_HOME`;
- a copied public identity registry;
- a temporary test-only HMAC key;
- a temporary event ledger.

It sends:

1. MCP `initialize`;
2. MCP `tools/list`;
3. first `decision_submit`;
4. replay of the same `request_id`;
5. stdin EOF for clean server exit.

Verified outcome:

```json
{
  "server": "die-executive-line2",
  "tools": ["decision_submit"],
  "first_status": "committed",
  "first_canonical_mutation": true,
  "replay_same_record_id": true,
  "replay_canonical_mutation": false,
  "decision_rows": 1,
  "live_decisions_changed": false,
  "isolated_events_changed": false,
  "production_hmac_provisioned": false
}
```

The temporary test directory and key are pytest-scoped and are not part of canonical runtime state.

## Verification evidence

```text
python bin/die_company_brain_check.py
PASS — identity_count=5, runtime_identity_count=4

python -m py_compile bridge/income_os_bridge/executive_mcp_server.py bin/die_executive_mcp.py
PASS

python -m pytest bridge/tests -q
62 passed

git diff --check
PASS

live state/DECISIONS.jsonl mutation
NONE

production HMAC key present
FALSE
```

Coverage includes:

- exactly one business mutation tool;
- no caller-controlled principal or scope;
- P5/P6 composition and fixed authority;
- unknown-field and identity-spoof rejection;
- raw-host-path rejection;
- unsigned snapshot rejection before writer invocation;
- unknown-tool rejection;
- mutation rate limiting;
- malformed JSON-RPC params rejection;
- append-only commit and replay;
- isolated real stdio MCP round-trip;
- event-ledger non-mutation.

## Current build position

### P0 — Codebase Recovery / Autopsy

COMPLETE.

### P1 — Company Brain + Constitution + Identity

COMPLETE. PR #2 merged.

### P2 — Architect Engineering Bridge

FUNCTIONALLY COMPLETE; SECURITY HARDENING DEBT REMAINS.

### P3 — ChatGPT Plus Line 1 + Line 2

PARTIAL, WITH LOCAL EXECUTABLE LINE 2 v1 READY FOR PUBLICATION.

Completed:

- Executive identity;
- bounded Line 1 `context_snapshot`;
- P5 typed semantic request normalization;
- P6 committed/rejected Decision Gateway;
- dedicated Executive Line 2 stdio MCP;
- one semantic `decision_submit` capability;
- isolated commit/replay MCP proof.

Still missing:

- publication and merge of Executive Line 2 v1;
- production snapshot-signing key provisioning through a separate authorized deployment;
- authenticated network adapter / remote MCP hosting;
- ChatGPT app registration and confirmation flow;
- wake/catch-up invocation transport;
- Hermes committed-decision delivery and acknowledgment.

### P4 — Division Decision Engine Line 1 + Line 2

TEMPLATE FOUNDATION ONLY.

`division-head-template` remains rejected until a registered division instance and scoped projection filter exist. Executive Line 2 identity pinning must not be reused for Division Heads.

### P5 — DIE State Layer

STATE CONTEXT v1 COMPLETE. PR #3 merged.

### P6 — Decision Gateway

COMPLETE. PR #4 merged.

### P7 — Hermes -> Worker -> Proxima

PARTIAL EXISTING IMPLEMENTATION.

Default remains:

```text
Hermes -> Worker -> Proxima -> Production Engine
```

Hermes remains the one operational control plane. Proxima is not a Company Brain bridge and not a second orchestrator.

### P8 — Dashboard

BLOCKED BY DESIGN until one real division and one economic loop exist.

### P9 — Genome / Bootstrap / Northstar / Factory

READY FOR LATER CLASSIFICATION as ADOPT / ADAPT / MERGE / REJECT after the current decision/execution loop is operational.

## Exact publication manifest for draft PR #5

Modified:

- `LASTSTANDINGPOINT.md`

New:

- `bin/die_executive_mcp.py`
- `bridge/income_os_bridge/executive_mcp_server.py`
- `bridge/tests/test_executive_line2_mcp_v1.py`
- `docs/architecture/EXECUTIVE_LINE2_MCP_V1.md`

Explicit exclusions:

- `state/EVENTS.jsonl`;
- `state/DECISIONS.jsonl`;
- all runtime keys and credentials;
- temporary files and temporary test state;
- `__pycache__`, `.pytest_cache`, and all cache artifacts;
- production HMAC provisioning;
- remote deployment/app registration;
- Hermes integration;
- MCP Proxima changes.

No path is staged at this standing point.

## Next authorized publication action

Required Founder authorization:

```text
AUTHORIZED: stage the exact Executive Line 2 MCP v1 manifest only,
commit, push architect/executive-line2-mcp-v1,
and create draft PR #5.
Exclude state/EVENTS.jsonl, state/DECISIONS.jsonl,
all runtime secrets, temporary files, and cache artifacts.
Do not provision the production HMAC key.
Do not deploy or register the MCP service.
```

After PR #5 merge, keep deployment actions separate:

1. provision/rotate the production snapshot HMAC key under explicit Founder authorization;
2. build or configure the authenticated network-facing MCP adapter and TLS boundary;
3. register Line 1/Line 2 with the ChatGPT Plus Executive lane and verify confirmation behavior;
4. add Hermes committed-decision acceptance/acknowledgment without creating a second orchestrator;
5. only then add wake/catch-up invocation transport.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repo.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not merge Line 2 mutation into the read-only observation MCP.
Do not expose raw paths, credentials, or DEV capability to runtime cognition.
Do not stage or discard `state/EVENTS.jsonl`.
Do not write synthetic decisions to live canonical state.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.
