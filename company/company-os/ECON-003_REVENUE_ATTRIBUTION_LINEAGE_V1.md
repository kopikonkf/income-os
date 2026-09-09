# ECON-003 — Revenue Attribution Lineage v1

Status: ACCEPTED E0 ATTRIBUTION CONTRACT / NO REVENUE CREATION
Date: 2026-09-09
Depends on: ECON-001

## 1. Purpose

Define how realized revenue/commission is linked back to the opportunity, product/asset, production, distribution and conversion lineage that plausibly created it, without guessing missing evidence or double-counting money.

ECON-003 does not create revenue. Revenue exists exactly once as an ECON-002 Ledger event. Attribution is a governed analytical projection over that event.

## 2. Canonical lineage

Reference business path:

```text
OPPORTUNITY
 -> BLUEPRINT
 -> PRODUCT_ASSET
 -> PRODUCTION_JOB
 -> LISTING_DISTRIBUTION
 -> CLICK_SESSION       (when observable)
 -> ORDER_SALE
 -> REVENUE_EVENT
 -> COMMISSION_PAYOUT   (when affiliate model applies)
```

Incident nodes may attach as `AFFECTED_BY` evidence but do not create commercial credit.

Not every Holding uses every node. H01 asset marketplaces may jump from listing to sale/revenue. H03 direct products may have product -> listing -> order -> revenue. H02 affiliate flows may include click/session -> external order -> commission payout.

## 3. Stable trace identity

`economic_trace_id` identifies one economic production lineage, not one accounting event.

Conceptually:

```text
TRACE-H03-...
  opportunity
  product
  production job
  listing/distribution
  downstream conversion evidence
```

A Ledger event may reference one trace directly when known, but the canonical revenue split is governed by an attribution claim.

## 4. Attribution claim

One realized revenue Ledger event has at most one active canonical attribution claim/version for the same attribution policy context.

Claim fields include:

```text
claim_id
revenue_event_id
holding_id
currency
amount_minor
source_sale_or_order_id
source_channel
allocation_policy_id
allocations[]
unknown_bps
provenance_refs
lineage_nodes[]
lineage_edges[]
```

The claim amount/currency must match the underlying realized-revenue event in a future live implementation. ECON-003 does not duplicate that amount into another ledger.

## 5. Attribution basis hierarchy

Accepted attribution bases:

### `DIRECT_SOURCE_ID`

Strongest evidence. A source-native stable identifier directly links sale/order/payout to one trace, listing, campaign or product.

Examples:

- marketplace order references exact listing/product ID;
- affiliate payout references exact tracked order/campaign link;
- direct checkout references product SKU/order.

### `DETERMINISTIC_JOIN`

Stable fields deterministically join source records without subjective scoring.

Examples:

- unique campaign code -> landing page -> product -> order;
- immutable listing ID appears across listing and payout exports;
- exact transaction/order reference joins two systems.

### `POLICY_ALLOCATED`

Used only when multiple known traces legitimately share credit and a named allocation policy exists.

Examples:

- a documented multi-touch split;
- bundle revenue allocated across component products under an explicit policy;
- pooled campaign sale allocation when exact deterministic trace cannot be singularly assigned but a ratified rule exists.

`POLICY_ALLOCATED` requires `allocation_policy_id` plus evidence refs.

## 6. What is NOT accepted as accounting attribution

The following may be research signals but cannot directly claim realized revenue:

```text
"AI thinks this content probably caused it"
semantic similarity alone
visual similarity alone
same-day temporal proximity alone
model confidence score alone
unverified browser history guess
memory inference without source evidence
```

Model inference may generate an attribution **candidate for review**, but the accepted revenue claim remains `ATTRIBUTION_UNKNOWN` until direct/deterministic/policy evidence exists.

Machine contract therefore fixes:

```text
model_inference_can_claim_revenue=false
```

## 7. 10,000-basis-point invariant

Every revenue event's attribution claim must satisfy:

```text
sum(allocation_bps) + unknown_bps = 10,000
```

Examples:

### Fully direct

```text
TRACE-H03-001 = 10,000 bps
unknown        = 0
```

### Partial evidence

```text
TRACE-H02-A = 6,000 bps
unknown     = 4,000 bps
```

### No defensible evidence

```text
allocations = []
unknown_bps = 10,000
```

Unknown is a first-class result, not an error to hide.

## 8. No double counting

Attribution weights distribute analytical credit over one Ledger revenue event; they never create additional revenue events.

If one Rp100,000 revenue event is split 60/40:

```text
Ledger revenue = Rp100,000 once
Trace A attributed value = Rp60,000 derived projection
Trace B attributed value = Rp40,000 derived projection
```

Company revenue remains Rp100,000, not Rp200,000.

## 9. Duplicate trace rule

One claim may mention a given `economic_trace_id` only once. Multiple pieces of evidence belong inside that allocation's `evidence_refs`, not as duplicate allocations.

This keeps the 10,000-bps accounting surface unambiguous.

## 10. Lineage graph

Allowed node types:

```text
OPPORTUNITY
BLUEPRINT
PRODUCT_ASSET
PRODUCTION_JOB
LISTING_DISTRIBUTION
CLICK_SESSION
ORDER_SALE
REVENUE_EVENT
COMMISSION_PAYOUT
INCIDENT
```

Allowed relations:

```text
DERIVED_FROM
COMPILED_AS
PRODUCED_AS
DISTRIBUTED_AS
CLICKED_THROUGH
CONVERTED_TO
REALIZED_AS
COMMISSIONED_AS
AFFECTED_BY
```

Every edge requires evidence refs. An edge cannot point to a node absent from the claim's node set.

A future storage implementation may deduplicate canonical lineage nodes/edges globally; the v1 claim contract is intentionally self-contained for auditability.

## 11. H01 mapping

Factory/asset example:

```text
opportunity / seed expression
 -> blueprint
 -> semantic asset / production job
 -> marketplace package/listing
 -> marketplace sale/download event if exposed
 -> realized marketplace revenue/payout
```

If a marketplace payout is only available as an aggregate with no item-level evidence, the aggregate revenue remains real but item-level allocation can stay partly/fully UNKNOWN or use an explicit allocation policy later.

## 12. H02 mapping

Affiliate/media example:

```text
commerce opportunity
 -> content angle/script
 -> video/post
 -> tracked affiliate link/campaign
 -> click/session when available
 -> external order
 -> commission event/payout
```

H02 is expected to have harder multi-touch attribution. Missing source evidence must not be replaced by AI certainty.

## 13. H03 mapping

Knowledge/PDF example:

```text
human pain/problem opportunity
 -> product hypothesis
 -> knowledge/PDF/tool product
 -> product page/listing
 -> checkout/order
 -> realized sale
```

This is likely cleaner for early Economic Layer pilots because product/order lineage can often be deterministic.

## 14. Refund/chargeback attribution

Refunds/chargebacks are separate ECON-002 Ledger events.

A future attribution implementation should normally inherit/reconcile the original sale attribution where source evidence links the reversal to the original order. It must not create a new positive-revenue claim.

If the source reversal cannot be deterministically tied to an original trace, the refund remains an economic fact with UNKNOWN attribution.

## 15. Commission semantics

Affiliate commission can be represented as realized revenue only when the applicable policy says the commission is realized (for example payout/locked commission status rather than estimated dashboard earnings).

The attribution lineage may include both `ORDER_SALE` and `COMMISSION_PAYOUT`. The Ledger amount is the economic revenue recognized by policy, not necessarily the underlying merchant GMV.

## 16. Attribution version/correction principle

Like Ledger facts, attribution must remain auditable.

A future live implementation should not silently overwrite historical claims. Corrected claims should create a new version/supersession record referencing the prior claim and policy/evidence change.

ECON-003 locks the semantic rule; storage/version DDL is deferred to the future attribution implementation task rather than creating a second live database here.

## 17. Data completeness

Period-level attribution completeness can be derived as:

```text
AttributedBps = sum(10,000 - unknown_bps across revenue events)
TotalPossibleBps = revenue_event_count * 10,000
AttributionCoverage = AttributedBps / TotalPossibleBps
```

A more economically weighted coverage may also be reported:

```text
KnownAttributedRevenue / TotalRealizedRevenue
```

Both denominator and policy must be explicit.

## 18. Security/authority boundary

Attribution claims state:

```text
creates_revenue=false
spend_authorized=false
submission_authorized=false
model_inference_can_claim_revenue=false
credentials_embedded=false
```

The system never stores marketplace/browser credentials in lineage evidence.

## 19. Validation surface

Canonical schema:

```text
company/company-os/schemas/die.revenue-attribution.claim.v1.schema.json
```

Canonical validator/tests:

```text
company/company-os/lib/economic_contracts.py
company/company-os/tests/test_economic_contracts.py
```

Acceptance tests prove:

- direct full attribution;
- partial attribution preserves UNKNOWN residual;
- no evidence produces 100% UNKNOWN;
- allocations + UNKNOWN must equal exactly 10,000 bps;
- duplicate trace IDs are rejected;
- policy allocations require policy ID;
- model inference cannot claim realized revenue;
- lineage edges cannot reference unknown nodes.

## 20. ECON-003 acceptance

**PASS.** Revenue lineage from opportunity through product/production/distribution/conversion to realized revenue/commission is defined, attribution evidence classes are explicit, UNKNOWN is first-class, 10,000-bps conservation prevents over/under-allocation, and attribution cannot create/double-count revenue. No marketplace/payment integration, live tracking pixel, credential access, submission, spend or revenue mutation was performed.
