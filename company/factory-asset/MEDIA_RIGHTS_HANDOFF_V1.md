# Media Rights Automatic Handoff V1

Status: implementation-ready.

## Purpose

Factory Asset emits a deterministic, hash-bound handoff for the exact marketplace-delivery derivative after PACKAGE_READY.

This does not grant publication or submission authority.

## Runtime point

Production orchestration creates the handoff after final-artifact.json is materialized and before WAITING_FOUNDER_QC.

Files:

- root/media-rights-handoff-result.json
- workspace/handoff/media-rights-handoff.json

The second file is a durable outbox and survives receiver/network failure.

## Identity

The handoff binds:

- task / semantic asset / blueprint
- package-plan SHA-256
- exact delivery derivative SHA-256
- MIME / byte size
- filename / derivative ID
- QA receipt reference
- optional provider-fetchable HTTPS source URI

## Rights boundary

Automated rights-signal PASS remains an automated signal only.

It never becomes human/legal/commercial clearance by itself.

Without workspace/rights-authorization.json:

`rights.state = REVIEW_REQUIRED`

and publish/commercial flags are false.

An explicit rights authorization must use schema:

`die.factory-asset.rights-authorization.v1`

and must be bound to the exact artifact SHA-256.

Only then does H01 emit:

`rights.state = ATTESTED`

The handoff itself always keeps:

- publication_authorized=false
- submission_authorized=false
- founder_qc_required=true
- human_rights_clearance_claimed=false

## Delivery URL

Optional:

`DIE_MEDIA_PUBLIC_BASE_URL=https://...`

When absent:

- source_uri=null
- delivery_state=DELIVERY_URL_PENDING

The downstream registry may record provenance but media publishing remains locked until an exact HTTPS delivery URL is bound.

## Transport

Optional automatic delivery:

`DIE_AGENTS_H01_HANDOFF_URL=https://agents-mcp.aethers.web.id/handoff/h01/media-rights`

`DIE_AGENTS_H01_HANDOFF_TOKEN=<plaintext service token>`

If either is absent, the outbox remains PENDING/DEFERRED and Factory Asset continues normally.

Network/receiver failures never fabricate delivery success.

## Safety

H01 production does not depend on Office availability.

No provider publication occurs from this handoff.

No rights clearance is inferred from detector PASS.

No artifact identity may change after the SHA-bound package is ready.
