# ECON-001 — Economic Observer v1 Measurement Contract

Status: ACCEPTED E0 SHADOW MEASUREMENT / NO SPEND AUTHORITY
Date: 2026-09-09
Maturity: `E0 OBSERVE`
Authority: subordinate to DIE Constitution and COS-003 Aether↔DIE bridge. Measurement does not authorize capital allocation, purchasing, paid-plan upgrades or reinvestment.

## 1. Purpose

Answer, with evidence rather than intuition:

> Is this organism producing more economic value than the cash, compute, provider capacity, Founder time and operational attention it consumes?

The Observer measures. It does not spend, optimize by itself, or move capital.

## 2. Required economic views

### 2.1 Revenue

Record **realized** revenue/commission/cash-equivalent business proceeds separately from forecasts.

```text
GrossRealizedRevenue
- refunds
- chargebacks/reversals
= NetRealizedRevenue
```

Forecast, GMV, listing price, unpaid invoice and estimated affiliate commission are not realized revenue unless an explicit policy says otherwise.

### 2.2 Contribution P&L

```text
NetRealizedRevenue
- DirectVariableCosts
- SharedVariableUsageCosts attributable by measured consumption
= ContributionProfit
```

Variable/direct examples: paid API/render jobs, marketplace/payment fees, ads/distribution, per-job services, directly attributable storage/egress and product-specific purchased inputs.

### 2.3 Company Cash Operating P&L

```text
ContributionProfit_company
- GlobalFixedOperatingCashCosts
- OtherNonVariableOperatingCashCosts
= CashOperatingProfit
```

Fixed/shared examples: VPS/server subscriptions, AI/web-chat subscriptions, domains/infrastructure, baseline storage, software subscriptions and company-level connectivity/tooling.

Each cash expense is counted **exactly once** at company level.

### 2.4 Economic P&L including Founder labor

Founder effort is measured in actual active minutes first.

If Founder configures shadow hourly rate `FounderRate`:

```text
FounderLaborCost
= FounderActiveMinutes / 60 * FounderRate

EconomicOperatingProfit
= CashOperatingProfit - FounderLaborCost - OtherExplicitNonCashLaborCost
```

If no Founder shadow hourly rate is configured:

```text
EconomicOperatingProfit = NOT_COMPUTABLE_RATE_UNSET
```

Still report Founder minutes and, when minutes > 0:

```text
FounderBreakEvenHourlyValue
= CashOperatingProfit / (FounderActiveMinutes / 60)
```

This exposes the implied value of Founder time without inventing a labor rate.

## 3. Founder-time measurement

Categories:

- `FOUNDER_AUTHORITY_DECISION`
- `FOUNDER_MANUAL_PRODUCTION`
- `FOUNDER_QC_REVIEW`
- `FOUNDER_INCIDENT_RECOVERY`
- `FOUNDER_REAUTH_ACCOUNT_SETUP`
- `FOUNDER_ENGINEERING_ASSIST`
- `FOUNDER_ADMIN_DISTRIBUTION`
- `FOUNDER_STRATEGY_RESEARCH`
- `FOUNDER_OTHER_ACTIVE`

Record active effort, not passive waiting.

Every observation stores:

```text
started_at / ended_at or duration_minutes
precision = MEASURED | ESTIMATED | UNKNOWN
holding_id or GLOBAL
parent_task_id / incident_id where applicable
reason/category
```

`UNKNOWN` time must not be silently converted to zero.

## 4. Automation-efficiency metrics

### Zero-Touch Rate

A workflow is `zero_touch_eligible=true` only when its accepted contract does not require a Founder action for normal completion.

```text
ZeroTouchRate
= eligible completed workflow instances with 0 Founder active minutes after dispatch
/ all completed zero-touch-eligible workflow instances
```

Founder-gated QC/constitutional decisions are reported separately rather than counted as automation failure.

### Founder Intervention Rate

```text
FounderInterventionRate
= completed workflow instances with >0 Founder active minutes
/ completed workflow instances
```

### Founder Minutes per Revenue

```text
FounderMinutesPerRevenueUnit
= FounderActiveMinutes / NetRealizedRevenue_in_reporting_currency
```

Dashboards may normalize per 1,000 or 1,000,000 currency units, but must expose the normalization factor.

### Automated Recovery Rate

For policy-eligible automatically recoverable incidents (`L0` or accepted `L1`):

```text
AutomatedRecoveryRate
= recoverable incidents resolved without Founder active intervention
/ all recoverable incidents resolved in period
```

### Architect Escalation Rate

```text
ArchitectEscalationRate
= incidents/workflows entering L2 engineering escalation
/ explicitly stated relevant denominator
```

Never hide the denominator.

## 5. Economic trace identity

Every lineage receives stable `economic_trace_id`.

Minimum correlation dimensions:

```text
economic_trace_id
holding_id
business_unit_id (optional)
opportunity_id (optional)
product_or_asset_id
production_job_id
listing_or_distribution_id (optional)
campaign_id (optional)
order_or_sale_id (optional)
revenue_event_id (optional)
incident_id (optional)
mission_task_id (optional)
```

Missing lineage is `ATTRIBUTION_UNKNOWN`; it is never guessed.

`ECON-003` will define detailed revenue attribution. ECON-001 only locks the minimum correlation contract.

## 6. Cost attribution rules

### Direct cost

If a cost is caused by exactly one economic trace/Holding, tag it directly.

### Shared variable usage

Allocate by measured consumption where available, for example API billing units/tokens, render minutes, CPU-seconds, storage GB-month, egress bytes, or paid provider-capacity units.

Do not allocate shared variable cost equally by Holding count when usage measurements exist.

### Global fixed overhead

Global control-plane/server/subscription costs are company overhead by default.

A Holding contribution P&L may exclude unallocable global overhead rather than fabricate precision.

A fully allocated Holding P&L requires explicit `allocation_policy_id`; preserve both pre-allocation and post-allocation views.

## 7. Resource usage events from ORG-001

Economic Observer ingests resource measurements tagged:

```text
holding_id
runtime_id
principal_id/provider_id
resource_class = G0 | H1 | H2 | P1 | P2 | P3 | P4 | A1
usage_quantity
usage_unit
cost_event_ref if paid
parent_task_id
economic_trace_id
```

This keeps pooled architecture measurable without pretending every Holding owns dedicated hardware.

## 8. Reporting currency and money representation

Store source monetary events in original currency and integer minor units where practical.

Any reporting-currency conversion records:

```text
source_currency
source_amount_minor
reporting_currency
conversion_rate
rate_timestamp
rate_source
converted_amount_minor
```

No exchange rate is invented or silently backfilled.

## 9. Economic truth statuses

### `CASH_POSITIVE`

May be claimed only when NetRealizedRevenue > 0, CashOperatingProfit > 0, and no materially unbounded/unknown cash revenue or cash cost prevents the conclusion.

### `ECONOMIC_POSITIVE`

May be claimed only when cash-positive conditions hold, Founder shadow hourly rate is explicitly configured, EconomicOperatingProfit > 0, and relevant Founder-time observations are not materially unknown.

### `NEGATIVE`

Use when the corresponding measured profit is <= 0 with sufficiently complete data.

### `UNPROVEN`

Use when missing/ambiguous revenue, cost, attribution, labor-time or FX data prevents a defensible conclusion.

Prefer `UNPROVEN` over an unsupported positive claim.

## 10. Data completeness

Every period reports:

```text
revenue_complete
cash_cost_complete
variable_usage_complete
founder_time_complete
attribution_complete
fx_complete
```

Values: `YES | PARTIAL | NO | NOT_APPLICABLE`.

A positive verdict cannot rely on a missing material category being treated as zero.

## 11. Company vs Holding economics

### Company view

Answers whether DIE as a whole is cash/economic positive after all company overhead and Founder effort. Includes global fixed costs exactly once.

### Holding contribution view

Answers whether Hxx generates positive contribution before arbitrary corporate-overhead allocation. This is the primary marginal SCALE/HOLD/KILL input later.

### Fully allocated Holding view

Optional and policy-dependent. Never replace contribution view because overhead allocation can distort marginal economics.

## 12. Periodic report minimum

Daily/weekly/monthly report:

```text
period
reporting_currency
NetRealizedRevenue
DirectVariableCosts
SharedVariableUsageCosts
ContributionProfit
GlobalFixedOperatingCashCosts
CashOperatingProfit
FounderActiveMinutes
FounderShadowHourlyRate or UNSET
FounderLaborCost or NOT_COMPUTABLE
EconomicOperatingProfit or NOT_COMPUTABLE
FounderBreakEvenHourlyValue if defined
ZeroTouchRate
FounderInterventionRate
AutomatedRecoveryRate
ArchitectEscalationRate
attribution/completeness
cash verdict
economic verdict
top cost drivers
top revenue contributors
```

Forecasts remain separate from actuals.

## 13. Operational cost vs revenue proof

The organism is **not proven economically positive** merely because cash revenue exists.

```text
Revenue observed
-> contribution positive?
-> company cash operating positive?
-> how many Founder minutes were required?
-> if Founder rate configured: economic operating positive?
-> is the result repeatable across multiple periods?
```

ECON-001 does not invent how many profitable periods are required to scale; later governance defines that evidence threshold.

## 14. E0 authority boundary

Economic Observer may ingest/normalize measurement events, calculate/report formulas, flag missing data and produce shadow analysis.

It may not purchase/upgrade an AI plan, provision/terminate paid infrastructure, move money, change provider billing, allocate live spending envelopes, reinvest profit, submit/publish externally, mutate credentials, or infer Founder approval from observation.

## 15. ECON-001 acceptance

**PASS.** Cash P&L, contribution P&L, economic P&L, Founder active-time measurement, Zero-Touch Rate, Founder Intervention Rate, Automated Recovery Rate, Architect Escalation Rate, minimum attribution IDs, pooled-resource cost tags, completeness rules and defensible positive/negative/unproven verdicts are defined. No Founder labor rate, spend authority, capital allocation, infrastructure purchase, provider upgrade or runtime mutation is created.
