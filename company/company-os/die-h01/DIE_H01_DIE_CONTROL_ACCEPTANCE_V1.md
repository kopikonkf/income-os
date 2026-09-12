# DIE-H01 die-control Windows Control-Plane Acceptance v1

Status: **H01-011 PASS / ACCEPTED FOR DOWNSTREAM CONTROL-PLANE WORK**
Date: 2026-09-12
Scope: inventory and acceptance of the target Windows `die-control` failure domain only. This task does not cut over business scheduling, retire legacy services, deploy H01 Runtime Gateway, or mutate `/srv/die`.

## Acceptance decision

The target Windows control plane satisfies H01-011 acceptance for Mission Control, Universal MCP, DIE State Manager writer-domain bridge/boundary, principal registry, durable Mission Control state, backup/recovery evidence, and network ingress. Canonical dependency `H01-010` was DONE before execution. Founder authorization was active for H01-011 only.

## Mission Control runtime

Observed live on Windows Server 2025:

```text
Mission Control version     0.8.45
listen                      127.0.0.1:8891
health                      HTTP 200 / ok=true
protocol                    mc-mission-v1
runtime release HEAD        0844f813122d390f822ad6dc252cd197178e95f2
runtime script              D:\tmp\mission-control-release-global-0844f81\dist\src\server.js
state directory             D:\MISSION_CONTROL\state
SQLite                      D:\MISSION_CONTROL\state\mission-control.db
```

`/health` reported 165 tasks, 315 checkpoints at the direct probe, 70 reviews, 203 owner attempts and 245 wake records. `/api/mission/status` returned `ok=true`. Subsequent H01-011 checkpoints were durably written after that snapshot, proving the broker-to-SQLite path is live rather than a static health fixture.

The checkout at `D:\MISSION_CONTROL` is not treated as deployment authority. The active process is pinned to the release worktree above. Host-local watchdog/session bindings and operational helper scripts are runtime state, not canonical H01 repository evidence.

## Universal MCP

`MCPUniversal` is Running with Automatic startup. Its live process is `D:\MCP\dist\server.js` on `127.0.0.1:8793`. Local and external health both returned HTTP 200:

```text
name        mcp-universal
version     0.1.0
toolCount   46
scopes      read, write, exec
public MCP  https://universal-mcp.aethers.web.id/mcp
```

This H01-011 session used Universal MCP itself to read/checkpoint Mission Control, query GitHub broker status, and execute through the allowlisted H01 SSH target. GitHub broker reported authenticated account `kopikonkf`; SSH broker exposed one enabled factory target, `die-prod-01`.

## State Manager bridge / writer sovereignty

H01-011 does not invent a second State Manager service. Canon defines DIE State Manager as one logical canonical Company Truth writer with bounded domain adapters. Current executable conformance returned:

```text
status                       PASS
canonical_state_writer       die-state-manager
sole_physical_writer_count   1
unauthorized writers         0
factory adapter              company/factory-asset/lib/factory_state_manager.py
factory writer token         DIE_STATE_MANAGER
```

A separate live scan of deployed Mission Control `src/`, `scripts/` and `config/` found zero references to the audited canonical Company Truth stores/writer entrypoints. Mission Control SQLite therefore remains operational control-plane state and does not silently supersede State Manager sovereignty.

## Principal registry

The live Mission Control endpoint loaded eight configured principals: `chatgpt-architect`, `chatgpt-web-02`, `claude-web-01`, `manus-web-01`, `qwen-studio-01`, `grok-web-01`, `gemini-web-01`, and `qwen-web-01`. Accepted/deferred surfaces remain explicit rather than silently promoted. Ephemeral execution principals may appear in runtime health without changing this configured registry contract.

## Durable state

The live Mission Control SQLite database was opened read-only:

```text
PRAGMA quick_check = ok
journal_mode       = wal
tasks              = 165
task_reviews       = 70
owner_attempts     = 203
wake_queue         = 245
```

The H01-011 row was present as `RUNNING / chatgpt-architect`, and checkpoint IDs 314 and 315 were present in SQLite with the exact summaries previously returned by Mission Protocol.

## Backup and recovery

Six retained pre-v0.8.x Mission Control SQLite snapshots under `D:\MISSION_CONTROL\state` all opened read-only with `PRAGMA quick_check=ok` and contained Mission task schema/history. Recovery is independently proven by `MC-008I`: a real controlled Windows reboot on 2026-09-08 recovered all required runtimes and preserved durable task/review history. Current `Mission Control Runtime Boot` and `Mission Control Runtime Watchdog` Scheduled Tasks remain installed; the watchdog continues with `LastTaskResult=0` and no missed runs.

H01-011 does not claim an arbitrary raw copy of the active WAL database is a valid backup. Application-consistent snapshots / controlled recovery evidence remain the standard.

## Network ingress

Mission Control remains loopback-only on `127.0.0.1:8891`. Public principal ingress terminates through Cloudflare Tunnel to Universal MCP instead of exposing Mission Control SQLite/broker directly:

```text
public hostname   universal-mcp.aethers.web.id
service           http://localhost:8793
external health   HTTPS 200
cloudflared       Running / Automatic
DNS               Cloudflare edge addresses resolved
```

The installed watchdog startup order is Universal MCP -> principals-primary browser -> architect-primary browser -> Qwen Desktop when required -> Mission Control. It is recovery/liveness infrastructure, not a second scheduler.

## Non-actions / cutover boundary

H01-011 performed no business scheduler cutover, H03 rebind, H01 Runtime Gateway deployment, Canonical Feeder start, Supervisor start, legacy service retirement, `/srv/die` mutation, credential/session export, marketplace action, or spend. H01-013, H01-014 and H01-015 become dependency-ready after H01-011 acceptance but remain separate tasks and are not executed here.
