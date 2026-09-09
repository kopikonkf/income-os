# H03 Production Organism v1

Status: CANONICAL EXECUTION DESIGN
Date: 2026-09-09
Holding: H03 Knowledge Product Factory

## Objective

H03 converts observed human problems into evidence-backed, useful, sale-ready knowledge products and closes the loop through organic distribution and measured commercial outcomes. The organism is designed for bounded scale but does not encode an arbitrary product-count target as truth.

```text
human problem universe
  -> seed curation
  -> demand + willingness-to-pay evidence
  -> worth-making gate
  -> research plan
  -> multi-provider research fan-out
  -> synthesis fan-in
  -> Knowledge Package
  -> useful-product planning
  -> semantic production fan-out
  -> deterministic compile + QA
  -> local commerce package
  -> Founder publication gate
  -> listing + organic promotion
  -> marketplace/social analytics
  -> demand/WTP learning loop
```

## Control plane versus worker plane

Mission Control is the supervisor, not the prompt executor. It owns batch/product standing, recovery, durable checkpoints, escalation, Founder gates and cross-system authority. Universal MCP/Mission Protocol is a privileged capability path for primary principals and control actions.

Standard H03 cognition workers do not require MCP, shell access or local-filesystem access. Their normal hot path is:

```text
H03 orchestrator / role queue
  -> normalized Work Card
  -> web-ai-adapter
  -> provider adapter
  -> SESSION_API or BROWSER_CDP
  -> web-AI session
  -> normalized result
  -> durable H03 artifact
```

Future workers may receive additional capabilities if a task proves they are necessary; absence of MCP is not a blocker for ordinary curator/researcher/producer work.

## First-class web-AI workforce

Qwen 3.8 Max and Gemini are first-class H03 worker candidates, not fallback-only providers. Manus is a strong autonomous-research candidate. ChatGPT, Claude and Grok remain pluggable candidates for synthesis, architecture, review, signals, production and growth according to observed quality/capacity.

Logical roles are `SEED_CURATOR`, `MARKET_RESEARCHER`, `KNOWLEDGE_RESEARCHER`, `SYNTHESIZER`, `PRODUCT_ARCHITECT`, `PRODUCER`, `REVIEWER`, and `GROWTH_PRODUCER`. Roles are Work Card identities, not accounts or browser profiles. A healthy provider may serve multiple roles; routing is role/capability/health/capacity based.

## Persistent Brave profile pool

A persistent Brave profile may contain authenticated sessions for multiple web-AI providers and may be the first runtime shard. H03 does not pre-create profile clusters merely to satisfy an imagined scale target. Additional profiles become fallback/capacity shards when real health, queue or throughput observations justify them.

Browser profile/session/cookie/token bytes remain host-local capability state and never become Knowledge Package or product truth. Knowledge workforce profiles and Growth/social profiles are separate security/failure domains.

## Durable continuity

Continuity is artifact-based, not conversation-thread based:

```text
problem-seed.json
  -> opportunity-candidate.json
  -> demand-wtp-packet.json
  -> research-plan.json
  -> research-packet-1..N.json
  -> knowledge-map.json
  -> knowledge-package.json
  -> product-blueprint.json
  -> content-blocks-1..N.json
  -> document-ast.json
  -> product package + manifest
  -> review-card.json
  -> commerce-package.json
  -> campaign/analytics observations
```

A provider session can disappear without destroying pipeline standing. A replacement worker resumes from durable artifacts.

## Fan-out/fan-in research and production

Research is a bounded parallel job set, not one giant model turn. A research plan may divide work into market/WTP, community pain, official/academic/domain evidence, competitor/solution analysis or other bounded subquestions. Eligible workers such as Qwen, Gemini and Manus may execute different packets simultaneously; a synthesizer performs fan-in.

Production can similarly fan out semantic sections/content blocks. Generative workers own semantics; deterministic local code owns layout, pagination, file naming, metadata mechanics, hashes, manifests and technical QA.

## Minimal governance kernel

V1 has three material gates: `OPPORTUNITY_GATE`, `KNOWLEDGE_GATE`, and `FOUNDER_PUBLICATION_GATE`. Routine low-risk deterministic validation should be automated.

## Economics and attribution

Company canon now contains `ECON-002A` State Manager commit semantics and `ECON-002B` economic admission validation. H03 may prepare evidence-linked `validated_not_committed` candidates through ECON-002B, but live canonical submit authority is not yet activated. H03 never writes `state/ECONOMICS.jsonl` directly.

Post-production assigns durable product/listing/campaign/creative/channel identities so observed Gumroad/Etsy/social traffic, orders and revenue can later be joined back to the originating problem seed and demand/WTP hypothesis. Unknown observations remain `UNKNOWN/UNPROVEN`.

## Organic post-production

The initial distribution strategy is organic. Paid ads are disabled until Founder authorization. Knowledge workforce profiles and Growth/social profiles remain separate. BROWSER_CDP is a viable initial social transport; official APIs, connector platforms or a dedicated social-manager engine remain future pluggable transports rather than blockers.

## Scale doctrine

No fixed number such as 1,000 products is an acceptance requirement. H03 scales from measured jobs/hour, products/hour, queue latency/backlog, failure rate, retry/fallback success, provider/profile capacity, quality, Founder review load and economic outcomes. The first profile remains sufficient until measured bottlenecks justify another shard.

## Atomic execution frontier

```text
Economic Intelligence:
H03-OPP-001
  -> H03-OPP-002 + H03-DMD-001
  -> H03-OPP-003
  -> H03-RSCH-001

Factory Runtime:
H03-RT-001
  -> H03-RT-002
  -> H03-RT-003
  -> H03-RT-004
  -> H03-RT-005
  -> H03-RT-006

Instrumentation:
H03-ECO-001
  -> shadow ECON-002B admissions only
```

Detailed dependency truth is `company/h03/task-graph-v1.json`.
