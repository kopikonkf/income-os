# DIE Company OS / Economic Layer Roadmap v1

Status: CANONICAL CANDIDATE  
Date: 2026-09-08  
Authority: subordinate to `CONSTITUTION.md`; this document grants no new spend, credential, publication, migration, or Aether mutation authority.

## Purpose

Create a company-level operating architecture that lets DIE scale from individual automation projects into a governed multi-Holding organism while preserving Founder sovereignty, evidence discipline, and cost control.

The program is intentionally separate from the H01 Linux engineering graphs and from Mission Control's runtime-development graph so the lanes can proceed in parallel without conflating engineering state with company governance.

## Current architectural hypothesis

```text
Founder / constitutional authority
          |
          v
Aether / strategic cognition candidate (KEEP_EXTERNAL)
          |
          | hypotheses, interpretation, proposals
          v
Economic Layer / resource fitness (shadow first)
          |
          | authorized work proposals
          v
Mission Control / deterministic operational control candidate
          |
          | leases, routing, failover, review, recovery, writeback
          v
Holding-local executors + pooled AI/compute production resources
          |
          v
Market evidence -> Revenue Attribution -> Economic Ledger
          |                         |
          +-------------------------+
                    feedback
```

This is a hypothesis, not a constitutional amendment. Current canonical documents that still name `hermes-operator` as operational control plane remain authoritative until explicitly reconciled and, where required, Founder-ratified.

## Why this track starts with host exit

The current Windows VPS has an observed remaining lifetime of roughly 21 days. Therefore survivability and portability outrank new autonomous-economic capabilities. The first atomic task is a read-only dependency map classifying every company-critical Windows dependency as `MIGRATE`, `REBUILD`, `REAUTH`, `RETIRE`, or `KEEP_EXTERNAL`.

No browser session secret, cookie, token, password, or credential is to be copied as part of this classification. Re-authentication is an explicit migration strategy.

## Company-level role separation

### Aether

Candidate strategic cognition / identity continuity layer. DNA principles such as Evidence > Confidence, falsifiability, traceability, capital efficiency, bounded experiments, and scale-after-external-evidence are strong inputs to future economic policy. Aether remains external and sandboxed unless a later governed task changes that boundary.

### Economic Layer

Measures rather than spends at first. E0 shadow mode observes operational cost, revenue, Founder intervention, attribution and unit economics. Any capital allocator/reinvestment result is simulated until Founder promotion.

### Mission Control

Candidate deterministic operational control plane. It should own scheduling, leases, principal selection, bounded failover, review routing, incident escalation, dependency progression and durable receipts once canonical governance is reconciled.

### Hermes

Existing constitutional/canonical operational orchestrator. Its future role must be evidence-audited rather than silently removed. Candidate outcomes include KEEP for unique edge functions, DEMOTE to compatibility/notification adapter, or RETIRE after Mission Control unattended acceptance and Founder-ratified reconciliation.

### OpenCode

Candidate ephemeral executor/provider surface rather than resident control plane. It should exist only where it adds capability or favorable economics.

## Economic maturity ladder

- `E0 OBSERVE`: telemetry only; no recommendations required; zero spend authority.
- `E1 ADVISE`: simulated/recommended capital decisions; Founder decides.
- `E2 BOUNDED`: small explicit pre-authorized envelopes after Founder promotion.
- `E3 PORTFOLIO`: reallocation inside approved envelopes.
- `E4 SELF_FUNDING`: governed reinvestment of realized profit.
- `E5 COMPOUNDING`: infrastructure/business capacity can grow or shrink within constitutional bounds.

Only E0 is authorized by this roadmap.

## Economic truth model

Two profit views are required:

1. Cash operating P&L: realized revenue minus actual cash costs such as VPS, API, subscriptions, rendering, storage, transaction fees and distribution spend.
2. Economic P&L: cash operating profit adjusted for measured Founder intervention/recovery/review time and other explicitly modeled non-cash operating effort.

Core operational-economics metrics include Founder Minutes per unit revenue, Zero-Touch Rate, Automated Recovery Rate, Architect Escalation Rate, attributable variable cost, contribution profit, payback and ROIC.

Revenue that cannot be traced to a production/distribution lineage must remain `ATTRIBUTION_UNKNOWN`; it must not be silently credited to an AI decision.

## Parallel execution model

```text
Lane A — Orchestration project
Company OS canon, host-exit, governance, Economic Layer

Lane B — DIE Linux session
H01/Linux migration and factory engineering using existing canonical graphs

Lane C — Mission Control runtime
MC-008J unattended soak; observation only unless invariant violation requires governed recovery
```

Remote publication remains serialized by the shared `income-os.repo-write` engineering lease. Parallel work means disjoint implementation and cognition, not simultaneous uncontrolled writes to `origin/main`.

## Immediate frontier

1. `COS-001` — 21-day Windows host-exit dependency/survivability map.
2. `COS-002` — operational control-plane authority reconciliation.
3. `COS-003` — Aether-DIE constitutional bridge contract.

These three are deliberately parallelizable and do not require changing Aether, spending money, or disturbing MC-008J.
