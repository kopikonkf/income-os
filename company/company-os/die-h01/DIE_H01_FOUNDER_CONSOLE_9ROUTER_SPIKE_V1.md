# DIE H01 Founder Console / 9router Architecture Spike v1

**Task:** H01-140  
**Date:** 2026-09-13  
**Status:** ACCEPTANCE CANDIDATE  
**Scope:** Architecture + bounded read-only shell only. No production cutover.

## 1. Canon reconciliation

Current H01 canon is explicit: `die-control` is the separate global Mission Control/control plane and H01 is a Linux execution plane. Mission Control owns durable work truth, scheduling, leases and authority. H01-local browser/session/runtime details remain local. Existing legacy `/srv/die` and localhost:8876 remain rollback/live until a separately accepted cutover.

H01-114 and H01-134 are DONE. H01-140 is therefore dependency-eligible. H01-108 is outside this spike and remains immutable.

The earlier `H01-140-CHROME-RESEARCH.txt` was read as research input only. Its conclusions were independently reconciled against current upstream and current H01 canon.

## 2. Upstream 9router audit

Audited upstream: `decolua/9router`.

- audited version: `0.5.75`
- audited commit: `17c4cc76877bd1755030a8414f8d0083f48dcccf`
- license: MIT; retain upstream copyright/license notices in any derivative
- application: Next.js App Router + React/TypeScript
- persistence: SQLite/Prisma plus direct SQLite/runtime caches in current architecture
- upstream responsibility: provider account/OAuth/API-key management, routing, OpenAI/Anthropic-compatible proxy endpoints, usage/quota/logging, dashboard/settings
- default HTTP port: 20128

This is materially more than a visual dashboard. Running the upstream application wholesale would introduce a second provider/routing authority surface next to DIE, which violates H01 V2 control-plane boundaries.

### Security posture

9router has had multiple 2026 advisories in exactly the surfaces DIE would otherwise expose: reverse-proxy locality/authentication bypass, Host/header-based proxy bypass, `/codex` authorization bypass, MCP-plugin command execution, SSRF, settings authorization downgrade and login-rate-limit bypass. Current 0.5.75 is newer than the affected ranges for several earlier advisories, but upstream still has a broad privileged surface and the repository currently has no SECURITY.md policy. One reviewed OIDC-test SSRF advisory is still listed without a patched version in the GitHub advisory database.

Therefore H01-140 does **not** connect 9router provider accounts, expose upstream `/v1` proxy APIs, import BYOK secrets, register MCP plugins, or place a raw 9router runtime behind a public reverse proxy.

Security invariant for any future edge: strip all inbound `X-9r-*` trust/locality headers; establish trust from the reverse-proxy transport; fail closed; never infer Founder/Mission authority from 9router locality or provider connectivity.

## 3. Fork-vs-adapter decision

**Decision: HYBRID — thin presentation fork + DIE read-only adapter.**

Not a full runtime fork and not an unmodified upstream adapter deployment.

```text
Founder browser
      |
      v
DIE reverse proxy / Founder auth
      |
      v
Founder Console BODY
(9router-derived layout/components/navigation only)
      |
      v
DIE read-only adapter
      |
      +--> Mission Control read model
      +--> H01 production/QC/package read models
      +--> Brave/provider health inventory
      +--> demand intelligence

Mission Control = BRAIN / authority
9router-derived UI = BODY only
```

Why not pure adapter to unmodified 9router: upstream server routes retain provider credentials, proxy, settings and mutation semantics that DIE does not need for Founder Console. Hiding menu items is not a security boundary.

Why not deep fork: it would create needless divergence from a fast-moving upstream. Only presentation primitives/navigation should be vendored/forked. DIE data, authority and actions stay in independent adapter contracts.

## 4. Minimal-divergence update plan

1. Pin an audited upstream tag/SHA; never float on `latest`.
2. Maintain a dedicated upstream remote in the future Founder Console repository.
3. Keep DIE changes under isolated Founder Console routes/components and `/api/die/v1/*`; do not patch provider adapter internals.
4. Do not ship upstream provider proxy/OAuth/MCP/plugin routes in the Founder Console deployment target.
5. For each update: fetch upstream -> security/advisory review -> diff presentation files -> rebase/cherry-pick UI changes -> run contract/build tests -> manual Founder visual review -> advance the pin.
6. Maintain a small patch ledger recording upstream SHA, DIE patch list and rejected upstream changes.
7. If an upstream UI change requires importing provider-runtime authority, reject it or reimplement the visual primitive locally.

Target divergence metric: presentation-only delta; zero Mission Control/task/rights/submission semantics stored in 9router state.

## 5. Port/domain/reverse-proxy topology

Observed live during H01-140: `127.0.0.1:8876` is LISTEN. Port `20128` was free before the canary.

```text
                 FUTURE TLS / Founder ingress
                 founder-console.<DIE_DOMAIN>:443
                              |
                              v
                      reverse proxy/auth
                strip inbound X-9r-* headers
                              |
                              v
                    127.0.0.1:20128
                Founder Console + RO adapter
                              |
                 +------------+------------+
                 |                         |
          MC/Runtime Gateway          H01 read models
          (read contract)             (local reads)

127.0.0.1:8876  LEGACY FACTORY CONSOLE / H01-108 VIEW
        |
        +---- remains alive, unchanged, rollback/coexistence
```

H01-140 allocates no public DNS name and installs no reverse-proxy configuration. The included nginx fragment is reference-only and uses a deliberately invalid placeholder hostname. Production TLS/domain activation belongs to a later task.

## 6. Founder Console information architecture

The UI contract is fixed to:

1. Overview
2. Production
3. Providers/BYOK
4. QC Gallery
5. Submission Ready
6. Demand Intelligence
7. Tasks/MC
8. System Health
9. Settings

These are Founder decision surfaces, not a mirror of 9router endpoint categories.

## 7. Read-only DIE integration API map — first contract

| Console view | Spike endpoint | Canonical source intent | H01-140 authority |
|---|---|---|---|
| Overview | `GET /api/die/v1/overview` | MC + H01 aggregate | READ |
| Production | `GET /api/die/v1/production` | H01 production read model | READ |
| Providers/BYOK | `GET /api/die/v1/providers` | Brave/provider inventory + health | READ; no secret values |
| QC Gallery | `GET /api/die/v1/qc/gallery` | QC/artifact evidence | READ |
| Submission Ready | `GET /api/die/v1/submission-ready` | rights + QA + package gates | READ; no submission |
| Demand Intelligence | `GET /api/die/v1/demand` | demand evidence | READ |
| Tasks/MC | `GET /api/die/v1/tasks` | Mission Control graph/leases | READ |
| System Health | `GET /api/die/v1/system/health` | runtime health | READ |
| Settings | `GET /api/die/v1/settings` | non-secret console-visible config | READ |

Every response carries `schema`, `read_only=true`, `source`, `observed_at`, and `data`. POST/PUT/PATCH/DELETE under `/api/die/v1/*` fail closed with HTTP 405. Provider credential values are never returned.

Later write actions, if ever approved, must be commands to Mission Control or another canonical authority endpoint. They must not become direct writes from a 9router-derived page into H01 runtime, provider accounts, rights state or marketplace state.

## 8. Bounded runnable spike

Location:

`company/company-os/die-h01/spikes/h01-140-founder-console/`

Contents:

- dependency-free Node HTTP shell bound by default to loopback `127.0.0.1:20128`
- nine requested Founder menu entries
- fixture-only read models proving adapter contract
- GET-only `/api/die/v1/*` namespace
- CSP, no-store, frame-deny and content-type hardening headers
- health receipt explicitly declaring `live_provider_accounts=false` and `marketplace_actions=false`
- reference-only nginx edge config that strips `X-9r-*`
- Node contract tests

This spike intentionally does not vendor the whole 9router runtime. It proves the architectural seam required by H01-141: a 9router-derived BODY can be substituted behind the exact same read-only DIE contract without inheriting 9router's control-plane semantics.

## 9. Migration while 8876 stays alive

### Phase A — current H01-140

Run the new shell only on loopback:20128 for bounded canaries. 8876 stays authoritative/available. No traffic cutover.

### Phase B — H01-141 shadow console

Implement the actual 9router-derived presentation shell and point it at the same read-only APIs. Compare Founder-visible production/QC/task/health state against existing 8876 views. Keep both available.

### Phase C — authenticated Founder ingress

After separate security acceptance, place only the Founder Console behind the DIE reverse proxy/auth boundary. Raw upstream 9router proxy/provider routes remain absent. 8876 remains fallback.

### Phase D — governed actions

Only later tasks may add explicit commands. Commands route through Mission Control/authority APIs with leases, idempotency and receipts. Provider/BYOK connections remain optional capacity; they never replace Brave UDD/session ownership.

### Phase E — legacy retirement

Out of scope for H01-140. Port 8876 may be retired only after separate Founder acceptance and a full rollback/cutover task.

## 10. Acceptance evidence

Focused test command:

`npm test`

Observed result:

- tests: 3
- pass: 3
- fail: 0
- all nine read models: PASS
- mutation rejection: PASS
- security headers/menu contract: PASS
- bounded-authority health receipt: PASS

Live loopback canary:

- `127.0.0.1:20128/healthz` -> PASS
- `/api/die/v1/tasks` -> Mission Control declared scheduler/graph authority
- simultaneous `127.0.0.1:8876` -> LISTEN
- canary auto-terminated after the bounded run; no service cutover

Negative actions:

- live provider accounts connected: NO
- BYOK secrets read/written: NO
- marketplace action: NO
- submission/publication action: NO
- H01-108 mutation: NO
- 8876 retirement/restart: NO

## 11. Result

**PASS — architecture spike proven.**

Adopt a thin presentation fork of audited 9router UI primitives plus an independent read-only DIE adapter. Do not deploy upstream 9router as a second DIE control plane. Mission Control stays the global scheduler/lease/authority BRAIN; H01 task truth, Brave UDD/session ownership, rights/QA and publication authority remain canonical outside the Founder Console.

H01-141 may proceed to the real 9router-derived UI shell using this contract. H01-142 remains separately scoped for optional BYOK/API-provider bridging.
