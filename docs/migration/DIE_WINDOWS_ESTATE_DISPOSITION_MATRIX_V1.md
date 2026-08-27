# DIE-101 — Windows Estate Disposition Matrix V1

Date: 2026-08-27
Status: CANON / DIE-101
Input: `docs/migration/DIE_WINDOWS_ESTATE_INVENTORY_V1.md`
Owner: Founder Dee

## 1. Purpose

DIE-101 converts the DIE-100 read-only Windows estate inventory into an explicit migration disposition. It is a decision/canon task only: it does not copy data, stop writers, move services, migrate credentials, change browser profiles, or cut over endpoints.

One Windows root may receive multiple dispositions because source, mutable data, runtime installation, credentials, and rollback evidence have different ownership and migration rules.

## 2. Canonical disposition vocabulary

- `MIGRATE_SOURCE` — import only clean, owned source/canon into the Git-tracked `/srv/die` tree through reviewed commits. Never import nested `.git`, runtime state, caches, credentials, or browser data as source.
- `REBUILD_LINUX` — recreate the executable/runtime/service/profile/configuration on Linux from source/config contracts. Do not byte-copy Windows binaries, Python venvs, `node_modules`, browser installations, or credential-equivalent profiles.
- `MIGRATE_DATA` — move durable business/operational data into `/var/lib/die` or `/var/lib/muxia` using count/hash/cursor/lineage receipts. Live-writer data requires a consistent snapshot or writer freeze.
- `ARCHIVE_PROVENANCE` — preserve read-only historical evidence, license material, migration receipts, or selected rollback artifacts outside the live source/runtime path.
- `RETIRE_AFTER_CUTOVER` — keep the Windows implementation available until its replacement and rollback gates pass; only then disable/retire it.
- `KEEP_EXTERNAL` — explicitly outside Chapter #4 DIE ownership. Observe dependencies but do not absorb, rewrite, move, stop, or reconfigure without separate Founder authorization.
- `UNRELATED_EXCLUDE` — regenerable, duplicate, temporary, cache, alias, or otherwise non-migration payload. Do not copy.

## 3. Physical target roots

The Chapter #4 Linux target separates source, mutable data, configuration, and installed runtime:

```text
/srv/die/                  Git-tracked source + company canon
/var/lib/die/              mutable non-MUXIA DIE state/data/artifacts
/var/lib/muxia/            MUXIA profiles/jobs/artifacts/state/logs
/etc/die/                  Linux config/secrets; not Git
/opt/die/                  installed DIE service runtimes/builds
/opt/mcp-architect/        Architect MCP runtime, final pre-cutover only
```

No Windows credential/profile tree is a valid shortcut into these roots.

## 4. Estate disposition matrix

| Windows estate/component | Disposition | Linux/canon target | Locked rule / gate |
|---|---|---|---|
| `C:\DIE` tracked/owned source | `MIGRATE_SOURCE` | `/srv/die` | GitHub main is the source transport. Do not mirror the dirty live tree. |
| `C:\DIE` live-only source candidates (`bin/`, `bridge/`, tests/docs) | `MIGRATE_SOURCE` | appropriate `/srv/die` logical owner | Reconcile each candidate against current main, test, commit, and review; never raw-copy all 37 dirty paths. |
| `C:\DIE\state` canonical runtime state/projection | `MIGRATE_DATA` + `RETIRE_AFTER_CUTOVER` | `/var/lib/die/state` | Preserve event ordering/cursor/count/hash; final sync requires writer freeze/replay proof. |
| `C:\DIE\logs` | `ARCHIVE_PROVENANCE` | `/var/lib/die/archive/windows-logs/` or sealed external archive | Logs are evidence, not Git source. Sanitize before long-term retention. |
| `C:\DIE\workspaces` (~533.5 MiB) | `ARCHIVE_PROVENANCE` selective + `UNRELATED_EXCLUDE` bulk | selected evidence only | Do not bulk-copy. Preserve only mission evidence/artifacts not already canonical elsewhere; caches/temp/test workspaces excluded. |
| `C:\DIE\.pytest_cache`, `__pycache__`, generated build/cache trees | `UNRELATED_EXCLUDE` | none | Regenerate if needed. |
| `C:\DIE\IDENTITY\chatgpt-plus-executive.md` + Executive source in `bin/bridge/ops` | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/executive/`, runtime `/opt/die/...`, state `/var/lib/die/...` | Preserve logical identity; recreate Linux service/browser/auth configuration, do not clone browser secrets. |
| `C:\DIE\IDENTITY\division-head-division01.md` + Division01 source in `bin/bridge/ops` | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/division/division001/` | Logical directory may be `division001`, but principal ID remains `division-head-division01` unless a separate identity migration is ratified. |
| `C:\DIE\IDENTITY\hermes-operator/{SOUL.md,AGENTS.md}` + Hermes control source | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/die-agents/hermes/` | Canonical identity/config comes from source; Linux runtime is rebuilt, not AppData-cloned. |
| worker templates/runtime contracts under `C:\DIE` | `MIGRATE_SOURCE` + `REBUILD_LINUX` | `/srv/die/company/workers/` | Import contracts/source only; worker temp state remains runtime-owned. |
| human-centric Atlas canon (`docs/atlas/HUMAN_CENTRIC_ATLAS_CANON.md`) | `MIGRATE_SOURCE` | `/srv/die/company/atlas/human-centric/` | Canonical document moves through Git history, not ad-hoc copy. |
| `D:\object-asset-engine` scripts/config/source | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/atlas/object-centric/object-asset-engine/`, runtime `/opt/die/...` | Clean import excludes DB/data/output/runtime caches. Linux paths/config must be OS-neutral. |
| `D:\object-asset-engine\data` (~3.064 GiB) | `MIGRATE_DATA` | `/var/lib/die/atlas/object-centric/object-asset-engine/data/` | Hash/count receipt required. |
| `D:\object-asset-engine\db` (~1.138 GiB, live SQLite/WAL) | `MIGRATE_DATA` | `/var/lib/die/atlas/object-centric/object-asset-engine/db/` | Must use a consistent SQLite snapshot/backup or quiesced writer. Plain copy while WAL/writer is active is forbidden. |
| `D:\object-asset-engine\outputs/state/reports` | `MIGRATE_DATA` selective + `ARCHIVE_PROVENANCE` | `/var/lib/die/atlas/object-centric/object-asset-engine/` | Preserve durable outputs/state with lineage; historical reports may be archived. |
| `D:\mcp-architect` clean repo source | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/architect/`, `/opt/mcp-architect/` | **DEFERRED TO FINAL PRE-CUTOVER STAGE.** Windows Architect MCP remains control/bootstrap channel until all Windows-dependent work is complete. |
| `D:\mcp-architect\workspace` | `ARCHIVE_PROVENANCE` selective + `UNRELATED_EXCLUDE` bulk | selected evidence only | Current clean publication work is already in GitHub. Do not import untracked workspace wholesale. |
| `D:\mcp-architect\node_modules` | `UNRELATED_EXCLUDE` | none | Rebuild with package lock on Linux. |
| `D:\mcp-architect\.env` / secrets | `REBUILD_LINUX` | `/etc/die/` or service-specific protected config | Re-provision; do not commit or bulk-copy secret values. |
| `D:\V2 Proxima` source/runtime | `ARCHIVE_PROVENANCE` + `RETIRE_AFTER_CUTOVER` | sealed legacy/provenance evidence; no MUXIA source import | Personal/non-commercial license boundary remains. MUXIA is independent DIE-owned implementation. |
| `D:\V2 Proxima\node_modules` (~835.6 MiB) | `UNRELATED_EXCLUDE` | none | Regenerable dependency cache. |
| `D:\V2 Proxima\.test-userdata` (~424.5 MiB) | `UNRELATED_EXCLUDE` | none | Test browser data is not source canon. |
| live Proxima profile `AppData\Roaming\proxima` (~645 MiB) | `RETIRE_AFTER_CUTOVER` | none by default | Do not bulk-copy cookies/tokens/session state. Keep Windows rollback profile until retirement gate. |
| `D:\proximav2-setup` | `ARCHIVE_PROVENANCE` + `RETIRE_AFTER_CUTOVER` | `/var/lib/die/archive/proxima-support/` or sealed provenance package | Preserve only after provenance classification; not executable canon. |
| `D:\OAUTH` source | `MIGRATE_SOURCE` + `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | `/srv/die/company/next-subprojects/web-ai-oauth-adapter/`, runtime `/opt/die/web-ai-oauth-adapter/` | **Distinct from Division01.** Treat as its own Web-AI multi-provider adapter. |
| `D:\OAUTH\credentials` | `REBUILD_LINUX` | `/etc/die/web-ai-oauth-adapter/` | Fresh/re-provisioned credentials only. No credential-value migration by bulk copy. |
| `D:\Digital_Income_Empire` historical docs/execution material | `ARCHIVE_PROVENANCE` selective | `/srv/die/docs/provenance/` and/or sealed archive | Deduplicate against current Git canon; do not create a second live canon. |
| `D:\Backup_VPS` (~7.859 GiB) | `ARCHIVE_PROVENANCE` | `/var/lib/die/archive/windows-vps/` or external durable archive | Preserve a manifest and at least the latest known-good required rollback set; deduplicate older copies rather than importing into `/srv/die`. |
| `D:\ASSETS\MASTER13` physical content | `MIGRATE_DATA` conditional | `/var/lib/die/artifacts/legacy/master13/` | If non-empty at migration time, inventory/hash/copy once; current DIE-100 observation found no regular files. |
| trailing-space alias `D:\ASSETS\MASTER13 ` | `UNRELATED_EXCLUDE` | none | Alias/duplicate path hygiene; never treat as a second dataset. |
| Hermes AppData root (`AppData\Local\hermes`) | `REBUILD_LINUX` + `MIGRATE_DATA` selective + `RETIRE_AFTER_CUTOVER` | Linux Hermes runtime under `/var/lib/die/...` | No bulk profile clone. Import only explicitly identified non-secret durable operational state after schema/ownership review. |
| Hermes `income-operator` profile | `REBUILD_LINUX` | Linux profile/runtime created from canonical SOUL/AGENTS/config | Fresh runtime/profile. Credential/session-equivalent contents are not migration payload. |
| BrowserClaw installation/data | `REBUILD_LINUX` functional equivalent + `RETIRE_AFTER_CUTOVER` | Executive Linux browser/wake implementation | Do not copy BrowserClaw user-data/profile tree. Rebuild only the required wake/read capability behind the new Linux contract. |
| Division01 Brave user-data root | `REBUILD_LINUX` + `RETIRE_AFTER_CUTOVER` | dedicated Linux Division01 browser/profile | Fresh operator-controlled authentication; no bulk profile/cookie copy. |
| Executive/Division Cloudflare/runtime credentials | `REBUILD_LINUX` | `/etc/die/...` protected configuration | Re-provision; source may contain templates only, never secret values. |
| `C:\aether\aether-ai-os` | `KEEP_EXTERNAL` | unchanged | Separate Aether repo; outside Chapter #4 scope unless explicitly reauthorized. |
| `D:\aether-bridge` + Aether Living MCP/herdr | `KEEP_EXTERNAL` | unchanged | Protected external. Do not move, stop, rewrite, rebind, or absorb. |
| `D:\aether-identity` | `KEEP_EXTERNAL` | unchanged | Aether identity estate. |
| `D:\state-shared` | `KEEP_EXTERNAL` | unchanged | Aether/shared-state estate; not DIE state canon. |
| unrelated host workspaces/tools (`ACO`, `AionUI`, `Jarvis`, Claude/Gemini/Cline/etc.) | `UNRELATED_EXCLUDE` | none | Not part of DIE one-canon migration absent separate authorization. |

## 5. One-canon ownership mapping

The logical company ownership after selective import is locked as:

```text
/srv/die/
├── docs/
│   └── provenance/                 # selected historical evidence only
├── company/
│   ├── architect/                  # imported last / final pre-cutover stage
│   ├── executive/
│   ├── atlas/
│   │   ├── human-centric/
│   │   └── object-centric/
│   │       └── object-asset-engine/
│   ├── muxia/
│   ├── division/
│   │   └── division001/            # principal ID stays division-head-division01
│   ├── die-agents/
│   │   └── hermes/
│   ├── workers/
│   └── next-subprojects/
│       └── web-ai-oauth-adapter/   # D:\OAUTH; NOT Division01
└── LASTSTANDINGPOINT.md
```

Mutable data never becomes a sibling Git source directory merely to make the tree look complete.

## 6. Source/data/config separation rules

1. `/srv/die` is Git source/canon only.
2. `/var/lib/die` and `/var/lib/muxia` contain mutable state/data/artifacts.
3. `/etc/die` contains Linux secrets/config and must not be committed.
4. `/opt/die` and `/opt/mcp-architect` contain installed service runtime/builds and may be regenerated from source.
5. No nested `.git`, `node_modules`, Python caches/venvs, browser profiles, cookie/token databases, `.test-userdata`, or raw Windows workspaces are imported into `/srv/die`.
6. Dirty live Windows source is reconciled file-by-file into Git; dirty state is migrated through state/data procedures, never by making the live working tree the source of truth.

## 7. Migration execution order

The ordering is now locked as follows:

```text
DIE-100 inventory
   -> DIE-101 disposition
   -> DIE-102 env/path abstraction
   -> DIE-103 clean component import
   -> DIE-104 canon validator
   -> DIE-200 Executive Linux
   -> DIE-201 Division01 Linux
   -> DIE-202 Hermes/Workers Linux
   -> DIE-203 Atlas/Object Engine Linux
   -> DIE-204 topology proof
   -> MX-060 observability
   -> MX-061 fault injection
   -> MX-062 soak
   -> MX-070 compatibility
   -> MX-071 governed production canary
   -> MX-072 evidence package
   -> MX-080 Founder promotion/cutover decision
   -> CUT-001 freeze Windows DIE writers EXCEPT Architect MCP
   -> CUT-002 final state/data sync
   -> CUT-003 restore/replay proof
   -> CUT-004 cut over non-Architect endpoints
   -> CUT-005 disable migrated Windows DIE services/tasks EXCEPT Architect MCP
   -> MX-053 build/deploy Linux Architect MCP
   -> MX-054 prove Linux Architect MCP via temporary/non-destructive route
   -> CUT-006 Founder-authorized Architect control-channel handoff
```

The Windows Architect MCP is deliberately the last Windows DIE control component kept alive. `CUT-006` is a terminal control-channel handoff: after it, no remaining migration task may depend on Windows Architect MCP access.

## 8. Critical dependency locks

### Architect MCP

- Do not migrate/switch Architect MCP early.
- `MX-053` cannot start before `CUT-005`.
- Windows Architect MCP remains listening/available through `CUT-005`.
- `MX-054` proves Linux MCP while Windows MCP still exists as rollback/control.
- The actual connector/control-channel switch requires explicit Founder action in `CUT-006`.

### Executive and Division01

- They are separate principals and remain separate Linux services/config roots.
- Division01 principal ID remains `division-head-division01`.
- Browser/auth state is recreated under operator control; no Windows cookie/profile clone.

### OAUTH

- `D:\OAUTH` is not Division01.
- It is an independent Web-AI adapter lane and may be retired later if no caller remains, but DIE-101 does not assume retirement.

### Object Asset Engine

- Source and data are separate migration units.
- SQLite DB migration must be consistent/quiesce-aware.
- Object-centric Atlas ownership does not mean DB files enter Git.

### Aether

- `C:\aether`, `D:\aether-bridge`, `D:\aether-identity`, and `D:\state-shared` are outside this migration and remain untouched.

## 9. Decisions intentionally deferred

DIE-101 does not decide:

- the exact Linux systemd unit names;
- final OAuth/Cloudflare secret values;
- marketplace submission automation;
- whether OAUTH remains long-term after all callers are mapped;
- whether historical Windows backups older than the latest required rollback set are retained forever;
- final retirement/deletion date for the Windows VPS;
- any Aether migration.

These require later execution evidence or explicit Founder decisions.

## 10. Acceptance

DIE-101 is accepted when:

- every DIE-100 estate root has an explicit disposition;
- `D:\OAUTH != Division01` is encoded;
- Aether is `KEEP_EXTERNAL`;
- Proxima source/profile is not imported into MUXIA;
- object-engine source/data are separated;
- source/runtime/config/state target roots are separated;
- Architect MCP is encoded as final pre-cutover control-plane migration;
- the task graph enforces the ordering;
- JSON/docs validation passes;
- no runtime migration is performed by DIE-101.

Next atomic task after closure: `DIE-102 — env/path abstraction`.
