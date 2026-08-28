# DIE-103 — Clean Component Import V1

Date: 2026-08-28
Status: PASS_WITH_ONE_REPAIR_CHILD
Input: `DIE-100`, `DIE-101`, `DIE-102`
Implementation SHA: `0eba02d772a3d19ab1a900d0cfc5c1b9427a2010`

## Purpose

DIE-103 materializes the Chapter #4 one-canon company topology without bulk-copying the Windows estate or creating duplicate active source trees. Existing in-repo runtime source remains referenced through logical ownership boundaries until its dedicated Linux migration task. External sources that must enter Git are imported as bounded, provenance-hashed source snapshots.

No Windows service, task, mutable state, browser profile, credential store, database, or active endpoint is migrated or cut over by this task.

## Materialized company ownership

`company/component-registry-v1.json` now records nine logical components:

- Architect — ownership only; physical source import deferred to `CUT-005 -> MX-053`.
- Executive — ownership boundary over existing identity/Runtime MCP source; no duplicate source copy.
- Division01 — ownership boundary; principal remains `division-head-division01`; OAUTH is not Division01.
- Hermes — ownership boundary over canonical SOUL/AGENTS/operator source; AppData is not copied.
- Workers — ownership boundary over worker identity/contract source.
- Atlas human-centric — canonical document physically moved into `company/atlas/human-centric/` through Git history.
- Atlas object-centric — bounded Object Asset Engine source snapshot imported.
- MUXIA — existing canon retained.
- Web-AI OAuth adapter — provider-neutral tracked core snapshot imported under `company/next-subprojects/`.

## Human-centric Atlas

Canonical path is now:

`company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md`

Operational/current references were updated atomically in company brain, identity docs, runtime canon context, canon-context loader, and tests. Historical inventory/receipt references are not rewritten merely to erase history.

## Object Asset Engine import

Source root: `D:\object-asset-engine` (non-Git live Windows source).

Imported snapshot:

`company/atlas/object-centric/object-asset-engine/source-snapshot/windows-v1/`

Rules:

- 22 syntax-valid Python source files imported.
- source bytes are provenance-hashed in `SOURCE_MANIFEST.json`;
- imported text is normalized to UTF-8/LF and separately hashed;
- `data/`, `db/`, `outputs/`, `reports/`, `state/`, `config.json`, `__pycache__`, `.pyc`, and Windows `.bat` launcher are excluded;
- all imported Object Engine files remain Windows-path-coupled and are explicitly `linux_runnable=false` until `DIE-203` refactors paths/config/runtime;
- no SQLite/database content is present in Git.

One upstream source defect was found and excluded rather than silently repaired:

`D:\object-asset-engine\scripts\audit\gemini_audit_parallel.py`

It contains a Python SyntaxError at line 126 (`f-string expression part cannot include a backslash`). Its source SHA-256 and bytes are recorded in the snapshot manifest. Repair/refactor is deferred to `DIE-203` only if that parallel lane is still required.

## Web-AI OAuth adapter import

Source root: `D:\OAUTH`
Source Git HEAD: `783c1e990c7f77ecdbf5bd2bab8c22be3cae2e49`

Imported snapshot:

`company/next-subprojects/web-ai-oauth-adapter/source-snapshot/core-v1/`

Only six tracked provider-neutral core files are imported:

- package init;
- `core.adapter` contract/types;
- `core.registry`;
- utils package init;
- SSE formatter.

Provider/auth/token/private-web/debug/network-capture code is deliberately excluded from DIE-103. Excluded material includes credentials, provider implementations, auth/token/PoW helpers, debug/live/network-capture scripts, server runtime, research/staging, untracked plugins, logs, and `.git`. It requires separate policy/runtime review before any Linux rebuild. This preserves the DIE-101 fact that OAUTH is a distinct next-subproject without absorbing risky or credential-equivalent implementation details into the main company canon.

## Architect MCP constraint

`company/architect/` exists only as a logical ownership boundary. `D:\mcp-architect` source/runtime was not copied into the DIE repo. Windows Architect MCP remains the active migration control channel. Physical Linux Architect import/deploy remains deferred to `CUT-005 -> MX-053 -> MX-054 -> CUT-006`.

## Validation

Windows/staging:

- component registry JSON: PASS;
- Object Engine provenance: 22/22 PASS;
- OAUTH Git provenance: 6/6 PASS;
- imported Python syntax: 28/28 PASS after excluding the one upstream syntax-invalid file;
- forbidden imported runtime paths: 0;
- high-confidence secret hits: 0;
- old operational Atlas-path references: 0;
- state/workspace mutation from validation: 0;
- full bridge regression: 204/204 PASS.

Linux exact implementation SHA:

- component registry: PASS;
- Atlas canon path: PASS;
- imported Python syntax: 28/28 PASS;
- forbidden imported runtime paths: 0;
- worktree: clean;
- HEAD: `0eba02d772a3d19ab1a900d0cfc5c1b9427a2010`.

Two Python `SyntaxWarning` messages from backslashes in Windows-path docstrings were observed on Linux. They do not invalidate syntax and are consistent with the snapshot's explicit `linux_runnable=false` state.

## Repair child

`DIE-103-R1` is the single repair child. It contains:

- null-safe correction to a metadata-only source-shape scan;
- exclusion and provenance capture of one upstream syntax-invalid Object Engine file;
- removal of test-created `__pycache__` from imported source;
- CRLF-to-LF normalization of imported/generated text plus dual source/imported hashes.

No live Windows source, runtime, database, profile, service, task, or credential state was mutated by the repair child.

## Next

`DIE-104 — One-canon validator` is the next eligible atomic task. It must validate target topology, forbidden paths, ownership registry, source/runtime/config separation, import manifests, and Architect/Aether/OAUTH boundaries fail-closed.
