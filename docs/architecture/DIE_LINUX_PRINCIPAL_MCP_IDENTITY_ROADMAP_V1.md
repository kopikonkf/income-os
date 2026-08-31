# DIE Linux Principal MCP + Identity Roadmap v1

Date: 2026-08-31  
Scope: Executive, Division01, Hermes; Architect remains last.  
Empirical reference: stable Windows runtime plus Linux OE/Operator-v2 improvements.

## 1. Governing decision

Migration preserves **behavioral contracts**, not Windows binaries or path layout. Windows remains the rollback reference until explicit Founder connector handoff. Linux may improve the substrate when it preserves or strengthens principal isolation, authority, continuity, and fail-closed behavior.

Two independent lines are mandatory for Executive and Division01:

```text
WAKE / COGNITION LINE                RUNTIME MCP / STATE LINE
outbound authenticated browser       inbound OAuth-protected MCP
principal-dedicated loopback CDP     principal pinned server-side
persistent continuity thread          context_snapshot + bounded decisions
never Company Truth                   current governed state
```

Wake may trigger cognition but never substitutes for `context_snapshot`. Runtime MCP never becomes a browser/CDP or wake actuator.

## 2. Empirical Windows reference

- Executive wake: BrowserOS neo / BrowserClaw, loopback CDP `:9110`; Runtime MCP `:8791`; principal `chatgpt-plus-executive`; 18 tools.
- Division01 wake: dedicated Brave profile `C:\ProgramData\DIE\BrowserProfiles\DIVISION-01`, loopback CDP `:9333`, health Scheduled Task; Runtime MCP `:8792`; principal `division-head-division01`; 6 tools.
- Division01 wake uses browser in-page backend requests, but it still binds to a persistent ChatGPT `conversation_id`; it is not a hidden non-history state channel.
- Windows Hermes `income-operator` runs gateway plus five cron jobs, including proactive operator every 30 minutes. Its SOUL matches source while runtime AGENTS has evolved as an overlay.
- Windows proactive scheduling is proven, but the observed provider dependency is currently degraded by repeated upstream 404 and must not be copied without classified failure handling.

## 3. Linux improvements to retain

- Executive and Division01 already have isolated Linux browser profiles with dynamic loopback CDP discovered through `DevToolsActivePort`; fixed Windows CDP ports are not required.
- Division01 gains formal OE-001 Signals, OE-002 Demand Score, OE-003 Longtail, OE-004 Worth-Making, and OE-005 Blueprint contracts/engines.
- Executive gains typed Worth-Making and Blueprint review contracts instead of becoming a generic second operator.
- Hermes uses Operator v2 routing/replay/recovery and should route semantic work to stronger Division/Executive cognition rather than absorbing their responsibilities.

## 4. Atomic execution graph

| Task | State | Purpose |
| --- | --- | --- |
| `ID-LNX-000` | DONE | Read-only Windows principal/runtime reference autopsy and receipt |
| `MCP-LNX-001` | DONE | Isolated Executive/Division01 staging MCP services on Linux |
| `MCP-LNX-002` | DONE | `linux-mcp` Cloudflare connector + two-host ingress |
| `COMPANY-INSTANCE-001` | DONE | Formalize sibling DIE-WINDOWS / DIE-LINUX runtime-instance model |
| `IDENTITY-LNX-REKEY-001` | DONE | Create `die-lnx-executive-001` |
| `IDENTITY-LNX-REKEY-002` | DONE | Create `die-lnx-division-001` |
| `IDENTITY-LNX-REKEY-003` | DONE | Rebind Linux staging MCP to Linux-specific principals |
| `IDENTITY-LNX-REKEY-004` | WAITING_OPERATOR_CREDENTIALS | Founder login of NEW dedicated Linux ChatGPT accounts |
| `MCP-LNX-003` | BLOCKED | Dedicated-account OAuth/principal/tool/context E2E parity |
| `WAKE-LNX-001` | BLOCKED | Dynamic-CDP Linux wake transport preserving Windows semantics |
| `WAKE-LNX-002` | BLOCKED | Wake cognition -> fresh principal-pinned state convergence |
| `ID-LNX-001` | DONE | Hermes prompt source pinned to native root -> component AGENTS chain |
| `ID-LNX-002` | READY | Hermes proactive scheduler parity using Operator v2 |
| `ID-LNX-003` | BLOCKED | Executive canonical cognition bootstrap |
| `ID-LNX-004` | BLOCKED | Division01 identity + OE engine cognition bootstrap |
| `ID-LNX-005` | BLOCKED | Cross-principal role/authority acceptance |
| `MCP-LNX-004` | BLOCKED | Restart/session/isolation/stability proof |
| `MCP-LNX-005` | BLOCKED | Executive + Division01 Linux MCP/wake acceptance |

`CUT-004A` and `CUT-004B` additionally depend on `MCP-LNX-005`. Therefore a Linux staging PASS cannot silently become connector cutover. Founder handoff remains a later explicit action.

## 5. Identity responsibilities

### Hermes
24/7 operational orchestrator, scheduler, anti-macet router, worker controller and recovery owner. It asks *who needs to think now?* and routes cognition; it does not become the Division intelligence engine or Executive reviewer.

### Division01
Domain intelligence owner for digital assets: seed/context retrieval, platform/search evidence, opportunity signals, demand scoring, longtail generation, Worth-Making judgment, platform-fit reasoning and production blueprint authorship. It cannot execute workers, submit marketplaces, spend, or mutate canon directly.

### Executive
Company/portfolio strategic intelligence and adversarial reviewer. It challenges opportunity quality, reviews Worth-Making/Blueprint capability when contractually required, compares cross-division tradeoffs, requests audits and escalates Founder-level decisions. It does not command workers or replace Division01 authorship.

### Architect
DEV/control plane only. Existing graph ordering remains: non-Architect cutover through `CUT-005` first, then `MX-053`, `MX-054`, and Founder `CUT-006`. Architect migration is intentionally last.

## 6. Cloudflare staging boundary

Staging domains already reserved: `executive-mcp.aethers.biz.id` and `division01-mcp.aethers.biz.id`. Tunnel `linux-mcp` exists but has no active connector. Linux staging ports `8891/8892` were observed free. Windows tunnel `aethers` and its `*.aethers.web.id` production endpoints remain untouched. Browser CDP and wake endpoints must never be routed through Cloudflare.

## 7. Parallelism with MX-062

MX-062 remains immutable on Linux source commit `dfb74d7e09b19f68381e1064899d70c645a61f26`. Roadmap/source work occurs in isolated Windows worktrees. Staging MCP may use separate service/config/runtime state without pulling/rebuilding/restarting the active MX-062 source tree or service.

## 8. Standing execution order

```text
ID-LNX-000 DONE
   |
   +--> MCP-LNX-001 -> 002 -> 003 -> WAKE-LNX-002 -> ID-LNX-003/004
   |                         ^              ^
   +--> WAKE-LNX-001 --------+              |
   |                                        |
   +--> ID-LNX-001 -> ID-LNX-002 -----------+
                                            |
                                      ID-LNX-005
                                            |
                                      MCP-LNX-004
                                            |
                                      MCP-LNX-005
                                            |
                               CUT-004A / CUT-004B
                                            |
                                          CUT-005
                                            |
                                MX-053 -> MX-054 -> CUT-006
```


## 9. Company-instance re-key amendment

Windows and Linux no longer share Executive/Division01 principal IDs. Windows retains `chatgpt-plus-executive` and `division-head-division01`; Linux uses `die-lnx-executive-001` and `die-lnx-division-001`. The semantic role documents remain shared. `MCP-LNX-003` and `WAKE-LNX-001` are gated by `IDENTITY-LNX-REKEY-004`, because real ChatGPT-cloud proof must use NEW Linux-dedicated external accounts rather than the existing Windows accounts.
