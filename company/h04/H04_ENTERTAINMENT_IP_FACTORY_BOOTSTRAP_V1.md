# DIE H04 — Entertainment & IP Factory Bootstrap V1

Status: BOOTSTRAP / CANONICAL STARTING POINT
Date: 2026-09-15
Branch: architect/die-h04-bootstrap-20260915

## 1. Operating Principle

BUILD > SHIP > CUAN.

H04 must stay simple per sprint. Do not overengineer the organism before the first usable signal, first generated master, first distribution canary, and first revenue signal exist.

## 2. Current Scope

DIE H04 focuses on:

- A. Audience / Content
- I. Entertainment

Initial market strategy:

- Market-01: US / English — primary revenue market.
- Market-02: Indonesia / Bahasa Indonesia — later localization / native-market expansion.

H04 is an AI-assisted Entertainment & IP Factory, not a mass-template content factory.

## 3. Current End-to-End Direction

```text
MARKET SIGNALS
    -> IDEATION CANDIDATES
    -> TOP 100 / TOP 10
    -> WORTH-MAKING GATE
       -> MAKE / MICRO-CANARY / SKIP
    -> ENTERTAINMENT TRUTH PACKET
    -> CREATIVE COGNITION
       -> persistent characters
       -> world / premise / story
       -> storyboard / copy / scene plan
    -> VIDEO GENERATION
       -> Google Flow / Veo
       -> Seedance
       -> other providers after capability research
    -> VIDEO MASTER / DERIVATIVES
    -> QUALITY / RIGHTS REVIEW
    -> WORTH-DISTRIBUTING GATE
    -> SOCIAL / STREAMING DISTRIBUTION
    -> PERFORMANCE TELEMETRY
    -> LEARNING
    -> SIGNALS
```

## 4. Demand / Signals Architecture

Do not use a single TREND_SCORE.

Canonical signal families:

1. Attention — what people are noticing now.
2. Search — what people actively seek.
3. Consumption — what people actually watch.
4. Conversation — what audiences discuss.
5. Durability — spike versus sustained / evergreen demand.
6. Cross-platform confirmation — isolated trend versus broad demand.
7. Monetization proxy — commercial environment before H04 has own RPM truth.
8. Supply / competition — overcrowding and content gap.
9. Format fit — short, episodic, long-form, movie, series.
10. Market fit — US audience relevance and geographic fit.

Freshness horizons:

- HOT: hours to 7 days.
- TRENDING: 7 to 90 days.
- EVERGREEN: approximately 6 months to 5 years.

## 5. Initial Signal Sources

V1 core candidates:

- Google Trends — search velocity, geography, seasonality, evergreen persistence.
- YouTube Data API / public market surface — popularity and attention/consumption proxies.
- TikTok Creative Center — attention, hashtag velocity, regional trend intelligence.
- TikTok Creator Search Insights — search intent where available to the authorized account.
- Netflix Top 10 — title-level viewing demand and persistence.
- Nielsen Streaming Top 10 — US streaming minutes and evergreen consumption.
- JustWatch — cross-streamer interest and durability.
- Tubi Most Popular — US AVOD demand proxy.
- IMDb MOVIEmeter — buzz / search-attention signal.
- Google Ads Keyword Planner / Ads API — monetization proxy, not actual entertainment RPM.

Later / conditional sources:

- Pinterest Trends — aesthetics and seasonality.
- X — conversation velocity.
- Reddit — only after acceptable commercial data-use path is established.
- Meta public research datasets — do not make a commercial H04 dependency.
- TMDB — do not make a canonical commercial AI dependency without appropriate licensing.

## 6. Two Gates

### Gate A — WORTH-MAKING

Purpose: decide whether H04 should spend compute, worker time, generation quota, and review capacity creating a new original entertainment asset / IP.

Inputs include:

- external demand
- durability
- cross-platform confirmation
- monetization proxy
- production feasibility
- distribution fit
- franchise / IP expandability
- rights / originality risk
- oversupply penalty

Default outcomes:

- MAKE
- MICRO-CANARY
- SKIP

### Gate B — WORTH-DISTRIBUTING

Purpose: after a master passes QA, decide which channel, format, locale, packaging, and promotion path should receive it.

Do not assume one master belongs on every platform.

## 7. Entertainment Truth Packet

The sealed pre-production packet should eventually contain:

- market / locale
- demand evidence
- audience hypothesis
- genre / subgenre / trope / emotional promise
- format / ideal duration
- monetization proxy
- production feasibility
- originality / IP safety constraints
- source receipts
- final MAKE / MICRO-CANARY / SKIP decision

Creative workers should consume the packet, not raw platform trends directly.

## 8. Creative / Production Kernel

H02 provides the useful production pattern to reuse conceptually:

- persistent character reference / character sheet
- storyboard before generation
- separate scene prompts
- controlled per-scene generation
- continuity across scenes

H04 extends this from product UGC into original entertainment IP with persistent characters, world, story arc, scene continuity, and multi-format masters.

## 9. Worker Direction

Known / planned workers:

- ChatGPT — cognition, creative planning, character/world/story/storyboard roles.
- Gemini — research and creative/review roles where useful.
- Google Flow / Veo — video generation candidate.
- Seedance — video generation candidate.
- Additional web-AI video generators — capability to be researched before admission.
- Hermes vanilla (Nous Research) — global install planned; H04-specific profile will manage social-media promotion lane.

Do not wire every worker before the task requires it.

## 10. Runtime Direction

Current primary runtime pattern remains:

- headful Brave
- persistent isolated profiles / UDD ownership
- CDP-driven worker execution
- demand-driven wake / work / close where practical

Android promotion surface is intentionally DEFERRED pending the separate VPS virtualization / WSA / emulator design decision.

H04 must not block upstream research, story, production, review, or distribution design on Android readiness.

## 11. Public Signals vs Own Truth

Public market signals are the bootstrap prior.

Once H04 ships content, own telemetry becomes higher-value truth:

- US audience share
- impressions / CTR
- watch time
- retention / completion
- replay
- subscribers / members
- actual RPM / CPM / revenue
- downstream streaming minutes / revenue when available

The long-term moat is the feedback loop:

PUBLIC SIGNALS
    + OWN PERFORMANCE TRUTH
    -> BETTER WORTH-MAKING DECISIONS
    -> BETTER CREATIVE / FORMAT / DISTRIBUTION CHOICES
    -> MORE REVENUE DATA
    -> LEARNING

## 12. First Build Order — intentionally small

Do not create a giant implementation graph yet.

First executable sequence when the new VPS is ready:

1. H04-001 — canonical signal contract + raw observation schema.
2. Add only the smallest useful signal collectors needed for a US canary.
3. Normalize title / genre / trope observations.
4. Produce a first ranked candidate set.
5. Run one Worth-Making decision.
6. Create one Entertainment Truth Packet.
7. Produce one micro-canary.
8. Ship it.
9. Measure it.
10. Use the result to decide the next engine work.

BUILD > SHIP > CUAN.

## 13. Explicit Non-Goals for Bootstrap

Not part of this bootstrap branch:

- full H04 task graph
- Android automation implementation
- large multi-provider browser workforce
- full streaming distributor integration
- owned OTT platform
- premature schema proliferation
- speculative scaling infrastructure

These are admitted only after a real canary proves the next bottleneck.

## 14. Resume Point

When the replacement Windows VPS is available:

- use this document as the H04 canonical starting point
- keep Mission Control / H03 / H04 runtime boundaries explicit
- assign workers only to concrete atomic tasks
- prioritize first usable signal -> first canary -> first shipped content -> first revenue / learning signal
