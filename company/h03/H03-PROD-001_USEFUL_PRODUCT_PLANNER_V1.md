# H03-PROD-001 — Useful Product Planner + Format Selection Engine v1

Status: DONE / PASS
Date: 2026-09-09

## Purpose

H03 product form is selected from the buyer's desired outcome and knowledge structure, not from arbitrary page-count targets and not from an ebook-first bias.

The planner separates three layers:

```text
problem / job-to-be-done
        -> useful product form
        -> Product Blueprint
        -> deterministic document representation / renderer
```

The product form is semantic UX/usage structure. PDF/HTML/EPUB/DOCX are later delivery representations.

## Deterministic form policy

```text
EXECUTE_SEQUENCE             -> guide
QUICK_VERIFY                 -> checklist
ONE_TIME_INPUT_WORKFLOW      -> worksheet
REPEATED_INPUT_WORKFLOW      -> workbook
COMPLEX_OPERATION            -> playbook
LOOKUP_REFERENCE             -> reference_sheet
EVIDENCE_DECISION + high depth/density -> report
EVIDENCE_DECISION + bounded depth       -> research_brief
REUSABLE_OUTPUT              -> template
BROAD_LEARNING               -> handbook
NARRATIVE_LEARNING           -> ebook
```

`ebook` has no fallback role. It requires an explicit narrative-learning delivery shape.

## Renderer compatibility

Existing PDF template registry is reused:

```text
guide / ebook / handbook / playbook -> guide.clean.v1
report / research_brief / reference_sheet -> report.compact.v1
checklist / worksheet / workbook / template -> worksheet.spacious.v1
```

Product form is chosen before rendering template. Template selection must support the selected form.

## Knowledge boundary

The planner accepts only canonical `die.h03.knowledge-package.v1` input. A `knowledge-package-candidate.v1` with `canonical_truth=false` cannot bypass Knowledge validation and become a Product Blueprint.

Section claim IDs must exist in the accepted Knowledge Package. Unknown claims fail closed.

## Page-count policy

The generated Product Blueprint records:

```text
format_selection_policy = OUTCOME_ORIENTED_V1
page_count_target = null
```

Page count is therefore an output of content/layout, not the product-selection objective.

## Artifacts

- `company/h03/contracts/product-planning-profile.v1.schema.json`
- `company/h03/lib/product_planner.py`
- `company/h03/tests/test_product_planner.py`
