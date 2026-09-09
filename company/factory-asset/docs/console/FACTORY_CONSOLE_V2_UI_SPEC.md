# Factory Console v2 — Clean-Room UI Specification

Task: FA-C014

## Shell

```text
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ Factory Console  │ Context header · freshness · scope                    │
│                  ├─────────────────────────────────────────────────────────┤
│ OPERATE          │ critical summary strip                                │
│  Overview        ├─────────────────────────────────────────────────────────┤
│  Queue           │                                                         │
│  Assets          │ primary operator surface                               │
│  QC Gallery      │ cards / table / topology / gallery                     │
│                  │                                                         │
│ RUNTIME          │                                                         │
│  Clusters        │                                                         │
│  Providers       │                                                         │
│  Sessions        │                                                         │
│                  │                                                         │
│ ANALYZE          │                                                         │
│  Usage           │                                                         │
│  Economics       │                                                         │
│  Capacity        │                                                         │
│                  │                                                         │
│ GOVERN           │                                                         │
│  Acceptance      │                                                         │
│  Rights          │                                                         │
│  Settings        │                                                         │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

## Component primitives

### StatusPill
Canonical state + optional reason + freshness. Always renders text.

### MetricTile
One decision metric/value with optional context. Maximum six in a summary strip.

### ClusterCard
Cluster ID, broker health, profile, owner, active/open/max tabs, active lease, provider membership, observable RAM/capacity, freshness/evidence link.

### ProviderSessionCard
Provider + cluster, readiness, capacity, transport, job/lease, cooldown/auth reason, evidence timestamp, model lineage when known.

### QueueRow
Job ID, seed/asset intent, route, durable state, attempt count, dispatch commitment, reconciliation state, age.

### AssetCard
Thumbnail, seed/title, provider@cluster, model evidence, QC state and lineage affordance. Click opens detail/lightbox only.

### EvidenceDrawer
Versioned receipts, hashes, lineage, runtime evidence and diagnostics. Raw JSON is secondary evidence, never the primary UI.

### AuthorityBanner
Shows principal/authority requirement and explicit lock reason for governed actions.

## Route map

```text
/                  Overview
/queue             Queue
/assets            Assets
/qc                QC Gallery
/clusters          Clusters
/providers         Providers
/sessions          Sessions
/usage             Usage
/economics         Economics
/capacity          Capacity
/acceptance        Acceptance
/rights            Rights
/settings          Settings
```

## Density rules

- default card minimum width 280px;
- provider/session cards target 300–360px;
- table rows 36–44px;
- left rail ~220px, collapsible;
- topology/table screens use full operator canvas;
- 4/8px internal spacing; 16/24px section spacing;
- no oversized headings below page-title level.

## State examples

```text
Qwen · cluster-a        HEALTHY     AVAILABLE
Duck.ai · cluster-b     DEGRADED    COOLDOWN
Gemini · cluster-a      AUTH_REQUIRED
PRODSEED000116          SUCCEEDED   qwen@cluster-a
job XYZ                 RECONCILIATION_REQUIRED
```

## Queue/routing surface

Queue represents canonical durable jobs, not browser tabs. Expandable routing evidence includes candidate routes, selected route, rationale, dispatch commitment and retry/reconciliation boundary. Route mutation is never a casual dropdown; governed mutation belongs to FA-C019.

## Usage/economics surface

Shared metric grammar:
- queue depth;
- accepted masters/day;
- provider/cluster success rate;
- dispatch commits;
- reject rate;
- latency;
- active tabs;
- RAM where observed;
- storage growth;
- provider cost where observed;
- `UNKNOWN` for unavailable quota/price/revenue evidence.

Observed $0 browser-provider spend must never be displayed as zero total infrastructure cost.

## QC Gallery relationship

Existing Founder QC Gallery is migrated conceptually into `/qc` with its current truth rules:
- one review representative per semantic job/workspace;
- exact FA-124 E4 accepted set available;
- opaque image IDs and hidden filesystem paths;
- model/version only from explicit lineage evidence;
- read-only until separate QC mutation authority exists.

## Accessibility and operability

- visible keyboard focus;
- status never relies on color alone;
- WCAG-AA-oriented text contrast;
- keyboard-accessible cards/tables/evidence drawers;
- reduced-motion respected;
- bulk gallery uses lazy loading/virtualization.
