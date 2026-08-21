# LASTSTANDINGPOINT.md

Date: 2026-08-21
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: P6 — DECISION GATEWAY v1 (DRAFT PR #4 OPEN)
Canonical runtime: `C:\DIE`
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: `architect/decision-gateway-v1`
Base branch: `main`
Base commit: `5f4c6bc29c4646a405d8b887a2b093869515550f`
Package commit: `4576e9b98a6d837aef2a627974e98da29f27434f`
Draft PR: https://github.com/kopikonkf/income-os/pull/4

## Verified merge standing

PR #3 — P5 State Context v1 was merged and closed:

https://github.com/kopikonkf/income-os/pull/3

- merged: TRUE
- merge commit: `5f4c6bc29c4646a405d8b887a2b093869515550f`
- `C:\DIE\main` fast-forwarded to the same merge commit
- Company Brain validator after merge: PASS
- regression baseline after merge: 40 passed
- branch `architect/decision-gateway-v1` was created from the merge commit

P5 State Context v1 is complete.

## Canonical synchronization and exclusion

```text
GitHub main
  = canonical code + constitutional/governed artifacts

C:\DIE\state
  = live append-only operational truth
```

`state/EVENTS.jsonl` continues to receive heartbeat events. It was preserved, was not rewritten by P6, and must remain excluded from staging/publication.

No synthetic P6 decision was written to live `state/DECISIONS.jsonl`. End-to-end commit verification used a temporary isolated `DIE_HOME`, which was removed immediately after the proof.

## P6 Decision Gateway v1 outcome

The smallest stateless mutation router now exists.

Implemented:

- `die.decision.gateway.result.v1`;
- exact normalized-wrapper input contract;
- rejection of raw/unvalidated semantic requests;
- registry-backed reauthorization before commit;
- full bounded source snapshot preservation in normalized requests;
- deterministic snapshot-integrity recomputation;
- server HMAC trust proof required for mutation;
- snapshot principal/scope/freshness revalidation;
- evidence restricted to the trusted source snapshot;
- commit-ready DECISION validation;
- raw host path, traversal, credential-shaped input, and size rejection;
- fail-closed writer-unavailable/writer-failure handling;
- canonical commit through `bin/die_event.py` only;
- `die.decision.v1` provenance fields;
- request-ID replay protection;
- committed/rejected typed receipt;
- fixed next owner: `hermes-operator`;
- route status: `ready_for_operational_acceptance`;
- UTF-8 BOM-safe Line 2 file input on Windows.

Preserved:

- DIE State Manager remains the sole physical canonical writer;
- the Gateway owns no database, queue, daemon, ledger, scheduler, or memory;
- Hermes remains mission owner and the sole operational control plane;
- P6 does not dispatch to Hermes or execute a mission;
- the existing MCP observation surface remains read-only;
- Architect DEV remains Founder-invoked and non-inheritable;
- no runtime actor receives filesystem, Git, service-control, or credential access;
- no production secret is tracked or exposed.

## Snapshot trust deployment gate

Mutation uses two process-environment settings:

- `DIE_SNAPSHOT_HMAC_KEY` — secret, minimum 32 bytes;
- `DIE_SNAPSHOT_HMAC_KEY_ID` — non-secret rotation identifier.

The snapshot issuer and Decision Gateway must share them. The key is never committed, returned to cognition, or written to canonical state.

Current standing:

- production HMAC key: NOT PROVISIONED by this implementation;
- read-only snapshots without a key: AVAILABLE;
- mutation with an unsigned/wrong-key snapshot: FAIL-CLOSED with `E_SNAPSHOT_UNTRUSTED`;
- isolated verification key: temporary only, removed with the test environment.

Provisioning the production key is a deployment action separate from the code PR and requires an explicit Founder authorization.

## Isolated end-to-end proof

```json
{
  "first_status": "committed",
  "first_record_id": "D-0001",
  "first_replayed": false,
  "second_record_id": "D-0001",
  "second_replayed": true,
  "decision_rows": 1,
  "route_next_owner": "hermes-operator",
  "signed_snapshot": true,
  "live_events_unchanged": true,
  "test_root": "temporary_removed"
}
```

This proves the executable path:

```text
signed context snapshot
  -> semantic request normalization
  -> Decision Gateway revalidation
  -> temporary DIE State Manager commit
  -> committed receipt
  -> replay without duplicate append
  -> Hermes-ready route
```

It does not claim Hermes delivery or production activation.

## Verification evidence

```text
python bin/die_company_brain_check.py
PASS — identity_count=5, runtime_identity_count=4

python -m py_compile <P6 Python paths>
PASS

python -m pytest bridge/tests -q
54 passed

git diff --check
PASS

isolated Line 2 CLI commit/replay proof
PASS

live canonical DECISIONS mutation
NONE
```

Adversarial coverage includes:

- raw unnormalized request rejected;
- stale snapshot rejected;
- unsigned snapshot rejected;
- wrong-runtime-key snapshot rejected;
- snapshot content tampering rejected;
- normalized authority tampering rejected;
- evidence absent from the trusted snapshot rejected;
- non-commit-ready decision rejected;
- raw host path rejected after normalization;
- unavailable/failing writer rejected without error-detail leakage;
- repeated request does not append a duplicate decision;
- decision commit does not mutate EVENTS;
- Windows UTF-8 BOM input accepted.

## Current build position

### P0 — Codebase Recovery / Autopsy

COMPLETE.

### P1 — Company Brain + Constitution + Identity

COMPLETE. PR #2 merged.

### P2 — Architect Engineering Bridge

FUNCTIONALLY COMPLETE; SECURITY HARDENING DEBT REMAINS.

### P3 — ChatGPT Plus Line 1 + Line 2

PARTIAL.

Completed foundation:

- Executive identity;
- bounded Line 1 `context_snapshot`;
- typed semantic decision request;
- P6 committed/rejected Gateway contract.

Still missing:

- separate Executive Line 2 MCP transport;
- production snapshot-signing key provisioning;
- wake/catch-up transport;
- committed-decision delivery/acknowledgment from Hermes.

### P4 — Division Decision Engine Line 1 + Line 2

TEMPLATE FOUNDATION ONLY.

`division-head-template` remains rejected until a registered division instance and scoped projection filter exist.

### P5 — DIE State Layer

STATE CONTEXT v1 COMPLETE. PR #3 merged.

### P6 — Decision Gateway

IMPLEMENTED; VERIFIED; PUBLISHED IN DRAFT PR #4; AWAITING FOUNDER REVIEW/MERGE.

### P7 — Hermes -> Worker -> Proxima

PARTIAL EXISTING IMPLEMENTATION.

Default remains:

```text
Hermes -> Worker -> Proxima -> Production Engine
```

Hermes remains the one operational control plane. Proxima is not a second orchestrator.

### P8 — Dashboard

BLOCKED BY DESIGN until one real division and one economic loop exist.

### P9 — Genome / Bootstrap / Northstar / Factory

READY FOR LATER CLASSIFICATION as ADOPT / ADAPT / MERGE / REJECT after the current decision/execution loop is operational.

## Exact publication manifest for draft PR #4

Modified:

- `bin/die_event.py`
- `bin/die_state_request.py`
- `bridge/income_os_bridge/snapshot.py`
- `bridge/income_os_bridge/state_request.py`
- `docs/architecture/STATE_CONTEXT_V1.md`
- `LASTSTANDINGPOINT.md`

New:

- `bin/die_decision_gateway.py`
- `bridge/income_os_bridge/decision_gateway.py`
- `bridge/tests/test_decision_gateway_v1.py`
- `docs/architecture/DECISION_GATEWAY_V1.md`

Explicit exclusions:

- `state/EVENTS.jsonl`;
- `state/DECISIONS.jsonl`;
- all runtime keys, credentials, temporary test files, and cache artifacts.

The exact 10-path manifest was committed and pushed in package commit `4576e9b98a6d837aef2a627974e98da29f27434f`. `state/EVENTS.jsonl` remains a live, unstaged local modification and is not part of the PR.

## Publication state

Draft PR #4:

https://github.com/kopikonkf/income-os/pull/4

- state: OPEN;
- draft: TRUE;
- mergeable: MERGEABLE;
- merge state: CLEAN;
- base: `main` at `5f4c6bc29c4646a405d8b887a2b093869515550f`;
- head branch: `architect/decision-gateway-v1`;
- package commit: `4576e9b98a6d837aef2a627974e98da29f27434f`;
- changed files: 10;
- external status checks reported by GitHub: NONE;
- local bridge regression: 54 passed;
- production HMAC key: ABSENT / NOT PROVISIONED;
- `state/EVENTS.jsonl`: EXCLUDED and preserved as a live unstaged modification;
- `state/DECISIONS.jsonl`: EXCLUDED and unmodified.

Remaining action for this package: Founder review and merge only. No automatic merge is authorized.

After PR #4 merge:

1. provision/rotate the production snapshot HMAC key through a separate explicit Founder-authorized deployment action;
2. build the separate ChatGPT Plus Executive Line 2 MCP transport over the P5/P6 contracts;
3. add Hermes committed-decision acceptance/acknowledgment without creating a second orchestrator.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repo.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not mix Line 2 mutation into the read-only observation MCP.
Do not expose raw paths, credentials, or DEV capability to runtime cognition.
Do not stage or discard `state/EVENTS.jsonl`.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.
