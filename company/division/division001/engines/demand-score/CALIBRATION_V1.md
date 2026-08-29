# Division01 Demand Score v1 Calibration

Status: OE-002E / OE-002F acceptance evidence
Model: `division001-demand-score-v1` `1.0.0`

## 1. Formula

For KNOWN non-risk components:

```text
base = sum(weight_i * component_i) / sum(weight_i for KNOWN components)
final = clamp(base - 0.15 * risk_penalty_if_known, 0, 1)
```

Missing optional evidence is excluded from both numerator and denominator. It is not imputed as zero. Numeric scoring is allowed only when `external_demand`, `supply_competition`, and `commercial_intent` are KNOWN and hard-veto status is CLEAR.

## 2. Weights

| Component | Weight | Meaning |
|---|---:|---|
| external_demand | 0.30 | fresh observed demand proxies |
| supply_competition | 0.20 | competition-adjusted attractiveness |
| commercial_intent | 0.20 | observable buyer/license intent |
| trend_seasonality | 0.08 | trend/season timing |
| platform_fit | 0.07 | observable/contract platform fit |
| niche_specificity | 0.05 | deterministic structural specificity |
| production_feasibility | 0.05 | reproducible production feasibility |
| eligibility | 0.05 | policy/account eligibility evidence |
| risk_penalty | 0.15 deduction multiplier | explicit soft risk only; hard veto remains separate |

Required market evidence therefore represents 0.70 of the non-risk base weight.

## 3. Versioned transforms

- index 0..100 -> `/100`
- boolean presence -> `1/0`
- autocomplete rank 1..10 -> bounded reciprocal-linear score
- demand count -> bounded log transform with 10k reference
- competition count -> inverse bounded log transform with 100k reference
- competition ratios -> `1-ratio`
- signed delta -100..100 -> `(delta+100)/200`
- deterministic/canon normalized evidence -> identity 0..1

The 10k/100k references are engineering calibration parameters, not marketplace facts. Any material change requires a model-version bump and replay against the pinned corpus. Unsupported signal semantics are REJECTED rather than guessed.

## 4. Calibration corpus

| Fixture | Status | Score | Purpose |
|---|---|---:|---|
| high | COMPLETE | 0.821907 | strong evidence profile |
| medium | COMPLETE | 0.613474 | middle evidence profile |
| low | COMPLETE | 0.109096 | weak/high-competition profile |
| saturation-low-supply | COMPLETE | 0.716357 | lower competition |
| saturation-high-supply | COMPLETE | 0.617330 | same thesis with higher supply |
| required-only | COMPLETE/LOW confidence | 0.672728 | optional UNKNOWN renormalization |
| explicit-optional-zero | COMPLETE/HIGH confidence | 0.470909 | proves explicit zero differs from UNKNOWN |
| missing | PARTIAL | null | missing required evidence |
| stale | PARTIAL | null | stale required evidence |
| insufficient | INSUFFICIENT_EVIDENCE | null | no evidence |
| veto-unknown | PARTIAL | null | required complete but veto clearance unknown |
| hard-veto | HARD_VETO | null | hard veto dominates strong market evidence |

These labels are calibration expectations, not universal production thresholds.

## 5. Legacy v0 comparison

Legacy `object-asset-engine/.../demand_score.py` assigns numeric defaults such as search=0.30 and marketplace=0.30 when signals are missing. OE-002 v1 deliberately refuses that behavior: no required evidence means no numeric final score. Legacy v0 remains calibration provenance only.

## 6. Ranking policy

`rank_demand.py` ranks only COMPLETE numeric score outputs. PARTIAL, INSUFFICIENT_EVIDENCE, and HARD_VETO are deferred without artificial bottom scores. Exact duplicate score payloads collapse idempotently; conflicting identical score IDs fail closed.

## 7. Authority

Demand Score ranks evidence-conditioned opportunity. It is not Worth-Making, Blueprint approval, Executive review, Founder production authorization, QA, QC, or submission authority.

## 8. Pinned fixtures

The 12 input evidence cases are stored under `fixtures/calibration/`; compact expected outcomes are pinned in `fixtures/calibration-expected.json`, and deterministic ranking output is pinned in `fixtures/calibration-ranking.json`. Full scorer outputs are intentionally not duplicated in canon.
