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

## Mass prompt authority gate

Any batch above 100 rows requires both the runtime PRODUCTION_ARMED marker and per-row prompt_authority=TYPED_VISUAL_CONTRACT_V1 with a matching prompt SHA-256. Canary fallback prompts are intentionally ineligible for mass production.

## Browser lifecycle

The NexaBurst H01 browser is a persistent authenticated UDD, but a single Chromium PID is not intended to live indefinitely. `nexaburst-browser-manager.sh ensure` enforces a default 3600-second maximum process age. Rotation is fail-safe: an active generation lock defers rotation; otherwise the old process is terminated first and the same UDD is reopened with a fresh PID. On H01, user cron invokes the manager every 5 minutes, so rotation occurs between jobs and never intentionally interrupts an in-flight generation.

## Telegram topic routing

Notifier configuration supports both `NEXABURST_TELEGRAM_CHAT_ID` and `NEXABURST_TELEGRAM_THREAD_ID`. Runtime credentials remain in `/home/kopiko/.config/die/nexaburst.env`; repository examples contain no secret values.

## Telegram Vault v1

nexaburst-vault.py is an asynchronous disaster-recovery lane. It scans real NexaBurst WEB_SESSION_INTERNAL_JOB_API workspaces that have reached WAITING_FOUNDER_QC, creates a ZIP containing the workspace plus provider original and generation receipt, embeds ARCHIVE_MANIFEST.json and CHECKSUMS.sha256, uploads to a dedicated Telegram forum topic, streams the uploaded document back through getFile directly into SHA-256 without writing a restore file, and only records BACKUP_VERIFIED when byte count and SHA-256 exactly match the local staging archive.

The vault is intentionally separate from post-processing: Telegram failure never causes rendering/upscale/post-production to rerun. archive_identity = SHA256(semantic_asset_id + master_sha256) makes retries idempotent. Synthetic/local post-process canaries are excluded from automatic scanning. Credential, token, cookie and UDD paths are excluded from archives. The source/raw/workspace are never deleted by the vault. The local ZIP is staging-only: after the durable BACKUP_VERIFIED receipt and ledger entry are written, the ZIP is deleted. Startup cleanup also removes any verified staging ZIP left behind by a crash between ledger write and cleanup.

Manual canary:

    python3 bin/nexaburst-vault.py --asset-id NB-CANARY-001 --dry-run
    python3 bin/nexaburst-vault.py --asset-id NB-CANARY-001

H01 runtime cadence uses a one-minute cron calling --once. A non-blocking file lock prevents overlap. With the official cloud Bot API, v1 deliberately requires an archive below the configured restore-verification ceiling (default 19.5 MB); larger packages fail closed until a larger verified transport such as the official Local Bot API is enabled.

## 30-render preset challenge

The bounded preset-selection challenge is canonicalized under config/challenge-30-typed.jsonl.
It uses 10 anchor nouns across three typed presets:

1. ISOLATED_SOFT_WATERCOLOR_CLIPART_WHITE_L0
2. ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0
3. ISOLATED_CLEAN_COMMERCIAL_CLAY_3D_L0

The challenge hot path is deterministic and does not invoke an LLM. Challenge assets are held from Factory V2 using runtime v2-hold-ids.txt until a Founder preset champion is selected.

A 100-noun market-canary source cohort is prepared but remains HOLD. Release requires a Founder preset champion, exact typed prompt compilation for all 100 rows, and disk-gate PASS.
