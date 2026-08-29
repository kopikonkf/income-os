# DIE Production Assurance, QC Automation, and Distribution Architecture v1

Date: 2026-08-29
Status: FOUNDATION / BUILD TARGET
Scope: Division-01 asset production lane, reusable later by other divisions

## 1. Why this layer exists

The current system has a deterministic M-001 Universal QA core and a manual-submission boundary, but QA, subjective QC, and marketplace submission are not yet first-class governed engines.

These concerns MUST stay separate:

- **QA** answers: "Is the artifact technically, structurally, legally/policy-wise, and package-wise conformant?"
- **QC** answers: "Is the artifact visually/commercially good enough to release?"
- **Submission** answers: "How is an already-approved package transferred to a specific external marketplace and reconciled safely?"

Hermes orchestrates these engines. Hermes does not become the QA rule author, QC judge, or submission authority.

## 2. Current implementation truth

### Existing QA core

`bridge/income_os_bridge/m001_asset_qa.py` is real executable code. It already verifies:

- artifact/file integrity;
- lineage and hashes;
- PNG/JPEG integrity and dimensions;
- allowed formats;
- exact duplicate binaries/asset IDs;
- rights review state;
- safety review state;
- watermark state;
- technical review state;
- visual-review presence;
- minimum megapixels and recovery route;
- batch pass-rate and hard-veto behavior.

It intentionally returns `REVIEW_REQUIRED` / `BLOCKED_REVIEW` when visual evidence is missing. Therefore the correct roadmap is to **promote/refactor this core into QA Engine v1**, not rewrite it from zero.

### Existing submission boundary

`bridge/income_os_bridge/m001_loop.py` currently produces a package that stops at `READY_FOR_MANUAL_SUBMISSION`. `bin/die_platform_receipt.py` ingests platform receipts after manual actions. This is correct V0 behavior but is not a Submission Engine.

### Existing QC

Founder/manual review currently fills the visual/aesthetic/commercial judgment gap. There is no calibrated automatic QC engine yet.

## 3. Target flow

```text
Worker / MUXIA Artifact
        |
        v
QA Engine
  universal + technical + rights + lineage + metadata/package
        |
        | PASS
        v
QC Engine
  visual + aesthetic + commercial usefulness + blueprint adherence
        |
        | PASS
        v
Submission Package
        |
        v
Platform-specific Submission Adapter
        |
        v
SUBMISSION receipt
        |
        v
Platform REVIEW receipt
        |
        +---- rejection reason ---> QA/QC/Blueprint/Signals learning
        |
        +---- approval -----------> asset-days / ERVA
```

## 4. QA Engine authority

QA is primarily deterministic and contract-driven.

### QA Engine owns

- file integrity and technical correctness;
- lineage/hash consistency;
- rights/safety/watermark hard gates from explicit evidence;
- exact/near-duplicate technical controls where deterministic;
- required metadata/package fields;
- blueprint/package consistency;
- universal QA profile;
- platform-specific preflight profile interface.

### QA Engine does not own

- subjective beauty/aesthetic judgment;
- commercial desirability;
- Worth-Making;
- Blueprint semantics;
- account/submission authority.

A QA failure may route to recreate/quarantine/review, never silently delete economic inventory.

## 5. QC Engine authority

QC handles quality judgment that cannot be safely reduced to file checks.

QC factors may include:

- visual defects/artifacts;
- composition quality;
- subject correctness;
- prompt/Blueprint adherence;
- semantic consistency across family/variations;
- commercial usefulness/readability;
- excessive similarity/repetition;
- obvious AI-generation defects;
- customer/use-case fitness;
- aesthetic coherence.

### Initial authority

Founder remains final QC authority while the automated QC engine runs in **SHADOW** mode.

### Future Founder-free QC

Yes, Founder manual QC can be removed from bounded lanes, but only after explicit delegation. Promotion path:

1. `SHADOW_ONLY` — engine scores/recommends; Founder labels ground truth.
2. `CALIBRATED_RECOMMENDER` — confidence/disagreement metrics are stable; Founder still final.
3. `BOUNDED_AUTO_QC` — explicitly approved low-risk asset classes may auto-PASS/route based on ratified thresholds.
4. `SAMPLED_AUDIT` — Founder reviews a sample and exception queue instead of every artifact.

Founder-free QC is **not** the same as Founder-free submission. Submission/publication/spend/account authority remains separately governed.

No QC model may self-promote from SHADOW to BOUNDED_AUTO_QC. Promotion requires a Founder-ratified delegation policy artifact.

## 6. QC calibration requirements

Before bounded auto-QC can replace manual Founder review, the engine must have a versioned labeled corpus and report at least:

- Founder/engine agreement rate;
- false-pass rate;
- false-fail rate;
- hard-defect miss count;
- confidence calibration;
- per-defect-class confusion/error counts;
- per-asset-class performance;
- drift/replay behavior across model versions.

Exact promotion thresholds are not hardcoded in this architecture. They are a versioned QC policy and require Founder ratification.

Hard rights/safety/watermark vetoes remain QA/policy hard gates and are never softened by a high QC score.

## 7. Submission Engine architecture

There are five M-001 marketplaces:

- Adobe Stock;
- Dreamstime;
- 123RF;
- Vecteezy;
- MotionElements.

Magnific is a production/recovery service and MUST NOT be modeled as a marketplace submission adapter.

### Common Submission Engine responsibilities

- immutable submission package manifest;
- asset/metadata/QA/QC/Blueprint lineage;
- per-platform route state machine;
- idempotency and duplicate-submission prevention;
- retry/reconciliation semantics;
- sanitized credential/session boundary;
- dry-run mode;
- irreversible-action authority check;
- platform submission ID capture;
- reconciliation with `die.platform.receipt.v1` or successor receipt;
- stop/review on unknown UI/policy/challenge states.

### Platform adapter responsibilities

Each marketplace adapter pins a dated platform/account contract and declares its allowed execution mode:

- `AUTOMATED_ALLOWED` — bounded automation is explicitly supported by current policy/account capability;
- `OPERATOR_REQUIRED` — engine prepares package and state, operator performs the required interaction, engine ingests resulting receipt;
- `OFFICIAL_API_ONLY` — only official documented API/export lane;
- `BLOCKED_POLICY_UNKNOWN` — fail closed.

An adapter can therefore be a fully automated executor **or** an operator-assisted state/receipt adapter. “Submission Engine” does not imply bypassing a platform that requires manual operation.

## 8. Submission authority

Current default:

```text
QA PASS
+ QC PASS
+ exact package hash
+ Founder submission authorization
= submission may proceed
```

Future delegated submission authority can be designed separately, but it must be an explicit bounded policy by marketplace/account/asset class/spend/volume. QC automation alone never grants submission authority.

## 9. Platform-specific QA

Universal QA is necessary but not sufficient. Each marketplace adapter references a dated platform QA profile for requirements such as:

- accepted media/format/dimensions;
- metadata length/content;
- AI disclosure/category requirements;
- similarity/distinctness constraints;
- account-specific eligibility;
- content restrictions;
- upload/package constraints.

Platform QA profile failure occurs before irreversible submission.

## 10. Market closed loop

`OE-007` is a governed **production canary**: intelligence -> Blueprint -> artifact -> QA/QC feedback. It does not prove external marketplace submission.

The first true market closed loop is `CL-001`:

```text
Opportunity Intelligence
-> production
-> QA
-> QC
-> selected marketplace adapter
-> submission receipt
-> review receipt
-> acceptance/rejection reason
-> learning feedback
-> ERVA/economics when actually available
```

A successful submission is not a successful review. An approved review is not revenue. License/payout receipts remain separate evidence classes.

## 11. Hermes integration

Hermes Operator v2 must treat these as typed prerequisites/receipts:

- QA receipt;
- QC receipt;
- QC delegation policy/version;
- platform QA profile;
- submission package hash;
- submission authorization/delegation receipt;
- submission receipt;
- platform review receipt.

Hermes may schedule/retry/follow-up/reconcile. It may not override QA hard vetoes, invent QC PASS, or self-authorize submission.

## 12. Build families

### QA-001 — Universal + platform-preflight QA Engine

Promote/refactor current `m001_asset_qa.py`, add package/metadata/platform profile interfaces, and seal deterministic regression.

### QC-001 — Automated QC Engine

Build rubric/schema, labeled corpus, evaluator, calibration, shadow mode, delegation policy, replay/audit.

### SUB-001 — Common Submission Engine

Build package/state/idempotency/authority/reconciliation framework.

### SUB marketplace adapters

- `SUB-ADOBE`
- `SUB-DREAMSTIME`
- `SUB-123RF`
- `SUB-VECTEEZY`
- `SUB-MOTIONELEMENTS`

Each has a dated contract capture, dry-run adapter, bounded activation proof, and adapter acceptance milestone.

### CL-001 — Full market closed-loop canary

One selected DONE adapter executes a governed real submission when separately authorized; submission/review/learning receipts complete the market loop.

## 13. Dependency relationship with OE

```text
OE-001 -> OE-002 -> OE-003 -> OE-004 -> OE-005
                                           |
                    +----------------------+
                    |                      |
                    v                      v
                 QA-001                 OE-006
                    |
                    v
                 QC-001
                    |                      |
                    +----------+-----------+
                               v
                            OE-007
                     governed production canary
                               |
                               v
                            SUB-001
                 +------+------+------+------+
                 |      |      |      |      |
              Adobe  Dream   123RF  Vecteezy Motion
                 \      |      |      |      /
                  +-----+------+------+-...-+
                               |
                               v
                            CL-001
                    full market closed loop
```

SUB framework/adapters may be implemented with fixtures before OE-007, but a live CL-001 action requires QA/QC, exact lineage, a DONE/eligible selected adapter, and explicit submission authority.