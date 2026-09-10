# Factory Asset Scale Economics Decision V1

Task: `FA-125`  
Decision authority: Founder  
Architect recommendation: **HOLD**  
Founder ratification: **PENDING**  
Date: 2026-09-10

## 1. Decision boundary

FA-125 decides whether evidence supports `PROMOTE | HOLD | REPAIR | STOP` after the 100-master acceptance canary. This document does **not** authorize a 100/day continuous production schedule, 500/day design/live load, new marketplace publication, spend, account creation, or a change to Founder QC policy. The baseline `die-production-cycle-v1` remains `0 */3 * * *`; `scale_100_per_day=false`.

## 2. Executive conclusion

**Recommendation: HOLD.**

The Factory is technically capable of producing 100 unique accepted masters in a bounded canary, and automated downstream compute is not the current bottleneck. The scale gate is instead blocked by economic and market evidence: Factory-attributed marketplace acceptance and realized licensing revenue are not yet observed, fully-loaded cost per marketplace-accepted asset is unknown, Founder QC remains 100% with unmeasured human service capacity, and current local free storage cannot hold a 30-day p95 100-workspace/day envelope without retention/archive action.

`HOLD` is preferred over `REPAIR` because the technical production, provider pool, queue, QA and storage models pass their acceptance tests. It is preferred over `STOP` because external marketplace policy and demand evidence shows a legitimate licensing path for AI-generated reusable design assets. It is preferred over `PROMOTE` because market absorption and positive bounded unit economics have not yet been demonstrated by the Factory's own distribution loop.

## 3. Evidence matrix

| Gate | Evidence | Observed value | Decision state |
|---|---|---:|---|
| Provider throughput | FA-124 | 100 accepted unique masters / 113 committed provider calls | PASS |
| Provider route breadth | FA-124 | all 10 provider@cluster routes certified | PASS |
| Exact duplicates | FA-124 | 0 | PASS |
| Observed provider spend | FA-124 | USD 0 | PASS, variable spend only |
| Overall bounded dispatch yield | FA-124 | 88.5% accepted per committed provider call | PASS for canary, not a marketplace rate |
| Automated downstream | FA-123 | 100/100 technical QA and package model; modeled automated backlog/day at 100 = 0 | PASS |
| Founder QC | FA-123 | 100 touches/day required at current 100% policy; measured Founder review capacity = UNKNOWN | **HOLD** |
| Full postprocessed 100-package run | FA-124 truth boundary | not created | **UNKNOWN** |
| Factory marketplace acceptance | current submission graph | no canonical accepted/rejected Factory submission outcome yet; first contract-capture tasks remain READY | **HOLD** |
| Factory realized licensing revenue | current economic evidence | none canonically attributed | **HOLD** |
| Fully-loaded cost/accepted marketplace asset | provider spend + VPS/storage + Founder time + distribution economics | UNKNOWN | **HOLD** |
| Browser concurrency | FA-312 | conservative two-owner basis 5,048.15 MiB; active-owner ceiling 8 | PASS |
| Storage retention | FA-314 + live disk observation | p95 workspace 50,045,853 bytes; ~4.661 GiB/day at 100/day | CONDITIONAL |
| Live free local disk | 2026-09-10 observation | ~63.395 GiB free | **HOLD without retention/archive** |
| 30-day p95 storage envelope | FA-314 linear 100/day planning envelope | ~139.826 GiB / 30 days | **HOLD** |
| Unmanaged local-storage runway | current free / p95 100-day rate | ~13.6 days | **HOLD** |
| Current runtime health | PROD-RUNTIME-R1 | Worker handoff repaired; Cluster A/B READY, 1/8 tabs, 0 leases | PASS after repair |

## 4. Unit economics truth

### 4.1 What is proven

FA-124 observed `USD 0` provider-call spend for 100 accepted unique masters. On that narrow variable-provider-spend basis:

- observed provider spend / successful master = `$0 / 100 = $0.00`;
- observed provider spend / accepted master = `$0 / 100 = $0.00`.

These are **not** claims that the Factory has zero economic cost. They exclude at least VPS/subscription allocation, storage/archive cost, Founder review time, submission labor, payment/marketplace economics and any future paid provider capacity.

### 4.2 What is not yet defensible

`FullyLoadedCostPerMarketplaceAcceptedAsset = UNKNOWN` because both numerator and denominator remain incomplete. There is no canonical Factory marketplace acceptance denominator and no complete attributable cash/labor cost ledger for this production cohort.

`ContributionProfitPerAsset = UNKNOWN` because Factory-attributed realized licensing revenue is not yet present. Nominal marketplace royalty percentages prove a monetization mechanism exists; they do not prove our portfolio's sales frequency or positive contribution profit.

## 5. Marketplace acceptance and licensing

Current public policy evidence supports a legitimate route to market, subject to each platform's account and content rules:

- Adobe Stock accepts properly labeled generative-AI images, vectors and videos; current official royalty rate for photos/vectors/illustrations is 33%. Adobe also limits highly similar generative-AI submissions and expects distinct commercial value.
- Vecteezy states that AI-generated images can be accepted within contributor guidelines and emphasizes unique, useful, high-quality resources; accepted resources monetize through downloads.
- Dreamstime states that it welcomes AI-generated content under its tagging/rights/quality rules and applies the same royalty treatment as regular uploads.
- 123RF states that it welcomes AI-generated images subject to rights requirements; its current contributor commission structure ranges from 30% to 60% by contributor level, with subscription earnings varying by level.
- MotionElements accepts generative-AI content under specific rules and requires AI-generated content to be managed under a separate AI-generated contributor account.

This is **policy eligibility**, not Factory marketplace acceptance. The canonical submission graph still has `SUB-ADOBEA`, `SUB-DREAMSTIMEA`, `SUB-123RFA`, `SUB-VECTEEZYA` and `SUB-MOTIONELEMENTSA` at contract-capture stage, with actual adapter activation/reconciliation downstream. Therefore the Factory's own moderation acceptance rate, review latency, download rate and revenue per accepted asset are still UNKNOWN.

## 6. Market-absorption evidence

The Project research on asset-format demand identifies reusable design primitives - vectors, icons, transparent elements, patterns, backgrounds and isolated objects - as high-opportunity asset families, but explicitly labels its demand scores as composite research scores rather than marketplace search-volume telemetry. Treat this as a demand prior, not revenue proof.

The Founder-provided `actual_income_research_intelligence-isolated_asset` screenshot bundle contains repeated Adobe Stock earnings notifications alongside isolated/watercolor-object portfolio examples. It is useful as an external existence proof that similar asset styles can be licensed, but it lacks authenticated account provenance, portfolio size, asset age, download counts and per-asset attribution. It therefore cannot close the Factory unit-economics or absorption gate.

## 7. Backlog and human-service risk

FA-123 proves automated downstream compute headroom at the 100/day model, but the current Founder QC policy requires one Founder touch for every package. At 100 masters/day this is 100 Founder touches/day. Because measured Founder review capacity is `EXTERNAL_UNPROVEN`, the human backlog can grow by up to 100/day if no reviews occur.

Scale should not convert a technically fast Factory into a large unreviewed inventory buffer. The next promotion gate must measure Founder QC service rate or explicitly ratify a lower governed sampling rate; FA-125 does neither.

## 8. Storage risk

FA-314 measured p95 workspace size at 50,045,853 bytes. A planning envelope of 100 such workspaces/day is approximately 4.661 GiB/day and 139.826 GiB over 30 days. The live Linux filesystem observation on 2026-09-10 showed about 63.395 GiB free. Without retention/archive/reclamation, that is only about 13.6 days of p95 100/day workspace growth and leaves a ~76.4 GiB 30-day shortfall.

FA-314 defines archive/restore controls but explicitly does not authorize external archive spend. Therefore storage is manageable architecturally, but not yet authorized operationally for continuous 100/day retention.

## 9. Provider capacity and today's runtime incident

FA-124 proved 100 accepted unique masters across all ten provider@cluster routes using dynamic healthy-capacity allocation. Duck.ai's observed daily quota showed why equal per-route throughput targets are unsafe; dynamic allocation correctly re-routed around constrained capacity.

On 2026-09-10 production retries stalled before MUXIA because Hermes emitted `handoff.scheduler_contract=FA-306` while the Worker V1 validator rejected that additional field. `PROD-RUNTIME-R1` repaired the envelope contract, passed 818/818 Linux Factory tests, deployed the canonical runner with rollback hash, and a scratch production Worker dispatch returned `accepted_status=done`. Cluster A/B remained READY. This is a repaired integration defect, not evidence against the provider-capacity model, but it argues against increasing cadence before market and operational evidence closes.

## 10. Promotion conditions

A future FA-125 Founder verdict may move from HOLD to PROMOTE only when all of the following are evidence-backed:

1. **Marketplace contract capture:** at least two intended marketplace lanes have dated account/submission/licensing contracts captured and are eligible for the actual asset provenance used by Factory.
2. **Bounded real submission:** a small, non-spam Factory batch is actually submitted through Founder-authorized lanes, producing measurable accepted/rejected moderation outcomes and review latency.
3. **Market absorption:** at least one Factory-attributed realized license/download/revenue event exists, or another Founder-ratified direct demand signal is strong enough to bound expected economics. Forecast revenue alone does not qualify.
4. **Fully-loaded unit cost:** attributable cash cost plus Founder review/submission time is measured sufficiently to compute a bounded cost per marketplace-accepted asset.
5. **Founder QC capacity:** actual review service rate is measured, or Founder explicitly ratifies a lower governed sampling policy with QA escape-rate controls.
6. **Storage envelope:** a 30-day hot/archive plan fits available capacity or an explicitly authorized storage budget; no unapproved spend is assumed.
7. **Provider health:** at least two healthy provider lanes remain independently usable and no unresolved committed-dispatch defect exists.

## 11. Decision register

| Field | Value |
|---|---|
| Architect recommendation | `HOLD` |
| Founder decision | `PENDING` |
| 100/day continuous scale authorized | `NO` |
| 500/day FA-126 resume condition satisfied | `NO` |
| Baseline 3-hour production | `PRESERVE` |
| New spend authorized | `NO` |
| Marketplace publication authorized by FA-125 | `NO` |

The HOLD is a **market/economics evidence hold**, not a technical rollback. Normal baseline production may continue at the existing three-hour cadence while submission-contract capture, bounded marketplace canaries, Founder QC measurement and retention evidence are gathered.
