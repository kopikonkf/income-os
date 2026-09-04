# Hermes Factory Orchestration v2 Wiring

Task: `FA-139`
Status: PASS
Date: 2026-09-04

## Live runtime change

The deterministic Hermes production runtime now calls `factory_orchestration_v2.py` after provider artifact creation. The former direct `ARTIFACT_CREATED -> upscale -> final/asset.png -> WAITING_FOUNDER_QC` path is removed from the active runtime.

Current L0 raster production remains continuity-safe through a compatibility bridge: the accepted legacy family Blueprint is projected into one bounded Object-Atlas-backed Asset Expression Plan plus Asset Blueprint v2, then FA-133 selects the governed producer route. The bridge does not claim external market evidence.

Postproduction uses FA-131 intake, FA-135 upscale normalization, FA-132 derivative planning, FA-024 derivative QA, FA-136 rights signals, FA-137 metadata/package readiness and FA-138 durable state progression. Missing detector evidence yields `REVIEW_REQUIRED` and the card does not falsely advance to package readiness.

## Human-friendly listing names

Immutable provider originals and active masters are never renamed for cosmetic purposes. Marketplace/export aliases are created only after package readiness using:

`<seed-noun>-<semantic-mode>__<active-master-sha8>.<delivery-ext>`

Example: `shopping-bag-isolated-object__463ac6d2.jpg`.

`metadata.json` and `submission-fields.json` carry title, description, keywords, AI disclosure and listing filename. Binary IPTC/XMP injection is deliberately **not** claimed by FA-139 (`binary_metadata_injected=false`); it is tracked separately so byte mutation receives its own read-back QA.

## Telegram milestones

Milestones are idempotently journaled before/with delivery:
- `PRODUCTION_STARTED`
- `ARTIFACT_CREATED`
- `QA_QC_UPDATE`
- `WAITING_FOUNDER_QC`

Replay of an identical event ID does not send a duplicate notification.

## Resume behavior

The active-card resolver recognizes all FA-138 postproduction states so a crash/restart resumes the same card. `WAITING_FOUNDER_QC` remains a parked human gate and does not prevent selection of a later independent seed.