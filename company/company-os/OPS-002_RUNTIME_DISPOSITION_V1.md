# OPS-002 — Hermes and OpenCode Runtime Disposition v1

Date: 2026-09-18  
Task: `OPS-002`  
Mode: cognition-only disposition; no runtime stop/restart, credential transfer, constitutional mutation, publication, or spend.

## Decision

The Windows Azure legacy copies are retired and are not migration cargo. The surviving Office and H01 runtimes are retained only for their bounded local value; they are not a second deterministic company control plane.

| Runtime / surface | Disposition | Basis |
|---|---|---|
| Azure Hermes D01 | **RETIRE / DO_NOT_MIGRATE** | Founder confirms D01 was replaced by DIE Linux H01. No Azure Hermes profile/state/credentials are required on Office. |
| Azure OpenCode / port 3000 | **RETIRE / DO_NOT_MIGRATE** | MC-011D already sealed Azure `opencode_3000=STOPPED_NO_RESPAWN`; replacement surfaces are live outside Azure. |
| DIE Linux H01 Hermes gateway | **KEEP runtime; DEMOTE control-plane role** | Gateway is live and retains useful provider/channel compatibility, including previously accepted Telegram E2E. It must not become a second deterministic orchestration/control plane beside Mission Control. |
| H01 Hermes Operator-v2 periodic orchestration | **DEMOTE / phase out as duplicate orchestration after authority ratification** | Current scheduler still ticks, but the last durable routing intent remains BLOCKED from 2026-08-31 and the 2026-09-18 receipt snapshot contained no new receipts. Mission Control has already passed MC-008J unattended orchestration acceptance. |
| Windows Office Hermes installation | **KEEP installed utility / compatibility surface** | Founder confirms Hermes is already installed on Office. No Azure cargo import is required. Installation does not grant company control-plane authority. |
| Windows Office shared OpenCode Web `:3000` | **KEEP current shared executor/operator surface** | MC-011D replacement proof records Office local `127.0.0.1:3000` with authenticated/public boundary and runtime owner `aethers`. It is an executor/UI surface, not an orchestration authority. |
| DIE Linux H01 OpenCode | **KEEP bounded worker/executor surface** | H01 Worker-001/OpenCode was previously accepted. OpenCode remains a replaceable executor/provider adapter, not a control plane. |

## External gate resolution

`OPS-002` was blocked on `MC-008J_FINAL_ACCEPTANCE_AVAILABLE`. That gate is now satisfied by Mission Control receipt `MC-008J-fully-unattended-24x7.acceptance.receipt.json`, status `DONE`, decision `FULLY_UNATTENDED_24X7_ACCEPTED`.

The accepted MC-008J evidence covers deterministic intake/progression, leases, bounded failover, independent review, unattended continuity, watchdog/recovery, and zero unauthorized spend/submission/credential mutation.

## Live runtime observations

On 2026-09-18:

- `die-hermes-gateway.service` on H01 was active/running.
- H01 Hermes Operator-v2 still updated its receipt snapshot/routing state, but the only durable routing intent remained `BLOCKED` with last action `2026-08-31T14:00:55Z`.
- `die-opencode-web.service` on H01 was active on `127.0.0.1:3000`.
- The Azure-retirement receipt records legacy Azure OpenCode `:3000` as stopped with no respawn.
- The same retirement receipt records the replacement shared Office OpenCode surface on `127.0.0.1:3000` and the H01 OpenCode authenticated boundary.

These observations support preserving useful channel/executor surfaces while removing the need for duplicate resident orchestration.

## Authority boundary

This disposition does **not** itself amend `CONSTITUTION.md` or transfer the constitutionally named operational-control-plane role. COS-002 already established that such a transfer requires Founder ratification.

Therefore:

1. Mission Control is the mechanically accepted deterministic orchestration/enforcement implementation.
2. Hermes H01 remains available for bounded channel/provider/compatibility value.
3. Hermes must not independently recreate a second task-truth, retry, lease, or company progression authority.
4. OpenCode remains a replaceable worker/executor surface.
5. Azure Hermes/OpenCode are not migration cargo and must not be resurrected merely for parity.
6. No credentials, state DBs, browser sessions, or user profiles are copied from Azure into Office/H01 by OPS-002.

## Acceptance

**PASS.** Unique runtime value is preserved, legacy Azure copies are explicitly retired, and the target topology no longer requires duplicate Hermes/OpenCode migration from Azure. Runtime shutdowns and constitutional authority changes are outside this cognition-only disposition and remain governed by their respective Founder/cutover gates.
