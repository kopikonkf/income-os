# H01 NexaBurst Engine

Runtime-isolated PoC for Object Atlas acquisition through the authenticated NEXABOT Web Creator Studio session.

## Identity
- Engine: H01 NexaBurst Engine
- Runtime id: H01-NEXABURST
- Profile: nexaburst-p001
- Display: :12.0
- Workspace: 4 (wmctrl index 3)
- CDP: 127.0.0.1:9311
- UDD: /var/lib/die/h01/nexaburst/profiles/nexaburst-p001/udd

## Flow
Object Atlas queue
-> nexaburst-adapter.mjs
-> authenticated same-origin POST /api/v1/generate
-> serial poll /api/v1/jobs/{id}
-> direct binary download
-> immutable raw + SHA256 receipt
-> v2-queue.jsonl
-> nexaburst-v2-worker.py
-> Factory Orchestration V2 postprocess
-> WAITING_FOUNDER_QC

No cookies, tokens, OTPs, or credential values are extracted.

## Safety / authority
- max in-flight per profile: 1
- billing: Unlimited only
- submission_authorized: false
- publication_authorized: false
- no marketplace upload
- no spend action

## Adaptive pacing
- poll: 2s
- success cooldown: 2s
- busy cooldown: 15s
- HTTP 429 cooldown: 60s
- server-side retry/rotation progress is polled, not duplicated by client

## Object Atlas source
Canonical DB: /var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db
Eligible slice: candidate_seeds.wave3_status = 'eligible'
Count: 43,005 unique canonical names
Materialized isolated queue:
config/object-atlas-eligible-43005-isolated.jsonl

## Commands
Browser:
  bin/nexaburst-browser.sh

Health:
  node bin/nexaburst-health.mjs

One generation:
  node bin/nexaburst-adapter.mjs --noun "ceramic mug" --style isolated-object --asset-id OA-TEST-001

Bounded batch:
  node bin/nexaburst-batch.mjs --input config/object-atlas-canary-5.txt --style isolated-object --max 5

V2 one queued item:
  /opt/die/factory-asset/venv/bin/python bin/nexaburst-v2-worker.py --once

## Current deployment boundary
The H01 dedicated browser requires a one-time manual NEXABOT login in Workspace 4. The Windows Office session is deliberately not copied.
