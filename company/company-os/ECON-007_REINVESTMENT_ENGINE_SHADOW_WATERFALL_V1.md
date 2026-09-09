# ECON-007 — Reinvestment Engine v1 Shadow Waterfall

Status: ACCEPTED E0 SHADOW WATERFALL / ZERO LIVE MONEY MOVEMENT
Date: 2026-09-09
Depends on: ECON-006

## 1. Purpose

Translate observed positive company cash operating profit into a **shadow** waterfall for tax liability, reserve top-up, retained earnings, and evidence-backed reinvestment candidates.

The engine simulates capital flow. It does not move money, pay taxes, buy infrastructure, change subscriptions, or create vendor commitments.

## 2. Profit basis

v1 uses:

```text
CASH_OPERATING_PROFIT
```

from the ECON-001/002 economic measurement layer.

The waterfall does not use forecast revenue, GMV, estimated commissions, or Capital Governor priority scores as profit.

Required:

```text
realized_profit_minor
completeness = YES | PARTIAL | NO
currency
period
```

## 3. Fail-closed tax treatment

Tax liability is a scenario/evidence input:

```text
tax_liability_minor
tax_basis_ref
```

The engine does **not** invent a tax rate.

If tax liability is unknown:

```text
tax_liability_minor = null
-> HOLD_INCOMPLETE_EVIDENCE
-> reinvestment_pool_minor = 0
```

Unknown tax liability is never silently treated as zero.

A tax set-aside is not a tax payment and does not constitute tax advice.

## 4. Waterfall order

For complete positive cash operating profit:

```text
Realized Cash Operating Profit
  ↓
Tax Liability Set-Aside
  ↓
Reserve Top-Up
  ↓
Retained Earnings Hold
  ↓
Reinvestment Pool
```

Formula:

```text
ReinvestmentPool
= max(
    RealizedCashOperatingProfit
    - TaxLiability
    - ReserveTopup
    - RetainedEarnings,
    0
  )
```

`reserve_topup_minor` and `retained_earnings_minor` require explicit basis refs. ECON-007 invents no percentage policy.

## 5. Status lattice

```text
profit completeness != YES
or tax liability unknown
  -> HOLD_INCOMPLETE_EVIDENCE
  -> pool 0

realized profit <= 0
  -> NO_POSITIVE_PROFIT_TO_REINVEST
  -> pool 0

complete positive profit
but set-asides consume all profit
  -> NO_POSITIVE_PROFIT_TO_REINVEST
  -> pool 0

complete positive profit
and residual exists
  -> READY_FOR_SHADOW_ALLOCATION
```

## 6. Capital Governor coupling

The reinvestment pool may be simulated against `ECON-006` decisions.

Eligible Governor decisions remain:

```text
SCALE
OPTIMIZE
```

`HOLD` and `KILL` never receive reinvestment allocation.

Every simulated allocation references a `CAP-SHADOW-*` decision and one class:

```text
INFRASTRUCTURE
PRODUCTION
EXPERIMENT
```

The total simulated reinvestment allocation must never exceed the calculated pool.

## 7. Infrastructure recommendations

If an eligible Governor decision belongs to `INFRASTRUCTURE`, the waterfall may emit a recommendation such as:

```text
recommendation = SCALE | OPTIMIZE
simulated_amount_minor > 0
evidence_refs = [...]
live_change_authorized = false
```

This can represent a hypothetical extra VPS, licensed AI/API capacity, storage, or redundancy proposal.

It cannot provision, purchase, terminate, or upgrade anything.

## 8. Reserve and retained earnings are protected semantics

The Reinvestment Engine allocates only the residual reinvestment pool. It cannot raid:

- tax set-aside;
- reserve top-up;
- retained earnings hold.

Those categories remain outside Governor deployment unless a later Founder-ratified policy changes the waterfall contract.

## 9. Evidence requirements

The waterfall requires evidence refs for:

- cash operating profit basis;
- tax liability basis when known;
- reserve top-up basis;
- retained earnings basis;
- infrastructure scale recommendations.

A model-generated number with no provenance is not valid economic evidence.

## 10. Relationship to Founder authority

The waterfall is a simulation of what **could** be retained/reinvested under its scenario inputs.

It does not answer:

> "May the company spend this money now?"

That remains a separate authority question. At E0, answer is no unless separately Founder-authorized outside this engine.

## 11. Authority boundary

Every waterfall carries:

```text
shadow_only=true
money_moved=false
spend_authorized=false
tax_payment_authorized=false
provider_plan_change=false
infrastructure_purchase=false
capital_transfer=false
new_vendor_commitment=false
credentials_embedded=false
```

## 12. Validation

Canonical schema:

```text
company/company-os/schemas/die.reinvestment-waterfall.shadow.v1.schema.json
```

Executable validator/tests:

```text
company/company-os/lib/economic_contracts.py
company/company-os/tests/test_economic_contracts.py
```

Tests prove:

- deterministic waterfall math;
- unknown tax -> HOLD / zero pool;
- incomplete profit evidence -> HOLD / zero pool;
- non-positive profit -> zero pool;
- over-allocation rejected;
- authority widening rejected;
- infrastructure recommendations remain non-live.

## 13. ECON-007 acceptance

**PASS.** Positive realized cash operating profit can be simulated through tax-liability, reserve, retained-earnings and reinvestment stages, then mapped to eligible Capital Governor decisions without moving money or changing paid infrastructure/provider state. Unknown tax/completeness fails closed.
