# NexaBurst Telegram Vault v1 Acceptance — 2026-09-20 WIB

## Scope

Disaster-recovery archive transport for H01 NexaBurst artifacts that have reached WAITING_FOUNDER_QC.

The vault is asynchronous from production/post-processing. Telegram outage must not rerun generation, upscale, derivatives, metadata, or rights processing.

## Telegram route proof

- Bot: @asset_ibot
- Chat: DIE~Digital Income Empire
- Bot API chat id: -1004358461724
- Forum: true
- Dedicated vault thread id: 5842
- Route-canary message id: 5845
- Route canary returned message_thread_id=5842

No bot token or credential value is committed.

## Archive canary

Asset: NB-CANARY-001

- Source state: WAITING_FOUNDER_QC
- Package state: PACKAGE_BLOCKED
- Rights state: REVIEW_REQUIRED
- Archive entries: 29 total, including manifest/checksums
- Payload files represented in manifest: 27
- Provider original included: PASS
- Generation receipt included: PASS
- Credential/cookie/token/UDD filename exclusion scan: PASS
- ZIP bytes: 4,884,461
- Master SHA-256: a4a5e5e2454e22f667002d14f7bacdc018f439714de677078cb24e74b1a02b12
- Archive SHA-256: 0e7a1a0ab1081f12ecd4dca58de56670fdda5a234e6e86bc8ec1c216acef6d0e
- Telegram archive message id: 5846
- Telegram thread id returned by API: 5842
- Download-back SHA-256: 0e7a1a0ab1081f12ecd4dca58de56670fdda5a234e6e86bc8ec1c216acef6d0e
- Result: BACKUP_VERIFIED

The archive was uploaded, fetched again through Telegram getFile, downloaded to H01, rehashed, and accepted only after exact SHA-256 equality.

## Idempotency / scheduling

archive_identity = SHA256(semantic_asset_id + ":" + master_sha256).

A second run for NB-CANARY-001 returned SKIP_ALREADY_VERIFIED and did not send a duplicate document.

Automatic discovery excludes local/synthetic post-process canaries and accepts only generation receipts with:

transport = WEB_SESSION_INTERNAL_JOB_API

H01 cron:

* * * * * /usr/bin/python3 /home/kopiko/die-sessions/NEXABURST-H01-P001/bin/nexaburst-vault.py --once >>/var/lib/die/h01/nexaburst/state/vault-cron.log 2>&1

A non-blocking flock prevents overlap.

## Fail-closed size boundary

Cloud Bot API v1 defaults:

- upload ceiling configured: 49,000,000 bytes
- restore-verification ceiling configured: 19,500,000 bytes

An archive above the restore-verification ceiling is not labeled BACKUP_VERIFIED; it fails closed until a larger verified transport is installed.

## Local retention

Vault v1 never deletes the local source, workspace, or archive. Retention/eviction is outside this acceptance scope.
