# DIE Production Assurance + Distribution Atomic Task Graph v1

Date: 2026-08-29
Status: EXECUTION CANON
Graph: `company/muxia-task-graph-v1.json`
Architecture: `docs/architecture/DIE_PRODUCTION_ASSURANCE_DISTRIBUTION_ARCHITECTURE_V1.md`

## 1. Purpose

This document materializes QA, QC automation, submission, and full market-loop work into atomic execution gates. It complements the OE roadmap rather than replacing it.

The key separation is:

`QA != QC != Submission != Market Review`

A pipeline may be technically correct yet visually weak, visually strong yet unauthorized for submission, or successfully submitted yet rejected by a marketplace.

## 2. Current implementation truth

- Universal QA executable core exists in `bridge/income_os_bridge/m001_asset_qa.py` and will be promoted/refactored under QA-001.
- QC remains Founder/manual today for visual/aesthetic/commercial judgment.
- M-001 submission remains manual today and stops at `READY_FOR_MANUAL_SUBMISSION`.
- Platform outcome receipt ingestion exists, but no common Submission Engine or per-marketplace submission adapters exist yet.

## 3. Batch execution map

### QA-B01 — QA promotion contracts

- QA-001A audit/promote existing universal QA core
- QA-001B universal QA receipt + defect taxonomy

### QA-B02 — QA engine completion

- QA-001C canonical reusable QA component
- QA-001D platform-specific QA profile interface
- QA-001E metadata/submission-package QA
- QA-001F regression/compatibility/failure suite
- QA-001 acceptance

### QC-B01 — automated QC foundation

- QC-001A rubric/outcome/authority contract
- QC-001B Founder-labeled reference corpus
- QC-001C automated QC evaluator

### QC-B02 — calibration and delegation readiness

- QC-001D calibration/confidence metrics
- QC-001E Founder SHADOW workflow
- QC-001F bounded auto-QC delegation policy
- QC-001G replay/drift/override/audit suite
- QC-001 acceptance

`QC-001 DONE` means the engine is delegation-ready, not that Founder review has automatically been removed. Removing mandatory Founder review requires an explicit Founder-ratified policy scope.

### SUB-B01 — common submission framework

- SUB-001A package/route-state schema
- SUB-001B authority/credential/session boundary
- SUB-001C idempotency/retry/reconciliation
- SUB-001D dry-run composer
- SUB-001E adapter contract/execution modes
- SUB-001F common regression
- SUB-001 acceptance

### SUB-B02 — Adobe Stock adapter

- SUB-ADOBEA dated contract/account profile
- SUB-ADOBEB dry-run adapter
- SUB-ADOBEC bounded activation/reconciliation proof
- SUB-ADOBE acceptance

### SUB-B03 — Dreamstime adapter

- SUB-DREAMSTIMEA/B/C
- SUB-DREAMSTIME acceptance

### SUB-B04 — 123RF adapter

- SUB-123RFA/B/C
- SUB-123RF acceptance

### SUB-B05 — Vecteezy adapter

- SUB-VECTEEZYA/B/C
- SUB-VECTEEZY acceptance

### SUB-B06 — MotionElements adapter

- SUB-MOTIONELEMENTSA/B/C
- SUB-MOTIONELEMENTS acceptance

Magnific is excluded from submission adapters because it is a production/recovery service, not a licensing marketplace.

### CL-B01 — full market closed-loop canary

- CL-001A select one eligible DONE marketplace adapter
- CL-001B pin QA/QC/platform-QA approved exact package
- CL-001C Founder/delegated submission authority
- CL-001D execute/operator-handoff one bounded submission
- CL-001E ingest marketplace review outcome
- CL-001F route feedback/economics
- CL-001 acceptance

## 4. Dependency model

```text
OE-005
  |
  +----> QA-001 ----> QC-001 ----> SUB-001 ----> marketplace adapters
  |          |            |
  |          +------------+-------> OE-007 QA/QC gate
  |
  +----> OE-006 -------------------> OE-007
                                      |
                                      v
                                    CL-001
```

`OE-007` is now explicitly a production canary that ends at first-class QA/QC feedback. It does not claim external market submission.

`CL-001` is the full market closed-loop proof.

## 5. Founder-free QC path

Founder manual review can eventually become exception/sampling only, but the graph intentionally separates engine capability from authority delegation.

Required sequence:

1. Founder-labeled corpus exists.
2. Automated evaluator runs in SHADOW.
3. Calibration metrics are reproducible.
4. False-pass/hard-defect-miss behavior is acceptable under a versioned policy.
5. Founder explicitly ratifies the bounded scope.
6. Only that scope may use BOUNDED_AUTO_QC or SAMPLED_AUDIT.

A later Founder decision may cover asset classes, marketplaces, model versions, confidence thresholds, and expiry. Silence means SHADOW/manual QC continues.

## 6. Submission execution modes

Each marketplace adapter must resolve to exactly one current mode:

- `AUTOMATED_ALLOWED`
- `OPERATOR_REQUIRED`
- `OFFICIAL_API_ONLY`
- `BLOCKED_POLICY_UNKNOWN`

An OPERATOR_REQUIRED adapter is still a valid Submission Engine adapter: it prepares/locks package state, presents the bounded action, and ingests/reconciles the resulting platform receipt. It does not need to bypass the operator requirement to be useful.

## 7. Current standing point

`OE-006 = DONE`. Parallel production-readiness is active:

- MUXIA reliability: `MX-060 = DONE`, `MX-061 = DONE`, `MX-062 = READY`;
- production assurance: `QA-001 = DONE` and `QC-001 = DONE`; the QC engine is calibrated/shadow-capable and delegation-ready while canonical delegation remains `SHADOW_ONLY` / unratified;
- `SUB-001A = READY`; marketplace submission, market-loop and `OE-007` remain separately authority/dependency-gated.

This standing point authorizes only the declared bounded build/verification work. It does not authorize a production provider invocation, marketplace submission, spend, or removal of Founder QC authority.
