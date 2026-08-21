# DIE State Context v1

Status: IMPLEMENTED ON FEATURE BRANCH
Constitutional authority: `CONSTITUTION.md`
Identity authority: `company/identity-registry.json`
Agency contract: `PROTOCOLS/agency-contract-v0.md`

## 1. Decision

Extend the existing read-only bridge with the smallest provider-neutral P5 slice:

1. registry-backed principal authorization;
2. typed, bounded, versioned `context.snapshot()`;
3. typed provenance and evidence references;
4. freshness enforcement;
5. deterministic semantic decision-request validation.

The slice does not create a database, queue, daemon, second writer, or Decision Gateway runtime.

## 2. Preserved boundaries

- `bin/die_event.py` remains the only physical writer for EVENTS/DECISIONS/ECONOMICS.
- DIE State Manager remains persistence authority.
- Hermes remains mission owner and operational control plane.
- Runtime cognition receives semantic projection only.
- Architect DEV capability is never inherited by runtime identities.
- `state/EVENTS.jsonl` is live truth and is neither rewritten nor included in this change.

## 3. Context snapshot contract

Public bridge/MCP surface: `context_snapshot`
Semantic operation: `context.snapshot()`
Initial and only v1 authorized consumer: `chatgpt-plus-executive`

A snapshot contains:

- schema and snapshot version;
- deterministic snapshot ID;
- principal, scope, and authority basis;
- creation/expiry timestamps and TTL;
- source event cursor;
- completeness and worst source trust;
- typed provenance;
- typed evidence references;
- bounded semantic data from system state, health, missions, and recent events.

Default TTL is 900 seconds. Expired snapshots fail with `E_STALE_SNAPSHOT`. Oversized recent-event data is trimmed before output; a payload still above the semantic size limit is rejected.

Unregistered principals fail closed. Identity templates cannot act before a governed instantiation exists. `division-head-template` is deliberately rejected in v1, and the snapshot action requires the Executive-only `semantic_observation` capability until division-level filtering exists.

## 4. Semantic decision request

`bin/die_state_request.py` validates one `die.state.request.v1` object and returns a normalized request with:

```json
{
  "accepted": true,
  "commit_status": "validated_not_committed",
  "writer": "die-state-manager"
}
```

The command never appends to canonical state. A future Decision Gateway/State Manager adapter may consume only normalized requests.

Initial supported action:

```text
state.decision.submit -> DECISION
```

Validation requires:

- registered principal and exact registered scope;
- required decision capability;
- fresh source snapshot;
- matching snapshot principal and scope;
- typed evidence references;
- no unknown request fields;
- no raw host paths, traversal, credential-shaped values, or oversized semantic objects.

## 5. Failure codes

| Code | Meaning |
| --- | --- |
| `E_UNAUTHORIZED_PRINCIPAL` | Principal is not in the Company Brain registry |
| `E_UNINSTANTIATED_TEMPLATE` | A template attempted to act directly |
| `E_FORBIDDEN_ACTION` | Principal lacks the required capability |
| `E_SCOPE_DENIED` | Requested scope exceeds registered scope |
| `E_DEV_PRIVILEGE_DENIED` | Runtime/semantic path attempted to acquire DEV privilege |
| `E_STALE_SNAPSHOT` | Snapshot expired |
| `E_SNAPSHOT_PRINCIPAL_MISMATCH` | Request and snapshot principals differ |
| `E_SNAPSHOT_SCOPE_MISMATCH` | Request and snapshot scopes differ |
| `E_EVIDENCE_INVALID` | Evidence reference is incomplete or untyped |
| `E_REQUEST_INVALID` | Request schema is malformed |
| `E_NO_RAW_ACCESS` | Semantic object contains a host path, traversal, or credential-shaped value |
| `E_REQUEST_TOO_LARGE` | Request or semantic object exceeds its bounded size |

## 6. Verification

```powershell
python bin/die_company_brain_check.py
python -m pytest bridge/tests -q
python -m py_compile bridge/income_os_bridge/authority.py bridge/income_os_bridge/snapshot.py bridge/income_os_bridge/state_request.py bin/die_state_request.py
python -m income_os_bridge context_snapshot --principal_id chatgpt-plus-executive
```

Acceptance requires unauthorized-principal and stale-snapshot rejection tests plus the complete regression suite.
