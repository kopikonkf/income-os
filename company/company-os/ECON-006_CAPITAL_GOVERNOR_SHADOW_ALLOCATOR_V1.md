# ECON-006 — Capital Governor v1 Shadow Allocator

Status: ACCEPTED E0 SHADOW GOVERNOR / ZERO LIVE CAPITAL AUTHORITY
Date: 2026-09-09
Depends on: ECON-005

## 1. Purpose

Convert Economic Work Card evidence into deterministic shadow recommendations and simulated capital allocations without moving money or creating live spending authority.

The Governor answers:

```text
SCALE | HOLD | OPTIMIZE | KILL
```

and, for eligible recommendations only, proposes a bounded `simulated_allocation_minor` inside the applicable Budget Envelope.

## 2. Governor is not the treasury

Capital Governor v1 may rank and simulate. It may not:

- spend or transfer money;
- change provider plans;
- purchase infrastructure;
- create vendor commitments;
- submit/publish externally;
- mutate credentials;
- convert a Work Card capital request into authorization;
- change `authorized_amount_minor` from zero.

At E0, every result remains advisory/shadow evidence.

## 3. Decision lattice: evidence before score

The recommendation is derived before priority scoring.

```text
actual not MEASURED or completeness != YES
  -> HOLD

MEASURED + complete + kill predicate TRUE
  -> KILL

MEASURED + complete + contribution profit <= 0
  -> KILL

MEASURED + complete + positive contribution + scale predicate TRUE
  -> SCALE

MEASURED + complete + positive contribution + hold predicate TRUE
  -> HOLD

MEASURED + complete + positive contribution
+ no scale/hold/kill predicate
  -> OPTIMIZE
```

Therefore a high AI/strategy score cannot turn incomplete evidence into SCALE or override a KILL condition.

## 4. Condition evaluation

The Governor consumes evaluated Work Card conditions:

```text
kill_condition  = TRUE | FALSE | UNKNOWN
scale_condition = TRUE | FALSE | UNKNOWN
hold_condition  = TRUE | FALSE | UNKNOWN
```

Those evaluations must be evidence-backed. The Governor does not parse free-form Work Card prose and pretend that semantic inference is accounting truth.

The Work Card falsifier is carried into the decision receipt and should feed the kill-condition evaluation when triggered.

## 5. Priority score v1

After the recommendation lattice is satisfied, eligible candidates may be ranked using explicit dimensions:

```text
ReturnSignalBps
EvidenceStrengthBps
StrategicFitBps
LearningValueBps
RiskPenaltyBps
```

All non-return dimensions are 0..10,000 bps and require evidence refs.

Risk retention:

```text
RiskRetentionBps = 10,000 - RiskPenaltyBps
```

Return signal:

```text
if actual_status == MEASURED and actual_roic_bps exists:
    ReturnSignalBps = actual_roic_bps
else:
    ReturnSignalBps = expected_roic_bps or 0
```

Priority score:

```text
max(ReturnSignalBps, 0)
* EvidenceStrengthBps
* StrategicFitBps
* LearningValueBps
* RiskRetentionBps
/ 10,000^4
```

Integer floor is used for deterministic implementation.

Formula version:

```text
capital-governor-v1-multiplicative-bps
```

This score is a ranking signal, not a financial truth statement and not authority.

## 6. Why multiplicative

Multiplication gives each dimension veto-like influence:

- zero evidence strength -> zero score;
- zero strategic fit -> zero score;
- zero learning value -> zero score;
- maximum risk penalty -> zero score;
- non-positive return signal -> zero score.

This matches the doctrine that an impressive single dimension should not hide a fatal weakness.

The numeric inputs themselves must remain evidence-backed; the formula does not make subjective inputs objective.

## 7. Dimension evidence

Every decision carries evidence arrays for:

```text
evidence_strength
strategic_fit
learning_value
risk_penalty
```

Examples:

- Ledger/Attribution completeness and repeatability evidence;
- Founder-ratified strategic/portfolio references;
- experiment/knowledge gain evidence;
- incident, dependency, provider, legal/authority, volatility or operational risk evidence.

A dimension without evidence is invalid rather than silently defaulted.

## 8. Simulated allocation

Each decision has:

```text
allocation_cap_minor
simulated_allocation_minor
```

The cap is a shadow maximum for this decision; it is not authorization.

Only:

```text
SCALE
OPTIMIZE
```

are allocation-eligible.

`HOLD` and `KILL` must have:

```text
simulated_allocation_minor = 0
```

A zero priority score also receives zero allocation.

## 9. Deterministic allocator ordering

Within one available shadow pool, eligible decisions are ordered by:

```text
1. SCALE before OPTIMIZE
2. higher priority_score first
3. economic_work_card_id ascending as deterministic tie-break
```

Allocation is then bounded sequentially:

```text
allocation = min(allocation_cap_minor, remaining_shadow_capital)
```

The allocator never creates extra capital and never exceeds a candidate cap.

A future Governor version may introduce portfolio diversification constraints, but v1 intentionally keeps ranking transparent and testable.

## 10. Envelope relationship

Governor decisions reference one non-reserve class:

```text
INFRASTRUCTURE
PRODUCTION
EXPERIMENT
```

The containing ECON-005 Budget Envelope remains responsible for overall shadow capital conservation and reserve protection.

The Governor does not allocate from `RESERVE`.

## 11. Expected vs observed economics

Observed economics dominate recommendation eligibility:

- complete observed unit economics can trigger SCALE/OPTIMIZE/KILL;
- partial or unmeasured economics default HOLD;
- expected ROIC may contribute to a ranking signal when actual ROIC is absent, but cannot bypass the HOLD gate.

This preserves `Evidence > Confidence`.

## 12. Founder-time and economic profit

Founder-time/economic-profit observations remain part of the Work Card evidence. Governor v1 does not invent a Founder hourly rate.

If economic profit is not computable because the Founder shadow rate is unset, the Governor must not claim the organism is `ECONOMIC_POSITIVE` merely from its priority score.

## 13. Recommendation semantics

### SCALE

Evidence supports increasing or fully supporting the bounded candidate in shadow allocation. It does not authorize execution.

### HOLD

Do not add shadow deployment now. Common causes: incomplete evidence, measurement window not mature, explicit hold predicate, or insufficiently proven actual economics.

### OPTIMIZE

Observed economics are positive but scale conditions are not yet satisfied and no hold/kill condition applies. The candidate may receive bounded shadow optimization allocation.

### KILL

Complete measured economics fail the kill predicate or contribution economics are non-positive. Shadow allocation is zero. A live shutdown/destructive action would still require its own operational/authority basis.

## 14. Authority boundary

Every machine decision requires:

```text
shadow_only=true
spend_authorized=false
payment_action=false
capital_transfer=false
provider_plan_change=false
infrastructure_purchase=false
new_vendor_commitment=false
external_submission=false
credentials_embedded=false
```

Failure of any boundary field invalidates the decision.

## 15. Validation surface

Canonical schema:

```text
company/company-os/schemas/die.capital-governor.shadow-decision.v1.schema.json
```

Canonical executable validation/allocation:

```text
company/company-os/lib/economic_contracts.py
```

Acceptance tests prove:

- complete positive candidate -> SCALE;
- incomplete evidence -> HOLD even with attractive expectation;
- complete non-positive economics -> KILL;
- positive measured candidate without scale/hold/kill -> OPTIMIZE;
- score cannot override recommendation lattice;
- score tampering is rejected;
- authority widening is rejected;
- SCALE precedes OPTIMIZE in simulated allocation;
- HOLD/KILL receive zero;
- allocation respects available pool and per-candidate caps;
- zero score receives zero allocation.

## 16. Relationship to ECON-007 / ECON-008

ECON-006 emits the evidence-backed shadow recommendation layer consumed by:

- `ECON-007` Reinvestment Engine v1 shadow waterfall;
- `ECON-008` Northstar Planner responsibility contract.

Neither downstream task inherits live spend authority from ECON-006.

## 17. ECON-006 acceptance

**PASS.** Historical/observed economics can produce deterministic SCALE/HOLD/OPTIMIZE/KILL decisions, evidence-backed multiplicative priority scores, falsifier/basis references, and bounded simulated allocations. Recommendation gates dominate score, allocation is conserved/capped, and all payment/spend/provider/infrastructure/vendor/credential/external authority remains false.
