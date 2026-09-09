# ECON-002 — Economic Ledger v1 Schema & Immutable Event Contract

Status: ACCEPTED E0 SHADOW LEDGER / NO BANK OR PAYMENT INTEGRATION
Date: 2026-09-09
Depends on: ECON-001

## 1. Purpose

Provide an append-only economic event journal that can support company/Holding cash P&L, Founder-time measurement, resource-usage costing and later attribution/capital analysis without granting any financial execution authority.

The Ledger records observed economic facts. It does not move money, connect a bank, execute a payment, upgrade a provider plan, or allocate capital.

## 2. Canonical event classes

`die.economic-ledger.event.v1` supports:

```text
REVENUE_REALIZED
REVENUE_REFUND
REVENUE_CHARGEBACK

COST_DIRECT_VARIABLE
COST_SHARED_VARIABLE
COST_GLOBAL_FIXED
COST_OTHER_NONVARIABLE

FOUNDER_TIME
RESOURCE_USAGE
FX_RATE_OBSERVED
REVERSAL
```

Normal monetary events store a **non-negative magnitude** in integer minor units. Event type determines economic direction:

```text
REVENUE_REALIZED      -> add revenue
REVENUE_REFUND        -> subtract revenue
REVENUE_CHARGEBACK    -> subtract revenue
COST_*                -> subtract profit / add cost
```

The journal does not encode business meaning through arbitrary positive/negative signs for normal events.

## 3. Append-only rule

Once appended, an event is immutable.

Reference SQLite schema enforces:

```text
UPDATE economic_events -> ABORT E_ECON_LEDGER_APPEND_ONLY_UPDATE_FORBIDDEN
DELETE economic_events -> ABORT E_ECON_LEDGER_APPEND_ONLY_DELETE_FORBIDDEN
```

Every event also has unique:

```text
event_id
idempotency_key
```

so replay of the same source observation cannot silently duplicate revenue/cost/time.

## 4. Correction semantics

Errors are corrected by **append**, never mutation.

```text
bad original event
-> append REVERSAL referencing original event_id
-> append corrected replacement event with a new event_id/idempotency_key
```

`REVERSAL` is reference-only: it carries no money/time/resource/FX quantity itself.

The effective projection excludes:

- all `REVERSAL` records themselves; and
- any original event referenced by a `REVERSAL`.

This one mechanism works consistently for money, Founder time, resource usage and FX observations.

A reversal cannot silently target another Holding. Application validation requires the original and reversal `holding_id` to match.

## 5. Minimum event identity/provenance

Every event requires:

```text
schema_version
event_id
observed_at
event_type
holding_id
source_system
idempotency_key
provenance_ref
authority_boundary
```

Optional correlation:

```text
economic_trace_id
parent_task_id
incident_id
source_event_id
```

`provenance_ref` points to evidence/receipt/source record. Credentials or secret values are never valid provenance payload.

## 6. Revenue events

`REVENUE_REALIZED` means a business policy considers the amount realized, not merely forecast/GMV/listing price.

Minimum monetary payload:

```json
{
  "currency": "IDR",
  "amount_minor": 100000
}
```

Refunds and chargebacks are separate immutable events and do not rewrite the original sale.

If attribution is unavailable, revenue still exists in the Ledger exactly once. ECON-003 may leave 100% attribution as UNKNOWN rather than delaying or inventing the economic fact.

## 7. Cost events

Cost categories are explicit:

- `COST_DIRECT_VARIABLE` — one trace/Holding directly caused it;
- `COST_SHARED_VARIABLE` — shared capacity consumed and later attributable by measured usage;
- `COST_GLOBAL_FIXED` — company fixed overhead such as baseline VPS/subscription;
- `COST_OTHER_NONVARIABLE` — other observed operating cash costs.

A cost event is counted exactly once. Allocation to Holding views is a projection/policy operation, not duplicate cost events.

## 8. Founder-time events

`FOUNDER_TIME` records actual active effort, with:

```text
duration_minutes
precision = MEASURED | ESTIMATED | UNKNOWN
category
```

Allowed categories are inherited from ECON-001.

`UNKNOWN` is not zero. The Ledger stores what is observed; later reports decide whether completeness is sufficient for an economic verdict.

The Ledger does not assign a monetary Founder rate. ECON-001 remains authoritative: rate defaults to `UNSET`.

## 9. Resource-usage events

`RESOURCE_USAGE` links ORG-001 pooled architecture to economics.

Required:

```text
resource_class = G0 | H1 | H2 | P1 | P2 | P3 | P4 | A1
usage_quantity
usage_unit
```

Optional:

```text
runtime_id
principal_id_or_provider_id
cost_event_ref
```

Usage and cost remain separate facts. A CPU-second observation does not fabricate a monetary cost if no paid cost evidence exists.

## 10. FX observations

`FX_RATE_OBSERVED` records a rate as evidence, not a silent global conversion assumption.

Required:

```text
base_currency
quote_currency
rate_text
rate_timestamp
rate_source
```

Original monetary events remain in source currency/minor units. Reporting-currency conversion is a derived projection that cites a dated FX observation.

## 11. Idempotency model

`idempotency_key` should be stable for the same source fact, conceptually:

```text
sha256(source_system + source_event_id + economic_fact_class + source_version)
```

The precise encoding is implementation-specific, but replay must return existing fact/no-op rather than creating a second event.

A changed source fact must produce a new source version/event and, if correcting a prior fact, use REVERSAL + replacement.

## 12. Reference storage schema

Canonical reference DDL:

```text
company/company-os/sql/economic-ledger-v1.sql
```

It provides:

- append-only `economic_events` table;
- uniqueness on event ID and idempotency key;
- Holding/trace/type/task indexes;
- no-UPDATE/no-DELETE triggers;
- raw event count view;
- effective event view excluding reversed events.

This DDL is a **reference schema**, not a live company ledger deployment.

## 13. Validation surface

Canonical validator:

```text
company/company-os/lib/economic_contracts.py
```

Acceptance tests prove:

- append-only UPDATE rejection;
- append-only DELETE rejection;
- duplicate idempotency rejection;
- reference-only REVERSAL semantics;
- effective projection excludes reversed facts;
- Founder UNKNOWN precision remains UNKNOWN;
- ORG-001 resource classes are enforced.

## 14. Relationship to State Manager

COS-002 preserves DIE State Manager sovereignty over canonical company operational truth.

ECON-002 defines the **economic event contract/storage model**, not an authority bypass. A future live ledger implementation must specify how accepted economic events are admitted through State Manager/governed company truth or another Founder-ratified canonical-write path.

Until that implementation exists, ECON-002 artifacts are schema/reference contracts only.

## 15. Security/authority boundary

Every event explicitly states:

```text
bank_integration=false
payment_action=false
spend_authorized=false
capital_allocation_authorized=false
credentials_embedded=false
mutable_after_append=false
```

The Ledger never stores bank passwords, payment credentials, browser cookies, provider tokens or secret material.

## 16. ECON-002 acceptance

**PASS.** An append-only Economic Ledger event schema, SQLite reference DDL, immutable correction/reversal semantics, idempotency model, provenance fields, Founder-time/resource/FX event types and deterministic tests are defined. No bank/payment integration, live financial ingestion, spend authority, capital allocation, credential mutation or runtime cutover was performed.
