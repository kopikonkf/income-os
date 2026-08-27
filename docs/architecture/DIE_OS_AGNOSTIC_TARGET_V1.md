# DIE OS-AGNOSTIC TARGET V1

Status: NORTHBOUND CANON / NO PHYSICAL MIGRATION AUTHORIZED
Date: 2026-08-26
Owner: Founder Dee

## Intent

After the Proxima -> MUXIA migration proves its runtime contract, DIE will progressively stop encoding company architecture as machine-specific drive paths and instead organize major capabilities as replaceable logical subprojects under one company topology.

This document records the target shape only. It does not authorize moving live repositories, browser profiles, services, credentials, runtime state, or identities.

## Target logical topology

```text
DIE_ROOT/
|
+-- docs/
|   +-- architecture/
|   +-- operations/
|   +-- missions/
|
+-- company/
|   +-- architect/          # current external source: D:\mcp-architect
|   +-- executive/          # current runtime concept: BrowserOS neo / Executive lane
|   +-- atlas/
|   |   +-- human-centric/
|   |   +-- object-centric/ # current external source: D:\object-asset-engine
|   |
|   +-- muxia/
|   |   +-- muxia-task-graph-v1.json
|   |
|   +-- division/
|   |   +-- division001/
|   |   +-- division002/
|   |   +-- ...
|   |   +-- division100/
|   |
|   +-- die-agents/
|   |   +-- sub-agent-a/
|   |   +-- sub-agent-b/
|   |   +-- ...
|   |   +-- sub-agent-z/
|   |
|   +-- workers/
|   +-- next-subprojects/
|
+-- LASTSTANDINGPOINT.md
```

`DIE_ROOT` is a logical root. Current Windows deployment remains `C:\DIE`; future Linux deployment may use another configured root. No code should depend on the literal root when an OS-agnostic configuration/registry can be used.

## Locked interpretation

1. `company/*` is a logical ownership/registry boundary, not proof that every external repository must become a Git subdirectory or monorepo immediately.
2. Existing repositories such as `D:\mcp-architect`, `D:\object-asset-engine`, Proxima/MUXIA source, and `D:\OAUTH` remain in place until a dedicated migration ADR defines `MOVE | MIRROR | SUBMODULE | PACKAGE | SERVICE | RETIRE` for each.
3. MUXIA is the first concrete OS-agnostic migration proving the pattern.
4. `atlas` is reserved as a first-class company capability; Founder will provide its fuller semantic/runtime definition later. Current distinction is `human-centric` and `object-centric`.
5. `die-agents` and `workers` are separate concepts: agents may own cognition/session lifecycle; workers execute bounded jobs under contracts.
6. Physical machine, OS, model provider, browser provider, and agent harness remain replaceable implementation details behind logical capability boundaries.
7. Cross-node communication will be designed through explicit protocols/registries rather than raw assumptions about `C:\`, `D:\`, or a particular VPS hostname.
8. Existing live identity `division-head-division01` is not silently renamed to `division001`. Naming/identity migration requires a separate ADR because identity IDs are referenced by Runtime MCP, state, receipts, and governance.

## Sequence rule

The broad OS-agnostic migration does not start as a simultaneous repository reshuffle.

Sequence:

`Proxima baseline -> MUXIA parity/refactor -> Linux proof -> MUXIA cutover decision -> inventory other external subprojects -> one-by-one migration ADRs -> company topology materialization`.

This prevents a large filesystem reorganization from becoming entangled with the currently proven production primitive.

## First proof vehicle

MUXIA is the first proof that a Windows/Electron-coupled capability can become:

- path-configurable;
- OS-neutral at the core;
- Linux-runnable;
- profile/session-state explicit;
- controlled by stable logical interfaces rather than desktop placement.

A successful MUXIA migration establishes the template for later Architect, Atlas, Division, Agent, and Worker refactors.

---

## 2026-08-27 — Chapter #4 migration authorization overlay

The original `NO PHYSICAL MIGRATION AUTHORIZED` status and sequence rule above are historical pre-authorization constraints. Founder subsequently authorized the Chapter #4 Windows-to-Linux refactor/migration under explicit rollback, evidence, and cutover gates.

The operative migration decision layer is now `docs/migration/DIE_WINDOWS_ESTATE_DISPOSITION_MATRIX_V1.md` plus `company/muxia-task-graph-v1.json`. This authorization does **not** permit bulk mirroring: source, mutable data, secrets/config, installed runtimes, browser profiles, provenance, and protected external estates remain separated by disposition.

Additional locked ordering: Windows Architect MCP remains the active Windows control/bootstrap channel through all Windows-dependent migration and non-Architect cutover work. Linux Architect MCP is built/proven only after `CUT-005`, and the actual Architect control-channel handoff is `CUT-006` under explicit Founder action.