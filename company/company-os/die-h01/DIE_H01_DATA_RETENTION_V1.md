# DIE-H01 Data Retention v1

Status: H01-005 ACCEPTANCE CANDIDATE
Date: 2026-09-12
Scope: H01 Linux persistent data and deployment staging only. `/srv/die` source cleanup remains governed by H01-004 and is not changed here.

## Retention classes

- `ACTIVE`: current runtime/source-of-truth state or a path referenced by an active service.
- `ROLLBACK`: retained to restore the legacy H01 organism or a prior accepted data state before V2 cutover.
- `ARCHIVE`: durable provenance, migration evidence, or source material whose historical bytes should be preserved.
- `REGENERABLE`: reconstructible staging/cache/material with no current runtime reference; retain unless deletion is separately proven safe.
- `DISPOSABLE`: a byte-for-byte duplicate whose retained parent/source reconstructs the exact deleted bytes and which has no live reference.

## Classification matrix

| Path / class | Observed bytes | Retention | Evidence / action |
|---|---:|---|---|
| `/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db` | 1,210,916,864 | ACTIVE | Canonical Object Atlas DB. SQLite `quick_check=ok`; 714,268 candidate seeds, 43,005 `wave3_status=eligible`. Keep. |
| `/var/lib/die/atlas/object-asset-engine/db/seed_library.db` | 66,695,168 | ACTIVE | Founder-approved DIE-203 runtime seed library; `quick_check=ok`; 475,560 objects. Keep. |
| `/var/lib/die/atlas/object-asset-engine/data/raw/enwiktionary_dump.jsonl` | 3,212,259,034 | ARCHIVE | Raw source/provenance for Object Atlas rebuild. Not disposable merely because the DB exists. Keep. |
| `/var/lib/die/atlas/object-asset-engine/state/pre-die203-final-20260830T0929Z` | 1,231,560,704 | ROLLBACK | Explicit rollback-safe pre-final promotion state from DIE-203. Keep until V2 cutover retirement. |
| `/var/lib/die/atlas/object-asset-engine/incoming/die203` after cleanup | 833,276,751 | ARCHIVE | Retained parent migration archives and receipts. Transport chunks were deleted only after concatenated SHA/byte parity with the retained parents. |
| `/var/lib/die/atlas/object-asset-engine/incoming/object_asset_engine.db.final.gz` | 246,966,615 | ARCHIVE | Compressed final migration payload. Its decompression exactly reconstructs the deleted uncompressed staging duplicate. Keep. |
| `/var/lib/die/atlas/object-asset-engine/incoming/seed_library_final.db.gz` | 20,437,500 | ARCHIVE | Compressed founder-approved final seed baseline; decompressed SHA equals active `seed_library.db`. Keep as migration provenance. |
| `/var/lib/die/state` | 1,496,190,401 | ACTIVE | Shared runtime state. Executive/Division01/Hermes/Factory units explicitly read/write it. Keep. |
| `/var/lib/die/workspaces` | 1,095,164,497 | ACTIVE | Hermes and MUXIA dispatch units explicitly use this workspace root. Keep. |
| `/var/lib/die/postprocess` | 1,295,564,886 | ROLLBACK | Legacy postproduction artifact bank. No bulk deletion before V2 proves a complete production cycle. |
| `/var/lib/die/manual-publish` | 19,746,366 | ROLLBACK | Founder/manual-publish artifact evidence. Keep through legacy rollback window. |
| `/var/lib/muxia` | 2,539,660,330 | ACTIVE | Browser/runtime state for currently active MUXIA cluster services. Keep. |
| `/var/log` | 1,144,083,768 | ACTIVE | Current and historical operational diagnostics; journald reports ~97.8 MiB active+archived journal usage. No H01-005 bulk log deletion. |
| `/opt/die/staging/income-os` | 53,921,810 | ACTIVE | Explicitly referenced by Hermes and Executive/Division01 staging services. Keep. |
| `/opt/factory-asset/fa124-runtime` | part of `/opt/factory-asset` 56 MiB | ROLLBACK | Referenced by FA-124 units; timers inactive but unit rollback/acceptance path remains. Keep. |
| `/opt/die/staging/income-os-pre-rekey-f5eb720` | 5,730,106 | ARCHIVE | Named pre-rekey source snapshot; migration provenance. Keep. |
| `/opt/die/staging/division-browser-source-e1503cb` | 50,645,844 | REGENERABLE | No live unit/process reference; source staging copy. Retained because exact canonical reconstruction proof was not established in H01-005. |
| `/opt/die/staging/exec-browser-source-6372a93` | 50,641,531 | REGENERABLE | No live unit/process reference; source staging copy. Retained because exact canonical reconstruction proof was not established in H01-005. |
| `/opt/die/staging/mcp002-source` | 5,756,693 | REGENERABLE | No live unit/process reference; historical staging source. Retained because exact canonical reconstruction proof was not established in H01-005. |
| `/home/kopiko/die-archive/legacy-live-snapshots` | 2,044,731 | ROLLBACK | H01-004 immutable legacy-live snapshot. Keep. |
| `/home/kopiko/die-archive/worktree-rescue-20260911` | 2,447,907 | ARCHIVE | Unique source evidence preserved by H01-002. Keep. |

## Proven DISPOSABLE deletion

Only two duplicate classes were deleted:

1. `/var/lib/die/atlas/object-asset-engine/incoming/die203/chunks/` — 833,236,641 bytes. The 8 Object DB chunks, 1 seed-library chunk, and 18 data-tar chunks each concatenate to exactly the retained parent archive by byte count and SHA-256.
2. `/var/lib/die/atlas/object-asset-engine/incoming/object_asset_engine.db.final` — 1,210,871,808 bytes. Its SHA-256 and byte count exactly equal the decompressed retained `object_asset_engine.db.final.gz`; no systemd/cron/process reference was found.

Total verified deletion: **2,044,108,449 bytes** (~1.90 GiB). Root filesystem usage fell from 35% to 33%.

## Post-delete integrity

After deletion:

- Object Atlas `object_asset_engine.db`: `PRAGMA quick_check = ok`.
- Seed library `seed_library.db`: `PRAGMA quick_check = ok`, 475,560 objects.
- Object Atlas still reports exactly 43,005 Wave-3 eligible candidates.
- Retained DIE-203 parent archives remain present.
- No `/srv/die` cleanup, service restart, runtime cutover, production-state deletion, artifact deletion, or log deletion was performed.

This policy is conservative by design: `REGENERABLE` is not synonymous with `DISPOSABLE`. H01-005 deletes only data for which exact duplicate reconstruction and non-use were proven.
