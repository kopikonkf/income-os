# Division01 Demand Score UNKNOWN and Freshness Policy v1

Status: CANONICAL CONTRACT
Task: OE-002C
Owner: Division-01 Digital Asset Intelligence

## 1. Core invariant

`NO EVIDENCE != ZERO DEMAND`.

Absence, expiry, policy rejection, or unsupported evidence is represented explicitly. The scorer may return no final numeric score when evidence coverage is insufficient.

## 2. Component states

- `KNOWN` ? sufficient fresh accepted evidence exists for this component.
- `UNKNOWN` ? no accepted evidence exists.
- `STALE` ? evidence exists historically but all usable evidence is expired at `evaluated_at`.
- `REJECTED` ? candidate evidence exists but fails schema/policy/provenance/normalization rules.
- `NOT_APPLICABLE` ? model contract explicitly says the component does not apply to this candidate/scope.

`UNKNOWN`, `STALE`, and `REJECTED` MUST have `normalized_score=null`. `NOT_APPLICABLE` also has `normalized_score=null` and is not treated as zero.

## 3. Score status

- `COMPLETE` ? every model component marked `required_for_complete=true` is `KNOWN`; a numeric final score may be emitted by OE-002D.
- `PARTIAL` ? at least one component is KNOWN but one or more required components are UNKNOWN/STALE/REJECTED; `final_score` MUST be null in v1.
- `INSUFFICIENT_EVIDENCE` ? no required component is KNOWN or no trustworthy evidence basis exists; `final_score` MUST be null.
- `HARD_VETO` ? a separate hard-veto artifact blocks scoring/promotion; numeric final score MUST be null even if market evidence is strong.

This conservative v1 rule intentionally refuses partial weighted arithmetic. A future model version may introduce an explicitly ratified missingness strategy, but it must not silently change v1 semantics.

## 4. Freshness

For Opportunity Signals, freshness is inherited from OE-001 receipt/registry semantics. At evaluation time:

- `evaluated_at < expires_at` -> potentially FRESH;
- `evaluated_at >= expires_at` -> STALE.

A stale receipt remains historical provenance but cannot support a `KNOWN` current component. Refreshing evidence creates a new observation; memory or a previous score does not refresh it.

For deterministic/canon evidence, the evidence artifact must state an effective/expiry or version-validity rule. If validity cannot be established, treat it as UNKNOWN or REJECTED rather than timeless.

## 5. Confidence and coverage

Demand Score output separately records:

- `evidence_coverage_ratio` ? fraction of model components in KNOWN state, excluding NOT_APPLICABLE from denominator;
- `required_coverage_ratio` ? fraction of required components KNOWN;
- `confidence` ? `HIGH|MEDIUM|LOW|NONE`, derived by OE-002D from explicit evidence quality/coverage rules.

Coverage is not a substitute score. A candidate can have high coverage and low eventual demand, or sparse coverage and therefore no numeric score.

## 6. Ranking boundary

Only `COMPLETE` outputs with numeric `final_score` may enter the normal demand ranking. `PARTIAL`, `INSUFFICIENT_EVIDENCE`, and `HARD_VETO` outputs are routed to evidence collection/research, not assigned an artificial bottom score.
