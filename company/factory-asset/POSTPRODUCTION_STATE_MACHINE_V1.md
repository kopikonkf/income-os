# Mandatory Postproduction Readiness State Machine v1

Task: `FA-138`
Status: PASS
Date: 2026-09-04

Canonical order:

`ARTIFACT_CREATED -> MASTER_VALIDATED -> UPSCALE_DECIDED -> DERIVATIVES_READY -> TECHNICAL_QA_PASS -> RIGHTS_SIGNAL_PASS_OR_REVIEW -> METADATA_READY -> PACKAGE_READY -> WAITING_FOUNDER_QC`

The state file is an atomic durable snapshot with append-only history. Every transition requires an event ID, expected revision and evidence payload. Identical event replay is idempotent; stale revisions and event-ID collisions fail closed.

Lineage rules:
- `source_master_sha256` is immutable;
- FA-135 may change only `active_master_sha256` through a valid upscale/recovery receipt;
- downstream derivative, rights, metadata and package evidence must bind to the active master hash;
- derivative hash sets must match across generation, technical QA, metadata and package plan.

Rights `REVIEW_REQUIRED` may be recorded at the rights stage but cannot advance through `PACKAGE_READY` until a later exact-master PASS resolution is journaled. `WAITING_FOUNDER_QC` is a parked human gate, not proof that Founder QC or human rights clearance happened.

Typed failures are journaled without deleting prior lineage. Retryable failures may resume from the same state; non-retryable failures remain blocked. The machine itself performs no provider generation, upload or publication.