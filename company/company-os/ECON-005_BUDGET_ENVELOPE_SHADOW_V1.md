# ECON-005 — Budget Envelope v1 Shadow Contract

Status: ACCEPTED E0 SHADOW ALLOCATION / ZERO LIVE SPEND AUTHORITY
Date: 2026-09-09
Depends on: ECON-004 + COS-003

## 1. Purpose

Represent how observed capital **could** be partitioned among reserve, infrastructure, production and experiments without moving money or changing any paid service.

The output is a simulation scenario, not a budget authorization.

## 2. Required envelope classes

Exactly one of each class exists in a v1 scenario:

```text
RESERVE
INFRASTRUCTURE
PRODUCTION
EXPERIMENT
```

Each envelope contains:

```text
envelope_id
class
holding_id (optional)
simulated_amount_minor
authorized_amount_minor = 0
basis
work_card_refs[]
```

## 3. Capital base and reserve

A scenario starts from an **observed capital base** supported by evidence refs.

```text
ObservedCapitalBase
ReserveFloor
ShadowDistributable
```

Deterministic rule:

```text
ShadowDistributable
= ObservedCapitalBase - ReserveFloor
```

and:

```text
ReserveFloor <= ObservedCapitalBase
ReserveEnvelope.simulated_amount >= ReserveFloor
```

No reserve percentage is invented by ECON-005. The amount/floor must come from a separate Founder/policy scenario input.

## 4. Allocation conservation

Only non-reserve envelopes consume `ShadowDistributable`:

```text
Infrastructure
+ Production
+ Experiment
<= ShadowDistributable
```

Unallocated distributable capital is allowed and remains shadow-unallocated.

Over-allocation is invalid rather than silently increasing the capital base.

## 5. Work Card coupling

Infrastructure/production/experiment envelopes may cite one or more `EWC-*` cards.

This provides an evidence path:

```text
Economic Work Card
 -> expected/actual unit economics
 -> shadow envelope proposal
```

A Work Card reference does not imply that its capital request is approved.

## 6. Reserve semantics

Reserve is not a profit center and does not need a Work Card. It is a protected shadow allocation representing the minimum capital the scenario intends not to deploy.

Future reserve policy may include operating runway, tax liabilities or other constraints, but ECON-005 does not invent percentages or accounting categories beyond the explicit `reserve_floor_minor` scenario input.

## 7. Infrastructure envelope

Used to simulate capacity proposals such as:

- another VPS;
- additional licensed AI/API capacity;
- storage/compute expansion;
- redundancy or throughput capacity.

A simulated infrastructure amount cannot provision a host or upgrade a plan. It becomes a candidate for later Governor/Founder evaluation only.

## 8. Production envelope

Represents simulated capital available for already-understood operating production costs, preferably linked to Work Cards with observed contribution economics.

It is not a blanket production-spend authorization.

## 9. Experiment envelope

Represents bounded learning/exploration capital in simulation.

Experiment candidates should cite Work Cards containing measurement windows, falsifiers and kill/scale conditions. This supports Aether's bounded-experiment principle without letting strategic cognition directly spend capital.

## 10. Shadow-only invariant

Every envelope must carry:

```text
authorized_amount_minor = 0
```

Top-level boundary:

```text
simulation_only=true
spend_authorized=false
payment_action=false
capital_transfer=false
provider_plan_change=false
infrastructure_purchase=false
new_vendor_commitment=false
credentials_embedded=false
```

A consumer must fail closed if any of these invariants are violated.

## 11. Evidence requirements

`capital_evidence_refs` cannot be empty. The scenario must state what observed Ledger/financial evidence supports its capital base.

This contract does not define a live bank-balance connector. Evidence may initially be manually/governedly observed economic records.

## 12. No implicit capital policy

ECON-005 deliberately does **not** set:

- reserve percentage;
- maximum drawdown;
- monthly spend cap;
- reinvestment percentage;
- infrastructure percentage;
- experiment percentage.

Those are policy/Founder decisions or later shadow Governor inputs. Encoding them here would silently create capital policy without authority.

## 13. Relationship to Capital Governor

ECON-006 consumes shadow envelopes and Economic Work Cards to produce recommendations such as:

```text
SCALE
HOLD
OPTIMIZE
KILL
```

But ECON-005 itself only checks that the hypothetical allocation is feasible under its stated capital base/reserve floor and contains zero live authorization.

## 14. Validation

Canonical schema:

```text
company/company-os/schemas/die.budget-envelope.shadow.v1.schema.json
```

Canonical validator/tests reject:

- nonzero authorized amounts;
- reserve below floor;
- over-allocation;
- missing capital evidence;
- duplicate/missing required envelope classes;
- any authority-boundary widening.

## 15. ECON-005 acceptance

**PASS.** Reserve, infrastructure, production and experiment envelopes are represented with observed capital base, explicit reserve floor, deterministic distributable math, Work Card links and zero authorization. The contract cannot move money, buy infrastructure, change provider plans, commit vendors or bypass Founder authority.
