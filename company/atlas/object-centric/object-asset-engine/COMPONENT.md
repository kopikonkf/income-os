# Atlas Object Centric - Component Ownership

Status: `LINUX_STAGED_WAITING_OBJECT_FILTER_COMPLETION`
Migration task: `DIE-203`

Object Atlas is the object/noun primitive lane: filtered object vocabulary -> keyword/semantic expansion -> asset opportunity generation. It is complementary to the Human-Centric Atlas, which starts from human needs/problems/intents.

Linux-ready source:
- `company/atlas/object-centric/object-asset-engine/source/SOURCE_MANIFEST.json`
- 23 Python source files (22 migrated operational scripts + OS-neutral path contract)
- Windows runtime path literals: 0
- Windows Gemini credential file is not copied; Linux audit credential is `DIE_OBJECT_ENGINE_GEMINI_KEY_FILE` and fails closed when absent.

Migration baseline:
- `company/atlas/object-centric/object-asset-engine/migration/POINT_IN_TIME_SNAPSHOT_V1.json`
- SQLite snapshots were produced with `sqlite3.Connection.backup` while Windows remained active.
- raw WAL/SHM files were not copied.
- 7 data files were hash-verified after Linux transfer.

Windows `D:\object-asset-engine` remains authoritative while the 800k+ noun filtering/audit worker runs. Linux Object Engine has no writer service active. Final completion requires Founder report that filtering is complete, Windows writer quiesce, final SQLite backup/delta, hash/quick-check/critical-count parity, then explicit Linux authority promotion.

Historical Windows source snapshot remains at `source-snapshot/windows-v1/` for provenance. The syntax-invalid `gemini_audit_parallel.py` remains excluded from active Linux source.
