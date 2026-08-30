# DIE-203 ? Atlas + Object Asset Engine Linux Migration V1

Date: 2026-08-28
Status: DONE
Implementation SHA: `f0cb0a90de45ca155f1109ceb15721365a8d7488`

## Scope and authority

DIE-203 covers the Human-Centric Atlas foundation material and Object-Centric Asset Engine Linux migration. The two Atlas lanes are complementary:

- Human-Centric Atlas: human need/problem/intent is the demand generator.
- Object-Centric Atlas: filtered object/noun primitives feed keyword/semantic expansion and asset opportunity generation.

Windows `D:\object-asset-engine` remains authoritative while the active `gemini_audit_scale.py --run` filtering/audit process continues over the 800k+ noun universe. Linux currently holds a verified point-in-time baseline only. No Linux Object Engine writer is active.

## Human-Centric Atlas foundations

Normative canon remains `company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md`.

Four Qwen-era documents from `D:\Digital_Income_Empire\Docs\Qwen 3.8 Max\The Algorithmic Cross-Join Matrix (Production Scalability)` were preserved byte-exact under `company/atlas/human-centric/foundations/qwen-crossjoin-v1/` with SHA256 provenance. They are intentionally `normative_canon=false` because the source material itself includes brainstorming and Pending Founder Ratification classifications.

Architectural primitives worth preserving for later ratification/refactor:

1. 10-dimensional Human-Centric matrix: Human, Activity, Object, Place, Time, Demographic, Emotion, Problem, Industry, Commercial Intent.
2. dimension classes: generative, contextual/constraining, commercial.
3. coherence/constraint filtering before candidate scoring.
4. weighted sampling rather than exhaustive Cartesian enumeration.
5. Opportunity Score + evidence confidence.
6. Worth-Making Gate before production.
7. executable blueprint contract.
8. metadata, QA, platform-routing and ERVA loop.
9. event-driven scaling thresholds.

Preservation does not ratify historical execution assumptions or supersede current Human Atlas canon.

## Object Engine source

DIE-103 had imported 22 syntax-valid Windows source files and excluded `scripts/audit/gemini_audit_parallel.py` because of its upstream f-string SyntaxError.

Current source drift audit found exactly one of the 22 tracked operational files changed on Windows: `gemini_audit_scale.py`, where the live throttle changed from 30 seconds to 5 seconds. That current source was reconciled before Linux path refactor. The syntax-invalid parallel script remains excluded.

Linux-ready source is materialized at:

`company/atlas/object-centric/object-asset-engine/source/`

Source manifest facts:

- 23 Python source files total: 22 operational migrations + `object_engine_paths.py`.
- 0 `__pycache__` directories.
- 0 `.pyc` files.
- 0 `D:\object-asset-engine` runtime literals.
- 0 `D:\Dee_Workspace` runtime literals.
- Linux default runtime root: `/var/lib/die/atlas/object-asset-engine`.
- audit credential path: `DIE_OBJECT_ENGINE_GEMINI_KEY_FILE`; missing credential fails closed.

Linux compile proof: 23/23 PASS. Two legacy docstrings emit invalid-escape SyntaxWarnings only; they do not prevent compilation or execution.

## SQLite consistency strategy

The Windows DB was active in WAL mode, therefore DIE-203 did not copy raw `.db + .wal + .shm`. `migration/sqlite_online_backup.py` uses Python `sqlite3.Connection.backup` while opening the source DB read-only, producing a transactionally consistent point-in-time snapshot.

Main snapshot:

- bytes: 1,188,335,616
- SHA256: `7a14ff13f4f1d2ea04b10ba84cb7774144313ef50bfa3cda3ec8fd1c8d407a00`
- `PRAGMA quick_check`: `ok`
- tables: 12
- candidate_seeds: 714,268
- audit_queue: 744,259
- audit pending: 251,294

Seed library snapshot:

- bytes: 43,192,320
- SHA256: `b881e98eb604aad36ccf9eecac74d00a9afdb4b64dcc7f7fa30348451fea3ec2`
- `PRAGMA quick_check`: `ok`
- tables: 1
- objects: 302,134

Raw WAL/SHM files were not copied.

## Data migration

Seven object-engine data files were SHA256-pinned before transfer. Total bytes: 3,212,340,964. The ~3.21 GB Wiktionary JSONL is included.

To avoid repeated multi-gigabyte SCP failure, the payload was compressed and split into 27 bounded chunks. Initial transfer completed 26/27 chunks; one connection-closed chunk was retried exactly once. All 27 chunk sizes/hashes and all three reconstructed archive hashes matched before extraction.

After Linux extraction, all 7 data files matched byte count and SHA256.

## Linux runtime

Runtime root:

`/var/lib/die/atlas/object-asset-engine`

Subtrees: `db/`, `data/`, `outputs/`, `reports/`, `state/`.

Ownership boundary: `root:die-runtime`.

`install-linux.sh` installs path/config contracts under `/etc/die/object-asset-engine` and verifies both SQLite DBs read-only. It does not start a writer or service. Windows credential file `D:\Dee_Workspace\makan.txt` is never copied.

Linux runtime proof:

- source compile: 23/23 PASS, 0 pyc/pycache.
- installer DB check: PASS.
- credential gate absent: fail-closed PASS (`DIE_OBJECT_ENGINE_GEMINI_KEY_FILE_REQUIRED`).
- point-in-time runtime verifier: PASS.
- main DB SHA/quick-check/table/count parity: PASS.
- seed DB SHA/quick-check/table/count parity: PASS.
- data 7/7 hash parity: PASS.

## DIE-203 final promotion — 2026-08-30

The filtering gate is complete. `audit_queue` contains 744,259 rows and all 744,259 are `audit_status=done`; verdicts are OBJECT 433,750, REJECT 295,676 and UNSURE 14,833. The Windows Gemini worker process count was zero at the final gate. Windows source DBs were not overwritten or deleted.

Final quiesced main database promoted to Linux:

- bytes: 1,210,871,808
- SHA256: `e6e43fbd4bbee712de651c31a159bb66872a91b1b555f809d0177ba856eeb891`
- `PRAGMA quick_check`: `ok`
- candidate_seeds: 714,268
- audit_queue / done: 744,259 / 744,259

The earlier 433,835-object `seed_library.db` snapshot (SHA256 `05ea44ad30a446ce4fe3ae835791d8a8a80cbf16b84ccfc69a245e08ca3c6d32`) is retained as a historical pre-Wave3 checkpoint only. Founder-approved `seed_library_final.db` is the DIE-203 production baseline and is promoted on Linux as canonical runtime `seed_library.db`:

- bytes: 66,695,168
- SHA256: `3035b179ba435a9cc4983ca567528b15941b1a9f205451d425cd40ce5925ab77`
- `PRAGMA quick_check`: `ok`
- objects: 475,560
- distinct `lower(trim(word))`: 475,560 (zero duplicates)
- not_in_wordnet 401,121; wave3_eligible 41,725; h4_capital 32,542; eligible_control 172.

Transport was verified by decompressed SHA before promotion. Promotion used same-filesystem rollback-safe rename: prior Linux runtime DB/WAL/SHM files were moved under `/var/lib/die/atlas/object-asset-engine/state/pre-die203-final-20260830T0929Z`; verified files were promoted with `root:die-runtime` ownership and mode `0660`. No Linux Object Engine writer was started. Post-promotion SHA, quick-check and critical-count parity all passed.

Linux is now authoritative for the migrated DIE-203 Object Engine baseline. The Windows estate remains preserved as rollback/provenance until broader cutover retirement.

## Validation

- DIE-203 targeted tests: 8/8 PASS.
- SQLite online-backup fixture under WAL: PASS.
- full bridge suite after DIE-203 additions: 249/249 PASS.
- one-canon: 11/11 PASS.
- live `C:\DIE` remains at `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`, 38 dirty paths observed and untouched.
- Object Engine Windows worker completed naturally and was observed at process count 0 before final promotion. Windows source DBs were not overwritten or deleted.

## Repair scope

`DIE-203-R1` is the single repair child for generated-bytecode manifest hygiene, transfer connection retry, shell quoting/read-only evidence hygiene, and provenance handling of byte-exact CRLF Human Atlas foundation documents. None of these repairs modify the active Windows Object Engine process or its database.
