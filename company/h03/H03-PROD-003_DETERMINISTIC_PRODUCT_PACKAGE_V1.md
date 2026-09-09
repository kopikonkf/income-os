# H03-PROD-003 — Deterministic Useful-Product Compile, QA + Local Package v1

Status: DONE / PASS
Date: 2026-09-09

## Purpose

Structured semantic content blocks are revalidated against the accepted Knowledge Package and Product Blueprint, assembled into the existing Document AST, rendered through the selected template, reopened and raster-QA checked, hashed, manifested and packaged locally.

The compiler owns mechanics:

```text
content-block batches
  -> claim/evidence revalidation
  -> deterministic Document AST
  -> template renderer
  -> PDF reopen + metadata QA
  -> PDFium raster/nonblank/edge QA
  -> manifest
  -> deterministic ZIP
  -> local package receipt
```

Producer workers do not own pagination, filename derivation, PDF metadata mechanics, hashing, manifests, raster QA or ZIP creation.

## Coverage and provenance gates

Every Blueprint claim assigned to a section must be covered by at least one content block. Content-block evidence refs must exactly match the accepted Knowledge Package claim evidence; invented or stripped provenance fails closed.

Semantic block normalization into AST v1 preserves current renderer compatibility:

- paragraph -> `paragraph`
- step -> numbered `bullet`
- bullet -> `bullet`
- checklist item -> `[ ]` bullet
- callout -> `Note:` paragraph
- input prompt -> local input-line paragraph

Richer renderer widgets can evolve later without changing the semantic content contract.

## Local package status

The package status is `LOCAL_SALE_READY_UNREVIEWED` and `external_publication=false`. External listing remains Founder-gated and subsequent reviewer/commercial tasks remain authoritative.

## Concrete internal acceptance

Acceptance uses canonical H03 MVP internal knowledge and an explicitly labeled `ACCEPTANCE_FIXTURE_NOT_LIVE_PROVIDER`; it does not pretend a live provider produced the semantic text.

- PDF pages: 2
- PDF SHA256: `8199048f4a9ee0f70a4e0b62c07c7617ab61b9077cf6700311192617c7eb20ee`
- deterministic ZIP SHA256: `c4366856e1aa0b41705a178e9f13dead2e8eac76df9b92af2a391b3b3af32e06`
- external publication: false

Artifacts:

- `company/h03/contracts/local-product-package.v1.schema.json`
- `company/h03/lib/product_packager.py`
- `company/h03/tests/test_product_packager.py`
- `company/h03/evidence/H03-PROD-003-ACCEPTANCE/`
