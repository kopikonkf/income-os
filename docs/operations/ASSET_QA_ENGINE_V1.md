# DIE Asset QA Engine v1 — Promotion Contract

Date: 2026-08-30
Tasks: QA-001A, QA-001B
Status: EXECUTION CANON

## 1. Purpose

Promote the existing M-001 deterministic raster QA implementation into the first-class DIE Asset QA boundary without discarding proven behavior. QA is a technical/compliance/preflight gate. It is not subjective visual/commercial QC and it never grants submission or publication authority.

## 2. Existing executable core audit

Canonical legacy-compatible core: `bridge/income_os_bridge/m001_asset_qa.py`.

Preserve these behaviors exactly through the promotion:

| Capability | Existing behavior | v1 classification |
| --- | --- | --- |
| workspace containment | manifest, assets, evidence and receipts must remain inside assigned workspace | HARD boundary |
| artifact integrity | SHA-256 is recomputed and compared to declared source hash | HARD veto on mismatch/missing artifact |
| raster integrity | PNG structure/CRC/IEND and JPEG framing/dimensions are parsed deterministically | technical failure |
| lineage | asset/blueprint/candidate/master/prompt fields are required and cross-checked | HARD veto when required lineage is absent or contradictory |
| format/dimension | allowed format and minimum megapixels are enforced | technical failure/recovery route |
| rights | structured evidence must exist and be CLEAR/PASS | HARD veto |
| safety | structured evidence must exist and be CLEAR/PASS | HARD veto |
| watermark | structured evidence must exist and be CLEAR/PASS | HARD veto for submission eligibility |
| exact duplicate | repeated asset IDs and binary SHA-256 values are detected | deterministic duplicate defect |
| visual evidence | missing visual review emits `REVIEW_REQUIRED` / `BLOCKED_REVIEW` | REVIEW_REQUIRED, never synthetic PASS |
| batch pass-rate | deterministic pass count/rate and bounded batch size | compatibility behavior |
| authority | receipt declares submission/publication false and hard vetoes non-waivable | mandatory boundary |

## 3. Promotion boundary

The reusable Asset QA v1 component SHALL expose universal checks independently of the M-001 CLI/manifest shape. The existing `m001_asset_qa.py` remains a compatibility adapter until parity is proven by QA-001F.

The promoted boundary must preserve deterministic checks while adding:

1. `die.asset.qa.v1` typed receipt semantics.
2. Stable defect and route taxonomy.
3. Versioned/dates platform QA profiles.
4. Metadata and submission-package preflight.
5. Regression proof against the existing M-001 behavior.

No migration step may silently reinterpret a legacy technical/rights/safety result as an aesthetic or commercial judgment.

## 4. Known gaps from the current core

The current M-001 implementation does **not** yet provide:

- a general-purpose receipt schema independent of M-001;
- canonical defect codes/severity separate from free-text reasons;
- dated per-marketplace requirement profiles;
- metadata/package validation against platform profiles;
- an interface for explicit UNKNOWN platform requirements that fails closed;
- a first-class platform-preflight receipt.

Those gaps are owned by QA-001B..F.

## 5. Defect and route semantics

Canonical taxonomy: `company/contracts/die.asset.qa-taxonomy.v1.json`.

Severity semantics:

- `HARD_VETO`: cannot become submission-eligible in the same QA receipt. A later corrected artifact/package must be re-evaluated and receive a new receipt.
- `FAIL`: deterministic defect requiring correction/recovery/re-routing.
- `REVIEW_REQUIRED`: evidence is insufficient for a deterministic QA conclusion; it is never treated as PASS.

`PASS` means only the declared QA scope passed. It does not mean aesthetically strong, commercially attractive, accepted by a marketplace, or authorized for submission.

## 6. Authority separation

Asset QA MUST NOT:

- author or mutate creative semantics;
- produce subjective aesthetic/commercial PASS when visual evidence is unavailable;
- waive rights, safety, watermark, integrity or lineage hard vetoes;
- grant Founder, QC, marketplace submission, publication, spend, credential, or account authority;
- execute a marketplace submission.

The receipt authority boundary is fail-closed: `submission_authorized=false`, `publication_authorized=false`, and `hard_vetoes_waivable=false`.

## 7. QA-001A acceptance

PASS when this audit maps the existing executable behavior, explicitly preserves reusable checks, records the gaps, and keeps QC/submission authority outside QA.

## 8. QA-001B acceptance

PASS when `company/schemas/die.asset.qa.v1.schema.json` and `company/contracts/die.asset.qa-taxonomy.v1.json` provide typed coverage for integrity, lineage, technical, rights, safety, watermark, duplicate, metadata/package and review-required states, including hard-veto semantics and the authority boundary.
