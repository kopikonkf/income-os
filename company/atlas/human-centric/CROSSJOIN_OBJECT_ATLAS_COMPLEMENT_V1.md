# Cross-Join Matrix + Object Atlas Complement v1

Status: CANONICAL COMPLEMENT
Date: 2026-08-29
Owner: Atlas architecture
Primary consumer: Division-01 Digital Asset Intelligence

This document extends, but does not overwrite, the preserved Qwen foundation corpus under `company/atlas/human-centric/foundations/qwen-crossjoin-v1/`. The original files remain byte-exact provenance snapshots. Where an old foundation statement conflicts with this document or the current identity/orchestration contracts, this document and the current canon govern.

## 1. Dual-Atlas doctrine

The two Atlas planes solve different problems.

### Human-Centric Atlas — demand generator

The Human Atlas models why demand exists:

`HUMAN × ACTIVITY × OBJECT × PLACE × TIME × DEMOGRAPHIC × EMOTION × PROBLEM × INDUSTRY × COMMERCIAL INTENT`

Its output is not a production prompt. It is a bounded demand context or commercial hypothesis.

### Object-Centric Atlas — validated semantic primitive generator

The Object Atlas models what object primitives are valid enough to be considered:

`raw noun universe -> structural filtering -> semantic audit -> valid cleaned object primitives`

A cleaned object is not automatically commercially valuable and is not bound to a media type. It becomes valuable only after demand context, external signals, competition, feasibility, and commercial intent are considered.

## 2. Object is a queryable dimension, not a duplicated static list

The `OBJECT` dimension in the 10D Human Atlas MUST evolve into a queryable projection of the cleaned Object Atlas. Do not maintain an independent giant manually duplicated noun list in the Human Atlas.

Two discovery directions are valid:

### Demand-first

`human/problem/industry/intent anchor -> retrieve compatible objects -> constrain -> score`

### Supply-first

`cleaned object primitive -> retrieve compatible human demand contexts -> constrain -> score`

Both directions converge on the same Opportunity pipeline.

## 3. No exhaustive Cartesian explosion

The theoretical 10D candidate space is not an instruction to enumerate every combination. Exhaustive cross-join is forbidden as an operational strategy.

Use:

1. primary anchor selection;
2. bounded retrieval;
3. coherence constraints;
4. evidence-aware weighting;
5. bounded candidate expansion;
6. external opportunity signals;
7. deterministic demand scoring;
8. cognitive Worth-Making judgment;
9. bounded blueprint authoring.

The operational doctrine is:

`signal -> retrieve -> constrain -> rank -> expand -> falsify`

not:

`for every object × every human × every activity × ...`

## 4. Product Expression is a separate axis

An object primitive is media-agnostic. Do not encode `noun = PNG` or any equivalent assumption in Object Atlas.

A validated commercial opportunity is better represented as:

`Object Primitive × Human Demand Context × Product Expression = Commercial Asset Hypothesis`

Product Expression is downstream from Atlas and may include:

- L0 primitive static asset — isolated raster, transparent PNG, icon, vector;
- L1 variation — material, angle, state, color, style, orientation;
- L2 composition — contextual scene, multiple objects, commercial layout;
- L3 family/pack/bundle — coherent asset collection;
- L4 functional template — presentation, social, printable, UI, editable asset;
- L5 motion — animation, loop, stock video, explainer motion;
- L6 spatial/interactive — 3D object, game prop, AR component, scene object.

A future production engine may add capabilities without changing Atlas truth.

## 5. Long-tail doctrine

Single generic nouns increasingly represent a red-ocean discovery surface on mature stock marketplaces. A cleaned seed noun is therefore a semantic starting point, not the final keyword strategy.

Long-tail generation SHOULD combine a valid object with bounded modifier classes such as:

- function / job-to-be-done;
- customer or audience;
- industry;
- use case;
- problem solved;
- place/context;
- time/occasion;
- material;
- physical state;
- style;
- emotion or buyer trigger;
- demographic when commercially and ethically relevant;
- commercial format / product expression.

Examples:

`pill organizer` -> `weekly pill organizer for senior medication routine`

`soil moisture meter` -> `soil moisture meter for indoor herb garden beginners`

`cable organizer` -> `desk cable organizer for remote work setup`

Long-tail candidates are hypotheses. They MUST NOT inherit demand merely because their parent noun passed Object Atlas cleansing.

## 6. Opportunity pipeline

The intended closed loop is:

```text
Cleaned Object Primitive
        +
Human Demand Context
        |
        v
Bounded Long-Tail / Cross-Join Candidate Generation
        |
        v
Opportunity Signals
        |
        v
Demand Score + Evidence Confidence
        |
        v
Worth-Making Gate
        |
        v
Blueprint Authoring + Review
        |
        v
Founder Production Authorization
        |
        v
Hermes orchestration
        |
        v
Bounded Worker -> MUXIA -> Artifact
        |
        v
Platform receipts / ERVA / rejection evidence
        |
        +-------------- feedback --------------+
```

## 7. Engine separation

The following concerns MUST remain separate even when implemented in one repository:

- Object cleansing establishes semantic validity.
- Long-tail generation creates bounded keyword/context candidates.
- Opportunity Signals records external observations.
- Demand Score computes a reproducible ranking from evidence.
- Worth-Making is a governed commercial judgment, not merely a numeric score.
- Blueprint Authoring converts an approved hypothesis into an executable production specification.
- Blueprint Compilation serializes/validates/hash-locks authored semantics; it MUST NOT invent them.
- Hermes orchestrates prerequisites and anti-macet follow-up; it MUST NOT originate commercial judgment or prompt semantics.

## 8. Authority doctrine

### Division-01

Division-01 is the primary domain cognition author for asset-market commercial judgment. It owns:

- interpretation of Opportunity Signals;
- division-scoped Demand Score policy and calibration proposal;
- Worth-Making semantic judgment;
- buyer/use-case/commercial-positioning hypothesis;
- Blueprint semantics;
- master prompt and semantic variation plan.

### Executive

Executive is the second-line strategic reviewer, not the production operator. For a family that is proposed for production, Executive reviews/challenges:

- evidence sufficiency and contradictions;
- portfolio cannibalization or strategic overlap;
- scoring-model misuse;
- commercial thesis quality;
- Worth-Making judgment;
- Blueprint family coherence and overfitting;
- new medium/product-expression risk.

Executive emits a bounded review / challenge / NO-VETO / VETO-AND-REVISE artifact. It does not edit the production blueprint directly.

### Founder

Founder owns sovereign production authorization, spend, account action, publication/submission, and final ratification of material policy/model changes.

### Hermes

Hermes owns orchestration only:

- detect missing prerequisite receipt;
- request Division-01 cognition;
- request Executive review when required;
- dispatch deterministic/worker jobs;
- follow up stalled work;
- validate presence/freshness/hash relationships;
- draft Founder authorization requests;
- invoke production only after committed authority.

Hermes MUST NOT:

- assign or invent Worth-Making scores;
- resolve ambiguous evidence itself;
- author buyer/commercial thesis as if it were Division-01;
- create or rewrite master prompts/semantic variation plans;
- convert a legacy Kanban `done` status into proof that a cognitive gate passed.

### Worker

Workers execute bounded deterministic or implementation tasks. They may collect signals, run scoring code, expand candidates, serialize a blueprint, validate schemas/hashes, or operate MUXIA when authorized. They do not own commercial judgment.

## 9. Two-stage cognition for Worth-Making and Blueprint

For production-family promotion, the target chain is:

```text
Deterministic evidence / score
        |
        v
Division-01 AUTHOR
        |
        v
Executive CHALLENGE / NO-VETO
        |
        v
Deterministic compiler + hash lock
        |
        v
Founder authorization of exact hash
```

This reuses the stronger tool/memory/iteration characteristics of the Division-01 and Executive ChatGPT lines while keeping execution authority outside those cognition principals.

## 10. Evidence freshness

Every signal, score, Worth-Making receipt, Executive review, and Blueprint MUST identify:

- schema/version;
- principal or engine identity;
- source snapshot IDs;
- source/evidence timestamps;
- market/platform scope;
- confidence/staleness;
- exact upstream hashes where applicable;
- downstream artifact hash when produced.

A stale receipt never becomes fresh through conversational memory.

## 11. Current implementation note

As of 2026-08-29, this architecture is a target foundation. Some named engines are absent or only partial/heuristic. The executable-code audit is recorded in `docs/architecture/DIE_OPPORTUNITY_ENGINE_AUDIT_V1.md` and MUST be consulted before claiming an engine exists.