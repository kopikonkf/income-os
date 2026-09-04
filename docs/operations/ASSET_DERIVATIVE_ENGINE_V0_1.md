# Asset Derivative Engine v0.1 — Acceptance and Rollback

Task: `FA-030`
Status: PASS
Date: 2026-09-04

## Accepted surface

Asset Derivative Engine v0.1 consists of the deterministic contracts and workers completed by FA-020 through FA-029:

- derivative recipe + receipt schemas;
- deterministic PNG master -> JPEG/WebP/TIFF raster worker;
- deterministic PDF + preview packaging;
- explicit sRGB/ICC, alpha, DPI and metadata policy;
- derivative QA / compatibility inspector;
- vectorizability gate;
- native SVG normalization + editable EPS export;
- gated OpenCV raster-trace fallback;
- marketplace dry-run package composer;
- five-current-master production canary.

## Immutable-master rule

The engine never edits or overwrites a master. Every worker rejects an output path equal to the source master. FA-029 used read-only copies of five current Linux production masters in an isolated Windows canary workspace; Linux production bytes were not changed.

## Semantic identity rule

JPEG/WebP/TIFF/PDF/SVG/EPS and previews are packaging or representation derivatives only. They retain `semantic_identity_effect = NONE`; physical file count and package-manifest count never increase semantic asset count.

## Validation sealed by this acceptance

- FA-001 Linux inventory: five current masters; observed path/MIME/magic/dimensions/bytes/SHA-256 match production manifests 5/5.
- FA-029 actual canary: 5 master copies hash-match inventory 5/5.
- Actual derivative outputs: 20/20 generated and QA PASS.
- Actual rerun idempotency: 20/20 second-pass hashes equal first pass.
- Actual dry-run packages: 5/5 PASS.
- Actual duplicate suppression probe: two manifest entries with identical bytes map to one physical package file.
- Actual vector-gate outcomes: 5/5 fail closed as `NOT_VECTORIZABLE` because trace is not authorized for those current raster masters.
- Targeted derivative regression: 39/39 PASS.
- Full Factory Asset regression: 226/226 PASS.

The PyPDF2 package emits a deprecation warning but PDF reopen validation passes; this is technical debt, not an acceptance failure, because the installed supported runtime remains functional and no pypdf dependency is currently present.

## Disable / rollback path

The engine has no autonomous production hook at v0.1. Disable is therefore immediate and non-destructive:

1. stop invoking the derivative worker/package composer from callers;
2. leave immutable masters untouched;
3. quarantine or delete only derivative/package output roots after their receipts are retained;
4. do not promote derivative or package state into canonical Factory truth;
5. retain FA-001/FA-029 receipts for provenance and investigation;
6. re-enable only after the same recipe versions and QA tests pass.

The operational FA-029 evidence root is outside Git under `D:\FACTORY_ASSET\canaries\FA-029`. Removing that canary root does not remove or modify Linux production masters.

## Authority boundary

This engine contains no marketplace upload/publication action, provider generation action, credential handling, browser/CDP ownership, or canonical DIE State Manager mutation. Content-addressed canonical master ingestion is a separate task (`FA-106`).