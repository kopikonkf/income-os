# COS-001 — Windows Host-Exit Dependency & Survivability Map v1

Status: ACCEPTED / READ-ONLY INVENTORY
Observed: 2026-09-08
Founder planning horizon: approximately 21 days remaining on the current Windows VPS.
Planning T-0: approximately 2026-09-29 if the 21-day observation remains exact.
Operational objective: complete authoritative cutover by **T-3** (approximately 2026-09-26), preserving roughly 72 hours for rollback observation before T-0.

Authority: subordinate to `CONSTITUTION.md`, the canonical Chapter #4 / Mission Control graphs, and Founder gates. This artifact authorizes no cutover, service stop, credential transfer, spend, DNS mutation, or Aether mutation.

## 1. Executive decision

The current Windows VPS cannot be retired safely by cloning the machine or copying `D:` wholesale. The estate contains four different state classes that require different treatment:

1. **Reconstructible source/runtime** — rebuild from canonical Git and pinned installers on the target host.
2. **Durable operational state** — migrate using quiescent or application-consistent snapshots with hashes/counts/integrity checks.
3. **Machine/account-bound authentication** — reprovision or manually reauthenticate; do not bulk-copy browser profiles, cookies, OAuth/session bytes, tokens, or credentials.
4. **Legacy/external estates** — retire only after accepted replacement, or keep external with an independent migration owner.

Canonical target topology is already defined by Mission Control planning:

```text
Global control plane
  Mission Control + Universal MCP + primary browser workforce + H03 Architect
  -> REBUILD/MIGRATE to new H03 Windows VPS

Holding H01 execution
  Executive/Division/Hermes/MUXIA/Factory + H01 Architect
  -> remain/complete cutover on H01 Linux

Aether
  -> KEEP_EXTERNAL; must have its own survivability plan before old VPS retirement
```

The old Windows VPS remains rollback authority until each corresponding acceptance gate passes. No component is considered migrated merely because a replacement process exists.

## 2. Live evidence snapshot

Observed live on the current Windows host (`Windows Server 2025 Datacenter`, boot `2026-09-08 16:06:53`):

| Surface | Live evidence |
|---|---|
| Windows Architect MCP | `127.0.0.1:8790`, `mcp-architect` v0.1.2, 31 tools |
| Executive Runtime MCP | `127.0.0.1:8791`, v1.1.0, 18 tools |
| Division01 Runtime MCP | `127.0.0.1:8792`, v1.1.0, 6 tools |
| Universal MCP | `127.0.0.1:8793`, v0.1.0, 45 tools |
| Grok relay | `127.0.0.1:8794`, healthy |
| Mission Control | `127.0.0.1:8891`, v0.8.15 |
| Division01 Brave | CDP `127.0.0.1:9333`, interactive Session 2 |
| Primary principals Brave | CDP `127.0.0.1:9444`, interactive Session 2 |
| Architect-primary Brave | CDP `127.0.0.1:9555`, interactive Session 2 |
| Qwen Desktop | CDP `127.0.0.1:9666`, interactive Session 2 |
| Cloudflared | Windows service, Automatic, LocalSystem; metrics `127.0.0.1:20120` healthy |
| Aether Gateway/Senses | `127.0.0.1:8000`, v0.19.2 healthy |
| Aether Living MCP | `:8787` not listening during this audit |

Approximate live storage observations (informational, not migration manifests):

| Root | Files | Approx bytes | Interpretation |
|---|---:|---:|---|
| `D:\MISSION_CONTROL\state` | 10,011 | 95,138,683 | durable control-plane state + caches/dispatch |
| `D:\MISSION_CONTROL\browser-profiles\principals-primary` | 5,469 | 545,106,148 | machine/account-bound browser state; do not clone as migration strategy |
| `D:\MISSION_CONTROL\browser-profiles\architect-primary` | 1,221 | 197,442,377 | machine/account-bound browser state; do not clone as migration strategy |
| `D:\MCP` | 2,842 | 57,771,027 | Universal source/runtime plus durable state |
| `D:\mcp-architect` | 114,823 | 5,166,147,129 | dirty source + worktree/artifact farm; must not be bulk-migrated |
| `C:\ProgramData\DIE\BrowserProfiles\DIVISION-01` | 1,688 | 197,369,625 | legacy Windows browser session; replacement already staged on Linux |
| `C:\aether\aether-ai-os` | 22,795 | 619,945,905 | Aether external Git estate |
| `C:\ProgramData\Aether` | 971 | 670,668,027 | Aether external mutable estate |

## 3. Classification matrix

`Target deadline` is relative to the current host T-0. `T-3` is the desired end of authoritative cutover; T-0 is not an acceptable first-cutover date.

| Dependency | Class | Target | Target deadline | Required migration/rebuild treatment | Rollback | Acceptance evidence / gate |
|---|---|---|---|---|---|---|
| Mission Control code/runtime | **REBUILD** | H03 new Windows VPS | stage T-10; authority T-3 | Fresh clone canonical `mission-control`; pinned Node/dependencies; build/test; reconstruct service/task definitions. Do not copy dirty live worktree as source authority. | Current Windows MC remains authoritative until cutover acceptance. | `MC-010P1/P2/P3 -> MC-010A -> MC-010B`; version/health, regression, restart/watchdog, unattended-path evidence. |
| Mission Control durable DB/state | **MIGRATE** | H03 | rehearsal T-5; final T-3 | Application-consistent SQLite snapshot after controlled quiesce/checkpoint; copy only disposition-approved durable state. Preserve source commit/time and hashes. Canonical-source cache may be rebuilt; authoritative DB/event/writeback state must be explicitly classified. | Preserve immutable pre-cutover snapshot on old VPS; do not resume two writers against one canonical state. | SQLite `quick_check`, schema/version, row counts/max event IDs, task/lease/review continuity, hashes, successful H03 boot. |
| MC `principals-primary` browser workforce | **REAUTH** | H03 | T-5 | Rebuild browser profile directory empty; install canonical Brave; manually authenticate provider accounts. Do **not** copy cookies/session/profile bytes as migration strategy. | Old profile stays intact/read-only rollback until H03 composer-level acceptance. | CDP health, exactly one root/profile, authenticated composer checks, principal READY/DEFERRED honesty. |
| MC `architect-primary` browser profile | **REAUTH** | H03 | T-5 | Fresh profile + manual ChatGPT authentication; no profile-byte clone. | Old architect-primary stays available until H03 accepted. | CDP health + composer-level auth + Architect workflow canary. |
| Qwen Desktop principal | **REBUILD + REAUTH** | H03 | T-5 | Install/pin Qwen Desktop, enable loopback CDP, authenticate manually. Do not migrate app/session store as authority. | Current Session-2 Qwen remains rollback. | `:9666` CDP, correct model/surface readiness, bounded marker canary. |
| Windows Runtime Watchdog / Boot / Interactive handoff tasks | **REBUILD** | H03 | T-5 | Recreate from canonical Mission Control scripts; use H03 user/service identities, not exported Task Scheduler credentials. | Old watchdog continues controlling only old host until authority switches. | Cold boot + watchdog recovery + correct interactive-session ownership + no duplicate roots. |
| Universal MCP source/runtime | **REBUILD** | H03 | T-7 | Fresh clone `D:\MCP` equivalent on H03; build; recreate service/tunnel integration from canonical config. | Current `:8793` remains canonical until cloud E2E passes. | health/fingerprint/tool parity; local + external MCP connector test; service restart proof. |
| Universal MCP `state\memory.db` | **MIGRATE** | H03 | rehearsal T-5; final T-3 | Treat as durable continuity state: quiescent SQLite backup/checkpoint; hash + integrity + logical count verification. | Keep pre-cutover immutable source DB; one writer after cutover. | `quick_check`, hash, logical row/count parity, read/write canary on H03. |
| Universal MCP OAuth / connector authorization state | **REAUTH** | H03 | T-5 | Re-register/re-authorize connectors on H03. Do not blindly copy `oauth.json`, private keys, tokens, or machine-bound auth bytes. | Existing Windows authorization stays active until H03 cloud E2E. | OAuth/DCR flow, unauthorized fail-closed, ChatGPT/connector tool call from user context. |
| Windows Architect MCP runtime (`:8790`) | **REBUILD**, then old runtime **RETIRE** | H03 Architect + H01 holding-local Architect | source reconciliation T-14; target acceptance T-3 | Build H03 from canonical `mcp-architect`; H01 remains holding-local executor. Old `D:\mcp-architect` is dirty and origin-divergent: canonicalize required source or preserve explicit patch/receipt before retirement; do not copy the 5+ GB worktree farm. | Old `:8790` remains break-glass/control until MC runtime resolver + H03 cutover acceptance. | `MC-009A..L`, H01 local-executor proof, H03 Architect parity, `MC-010B`; no unpublished required code remains. |
| `D:\mcp-architect\workspace` / engineering worktree farm | **RETIRE** (selective evidence only) | Git canon + explicit receipts | T-7 | Do not bulk-migrate worktrees, node_modules, logs, caches, temporary patches. Promote required code to canonical repos; preserve only explicitly required receipts/patches with hashes/provenance. Ensure engineering leases are quiescent/expired cleanly before host retirement. | Old disk retained during rollback window. | Inventory proves no unpublished required implementation/config remains; no active lease references old host-only state. |
| Grok local relay `:8794` | **REBUILD** if still required; otherwise retire via disposition | H03 | decision T-7; build T-5 | Recreate from canonical/sanitized source and provider configuration only if a surviving consumer still requires it. Do not make it a hidden dependency of MC. | Current relay retained until dependent OpenCode/provider path is accepted or retired. | `OPS-002` disposition + health/consumer canary if retained. |
| Cloudflared service / global control-plane ingress | **REBUILD + REAUTH** | H03 | stage T-5; route switch T-3 | Install fresh cloudflared/service. Reprovision tunnel authorization from Cloudflare-managed authority rather than copying credential material. Rebind only after local H03 health/parity. | Existing tunnel remains serving old origins until individual route switch accepted. | metrics healthy; external `/health`/MCP OAuth/security probes; deterministic hostname->single-host routing; rollback route documented. |
| `universal-mcp.aethers.web.id` | **MIGRATE** route | H03 Universal MCP | T-3 | Point ingress to accepted H03 Universal only. | Re-point to old origin while rollback host exists. | External MCP tool E2E + identity fingerprint. |
| `mcp.aethers.web.id` legacy Architect route | **RETIRE** legacy route after successor naming/cutover | H03/H01 namespaced Architect endpoints | T-3 | Replace generic legacy route with canonical holding/runtime endpoint model from MC-009; retain alias only if explicitly required for rollback compatibility. | Old alias -> old `:8790` during rollback. | MC-009 endpoint resolver/ingress acceptance + H03/H01 connector E2E. |
| Executive Windows Runtime MCP `:8791` + `executive-mcp.aethers.web.id` | **RETIRE** Windows; Linux endpoint completes handoff | H01 Linux | T-7 preferred, no later T-3 | Linux Executive runtime is already DONE/PASS locally. Complete public connector handoff; fresh Linux auth already canonical. No Windows profile clone. | Windows 8791 remains rollback until connector cloud parity. | `CUT-004A` then `CUT-004/CUT-005`; cloud tool parity and rollback proof. |
| Division01 Windows Runtime MCP `:8792` + Brave `:9333` + public route | **RETIRE** Windows; Linux endpoint completes handoff | H01 Linux | T-7 preferred, no later T-3 | Linux Division01 runtime is already DONE/PASS locally with fresh auth. Complete public connector handoff. | Windows runtime/profile remains rollback until connector parity. | `CUT-004B` then `CUT-004/CUT-005`; cloud tool parity and rollback proof. |
| Windows Hermes gateway tasks | **RETIRE** Windows | H01 Linux Hermes | T-7 | H01 Hermes migration is canonical DONE; do not migrate Windows Hermes profile/state/credentials. Future Hermes role may be reduced separately by `OPS-002`. | Linux Hermes already proven; old Windows task remains only until cutover graph permits disable. | `DIE-202/DIE-204` standing + `CUT-004/CUT-005`; later `OPS-002` role disposition. |
| Windows OpenCode Web Serve / OpenCodeBridge | **RETIRE** resident Windows copies | H01 Linux ephemeral Worker-001 / future pooled executor | T-7 | Do not carry resident Windows worker daemon merely for parity. Preserve only unique required source/config through Git; H01 OpenCode Worker-001 already canonical DONE. | Re-enable old task only inside rollback window if a proven unique dependency remains. | `DIE-202/DIE-204`; `OPS-002` confirms no unique company-control function remains. |
| Live dirty `C:\DIE` source/state | **MIGRATE** approved state; source **REBUILD** from Git | H01 / canonical Git | freeze/sync path by T-7; final by T-3 | Never clone dirty tree. Existing `CUT-001 -> CUT-003` governs final writer freeze/state sync/restore. Any unpublished required source must be promoted separately or explicitly retired. | Old frozen source/data snapshot retained through rollback. | `CUT-001/002/003`, hashes/counts/cursors/open-job/artifact lineage; clean canonical source on target. |
| Aether source `C:\aether\aether-ai-os` | **KEEP_EXTERNAL** | Aether-owned successor host/plan | owner plan required by T-10; resolved before T-3 | COS does not migrate or mutate Aether. Source is currently Git-clean and DNA integrity was separately observed PASS; use Aether's own governed migration plan. | Current Aether host remains until its own acceptance. | Aether-owned integrity/startup/senses/governance acceptance. Old VPS cannot be retired while Aether remains host-critical. |
| Aether mutable estate (`C:\ProgramData\Aether`, `D:\aether-bridge`, `D:\aether-identity`, `D:\state-shared`) | **KEEP_EXTERNAL** | Aether-owned successor | owner plan required by T-10; resolved before T-3 | No DIE bulk copy/absorption. Classify Aether canonical memory/state independently with quiescent/hash receipts where appropriate. | Current estate untouched by COS. | Aether migration receipt; no DIE symlink/dependency absorption. |
| `aethers.my.id`, `aethers.biz.id`, `aethers.web.id`, `jarvis.aethers.my.id` routes | **KEEP_EXTERNAL** | External/Aether/web owner | route owner decision T-10; resolved T-3 | These routes currently share the old Windows Cloudflare tunnel. They must be rehomed or explicitly retired by their owning project even though they are not DIE control-plane authority. | Existing route continues until owner accepts replacement. | Owner-specific external health + DNS/tunnel evidence. |
| `oc.aethers.my.id` | **RETIRE** unless `OPS-002` proves retained value | H01/H03 only if explicitly retained | decision T-7 | Current OpenCode web surface must not keep the old VPS alive by accident. | Existing route through rollback window. | `OPS-002` disposition; if retained, fresh rebuild + health/auth proof. |

## 4. Cloudflare route dependency map

The current single Windows Cloudflare tunnel routes at least these hostnames from the old VPS:

```text
universal-mcp.aethers.web.id -> localhost:8793
executive-mcp.aethers.web.id -> localhost:8791
division01-mcp.aethers.web.id -> localhost:8792
mcp.aethers.web.id -> localhost:8790

aethers.my.id / www -> localhost:8080
aethers.biz.id / www -> localhost:8080
aethers.web.id / www -> localhost:8080
oc.aethers.my.id -> localhost:3000
jarvis.aethers.my.id -> localhost:8010
```

Therefore old-host retirement is a **route ownership problem**, not only a process migration problem. Every hostname must have an accepted new origin or an explicit retirement decision before the old tunnel is removed.

## 5. Non-reconstructible / high-attention state

### Mission Control

`D:\MISSION_CONTROL\state` contains the authoritative SQLite DB plus active WAL/SHM, canonical writeback records, dispatch receipts and soak evidence. It must use an application-consistent snapshot; raw copying while writers are active is not sufficient acceptance.

### Universal MCP

`D:\MCP\state\memory.db` is continuity-bearing data and should receive SQLite integrity/hash/count treatment. OAuth authorization state is **not** in the same migration class: it must be reprovisioned/re-authorized rather than treated as ordinary database cargo.

### Windows Architect

`D:\mcp-architect` is the largest migration hygiene risk observed in this task. It is approximately 5.17 GB, has tracked modifications, untracked generated/runtime/worktree content, and its local HEAD is not equal to current `origin/main`. The host cannot be retired until all required implementation/configuration is either:

- canonicalized into the appropriate Git repository,
- preserved as an explicit bounded patch/receipt with provenance, or
- explicitly declared disposable.

No blanket directory copy is accepted as remediation.

### Live `C:\DIE`

The tree remains intentionally dirty and must not be reset/stashed/cleaned by this program. Final state movement remains governed by `CUT-001 -> CUT-003`. Source authority comes from Git, not from copying the live dirty tree.

## 6. Hard blockers to a safe host exit

1. **H03 is not yet provisioned.** `MC-010P1` remains blocked awaiting new-VPS connection/runtime details.
2. **MC-008J must complete honestly.** H03 control-plane migration acceptance depends on accepted unattended runtime, not merely process health.
3. **MC-009 runtime/holding resolver chain is blocked behind MC-008J.** H01/H03 Architect endpoint identity and local-executor convergence must land before legacy Windows Architect retirement.
4. **Legacy Chapter #4 cutover chain remains blocked.** `CUT-001/002/003`, `CUT-004A/B`, `CUT-004`, `CUT-005`, and `CUT-006` are not complete.
5. **Executive and Division01 cloud connectors still terminate on Windows endpoints.** Linux runtimes are locally accepted but public/cloud handoff remains undone.
6. **`D:\mcp-architect` has unpublished/dirty material.** Required code/config must be reconciled before retirement.
7. **`C:\DIE` remains a dirty live state/source estate.** It requires governed final state freeze/sync rather than host cloning.
8. **Aether remains external but co-resident on this VPS.** DIE cannot declare the host disposable until the Aether owner separately rehomes or retires its host-critical services/routes/state.
9. **Cloudflare ingress is centralized on the old Windows host.** All listed hostnames require new-origin or retirement evidence.

## 7. 21-day execution clock

The dates below are planning targets derived from the Founder-observed 21-day remaining life, not provider billing guarantees.

### T-21 to T-15 — now through ~2026-09-14

- Complete this inventory and keep it canonical.
- Finish MC-008J soak/final acceptance.
- Reconcile `D:\mcp-architect` unpublished required implementation/config.
- Finish company-level `COS-002` control-plane authority reconciliation and `COS-003` Aether-DIE bridge design.
- Founder supplies H03 VPS details early enough to open `MC-010P1`.

### T-14 to T-10 — ~2026-09-15 to 2026-09-19

- `MC-010P1/P2`: H03 OS/storage baseline + reproducible base tooling.
- Create Aether-owned host-exit plan or explicit decision so Aether cannot become a T-0 surprise blocker.
- Drive MC-009 H01/H03 Architect/runtime convergence as dependencies open.
- Resolve Executive/Division public connector handoff prerequisites.

### T-9 to T-7 — ~2026-09-20 to 2026-09-22

- `MC-010P3`: clean-clone H03 staging.
- Build/test Mission Control, Universal MCP, H03 Architect and browser definitions without authority switch.
- Complete/accept H01 connector transitions and retire unnecessary resident Windows Hermes/OpenCode dependencies when canonical gates permit.
- Perform first dry-run durable-state backup/restore validation.

### T-6 to T-5 — ~2026-09-23 to 2026-09-24

- Manual H03 browser/Qwen reauthentication.
- H03 Universal/Architect connector authorization.
- External ingress shadow probes.
- Cold-boot/watchdog/session handoff proof on H03.

### T-4 to T-3 — ~2026-09-25 to 2026-09-26

- Controlled final Mission Control/Universal durable-state synchronization with single-writer fencing.
- Execute `MC-010A/B` acceptance when dependencies are satisfied.
- Switch global control-plane ingress to H03 one route at a time.
- Confirm H01 remains independently controllable through holding-local execution.
- Confirm old Windows VPS has no unpublished code/config or unique authoritative runtime remaining.

### T-2 to T-1 — ~2026-09-27 to 2026-09-28

- Rollback observation window: no new dependency may be introduced onto old Windows.
- Verify external connectors, watchdog recovery, canonical writeback, principal auth honesty, state continuity and H01 operations.
- Rehome/retire all external Aether/web/OpenCode routes still attached to old cloudflared.

### T-0 — ~2026-09-29

Old Windows VPS may be retired only if all retirement gates below are green. Otherwise the correct action is to extend/renew the host or provision temporary overlap capacity; silent forced retirement is not accepted.

## 8. Retirement gates

The old Windows VPS is `RETIRE_READY` only when all are true:

- H03 Mission Control + Universal + primary browsers + H03 Architect accepted and restart-safe.
- Mission Control durable state is migrated with integrity/continuity evidence and exactly one canonical writer.
- H01 production/execution remains healthy independently of the old Windows host.
- Executive/Division public connectors no longer require Windows 8791/8792.
- Windows Architect 8790 is no longer a unique required control channel.
- No active engineering lease or unreconciled required source/config exists only under `D:\mcp-architect`, `C:\DIE`, or other old-host worktrees.
- All Cloudflare hostnames have an accepted new origin or explicit retirement decision.
- Browser/Qwen credentials were reprovisioned/reauthed; no migration depends on copied cookie/token/session bytes.
- Aether external estate has its own accepted disposition and no host-critical Aether service/state remains stranded.
- A sanitized host-exit receipt records source/target identities, final hashes/counts, external route status, rollback state and authority decision.

## 9. Parallel work contract

This map explicitly supports three concurrent lanes:

```text
Lane A — Company/Orchestration
  COS-002, COS-003, host-exit governance, H03 preparation coordination

Lane B — H01 Linux engineering
  Chapter #4 / Factory / MUXIA / connector and local-executor work

Lane C — Mission Control
  MC-008J soak and then MC-009/MC-010 as dependencies open
```

The lanes may execute concurrently on disjoint tasks/resources. Remote `income-os` publication remains serialized by the shared `income-os.repo-write` engineering lease. Live `C:\DIE` and live production H01 remain protected by their existing graph rules.

## 10. COS-001 acceptance decision

**PASS.** Every company-critical Windows dependency discovered in the bounded audit has a migration class, target, deadline, rollback rule and evidence requirement. No runtime cutover, service stop, credential/session extraction, DNS change, spend, or Aether mutation occurred.

The next company-level READY nodes remain `COS-002` and `COS-003`. The highest time-risk external dependency is provisioning H03 early enough to start `MC-010P1` while at least one week of old-host rollback capacity remains.
