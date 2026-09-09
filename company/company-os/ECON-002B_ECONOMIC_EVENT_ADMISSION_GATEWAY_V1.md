# ECON-002B ? Economic Event Admission Gateway v1

Status: **DONE / PASS / SHADOW VALIDATION ONLY**
Date: 2026-09-09
Depends on: `ECON-002A`

## 1. Purpose

Define the only supported **pre-commit** envelope for future economic observations before they are eligible to reach the State Manager writer boundary.

This task does not authorize canonical economic commits. It prepares a deterministic `validated_not_committed` object that preserves Holding identity, provenance and zero-authority guarantees.

## 2. Separation of responsibilities

```text
Holding / observer / worker
        ?
Economic candidate event
        ?
ECON-002B admission validation
        ?
validated_not_committed
        ?
[future separately authorized commit activation]
        ?
ECON-002A State Manager commit primitive
        ?
state/ECONOMICS.jsonl
```

The admission module does not import or invoke `die_event` and has no filesystem write surface.

## 3. Canonical admission module

```text
company/company-os/lib/economic_admission.py
```

Primary functions:

```text
prepare_admission(event, evidence_refs, holding_id)
validate_admission(payload)
```

The module reuses the accepted ECON-002 validator:

```text
economic_contracts.validate_ledger_event()
```

No duplicate economic event semantics are defined here.

## 4. Admission envelope

A valid envelope has exactly:

```text
schema_version
status
writer
holding_id
event
evidence_refs
authority_boundary
```

Required identity:

```text
schema_version = die.economic-ledger.admission.v1
status         = validated_not_committed
writer         = die-state-manager
```

The event `holding_id` must exactly match the envelope Holding.

## 5. Evidence requirements

Admission requires at least one non-empty evidence reference.

The event's own:

```text
provenance_ref
```

must appear in:

```text
evidence_refs[]
```

This prevents a candidate event from carrying provenance text that is not actually part of the submitted evidence set.

Duplicate evidence references are rejected.

## 6. Authority boundary

Every admission envelope is forced to:

```text
canonical_commit_authorized = false
live_ingestion_authorized = false
spend_authorized = false
payment_action = false
capital_allocation_authorized = false
credential_access = false
external_submission = false
```

Any changed field causes deterministic rejection.

Therefore `validated_not_committed` means exactly that: the event passed semantic/schema/provenance checks but does not gain canonical mutation authority.

## 7. No premature principal authority

This task intentionally does **not** add a new `state.economic.submit` action or capability to `company/identity-registry.json`.

Reason: current constitutional/control-plane reconciliation is not yet complete. Adding a submitter now would prematurely choose whether Executive, Hermes, Mission Control, a Holding-local runtime or another principal owns economic admission authority.

That authority decision remains separate from this data contract.

## 8. No writer coupling

Static acceptance proves the admission module contains none of:

```text
die_event
ECONOMICS.jsonl
open(
write_text
write_bytes
```

Thus this layer cannot become a hidden second writer.

## 9. H03 / H01 use

H03 Knowledge/PDF Factory and H01 Factory may produce admission candidates while remaining non-sovereign.

Example H03 flow:

```text
PDF build receipt
  -> RESOURCE_USAGE event candidate
  -> evidence_refs include build receipt
  -> ECON-002B validation
  -> validated_not_committed
```

At this stage the candidate can be inspected, tested and retained as shadow evidence without writing canonical economics.

## 10. Future activation boundary

A later governed task may define:

- which registered principal/action may submit economic admissions;
- whether Mission Control routes but does not author them;
- whether a human/Founder gate is required for specific event classes;
- how validated admissions reach `die_event.commit_economic_event`;
- replay/reconciliation when an external source is ambiguous.

Until that task is accepted, this gateway remains validation-only.

## 11. Acceptance tests

`company/company-os/tests/test_economic_admission.py` proves:

1. valid candidate becomes `validated_not_committed`;
2. evidence is mandatory;
3. provenance must be represented in evidence refs;
4. Holding mismatch fails;
5. authority widening fails;
6. writer/status mutation fails;
7. ECON-002 authority rules are reused;
8. the admission module has no physical writer path.

Focused suite: **8/8 PASS**.

## 12. Acceptance

**PASS.** DIE now has a deterministic economic pre-commit admission contract that can be used by H01/H03 shadow economics without granting live ingestion or canonical-write authority. Physical writing remains exclusively behind ECON-002A State Manager commit semantics and is not callable from this module.
