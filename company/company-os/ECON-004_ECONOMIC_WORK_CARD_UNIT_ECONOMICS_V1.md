# ECON-004 — Economic Work Card & Unit-Economics Contract v1

Status: ACCEPTED E0 SHADOW CONTRACT / NO SPEND AUTHORITY
Date: 2026-09-09
Depends on: ECON-002 + ECON-003

## 1. Purpose

Turn a business hypothesis into one bounded economic experiment that can later be judged from evidence rather than confidence.

The Economic Work Card (EWC) is not a purchase order and not execution authority. It connects one `economic_trace_id` to expected economics, a measurement window, falsifier, scale/hold/kill conditions, and later actual Ledger/Attribution evidence.

## 2. Required structure

```text
economic_work_card_id
holding_id
economic_trace_id
parent_task_id
measurement_window
hypothesis
expected
actual
decision_conditions
authority_boundary
```

The card must preserve **forecast vs actual** as separate domains.

## 3. Hypothesis contract

Every card states:

```text
statement
evidence_refs
confidence_basis
falsifier
```

A hypothesis without evidence and a falsifier is rejected. High model confidence is not a substitute.

## 4. Expected economics

Expected values use one explicit currency and include:

```text
capital_requested_minor
revenue_minor
direct_variable_cost_minor
shared_variable_cost_minor
contribution_profit_minor
contribution_margin_bps
payback_days
roic_bps
```

Deterministic math:

```text
ExpectedContributionProfit
= ExpectedRevenue
- ExpectedDirectVariableCost
- ExpectedSharedVariableCost

ExpectedContributionMarginBps
= ExpectedContributionProfit / ExpectedRevenue * 10,000
  (null when expected revenue = 0)

ExpectedROICBps
= ExpectedContributionProfit / CapitalRequested * 10,000
  (null when capital requested = 0)
```

`capital_requested_minor` is a forecast/request field only. It does not authorize spending.

## 5. Actual economics

Actual status is one of:

```text
NOT_MEASURED
PARTIAL
MEASURED
```

Actual fields include:

```text
ledger_event_refs
attribution_claim_refs
currency
capital_observed_minor
revenue_minor
direct_variable_cost_minor
shared_variable_cost_minor
contribution_profit_minor
contribution_margin_bps
founder_active_minutes
cash_profit_minor
economic_profit_minor
payback_days
roic_bps
completeness
```

Rules:

- `NOT_MEASURED` must contain no actual numeric values and no Ledger/Attribution refs.
- `PARTIAL` or `MEASURED` requires Ledger evidence.
- `MEASURED` requires `completeness=YES`.
- contribution profit/margin and ROIC are formula-checked when the required inputs exist.
- `economic_profit_minor` may remain null when Founder shadow rate is unset or completeness is insufficient.

Actual values are observations/derived projections from ECON-002/003; they are never copied from the expected block.

## 6. Capital semantics

Two distinct quantities exist:

```text
capital_requested_minor
= forecasted/requested experiment resource need

capital_observed_minor
= observed capital actually consumed/committed in the measurement evidence
```

The presence of `capital_requested_minor` never grants payment, provider-plan, vendor, infrastructure, or market authority.

## 7. Payback and ROIC

Payback may be null until the measurement window contains enough realized cash-flow evidence.

ROIC v1 uses contribution profit over capital requested/observed because contribution economics is the least arbitrary Holding-level marginal view defined in ECON-001.

Later portfolio policy may add other return metrics, but must not silently redefine v1 ROIC.

## 8. Decision conditions

Every card includes explicit:

```text
kill_condition
scale_condition
hold_condition
```

These are evidence predicates, not execution commands.

Examples:

```text
KILL  -> contribution profit <= 0 after complete window
SCALE -> measured contribution positive + falsifier not triggered + completeness sufficient
HOLD  -> evidence incomplete / measurement window not mature
```

The card records the condition; future Capital Governor may evaluate it in shadow/advisory mode. No condition auto-spends money in ECON-004.

## 9. Evidence > confidence

A card cannot become `MEASURED` merely because an AI updates its estimate. Actuals require economic Ledger events and, where revenue trace credit matters, attribution claims.

If attribution is partial, the card must retain that uncertainty rather than assuming all revenue belongs to the trace.

## 10. Relationship to incidents and Founder time

`parent_task_id`, Ledger `incident_id`, and Founder-time events make recovery/debugging effort visible to the same economic trace. This allows a commercially profitable product to still show high Founder intervention cost.

## 11. Authority boundary

Machine contract fixes:

```text
spend_authorized=false
capital_requested_is_authority=false
external_commitment_authorized=false
provider_plan_change_authorized=false
credentials_embedded=false
```

## 12. Validation

Canonical schema:

```text
company/company-os/schemas/die.economic-work-card.v1.schema.json
```

Canonical validator/tests:

```text
company/company-os/lib/economic_contracts.py
company/company-os/tests/test_economic_contracts.py
```

Tests prove expected math, margin/ROIC math, actual Ledger-evidence requirements, and forecast/actual separation.

## 13. ECON-004 acceptance

**PASS.** Capital requested/observed, expected vs actual revenue/profit/margin/payback/ROIC, Founder minutes, measurement window, falsifier, hold/kill/scale conditions and evidence references are defined with forecast/actual separation. No spend, provider change, external commitment or new authority is created.
