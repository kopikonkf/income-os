# ECON-002A ? State Manager Economic Ledger Commit Boundary v1

Status: **DONE / PASS / SHADOW COMMIT PRIMITIVE ONLY**
Date: 2026-09-09
Depends on: `ECON-002`, `COS-002A`

## 1. Purpose

Close the writer-domain gap intentionally left by ECON-002: the Economic Ledger contract existed, but `state/ECONOMICS.jsonl` had no canonical State Manager commit implementation.

This task adds that implementation **without enabling live financial ingestion**.

## 2. Sovereign writer placement

No second economics writer module was created.

Physical append remains in the already-governed sole writer:

```text
bin/die_event.py
```

The same logical service now owns:

```text
state/EVENTS.jsonl
state/DECISIONS.jsonl
state/ECONOMICS.jsonl
```

through one physical State Manager implementation boundary.

Writer identity is fixed:

```text
die-state-manager
```

Any other `writer_id` fails closed with:

```text
E_ECON_WRITER_ID_FORBIDDEN
```

## 3. Commit primitive

New primitive:

```text
die_event.commit_economic_event(event, writer_id="die-state-manager")
```

Before any append it executes the existing ECON-002 validator:

```text
economic_contracts.validate_ledger_event(event)
```

Therefore the original ECON-002 event contract remains authoritative and is not duplicated or rewritten.

## 4. Idempotency

The canonical store enforces application-level replay protection before append.

Same `idempotency_key` + byte-equivalent semantic event:

```text
replayed = true
no new row
```

Same `idempotency_key` + changed fact:

```text
E_ECON_IDEMPOTENCY_CONFLICT
```

Same `event_id` with a different idempotency key/fact:

```text
E_ECON_EVENT_ID_CONFLICT
```

This prevents duplicate sale/cost/time/resource facts from being silently recorded.

## 5. Correction / reversal

Corrections remain append-only.

For a `REVERSAL` commit:

1. target event must already exist;
2. ECON-002 `validate_reversal()` must pass;
3. Holding identity must match;
4. reversal must remain reference-only;
5. the same original event may not be reversed twice.

Missing target:

```text
E_ECON_REVERSAL_TARGET_NOT_FOUND
```

Second reversal:

```text
E_ECON_ALREADY_REVERSED
```

The original economic row is never edited or deleted.

## 6. Stored row contract

The row stored in `ECONOMICS.jsonl` remains the exact `die.economic-ledger.event.v1` object.

`committed_by` is returned in the commit result rather than injected into the ledger row because the ECON-002 JSON Schema uses `additionalProperties=false`.

This preserves schema compatibility:

```text
ledger row = economic fact
commit result = writer/provenance of mutation action
```

## 7. No live ingestion surface

This task intentionally does **not** add an `economics` CLI subcommand to `die_event.py`.

It also does not add:

```text
bank integration
payment integration
marketplace poller
revenue webhook
H03 product connector
automatic Founder-time observer
provider billing connector
Mission Control economic write path
Hermes direct ledger write path
```

So the new primitive is available for a future governed admission/gateway path, but there is no new autonomous producer of canonical economic events.

## 8. Authority boundary

Existing ECON-002 event authority flags remain mandatory:

```text
bank_integration = false
payment_action = false
spend_authorized = false
capital_allocation_authorized = false
credentials_embedded = false
mutable_after_append = false
```

A candidate with widened authority is rejected before the file is created or modified.

## 9. Executable acceptance

New tests:

```text
company/company-os/tests/test_economic_state_manager.py
```

They prove:

1. first commit appends exactly one event;
2. exact replay is idempotent;
3. wrong writer identity is rejected;
4. idempotency conflict is rejected;
5. event-id conflict is rejected;
6. valid reversal appends while preserving original;
7. missing reversal target is rejected;
8. second reversal is rejected;
9. authority widening causes no canonical write.

Focused task suite: **8/8 PASS**.

## 10. COS-002A relationship

COS-002A historically recorded:

```text
W_ECONOMICS_WRITER_NOT_IMPLEMENTED_CURRENTLY
```

That warning was correct at the time of its receipt and is not rewritten.

After ECON-002A, the executable writer-domain checker observes:

```text
state/EVENTS.jsonl    -> bin/die_event.py
state/DECISIONS.jsonl -> bin/die_event.py
state/ECONOMICS.jsonl -> bin/die_event.py

unauthorized_global_store_writers = []
warnings = []
status = PASS
```

Thus the implementation-completeness warning is resolved by a later auditable task rather than by mutating historical evidence.

## 11. H03 implication

H03 Knowledge/PDF Factory may now produce **candidate economic events** against the ECON-002 contract, but it still may not append to the canonical ledger itself.

Future path:

```text
H03 observation
  -> validated economic event
  -> governed admission/gateway
  -> die-state-manager
  -> state/ECONOMICS.jsonl
```

This keeps Holding code, Mission Control and cognition out of the sovereign writer role.

## 12. Acceptance

**PASS.** The Economic Ledger now has a deterministic State Manager commit primitive inside the existing sole physical writer, with validation, replay protection, immutable reversal semantics and fail-closed writer identity. No live ingestion, spend/payment authority, credential path, provider action or external financial integration was enabled.
