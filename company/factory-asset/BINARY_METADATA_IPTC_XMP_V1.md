# Binary IPTC/XMP Metadata v1

Task: `FA-141`
Status: PASS
Date: 2026-09-04

## Boundary

FA-141 embeds deterministic Factory metadata only into a **marketplace delivery derivative copy**. Immutable provider originals and active masters are never rewritten. After embedding, the derivative receives a new SHA-256, XMP/IPTC are read back from bytes, derivative technical QA runs again, and package evidence is rebound to the post-injection hash.

## JPEG v1

Supported binary embedding:
- XMP in JPEG APP1
- IPTC-IIM inside Photoshop APP13 IRB
- title
- description
- repeated keywords
- AI disclosure marker

Unsupported formats remain `SIDECAR_ONLY`; v1 does not fabricate metadata support. Platform form AI-disclosure requirements remain separate even when an AI disclosure marker exists in XMP/IPTC.

## Founder notification surface

Success-path Telegram is intentionally simple:
1. `PRODUCTION_STARTED` with `blueprint=REQUIRED`
2. cron response `status=STARTED`
3. `ARTIFACT_CREATED`
4. `WAITING_FOUNDER_QC`

Backend QA, rights and package states remain durable but are not emitted as extra success-path milestones. When rights signals require review, the backend remains `REVIEW_REQUIRED / PACKAGE_BLOCKED / submission_eligible=false`; externally the card parks at `WAITING_FOUNDER_QC` so Founder visual/rights review does not block independent production cadence. Failure alerts remain enabled for anti-stall operation.
