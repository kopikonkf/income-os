# Asset QC Foundation v1

Date: 2026-08-30
Scope: `QC-001A -> QC-001B -> QC-001C`
Mode: `SHADOW_ONLY`

## Purpose

This batch creates the first-class Asset QC boundary after accepted Asset QA. QC is intentionally distinct from QA, release authority, and marketplace submission.

`QA PASS` is a prerequisite for QC. A QA hard veto, non-PASS batch, non-PASS asset route, or asset-hash lineage mismatch blocks QC from recommending release. QC never waives QA defects.

## QC-001A — rubric, result, and authority contract

Canonical artifacts:

- `company/contracts/die.asset.qc-rubric.v1.json`
- `company/schemas/die.asset.qc-observation.v1.schema.json`
- `company/schemas/die.asset.qc.v1.schema.json`

The rubric covers Blueprint adherence, aesthetic coherence, commercial usefulness, visible AI artifact quality, use-case fitness, similarity/distinctness, and readability/composition. Scores are normalized to 0–100, confidence to 0–1, and recommendations are limited to:

- `PASS_RECOMMENDED`
- `REVIEW_RECOMMENDED`
- `FAIL_RECOMMENDED`
- `BLOCKED_BY_QA`

All outputs remain `SHADOW_ONLY`. A recommendation is not Founder approval, release authority, submission authority, publication authority, or delegation policy.

Recommendation thresholds in the rubric classify SHADOW output only. They are not the later QC-001F thresholds for promoting a scope to `BOUNDED_AUTO_QC` or `SAMPLED_AUDIT`; those remain unratified until explicit Founder approval.

## QC-001B — Founder/manual ground-truth corpus contracts

Canonical artifacts:

- `company/schemas/die.asset.qc-label.v1.schema.json`
- `company/schemas/die.asset.qc-corpus.v1.schema.json`
- `company/contracts/die.asset.qc-sampling.v1.json`

A label captures asset class, immutable asset/Blueprint/QA receipt hashes, PASS/FAIL/REVIEW decision, defect classes, evidence references, and a bounded `rationale_summary`. Private chain-of-thought or hidden reasoning is neither requested nor required.

The sampling contract uses reproducible SHA-256 ordering within declared strata. It exists to make later calibration reproducible and to reduce cherry-picking. Sampling grants no release or submission authority.

## QC-001C — bounded deterministic evaluator

Runtime:

- `bridge/income_os_bridge/asset_qc.py`
- `bin/die_asset_qc.py`

The evaluator consumes:

1. one first-class `die.asset.qa.v1` receipt;
2. one `die.asset.qc-observation.v1` observation;
3. the versioned QC rubric.

It validates exact asset hash lineage, exact rubric factor coverage, bounded score/confidence values, allowed defect classes, and evidence references. It emits a deterministic receipt identity, normalized score, confidence, defect classes, recommendation, and evidence refs. It does not mutate the artifact.

Critical visual defect classes force `FAIL_RECOMMENDED`. High score with low confidence remains `REVIEW_RECOMMENDED`. Any QA hard veto/non-PASS route forces `BLOCKED_BY_QA` regardless of QC score.

## CLI

```text
python bin/die_asset_qc.py \
  --qa-receipt <qa.json> \
  --observation <observation.json> \
  --output <qc.json>
```

Exit code 0 means only `PASS_RECOMMENDED` in SHADOW mode. Exit code 3 means review/fail/QA-blocked recommendation. Contract/input errors fail closed with exit code 2.

## Explicit non-goals

This batch does not:

- remove Founder manual QC;
- define or ratify bounded auto-QC promotion thresholds;
- run a production model/provider;
- grant release/submission/publication authority;
- submit to a marketplace;
- override QA hard vetoes;
- create calibration metrics or drift policy (QC-001D+).
