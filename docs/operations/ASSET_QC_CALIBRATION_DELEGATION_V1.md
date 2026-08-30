# Asset QC Calibration + Delegation Readiness v1

Date: 2026-08-30
Scope: `QC-001D -> QC-001E -> QC-001F -> QC-001G -> QC-001`
Default mode: `SHADOW_ONLY`

## Boundary

This layer measures and governs QC capability after `QA-001` and the QC-B01 SHADOW evaluator. It does not activate Founder-free QC by itself and never grants marketplace submission/publication authority.

`QC-001 DONE` means the engine is calibration-capable, SHADOW-capable, replay/drift-audited, and ready to consume a separately Founder-ratified bounded delegation policy. It does **not** mean such a policy exists.

## QC-001D ? calibration

`bridge/income_os_bridge/asset_qc_assurance.py` builds `die.asset.qc-calibration.v1` reports from pinned Founder/manual labels and SHADOW QC receipts. One report contains one reviewer ID/version and one pinned corpus hash.

Metrics are reproducible and include:

- exact Founder/engine agreement rate;
- false-pass rate (`engine PASS`, Founder `FAIL`);
- false-fail rate (`engine FAIL`, Founder `PASS`);
- hard-defect miss count based on critical rubric classes;
- mean confidence;
- confidence calibration by deterministic bands and aggregate gap;
- per-defect-class counts/misses;
- per-asset-class agreement/error metrics.

Mixed evaluator/model versions in one report fail closed. Model-version comparisons are performed by replaying the same pinned corpus into separate reports.

## QC-001E ? SHADOW dual review

Each Founder/manual label can be paired with the engine receipt to produce `die.asset.qc-shadow-case.v1`. Cases are retained in `die.asset.qc-disagreement-queue.v1` when any of these occur:

- Founder/engine disagreement;
- low confidence;
- engine `REVIEW_RECOMMENDED`;
- QA-blocked recommendation.

Founder remains final in SHADOW. Queue state grants no release or submission authority and records only bounded labels/rationale/evidence hashes, not private reasoning.

## QC-001F ? delegation policy

`die.asset.qc-delegation-policy.v1` defines exactly four modes:

1. `SHADOW_ONLY`
2. `CALIBRATED_RECOMMENDER`
3. `BOUNDED_AUTO_QC`
4. `SAMPLED_AUDIT`

The canonical default policy is `company/contracts/qc/die.asset.qc-delegation-policy.shadow.v1.json` and is unratified `SHADOW_ONLY`.

Every non-SHADOW policy must carry:

- `status = FOUNDER_RATIFIED`;
- `ratified_by = Founder`;
- ratification timestamp;
- hash of the exact policy body;
- explicit asset-class, marketplace, reviewer ID/version scope;
- validity window;
- explicit calibration thresholds.

A missing/forged hash, missing scope, expired window, out-of-scope asset/marketplace/model, or failed metric threshold fails closed. `CALIBRATED_RECOMMENDER` always retains Founder final authority. Only a separately ratified `BOUNDED_AUTO_QC`/`SAMPLED_AUDIT` scope may make `qc_release_authorized=true`; `submission_authorized` remains false in all QC modes.

No real production auto-QC policy is ratified by this implementation or by its tests. Synthetic ratified policies exist only in regression fixtures.

## QC-001G ? replay/drift/audit

`die.asset.qc-audit.v1` compares reports from the same corpus/rubric across evaluator versions. The canonical audit guardrail blocks:

- corpus or rubric mismatch;
- any false-pass-rate regression;
- any increase in hard-defect misses.

Material agreement/confidence-calibration drift is retained as `REVIEW_REQUIRED`. Audit output cannot self-promote a policy or grant release/submission authority.

## CLI

```text
python bin/die_asset_qc_assurance.py shadow ...
python bin/die_asset_qc_assurance.py calibrate ...
python bin/die_asset_qc_assurance.py audit ...
python bin/die_asset_qc_assurance.py delegation ...
```

The CLI serializes deterministic assurance artifacts. It performs no provider call, artifact mutation, marketplace submission, policy ratification, or Founder-authority removal.

## Production activation prerequisites after QC-001 acceptance

Actual Founder-free QC still requires all of the following outside this acceptance batch:

1. a real versioned Founder-labeled corpus;
2. SHADOW runs on that corpus/production class;
3. calibration metrics reviewed by Founder;
4. explicit bounded thresholds/scope/expiry;
5. exact Founder-ratified delegation-policy hash;
6. continuing drift/audit compliance.

Until those exist, canonical runtime mode remains `SHADOW_ONLY`.
