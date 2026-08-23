# Mission State Reconciliation v1

Date: 2026-08-23
Owner: Chief Executive Architect DEV
Scope: canonical mission projection, alarm lifecycle, and execution readiness

## Decision

Mission lifecycle is compiled from canonical `DECISIONS.jsonl`. Kanban is the
Hermes operational materialization of that lifecycle; it is not an independent
source that can erase or create a ratified mission by omission.

This follows the constitutional boundary:

- authorized actors are semantic authors;
- DIE State Manager is the sole physical canonical writer;
- Hermes owns decomposition and operational transitions;
- Kanban is an operational projection/materialization.

No database migration, new queue, daemon, or Runtime MCP tool is introduced.

## Deterministic lifecycle compiler

| Highest canonical decision | Projected status | Lifecycle state | Reconcile required | Execution ready |
| --- | --- | --- | --- | --- |
| `mission_ratification` | `ratified` | `ratified` | no | no |
| `propose_mission` | `pending_acceptance` | `proposed` | no | no |
| `mission_acceptance`, no linked Kanban card | `active` | `accepted` | yes | no |
| `mission_acceptance`, linked open/running card | `active` | `materialized` | no | yes |
| accepted, linked cards all completed | `completed` | `materialized` | no | no |
| accepted, linked card blocked/paused | `blocked` / `paused` | `materialized` | no | no |

`active_missions(status=active)` therefore returns an accepted mission even
when Kanban materialization is late. The same row explicitly reports the late
materialization and degrades completeness. Unrelated Kanban cards never count
toward a mission.

The acceptance decision does not authorize production by itself. Production
requires both:

1. mission row `execution_ready=true`; and
2. `system_health.execution_readiness.ready=true`.

M-001 marketplace submission remains A0 and requires Founder approval.

## M-001 reconciliation result

The verified chain is:

| Decision | Meaning |
| --- | --- |
| D-0020 | Founder ratified M-001 for DIVISION-01 |
| D-0021 | DIVISION-01 submitted the canonical mission proposal |
| D-0022 | Hermes accepted M-001 operationally |

Before a mission-linked Kanban card exists, the expected projection is:

```json
{
  "mission_id": "M-001",
  "division_id": "DIVISION-01",
  "status": "active",
  "lifecycle_state": "accepted",
  "reconcile_required": true,
  "execution_ready": false,
  "last_decision_id": "D-0022"
}
```

After Hermes materializes a card, the compiler requires either a CLI row whose
`mission_id` is exactly `M-001` or a canonical event carrying both
`mission_id=M-001` and that card's exact `task_id`. It then changes
`lifecycle_state` to `materialized`, clears `reconcile_required`, and sets
`execution_ready=true`.

The SQLite Kanban fallback has no `mission_id` column. It cannot prove mission
linkage and must not infer linkage from title, card order, assignee, or the
existence of unrelated open cards. A verified CLI row or canonical
mission/task event relation is required.

## Alarm lifecycle and production gate

Historical WARNING/CRITICAL records are fail-closed. They remain active until a
later event explicitly resolves either their `event_id` or their stable
`dedupe_key`.

New event fields are additive:

| Field | Contract |
| --- | --- |
| `dedupe_key` | Stable identity for one recurring alarm cause |
| `alarm_state` | `open` or `resolved` |
| `resolves_event_id` | Exact earlier alarm closed by verified recovery |

Repeated open events with the same `dedupe_key` collapse to the newest open
record. A resolution never deletes history; it only changes the compiled active
set. `system_health.execution_readiness` fails closed when the gateway is not
running, a health source is degraded, or any CRITICAL alarm remains active.

The heartbeat cron now resolves its own Kanban-CLI alarm only after a successful
Kanban read. Its executable lookup supports an explicit `DIE_HERMES_EXE`
override, PATH lookup, and the existing fixed candidates.

## Decision writer invariant

`mission_ratification` cannot be appended without all of:

- `request_id`;
- `semantic_object.division_id`;
- `semantic_object.mission_id`.

Passing any `semantic_object` without `request_id` is rejected instead of
silently dropping semantic metadata. This prevents recurrence of the D-0019
failure mode.

## Snapshot handoff design (deferred implementation)

Signed snapshots must not be copied through chat as large JSON payloads. The
current safe route remains byte-exact programmatic loopback submission.

A future Runtime MCP version may support an opaque one-use `snapshot_ref` with
these invariants:

- server-issued random token with at least 128 bits of entropy, stored hashed;
- bound to principal, scope, snapshot ID, key ID, and expiry;
- maximum one successful consume, atomically enforced;
- TTL no longer than the signed snapshot TTL;
- accepts exactly one of inline `source_snapshot` or `snapshot_ref`;
- never accepts filesystem paths, URLs, or actor-chosen references;
- consumption and failure are audit events;
- resolved bytes still pass the existing HMAC, freshness, scope, and evidence
  exact-match checks.

This document does not change Runtime MCP schemas or wake flow. That remains a
separate Founder-authorized implementation.
