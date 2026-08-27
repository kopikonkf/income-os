# DIE-100 — Windows Estate Inventory V1

Date: 2026-08-27
Status: PASS_WITH_ONE_REPAIR_CHILD
Scope: read-only Windows estate inventory before one-canon mapping and Linux migration.

## 1. Safety boundary

This inventory used metadata-only inspection. It did not read credential values, browser cookies, auth tokens, credential databases, session/localStorage contents, raw process command-line arguments, or secret file contents. No Windows service, scheduled task, process, firewall rule, repository, runtime state, browser profile, or application configuration was modified.

Live `C:\DIE` was not reset, checked out, stashed, discarded, or fast-forwarded.

## 2. Founder ordering constraint

Architect MCP Linux migration is explicitly deferred until the end of the migration sequence, immediately before the final control-plane/cutover stage. The Windows Architect MCP remains the bootstrap/control access path to the Windows VPS while estate audit, data migration, Executive/Division/Hermes/Worker migration, reliability proof, compatibility proof, and production canary work continue.

This ordering supersedes the earlier Batch 9 ordering that placed Architect MCP Linux migration first. Formal task-graph reordering is to be applied during the next planning/disposition step; no Architect MCP migration was started by DIE-100.

## 3. Windows host

- Host: `Variable`
- OS: Microsoft Windows Server 2025 Datacenter, build 26100, x64
- RAM: ~60.1 GB physical
- C: 63.45 GB total, 12.28 GB free
- D: 112 GB total, 84.17 GB free

## 4. Canon and repository state

### GitHub-clean publication source

- Windows staging: `D:\mcp-architect\workspace\muxia-b06-publish`
- branch at DIE-100 start: `main`
- HEAD: `3e09d0c984fc7b313f0cab21f01f302016c17be9`
- clean: yes

### Live Windows DIE

- root: `C:\DIE`
- repository: `https://github.com/kopikonkf/income-os.git`
- branch: `main`
- HEAD: `04eda313f1e757c0d0f8fd9d90251b92c0dd95a3`
- dirty paths: 37
- role: live runtime/reference; preserve until controlled migration/cutover gates

Dirty-path classes observed by name only:
- live state/projection changes under `state/`
- proactive-operator source/runtime additions under `bin/` and `bridge/tests/`
- untracked MUXIA publication tree/docs that already exist cleanly in GitHub main

Top-level physical size under `C:\DIE`:
- `workspaces/`: 533.5 MiB / 5,747 files
- `company/`: 20.5 MiB / 392 files
- `state/`: 2.2 MiB / 565 files
- `bridge/`: 1.8 MiB / 186 files
- `.git/`: 1.7 MiB / 761 files
- remaining source/docs/ops/identity/logs: small relative to the above

`workspaces/` is therefore not a source-canon candidate for bulk migration.

## 5. Estate roots observed

| Root | Evidence | Observed role; no formal DIE-101 disposition yet |
|---|---|---|
| `C:\DIE` | Git repo, live state, runtime MCP source, identities, docs, operator | Primary Windows DIE source/runtime estate |
| `D:\mcp-architect` | Git repo `kopikonkf/mcp-architect`, HEAD `f145796...`, listener 8790, 19 dirty paths all under untracked `workspace/` | Active Architect MCP; keep on Windows until final pre-cutover stage |
| `D:\V2 Proxima` | Git repo `kopikonkf/v2provima`, HEAD `06b9c9b...`, 10 dirty paths under `electron/`, active Electron | Legacy Proxima source/runtime and rollback reference |
| `D:\proximav2-setup` | non-Git, ~3 MiB | Proxima support/provenance artifacts |
| `D:\OAUTH` | Git repo without remote, HEAD `783c1e9...`, dirty 2 docs, listener 8456 | Separate Web-AI multi-provider OAuth adapter; not Division01 runtime |
| `D:\object-asset-engine` | non-Git, 4.118 GiB, active audit process, live SQLite/WAL | Object-centric engine with substantial mutable data |
| `D:\Digital_Income_Empire` | non-Git, 13.6 MiB, docs/execution material | Founder/project provenance candidate |
| `D:\Backup_VPS` | non-Git, 7.859 GiB, dated backup sets | Backup/archive estate; must not be mistaken for live canon |
| `D:\ASSETS` | `MASTER13` plus trailing-space alias entry targeting same location | Filesystem hygiene issue; do not double-count/copy |
| `C:\aether\aether-ai-os` | clean Git repo, HEAD `f84dcc2...`, origin `kopikonkf/aether-ai-os` | Aether estate visible on same host; external to DIE migration unless explicitly reauthorized |
| `D:\aether-bridge` | non-Git, active bridge/forum processes | Protected external Aether bridge/herdr estate; KEEP AS IS / DO NOT MODIFY |
| `D:\aether-identity` | small identity/provenance state | Aether-related external candidate |
| `D:\state-shared` | events JSONL + memory DB, ~0.6 MiB | Aether/shared-state dependency candidate; do not absorb into DIE without disposition proof |

## 6. Large-data decomposition

### Object Asset Engine — 4.118 GiB

- `data/`: 3,063.5 MiB
- `db/`: 1,138 MiB
- `outputs/`: 14.6 MiB
- `reports/`: 0.3 MiB
- source/scripts/state: negligible relative size

Database metadata:
- `object_asset_engine.db`: ~1,111.9 MiB
- `object_asset_engine.db-wal`: ~4 MiB and recently changing
- `seed_library.db`: ~22.1 MiB

An active audit process and `ObjectAssetAuditScale_KeepAlive` scheduled task were observed. This is a live mutable data estate and later migration must be snapshot/quiesce-aware; copying the SQLite DB while live is not acceptable evidence of a consistent migration.

### Proxima — 1.365 GiB source tree

- `node_modules/`: 835.6 MiB
- `.test-userdata/`: 424.5 MiB
- `electron/`: 84.3 MiB
- `.git/`: 44.1 MiB
- actual source/tests/agent files: small by comparison

Separate live Proxima browser/profile root:
- `C:\Users\aethers\AppData\Roaming\proxima`: ~645 MiB

Conclusion for later disposition: package cache/test userdata/browser profile must not be treated as clean source payload.

### Other mutable browser/runtime roots — metadata only

- Hermes local runtime: `C:\Users\aethers\AppData\Local\hermes` ~1,215.7 MiB
- Hermes `income-operator` profile: ~86 MiB / 718 files
- BrowserClaw install/data: ~1,040.3 MiB
- Brave user-data root: ~3,269.8 MiB
- OAUTH `credentials/`: 7 files / 12,192 bytes; values were not read

These are runtime/profile/credential-equivalent roots, not Git source payloads.

## 7. Live writer topology

Observed active writers/process families:

- `C:\DIE\state\EVENTS.jsonl` updated during inventory
- DIE Runtime MCP Executive Windows service active
- DIE Runtime MCP Division01 Windows service active
- Proxima Electron active from `D:\V2 Proxima`
- Proxima web agent process active
- Architect MCP active from `D:\mcp-architect`
- Object Asset Engine audit process active
- Aether gateway/watchdog/bridge/forum processes active but external to DIE

Key state metadata:
- `C:\DIE\state\EVENTS.jsonl`: 315,166 bytes; recently updated
- `C:\DIE\state\projection\.cursor`: 3 bytes
- `C:\DIE\state\projection\EVENTS.jsonl`: 70,716 bytes
- `C:\DIE\state\projection\BRIEFING.md`: 8,193 bytes
- `D:\state-shared\events.jsonl`: 392,569 bytes
- `D:\state-shared\memory.db`: 12,288 bytes

## 8. Relevant Windows services

Metadata-only service inventory observed:

- `DIERuntimeMCPExecutive`: Running / Auto / LocalSystem
- `DIERuntimeMCPDivision01`: Running / Auto / LocalSystem
- `AetherGateway`: Running / Auto / LocalSystem
- `AetherWatchdog`: Running / Auto / LocalSystem
- `AetherCaddy`: Running / Auto / LocalSystem
- `AetherLivingMCP`: Stopped / Auto / LocalSystem
- `AetherSenseWorker`: Stopped / Manual / LocalSystem
- `Cloudflared` service: Stopped / Auto, while a separate cloudflared process was active

No service state was changed.

## 9. Relevant scheduled tasks

Metadata-only task names/actions observed:

- `DIE Wake Brave CDP`
- `Hermes_Gateway`
- `Hermes_Gateway_income-operator`
- `ObjectAssetAuditScale_KeepAlive`
- `AetherBridgeWatch`
- `AetherForum`
- `AetherHerdrStartup`
- other Aether/Jarvis/OpenCode host tasks

Task arguments were intentionally omitted from the inventory.

## 10. Network/listener topology

Key listeners observed:

- `3211` loopback — Proxima Electron provider/session API
- `8501` loopback — `proxima_agent.web`
- `8456` loopback — Web-AI/OAUTH adapter via Uvicorn
- `8790` loopback — Architect MCP
- `8791` loopback — Executive Runtime MCP
- `8792` loopback — Division01 Runtime MCP
- `9010`, `9011` on `0.0.0.0` — BrowserClaw process
- `9110` loopback — BrowserClaw/Executive CDP
- `9333` loopback — Brave/Division01 CDP
- `8700`, `8701`, `8702` on `0.0.0.0` — protected Aether bridge/forum
- `8787`, `8789` loopback — Aether Living/OAuth-edge services
- cloudflared process active on loopback control port

Host-wide bindings are inventory risk flags only. DIE-100 did not alter firewall or listener configuration.

## 11. Current logical-source dispersion

Live `C:\DIE\company` currently contains only:

- `muxia/`
- `schemas/`

The target company canon is therefore not yet physically realized on Windows. Relevant logical components are currently dispersed across:

- `C:\DIE\IDENTITY` — Architect/Executive/Division/Hermes/worker identity files
- `C:\DIE\IDENTITY\hermes-operator\SOUL.md` and `AGENTS.md`
- `C:\DIE\bin` — wake/operator entrypoints
- `C:\DIE\bridge\income_os_bridge` — state, Runtime MCP, projection, gateway-related source
- `C:\DIE\ops\windows` — Runtime MCP/Executive deployment source
- `C:\DIE\docs\atlas\HUMAN_CENTRIC_ATLAS_CANON.md` — human-centric Atlas canon
- `D:\object-asset-engine` — object-centric engine/data
- AppData/runtime roots — mutable principal/browser/Hermes state

This confirms that one-canon migration must be a selective refactor/import, not a directory mirror.

## 12. Explicit boundaries carried forward

- `D:\aether-bridge` and associated Aether Living MCP/herdr are protected external components. No modification.
- `D:\OAUTH` must not be mapped directly to Division01; they are distinct components.
- Proxima personal/non-commercial source remains rollback/provenance reference; MUXIA remains independent implementation.
- browser profiles, cookies, tokens, OAuth credential stores, caches, `node_modules`, `.test-userdata`, nested `.git`, and mutable workspaces are not source-canon payloads.
- Windows remains rollback reference until all cutover gates pass.
- Architect MCP Linux migration is last, not first.

## 13. DIE-100-R1

Exactly one repair child was used: `DIE-100-R1`.

Root cause: two metadata-only PowerShell inventory snippets used a pipeline form incompatible with Windows PowerShell 5.1 `foreach` parsing. Both failed before execution/mutation. The repair child replaced those snippets with array-first PowerShell 5.1-compatible queries. No service, task, repository, runtime, credential, or application state was changed.

## 14. Acceptance

DIE-100 acceptance: PASS_WITH_ONE_REPAIR_CHILD.

Evidence obtained for:
- host/storage
- canonical/live repository state
- candidate estate roots
- large mutable data
- sensitive runtime-root metadata
- active writer topology
- services/tasks
- listeners
- logical-source dispersion
- protected external boundaries
- migration-order constraint

Next atomic task: `DIE-101 — disposition matrix` using the canonical statuses:

`MIGRATE_SOURCE | REBUILD_LINUX | MIGRATE_DATA | ARCHIVE_PROVENANCE | RETIRE_AFTER_CUTOVER | KEEP_EXTERNAL | UNRELATED_EXCLUDE`.
