# ECON-009 — H01/H03 Shadow Economics Pilot Design v1

Status: ACCEPTED PILOT DESIGN / NOT YET AN EVIDENCE WINDOW PASS
Date: 2026-09-09
Depends on: ECON-004 + ORG-001

## 1. Purpose

Select two deliberately different Holding flows for read-only E0 economic measurement before promoting the Economic Layer to E1 advisory maturity.

Pilot selection:

```text
H01 -> lineage-rich isolated asset production flow
H03 -> direct knowledge-product flow
H02 -> deferred from v1 because multi-touch affiliate/media attribution is harder
```

This task designs the pilot. It does not claim that the pilot evidence window has already occurred.

## 2. H01 pilot

Selected flow:

```text
H01-L0-ISOLATED-ASSET-LINEAGE-V1
```

Canonical lineage:

```text
Object/Human Atlas opportunity or seed
 -> Blueprint / product expression
 -> PRODSEED / Factory production job
 -> source-original + derivatives
 -> metadata / QA / rights / package
 -> platform listing/submission identity when available
 -> sale/download/order evidence when exposed
 -> realized marketplace revenue/payout
```

Why H01 first:

- canonical Factory production identities already exist;
- production artifacts/receipts/resource usage are relatively observable;
- seed/concept/production/package relationships are richer than a greenfield flow;
- Founder intervention and incident recovery costs can be attached to the same trace;
- downstream marketplace revenue can be added when actual evidence appears.

No marketplace revenue is assumed merely because an asset/package exists.

## 3. H01 measurement minimum

Capture when observed:

```text
production cost
pooled resource usage
Founder active minutes
incident/recovery Founder minutes
product/package lineage
listing identity
sale/revenue evidence
attribution completeness
```

Minimum outputs after a closed window:

- ECON-002 events;
- ECON-004 Work Card actuals;
- explicit attribution status;
- Founder intervention metrics;
- ECON-006 Governor recommendation when evidence reaches required completeness.

## 4. H03 pilot

Selected flow:

```text
H03-KNOWLEDGE-PRODUCT-DIRECT-SALE-V1
```

Canonical lineage model from ECON-003:

```text
human problem/opportunity
 -> product hypothesis
 -> knowledge/PDF/tool product
 -> product page/listing
 -> checkout/order
 -> realized sale
```

Current canon does **not** prove a live H03 product, checkout, or realized revenue path. Therefore the pilot begins honestly as:

```text
build cost
+ resource usage
+ Founder time
+ lineage readiness
+ future order/revenue evidence when it exists
```

Until real order/revenue evidence exists:

```text
revenue verdict = UNPROVEN
```

not an invented zero and not an invented positive value.

## 5. Why H02 is deferred

H02 affiliate/media has additional attribution complexity:

```text
content
 -> platform exposure
 -> tracked link/session
 -> external merchant order
 -> commission state
 -> payout
```

Multi-touch and cross-system gaps increase the risk that v1 attribution mechanics are confused with probabilistic marketing inference.

The safer sequence is:

```text
prove economic machinery on H01 + direct H03 lineage
then add H02 attribution complexity
```

H02 is deferred, not rejected.

## 6. Read-only collection model

ECON-009 does not connect a bank, marketplace, payment processor, checkout, or provider API.

Initial observations may come from already governed receipts/exports/manual evidence and are normalized into ECON contracts only through a future live ingestion task.

This design does not authorize that ingestion task.

## 7. Evidence window gate

`ECON-010` requires external gate:

```text
SUFFICIENT_SHADOW_EVIDENCE_WINDOW
```

ECON-009 explicitly records:

```text
satisfied = false
```

The gate requires evidence, not elapsed days.

At minimum:

1. H01 has a closed Work Card measurement window with required cost/resource/Founder-time completeness and explicit revenue-attribution status.
2. H03 has a closed Work Card measurement window covering build cost/resource/Founder time and explicit revenue state; lack of live orders remains `UNPROVEN`.
3. Founder-time UNKNOWN is not materially hiding intervention cost.
4. Cash-cost completeness supports the claimed verdicts.
5. `ATTRIBUTION_UNKNOWN` is preserved rather than converted to confident credit.
6. Governor shadow recommendations exist and can later be compared with outcomes.
7. No shadow layer has taken a live capital/account/provider/external side effect.

## 8. What does not satisfy the gate

Insufficient by itself:

- repository tests passing;
- one generated asset;
- one product draft;
- a forecasted revenue number;
- an AI confidence score;
- elapsed calendar time;
- a Work Card with `NOT_MEASURED` actuals;
- simulated Governor allocation;
- H03 product concept without an observed measurement window.

## 9. Pilot comparison objective

The two flows intentionally test different questions:

### H01

> Can a mature production lineage reduce Founder minutes and produce measurable contribution economics as assets move toward market evidence?

### H03

> Can a simpler direct-product lineage expose build economics and eventually deterministic order/revenue attribution without the multi-touch ambiguity of affiliate media?

Together they test whether the Economic Layer works across both a production-heavy Holding and a knowledge-product Holding.

## 10. Authority boundary

```text
mode=READ_ONLY_SHADOW
live_ingestion=false
spend_authorized=false
external_submission=false
payment_action=false
provider_plan_change=false
credential_mutation=false
```

The pilot does not make H01 submit assets or H03 launch a product.

## 11. Machine pilot plan

Canonical plan:

```text
company/company-os/pilots/H01_H03_SHADOW_ECONOMICS_PILOT_V1.json
```

Executable contract validation rejects H02 substitution, live-revenue assumptions, premature evidence-gate promotion, and authority widening.

## 12. ECON-009 acceptance

**PASS.** One lineage-rich H01 isolated-asset flow and one direct H03 knowledge-product flow are selected for read-only economics measurement. H03 live revenue is explicitly unproven, H02 multi-touch affiliate/media is deferred, and `SUFFICIENT_SHADOW_EVIDENCE_WINDOW` remains unsatisfied pending actual closed-window evidence.
