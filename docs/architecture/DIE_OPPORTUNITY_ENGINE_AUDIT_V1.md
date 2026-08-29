# DIE Opportunity / Worth-Making / Blueprint Engine Audit v1

Date: 2026-08-29
Scope: GitHub canon/main, live `C:\DIE`, Windows Object Asset Engine, Hermes `income-operator` profile/runtime
Status: EXECUTABLE-CODE AUDIT

## Executive finding

The current system has stronger governance documents than executable intelligence engines.

| Capability | Current status | Executable implementation | Audit conclusion |
|---|---|---|---|
| Opportunity Signals | ABSENT | none | Must be built |
| Demand Score | PARTIAL / HEURISTIC V0 | Object Engine `scripts/scoring/demand_score.py` | Real code, but not a live market-signal engine |
| Worth-Making Gate | DOC + VALIDATOR ONLY | historical scorecards; `m001_loop.py` validates supplied score/receipt | No real Worth-Making decision engine |
| Blueprint Engine | ARTIFACT + VALIDATOR ONLY | historical `ASSET_BLUEPRINT.json`; `m001_loop.py` validates/hash-locks | No semantic blueprint generator |
| Object Longtail Generator | PARTIAL / CURATED V0 | Object Engine `scripts/scoring/longtail_expand.py` | Real code, but not scalable or signal/customer-specific |
| Hermes Proactive Operator | REAL / ACTIVE | profile cron + `C:\DIE\bin\die_operator_tick.py` | Orchestrator exists, but current evidence model is insufficient for new engine architecture |

## 1. Opportunity Signals Engine — ABSENT

Repository search found no executable Opportunity Signals collector or normalized signal registry.

There is no canonical implementation that currently collects and receipts current observations such as:

- platform search-result density;
- autocomplete/query suggestions;
- marketplace supply counts;
- trend velocity;
- buyer/search intent proxies;
- platform-specific competition gaps;
- keyword-level freshness/staleness;
- external search-engine observations.

The Object Engine `demand_score.py` explicitly states that real marketplace signal collection is a future task.

Conclusion: references to `Opportunity Score`, `search`, `marketplace`, or platform demand in documents MUST NOT be interpreted as proof that an Opportunity Signals Engine exists.

## 2. Demand Score Engine — PARTIAL / HEURISTIC V0

Executable code exists at:

- Windows: `D:\object-asset-engine\scripts\scoring\demand_score.py`
- Linux-ready canon: `company/atlas/object-centric/object-asset-engine/source/scripts/scoring/demand_score.py`

Formula implemented:

`0.30*search + 0.25*marketplace + 0.20*intent + 0.10*trend + 0.10*feasibility + 0.05*seasonality - risk - saturation`

However the actual v0 inputs are mostly:

- `HIGH/MED` signal mapping;
- static intent priors by object class/category;
- a small hard-coded trend boost dictionary;
- a small hard-coded saturation dictionary;
- a small hard-coded seasonality dictionary;
- heuristic production-feasibility rules.

The source itself says:

- signals v0 derive from Qwen demand research + heuristic priors;
- wiki seeds without external signals are conservative/speculative;
- real marketplace signal collection is a later task.

Conclusion: this is a useful scoring prototype, not the target Demand Score Engine. It must be refactored to consume normalized, timestamped Opportunity Signal receipts and emit component-level evidence/confidence/staleness.

## 3. Worth-Making Gate — NO EXECUTABLE DECISION ENGINE

Current artifacts include:

- `company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md` H4;
- `docs/missions/M001_BLUEPRINT_BATCH1_V2.md` section 5;
- historical `C:\DIE\workspaces\M001-WORTHMAKING\TRIAGE.md`;
- historical `C:\DIE\workspaces\M001-WORTHMAKING\DEEP_SCORE.md`;
- `bridge/income_os_bridge/m001_loop.py` validation logic.

Repository/live-code search found:

- no `WorthMakingEngine` class;
- no `def worth...` decision function;
- no engine that gathers evidence and computes/justifies the gate end-to-end.

`m001_loop.py` does NOT decide Worth-Making. It only verifies that an input blueprint already contains:

- a numeric score >=75;
- `hard_vetoes_clear=true`;
- a non-empty `receipt_ref`.

Historical M-001 scorecards are research artifacts. They are not a reusable engine contract.

Authority provenance is also legacy/ambiguous: the historical blueprint says `evaluated_by=division01-worker:income-operator:t_c5a7a93b`, while the old T2/T2-R2 Kanban cards were assigned to `income-operator`. That is not sufficient future evidence that the Division-01 principal authored the commercial judgment.

Conclusion: Worth-Making requires a new governed engine/receipt chain with Division-01 as semantic author and Executive as second-line reviewer before family promotion.

## 4. Blueprint Engine — NO SEMANTIC GENERATOR

Historical executable artifact exists:

`C:\DIE\workspaces\M001-U1-001\ASSET_BLUEPRINT.json`

Observed fields include:

- schema `die.m001.asset-blueprint.v1`;
- blueprint ID `BP-M001-U1-MASTER13-R1`;
- Worth-Making score 93;
- a 460-character master prompt;
- 20 semantic variations;
- batch size 20;
- canary size 5;
- engine `proxima:chatgpt:3211`.

But the artifact states:

`compiled_by=opencode-integrator`

and no canonical semantic Blueprint generator was found.

`m001_loop.py` only validates and hash-locks a blueprint that already exists. It does not:

- research buyer demand;
- decide the product expression;
- author the master prompt;
- create the semantic variation plan;
- resolve evidence contradictions.

Conclusion: the target Blueprint Engine must separate:

1. Division-01 semantic authoring;
2. Executive review/challenge;
3. deterministic/Worker compilation, schema validation, and hash lock;
4. Founder authorization of the exact hash.

OpenCode/Worker may compile a blueprint but MUST NOT invent its commercial thesis or prompt semantics.

## 5. Object Longtail Generator — PARTIAL / CURATED V0

Executable code exists at:

`company/atlas/object-centric/object-asset-engine/source/scripts/scoring/longtail_expand.py`

Useful existing features:

- canonical phrase normalization;
- exact/parent-child duplicate controls;
- modifier classification;
- Jaccard near-duplicate guardrails;
- per-seed quota;
- basic IP-term blocklist;
- idempotent DB writes.

But candidate generation is currently a hard-coded `EXPANSIONS` dictionary for only a handful of seeds such as bottle, trophy, candle, shopping bag, and question mark.

It does not yet:

- expand from the cleaned noun DB at scale;
- retrieve Human Atlas customer/use-case contexts;
- use external opportunity signals;
- generate niche/customer-specific long tails dynamically;
- rank long tails by fresh competition/demand evidence;
- learn from marketplace receipts.

Conclusion: keep the dedup/modifier guardrail concepts, replace the curated dictionary with a bounded retrieval/generation/ranking engine over cleaned object seeds + Human Atlas context + Opportunity Signals.

## 6. Hermes proactive operator — ACTIVE, but not yet aligned to the target engine receipt chain

### Actual runtime

Hermes profile cron job:

- name: `die-proactive-operator-v1`;
- cadence: `*/30 * * * *`;
- model snapshot: `nemotron-3-ultra-free`;
- mode: agent-enabled / PROPOSE_ONLY;
- workdir: `C:\DIE`.

The cron uses profile-local wrapper:

`C:\Users\aethers\AppData\Local\hermes\profiles\income-operator\scripts\die_operator_prepare.py`

That 216-byte wrapper hardcodes `C:\DIE\bin` and delegates to:

`C:\DIE\bin\die_operator_tick.py prepare`

The wrapper itself is not currently Git-canonical.

### What `die_operator_tick.py` does well

- bounded envelope;
- no network in the tick collector;
- exact canon hashes;
- Kanban snapshot;
- Founder decisions;
- platform receipts;
- pause/lock semantics;
- max one state transition;
- max three mutations;
- final receipt and event logging;
- production invocation only after separate Founder authority path.

### Current alignment gaps

#### Gap A — Kanban `done` can masquerade as cognition completion

The current envelope includes Kanban card status but no first-class structured receipts for:

- Opportunity Signals;
- Demand Score;
- Division-01 Worth-Making;
- Executive Worth-Making review;
- Division-01 Blueprint authoring;
- Executive Blueprint review.

Recent runtime output shows Hermes inferred old T1/T2/T2-R2 work was complete and selected `CREATE_BLUEPRINT_COMPILE_CARD` based on legacy cards/artifacts.

A legacy Kanban `done` status MUST NOT be sufficient proof that a cognitive gate passed.

#### Gap B — action authority is partly LLM-asserted

The schema allows the agent to emit both `action_type` and an `authority` enum. Finalization rejects an action if it labels itself `FORBIDDEN`, but the code does not currently enforce a fixed canonical mapping of `action_type -> allowed authority class`.

`ACTION_TYPES` is defined, but the current finalizer does not use it as a hard authority map.

Target: authority classification must be deterministic from canon, never self-declared by the model.

#### Gap C — no Executive review receipts

The envelope currently collects Founder decisions but not Executive family-review receipts. Therefore the runtime cannot enforce the intended Division-01 AUTHOR -> Executive CHALLENGE/NO-VETO -> Founder authorization chain.

#### Gap D — state machine is too coarse for the new engine graph

`RESEARCH_PENDING -> BLUEPRINT_PENDING` hides distinct missing prerequisites such as signals, scoring, Worth-Making, and Executive review.

The v2 operator may keep a small top-level state set, but it MUST expose `next_required_receipt` or equivalent deterministic prerequisite status so Hermes knows exactly what to request.

#### Gap E — historical Windows wrapper is non-canonical and OS-bound

`die_operator_prepare.py` lives inside the mutable Hermes profile and hardcodes Windows `C:\DIE`. Linux migration already established a canonical Hermes source/config split; this wrapper must be replaced by a canonical OS-neutral entry point before Linux Hermes activation.

## 7. Current authority truth

Existing canon already contains the core correct boundary:

- Division-01: research, opportunity scoring, Worth-Making judgment, exact Asset Blueprint semantics/master prompt;
- Hermes: orchestration;
- Worker: bounded execution/compilation;
- Founder: production/spend/submission authority.

The missing piece is the Executive second-line review contract and executable receipt enforcement.

The old Qwen foundation phrase `Worth-Making Gate (Hermes Decision Engine)` is superseded by current canon. Hermes is NOT the Worth-Making decider.

## 8. Required build order

Recommended dependency order:

1. Opportunity Signals Engine v1;
2. Demand Score Engine v1 consuming signal receipts;
3. Object Longtail Generator v1 consuming cleaned object seeds + Human contexts;
4. Worth-Making Gate v1 with Division-01 author + Executive review;
5. Blueprint Engine v1 with Division-01 author + Executive review + deterministic compiler;
6. Hermes Operator v2 receipt/prerequisite refactor;
7. only then autonomous production-family progression.

Do not build Blueprint automation on top of heuristic demand and legacy Kanban status.