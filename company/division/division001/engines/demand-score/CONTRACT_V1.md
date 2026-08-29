# Division01 Demand Score v1 Contract

Status: CANONICAL CONTRACT
Batch: OE-B03
Milestone: OE-002 — ACCEPTED ENGINE v1

## Contract layers

- `DEMAND_SCORE_MODEL_V1.contract.json` ? component registry, model ID/version and evidence-kind boundaries.
- `die.division001.demand-score.v1.schema.json` ? strict score-output schema.
- `EVIDENCE_NORMALIZATION_V1.md` ? component-to-evidence mapping and no-hidden-priors rule.
- `UNKNOWN_FRESHNESS_POLICY_V1.md` ? missing/stale/rejected evidence semantics.
- `validate_demand_score.py` ? cross-field semantic validator.

## Required components for COMPLETE

- `external_demand`
- `supply_competition`
- `commercial_intent`

All three must be `KNOWN` from accepted evidence. A numeric final score is not emitted for `PARTIAL`, `INSUFFICIENT_EVIDENCE`, or `HARD_VETO`.

## Non-required contextual components

- trend/seasonality
- platform fit
- niche specificity
- production feasibility
- eligibility
- risk penalty

Their absence does not become zero. They remain explicit UNKNOWN/NOT_APPLICABLE/stale/rejected states and their evidence coverage remains visible.

## Hard-veto separation

A strong market score can never erase rights, safety, deception, forbidden-platform, or equivalent hard vetoes. Those remain separately receipted and can force `HARD_VETO` with `final_score=null`.

## v0 relation

The historical Object Engine `demand_score.py` is calibration/provenance only. Its static defaults/dictionaries are not production-v1 evidence.

## Implementation acceptance

OE-B04 completed the deterministic scorer, versioned transforms/weights, pinned calibration corpus, ranking/deferred policy, arithmetic validation and deterministic replay. See `CALIBRATION_V1.md`, `score_demand.py`, `rank_demand.py`, and the OE-002 milestone receipt.

Demand Score remains an evidence-ranking engine only; Worth-Making, Executive review, Founder authority, QA/QC and submission remain downstream gates.
