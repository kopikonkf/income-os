# Factory Console v2 — Web-First Control Plane ADR

Status: ACCEPTED FOR IMPLEMENTATION  
Task: FA-C014  
Date: 2026-09-09  
Authority: Architect, after FA-C013 Founder acceptance

## Decision

Factory Console v2 is a **web-first, loopback-served operational control plane**. The authoritative implementation boundary is the web application and its local Python control-plane backend. A desktop shell is optional packaging only and is deferred to FA-C021 after FA-C020.

The v2 UI uses a clean-room dense operator pattern inspired by the Founder-supplied 9router reference: persistent left navigation, compact status-rich cards, clear section hierarchy, restrained dark surfaces, visible health/capacity state, and fast scanability. No brand assets, provider logos, source CSS, source layout measurements, or source code are copied.

## Stack

### Frontend
- TypeScript + React single-page application.
- Vite build/dev tooling.
- Native CSS variables, CSS Grid and Flexbox; no copied third-party design system.
- Browser `fetch` for query/command APIs and bounded polling for initial live topology. SSE may be added later only if polling is a measured bottleneck.
- No Redux requirement. Server truth remains authoritative; local state is limited to navigation, filters, selections, drawers and command forms.

### Backend
- Python 3 loopback control-plane process evolving from the proven Console bridge.
- Versioned, machine-testable JSON contracts.
- Canonical Factory libraries/registries/receipts/runtime state are imported rather than reimplemented in the frontend.
- No browser cookies, OAuth material, credential values, private keys or raw session storage are exposed to the frontend.

### Packaging
- Primary runtime: browser at `127.0.0.1`.
- Remote operator transport terminates outside Console authority.
- Optional Tauri shell: FA-C021 only, wrapping the same web control plane and owning no separate queue/provider/credential/publication state.
- Electron rejected: extra heavyweight runtime with no current requirement benefit.

## Why web-first

1. Current Console already proves loopback browser operation, queue controls, recovery, QC Gallery and Production Acceptance.
2. Linux is production host while Windows and remote laptops are operator surfaces; browser UI is portable.
3. One web authority boundary prevents desktop wrappers becoming a second source of truth.
4. FA-C019 governed command API remains independently testable.
5. Tauri can wrap the accepted web surface later without rewriting operations.

## Authority boundary

Read-only by default:
- cluster/provider readiness;
- tab and lease occupancy;
- queue state;
- asset lineage and derivatives;
- QA/QC evidence;
- throughput/economics telemetry;
- rights/marketplace readiness;
- receipts/reconciliation state.

Not implied by UI presence:
- provider dispatch authority;
- credential/session access;
- marketplace submission/publication;
- spend authority;
- Founder QC approval;
- scale authorization.

Locked controls state why they are locked instead of disappearing.

## Information architecture

Persistent navigation is organized by operator intent.

### OPERATE
- Overview
- Queue
- Assets
- QC Gallery

### RUNTIME
- Clusters
- Providers
- Sessions

### ANALYZE
- Usage
- Economics
- Capacity

### GOVERN
- Acceptance
- Rights
- Settings

Wide screens keep the rail fixed and compact. Narrow screens collapse it to drawer/icon navigation without changing route semantics.

## Screen anatomy

Every operator screen follows:
1. context header — title, purpose, scope, freshness;
2. critical summary strip — 3–6 decision metrics;
3. primary surface — grid/table/topology/gallery/queue;
4. evidence drawer — lineage, receipts, reconciliation, diagnostics;
5. authority state where mutation is possible.

Non-actionable details stay in the evidence drawer rather than creating dashboard sprawl.

## Cluster/provider visual model

Cluster is a first-class card. Minimum fields:
- cluster/profile ID;
- broker and browser-owner state;
- active/open/max tabs;
- active generation lease;
- provider-session membership;
- RAM/capacity where observable;
- current job/lock owner;
- freshness timestamp.

Provider-session minimum fields:
- provider + cluster;
- readiness + capacity;
- transport;
- active job/lease;
- accepted/success counters when in scope;
- model/version evidence only when explicitly captured;
- cooldown/auth-required reason;
- last evidence timestamp.

`UNKNOWN` is a valid state and is never rendered as healthy by omission.

## Canonical status pills

HEALTHY, DEGRADED, AUTH_REQUIRED, CHECKPOINT, UNAVAILABLE, AVAILABLE, SATURATED, QUEUED, IN_FLIGHT, RECONCILIATION_REQUIRED, PAUSED, BLOCKED, TECHNICAL_PASS, FOUNDER_REVIEW, ACCEPTED, REJECTED, UNKNOWN.

Status uses text plus restrained semantic color; color alone never carries meaning. Frontend labels map to runtime contracts instead of inventing hidden synonyms.

## Visual system

- near-black neutral application canvas;
- slightly lifted navigation panel;
- operational cards with subtle 1px boundary;
- high-contrast primary text, subdued secondary text;
- one Factory accent for active navigation/selection;
- semantic green/amber/red/blue/violet for state classes;
- moderate consistent radius;
- dense 4/8px internal rhythm, 16/24px section rhythm;
- system sans typography; tabular numerals for metrics;
- functional monochrome icons; provider branding optional.

No glassmorphism, decorative gradients, hero banners or marketing-style empty space.

## Interaction rules

- Card click opens evidence; it never mutates runtime state.
- Governed/destructive actions use explicit controls and appropriate confirmation.
- Long operations expose durable job IDs and reconciliation state.
- Sorting/filtering never changes canonical state.
- Refresh/polling never performs provider calls.
- Stale evidence displays age/timestamp.
- Large asset/queue surfaces use pagination or virtualization.
- QC Gallery remains read-only until a separate Founder QC mutation contract exists.

## Responsive boundary

Desktop operator layout is primary. Dense topology target minimum width is ~1180px. Below it, cards collapse progressively and evidence drawers become full-width. Mobile is for inspection/emergency control, not bulk QC.

## Migration strategy

1. Freeze current prototype as compatibility reference.
2. Build v2 shell/routes beside it.
3. Port read-only surfaces: Clusters/Providers (FA-C015), Queue/Routing (FA-C016), Assets/QA (FA-C017), Telemetry (FA-C018).
4. Add governed mutation API only in FA-C019.
5. Run FA-C020 integration acceptance.
6. Evaluate optional Tauri wrapper in FA-C021.

Until FA-C020 passes, current loopback Console remains accepted fallback.

## Rejected alternatives

- Continue expanding monolithic `app.js`: rejected due coupling/state-management cost.
- Native desktop first: rejected because it splits Linux/web/Windows behavior prematurely.
- Copy 9router component hierarchy: rejected; only density/ergonomic principles are reused.
- Expose MCP/CDP/browser control directly to frontend: rejected; governed backend contracts remain mandatory.

## Exit criteria

FA-C014 passes when the clean-room dense operator language, navigation, cluster/provider cards, status semantics, queue/usage/economics patterns, dark visual system, frontend/backend stack, desktop-wrapper boundary, security authority boundary and FA-C015..C021 migration path are all explicit.
