# DIE Decision Gateway v1

Status: IMPLEMENTED LOCALLY ON FEATURE BRANCH
Constitutional authority: `CONSTITUTION.md`
Identity authority: `company/identity-registry.json`
Input contract: `die.state.request.v1`
Result contract: `die.decision.gateway.result.v1`

## 1. Decision

P6 v1 is the smallest stateless commit router between runtime cognition and the provider-neutral DIE State Manager.

```text
context.snapshot()
  -> semantic decision request
  -> P5 authority/freshness normalization
  -> P6 Decision Gateway revalidation
  -> DIE State Manager commit
  -> committed/rejected receipt
  -> Hermes operational acceptance
```

The Gateway does not own missions, canonical state, credentials, workers, retries, scheduling, or strategic judgment.

## 2. Preserved boundaries

- `bin/die_event.py` remains the sole physical append-only writer.
- The Gateway has no database, queue, ledger, daemon, or private memory.
- The read MCP remains read-only; Line 2 commit is not mixed into observation tools.
- Hermes remains the sole operational mission control plane.
- A committed decision is routed to Hermes as `ready_for_operational_acceptance`; P6 v1 does not dispatch or execute it.
- Architect DEV capability is never exposed to runtime cognition.
- `state/EVENTS.jsonl` is not a Gateway input and is never modified by Gateway validation.

## 3. Accepted input

The Gateway accepts only the exact output wrapper from
`state_request.validate_and_normalize()`:

```text
accepted: true
commit_status: validated_not_committed
writer: die-state-manager
normalized:
  schema_version: die.state.request.v1
  request_id: REQ-...
  principal_id / identity_id / scope
  registry-derived authority
  source_snapshot: <complete bounded die.context.snapshot.v1 object>
  object_type: DECISION
  object: <commit-ready decision>
  typed evidence_refs
  assumptions
  submitted_at
```

The complete bounded snapshot is preserved so the Gateway can recompute its deterministic ID, verify its server HMAC, enforce expiry, and match snapshot principal/scope. Decision evidence must already be present in that trusted snapshot.

Raw `die.state.request.v1` input is rejected. The Gateway revalidates registry authority, deterministic integrity, server HMAC, scope, expiry, typed evidence, size bounds, raw-path exclusion, and commit-ready decision fields. Unsigned snapshots, wrong-key signatures, and forged evidence fail closed.

A commit-ready decision requires:

```json
{
  "decision_class": "strategy",
  "choice": "Run the cheapest falsification experiment",
  "reason": "It minimizes cost before scaling",
  "alternatives_rejected": []
}
```

## 4. Commit and replay contract

The Gateway calls only an injected DIE State Manager writer. The production CLI injects `die_event.commit_normalized_decision`.

The State Manager appends `die.decision.v1` with:

- canonical decision ID and timestamp;
- semantic author and registered identity;
- exact request ID and scope;
- authority basis;
- source snapshot cursor and expiry;
- typed evidence references;
- complete bounded semantic decision object;
- `committed_by: die-state-manager`.

`request_id` is the replay key. A repeated request returns the previously committed decision ID and does not append a duplicate record.

## 5. Result

Committed:

```json
{
  "schema_version": "die.decision.gateway.result.v1",
  "gateway": "die-decision-gateway",
  "request_id": "REQ-P6-0001",
  "status": "committed",
  "writer": "die-state-manager",
  "canonical_mutation": true,
  "error": null,
  "commit": {
    "object_type": "DECISION",
    "record_id": "D-0019",
    "committed_at": "2026-08-21T03:02:00+00:00",
    "replayed": false
  },
  "route": {
    "next_owner": "hermes-operator",
    "status": "ready_for_operational_acceptance"
  }
}
```

Rejected results always have `canonical_mutation: false`, no commit receipt, no route, and a typed failure code.

## 6. Snapshot trust deployment gate

Mutation requires the snapshot issuer and Decision Gateway process to share:

- `DIE_SNAPSHOT_HMAC_KEY` — runtime secret of at least 32 bytes;
- `DIE_SNAPSHOT_HMAC_KEY_ID` — non-secret rotation identifier.

The key is never committed, included in a snapshot, written to canonical state, or exposed to runtime cognition. If the key is absent, read-only snapshots remain available but Decision Gateway commit rejects with `E_SNAPSHOT_UNTRUSTED`. A production key has not been provisioned by this local implementation.

## 7. Executable interface

```powershell
python bin/die_state_request.py --input semantic-request.json > normalized.json
python bin/die_decision_gateway.py --input normalized.json
```

The second command is a real commit path. Verification must use an isolated temporary `DIE_HOME` or an injected test writer; it must not create a synthetic decision in live canonical state.

## 8. Verification and acceptance

```powershell
python bin/die_company_brain_check.py
python -m py_compile bridge/income_os_bridge/decision_gateway.py bin/die_event.py bin/die_decision_gateway.py
python -m pytest bridge/tests -q
```

Acceptance requires proof that:

- raw and stale inputs are rejected;
- normalized authority tampering is rejected;
- unsigned and wrong-key snapshots are rejected;
- host paths and credential-shaped values are rejected again;
- an unavailable/failing writer fails closed;
- valid decisions commit only through DIE State Manager;
- replay returns the same decision ID without a second append;
- the Gateway result routes only to Hermes;
- the event log is unchanged by decision commit tests.
