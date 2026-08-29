# DIE Opportunity Intelligence Engine Architecture v1

Status: FOUNDATION / BUILD TARGET
Date: 2026-08-29
Primary domain: Division-01 Digital Asset Intelligence
Canonical inputs: Human-Centric Atlas, Object-Centric Atlas, Platform Contracts, governed receipts

## 1. Goal

Build a reusable opportunity-intelligence pipeline that converts validated semantic primitives and human demand contexts into evidence-backed, executable asset hypotheses without allowing Hermes or a low-reasoning runtime model to substitute for governed commercial cognition.

The architecture separates deterministic engines, bounded cognition principals, orchestration, execution, and sovereign authority.

## 2. Target engine graph

```text
Object Atlas cleaned seeds -----------------------------+
                                                        |
Human Atlas demand contexts ----------------------+     |
                                                   |     |
                                                   v     v
                                      Longtail / Cross-Join Candidate Engine
                                                   |
                                                   v
                                      Opportunity Signals Engine
                                                   |
                                                   v
                                         Demand Score Engine
                                                   |
                                                   v
                               Division-01 Worth-Making Authoring
                                                   |
                                                   v
                                  Executive Challenge / NO-VETO
                                                   |
                                                   v
                               Division-01 Blueprint Authoring
                                                   |
                                                   v
                                  Executive Blueprint Review
                                                   |
                                                   v
                             Deterministic Blueprint Compiler
                                                   |
                                                   v
                                   Founder Authorization
                                                   |
                                                   v
                                      Hermes Orchestration
                                                   |
                                                   v
                                    Worker -> MUXIA -> Artifact
                                                   |
                                                   v
                                  receipts / ERVA / rejection
                                                   |
                                                   +---- feedback ---->
```

The longtail and signals stages may iterate: collect coarse seed signals -> prioritize expansion -> collect phrase-level signals -> re-score.

## 3. Authority matrix

| Component | Semantic owner | Reviewer / governance | Executor | Hermes role | Founder role |
|---|---|---|---|---|---|
| Object cleansing | Object Atlas contract | Atlas/Architect policy | Object Engine worker | observe/follow-up only | policy/credential gates if needed |
| Object Longtail Generator | Division-01 policy + Object Atlas inputs | Executive only for material model/policy changes | deterministic engine/Worker | schedule, route receipts | ratify material policy changes |
| Opportunity Signals Engine | Division-01 domain policy | Executive can challenge source/model design | connectors/Worker | schedule bounded collection | approve sensitive credential/spend/ToS lanes |
| Demand Score Engine | Division-01 scoring policy | Executive reviews model/weight promotion | deterministic scorer | route/freshness enforcement | ratify material threshold/policy change |
| Worth-Making Gate | **Division-01 AUTHOR** | **Executive CHALLENGE / NO-VETO / REVISE** | cognition principals + deterministic veto precheck | request/route/verify receipts only | production authorization later |
| Blueprint Authoring | **Division-01 AUTHOR** | **Executive family-level review** | Division-01 cognition | request/route only | exact-hash production authorization |
| Blueprint Compilation | authored semantics are immutable | schema/hash contract | Worker/OpenCode/deterministic compiler | dispatch compiler | none until authorization |
| Production | authorized blueprint only | QA/contracts | Worker + MUXIA | orchestrate | sovereign authorization / QC / submission |

Capability is not authority. A runtime capable of producing text or code does not own the commercial decision.

## 4. Engine 01 — Opportunity Signals Engine

### Purpose

Record current, platform-scoped external observations for candidate seeds/phrases.

### Inputs

- candidate phrase / seed ID;
- target platform/provider list;
- locale/language;
- query timestamp requirement;
- allowed acquisition method;
- Platform Contract / ToS boundary.

### Example signal classes

- search-result supply density;
- query/autocomplete suggestion presence;
- related-query observations;
- result-page composition / asset-type mix;
- visible popularity/download proxies where legitimately exposed;
- trend/search-engine indicators;
- buyer-language observations;
- platform fit / acceptance constraints;
- competition-gap observations.

### Output contract

Target schema: `die.division001.opportunity-signals.v1`.

Every observation carries:

- `signal_id`;
- `candidate_id` / `phrase_id`;
- `platform_id`;
- `signal_type`;
- raw/normalized value;
- unit / interpretation;
- acquisition method;
- observed timestamp;
- source reference;
- evidence label;
- confidence;
- expiry/staleness window;
- collector identity;
- policy/ToS profile version.

The engine records observations; it does not decide Worth-Making.

### Acquisition boundary

No private-token extraction, protective-measure bypass, credential scraping, stealth, or prohibited unattended consumer-output scraping. Where a platform requires operator-controlled acquisition, the engine consumes operator-created evidence receipts rather than bypassing the platform.

## 5. Engine 02 — Demand Score Engine

### Purpose

Produce a reproducible ranking from normalized evidence, not commercial judgment by itself.

### Target output

`die.division001.demand-score.v1`

Required fields:

- candidate/phrase ID;
- scoring model/version;
- each component score;
- each component evidence refs;
- missing-signal penalties;
- staleness penalties;
- confidence interval/band or confidence label;
- final normalized score;
- `UNKNOWN` components rather than invented defaults;
- timestamp and expiry.

### Design rule

The current Object Engine heuristic v0 may provide calibration fixtures but MUST NOT become the production scoring truth unchanged.

Recommended component families:

- external demand evidence;
- marketplace supply/competition;
- buyer/commercial intent;
- niche specificity;
- trend/seasonality;
- visual/product-expression feasibility;
- platform eligibility;
- evidence confidence/freshness;
- saturation penalty;
- rights/risk penalty where numeric treatment is appropriate.

Hard safety/rights vetoes remain outside a purely numeric score.

## 6. Engine 03 — Object Atlas Longtail Keyword Generator

### Purpose

Transform cleaned, commercially plausible seed nouns into bounded, niche-oriented and customer-need-oriented phrase candidates.

### Inputs

- cleaned Object Atlas seed;
- object taxonomy and synonyms;
- Human Atlas context retrieval;
- permitted modifier taxonomy;
- initial Opportunity Signals / Demand Score when available;
- language/locale;
- max expansion budget.

### Modifier taxonomy

At minimum:

- function;
- buyer/customer;
- audience;
- industry;
- use case;
- problem;
- place/context;
- time/occasion;
- material;
- state;
- style;
- demographic where relevant;
- commercial intent;
- product expression.

### Guardrails inherited from v0

Preserve useful concepts from `longtail_expand.py`:

- canonical normalization;
- exact duplicate rejection;
- parent-child redundancy rejection;
- mandatory modifier classification;
- near-duplicate similarity review/reject;
- per-seed quota;
- IP/trademark recheck;
- idempotent persistence.

### Replace

Remove the hard-coded small `EXPANSIONS` dictionary as the core generation strategy.

Target behavior:

`clean seed -> retrieve compatible modifier contexts -> bounded generate -> dedupe -> phrase-level signal collection -> demand score -> retain/reject`

The generator creates hypotheses, not demand facts.

## 7. Engine 04 — Worth-Making Gate

### Nature

Worth-Making is hybrid: deterministic evidence/veto checks plus high-quality bounded cognition.

It MUST NOT be a Hermes decision.

### Stage A — deterministic precheck

Validate:

- required signal/score freshness;
- mandatory evidence types;
- rights/IP/trademark hard vetoes;
- safety/deception vetoes;
- product-expression/platform eligibility;
- production-tool rights;
- spend authorization requirement;
- falsifiable buyer/use-case hypothesis.

### Stage B — Division-01 semantic authoring

Division-01 produces `die.division001.worth-making.v1` with:

- candidate/family ID;
- source signal + demand-score refs;
- buyer/job-to-be-done;
- commercial-use hypothesis;
- competition interpretation;
- differentiation thesis;
- production feasibility;
- product-expression recommendation;
- factor scores with evidence labels;
- hard-veto result;
- total score;
- confidence;
- cheapest falsification;
- recommendation: validate / research / defer;
- principal ID + snapshot/hash provenance.

### Stage C — Executive review

Executive emits `die.executive.worth-making-review.v1`.

For any family proposed for production, Executive MUST challenge at least:

- evidence weakness/contradiction;
- score inflation or double counting;
- portfolio overlap/cannibalization;
- strategic opportunity cost;
- medium/product-expression fit;
- assumptions that should remain hypotheses.

Review result:

- `NO_VETO`;
- `REVISE`;
- `VETO_PENDING_EVIDENCE`;
- `ESCALATE_FOUNDER`.

Executive does not rewrite the Division artifact; revision returns to Division-01.

## 8. Engine 05 — Blueprint Engine

### Separate authoring from compilation

The term Blueprint Engine refers to a governed pipeline, not a single local LLM script.

#### A. Division-01 Blueprint Authoring

Input requires a passing Worth-Making artifact + Executive review.

Division-01 authors:

- buyer/use case;
- asset family thesis;
- chosen Product Expression / complexity level;
- visual/composition constraints;
- master prompt;
- semantic variation plan;
- negative constraints;
- batch/canary recommendation;
- platform packaging/metadata direction;
- QA requirements;
- falsification metrics;
- source/evidence refs.

Target schema: `die.division001.blueprint-authoring.v1`.

#### B. Executive Blueprint Review

Target: `die.executive.blueprint-review.v1`.

Review family-level strategy, internal contradictions, differentiation, portfolio overlap, prompt overfitting, and whether the proposed expression actually tests the Worth-Making thesis.

Executive returns NO_VETO or revision request; it does not edit the prompt directly.

#### C. Deterministic Blueprint Compiler

Worker/OpenCode may:

- serialize exact authored semantics;
- normalize schema;
- verify source hashes;
- validate variation coverage;
- validate engine capability/contract refs;
- produce final `die.m001.asset-blueprint.v1` or successor schema;
- hash-lock the artifact.

Compiler MUST fail if it would need to invent missing semantic content.

#### D. Founder gate

Founder authorizes the exact compiled blueprint hash, batch/canary scope, spend ceiling, and irreversible action boundaries.

## 9. Hermes Operator v2 integration contract

Hermes remains the anti-macet orchestrator.

The operator envelope MUST evolve from Kanban-only inference to prerequisite receipts.

Minimum prerequisite set for production-family progression:

- fresh Opportunity Signals receipt;
- Demand Score receipt;
- Division-01 Worth-Making receipt;
- Executive Worth-Making review;
- Division-01 Blueprint Authoring receipt;
- Executive Blueprint Review;
- deterministic Blueprint Compile receipt/hash;
- Founder production authorization.

A Kanban card is workflow metadata, not proof of cognitive completion.

### Deterministic authority map

`action_type -> authority_class` MUST be hard-coded/config-canonical and validated by the finalizer. The agent must never be trusted to self-label an action's authority.

### Suggested prerequisite states

To avoid unnecessary state explosion, keep the high-level state machine but add deterministic `next_required_receipt` and `intelligence_stage` fields:

- `RESEARCH_PENDING / SIGNALS`;
- `RESEARCH_PENDING / DEMAND_SCORE`;
- `RESEARCH_PENDING / WORTH_MAKING`;
- `BLUEPRINT_PENDING / DIVISION_AUTHORING`;
- `BLUEPRINT_PENDING / EXECUTIVE_REVIEW`;
- `BLUEPRINT_PENDING / COMPILE`;
- `AWAITING_AUTHORIZATION`.

Hermes chooses which request to route from this deterministic prerequisite map; it does not decide the missing commercial content.

## 10. Target source layout

Initial Division-01-specific implementation:

```text
company/division/division001/
  engines/
    opportunity-signals/
    demand-score/
    worth-making/
    blueprint/

company/atlas/object-centric/object-asset-engine/
  ...
  longtail/ or successor scoring module
```

Shared schemas may later be promoted to company-level contracts only after a second division proves reuse.

## 11. Build roadmap

### OE-001 — Opportunity Signals Contract + fixture collectors

Deliver schemas, normalized receipt registry, staleness semantics, two low-risk fixture/platform adapters, tests.

### OE-002 — Demand Score v1

Consume OE-001 receipts; replace invented priors with explicit UNKNOWN/fresh evidence handling; calibrate against known examples.

### OE-003 — Object Longtail v1

Use cleaned Object Atlas seeds + Human modifier contexts; preserve dedup guardrails; produce bounded candidate phrases and request phrase-level signals.

### OE-004 — Worth-Making v1

Implement deterministic precheck, Division-01 authoring contract, Executive review contract, receipt validation, and failure paths.

### OE-005 — Blueprint v1

Implement Division authoring contract, Executive review, deterministic compiler/hash lock; no prompt invention by Worker/Hermes.

### OE-006 — Hermes Operator v2

Add prerequisite receipt registry, deterministic authority mapping, legacy-card quarantine, canonical OS-neutral prepare wrapper, and regression tests.

### OE-007 — Closed-loop canary

One candidate must pass signals -> score -> longtail/context -> Worth-Making -> Executive -> blueprint -> Founder hash authorization -> Worker/MUXIA synthetic or governed production canary with complete receipts.

## 12. Non-goals

- no exhaustive 10D materialization;
- no automatic marketplace submission;
- no Hermes-authored Worth-Making or prompts;
- no Executive worker control;
- no Worker strategic authority;
- no scoring model that silently substitutes static guesses for missing evidence;
- no coupling of Object Atlas nouns to raster-only production.

## 13. Executable task graph

The authoritative atomic execution DAG and conversational batch map are docs/architecture/DIE_OPPORTUNITY_ENGINE_TASK_GRAPH_V1.md and company/muxia-task-graph-v1.json. Architecture text alone is never completion evidence.
