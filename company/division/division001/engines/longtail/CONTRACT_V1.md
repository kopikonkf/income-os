# Division01 Longtail / Cross-Join Foundation v1

Status: CANONICAL FOUNDATION
Batch: OE-B05
Milestone: OE-003 foundation only; candidate generation remains OE-B06

## 1. Purpose

OE-B05 establishes typed, bounded retrieval contracts for the Longtail / Cross-Join engine. It deliberately does **not** generate a Cartesian Human×Object universe and does not assign child demand.

Operational doctrine:

```text
signal -> retrieve -> constrain -> rank -> expand -> falsify
```

not:

```text
for every object × every Human Atlas dimension × every Product Expression
```

## 2. OE-003A — modifier ontology and candidate contract

`MODIFIER_ONTOLOGY_V1.json` defines 14 canonical modifier families:

- function;
- buyer;
- audience;
- industry;
- use case;
- problem;
- place;
- time;
- material;
- state;
- style;
- demographic;
- commercial intent;
- Product Expression.

Product Expression remains a separate L0–L6 axis and is not Object Atlas truth.

`die.division001.longtail-candidate.v1.schema.json` requires every generated child candidate to carry:

- parent Object Atlas retrieval lineage;
- Human Context retrieval lineage;
- typed modifiers;
- bounded generation budget;
- explicit Product Expression when selected;
- `evidence_state=REQUIRES_PHRASE_LEVEL_OE001_OE002`;
- `parent_demand.inherited_by_child=false`.

A child phrase is therefore a hypothesis, not a scored opportunity merely because the parent seed was cleaned or scored.

## 3. OE-003B — Object Atlas retrieval

`retrieve_object_seeds.py` reads the canonical Object Asset Engine SQLite database in `mode=ro` with `PRAGMA query_only=ON`.

The adapter:

- retrieves only `seeds.status='approved'`;
- supports bounded lookup by seed ID, canonical name, object class, and category prefix;
- limits each result set to at most 50;
- exposes no arbitrary SQL interface;
- pins/source-references a DB SHA-256 snapshot identity;
- does not require the Object Atlas dataset to be permanently final;
- intentionally omits legacy `demand_score` from returned seed records.

The last rule prevents the old Object Engine heuristic score from becoming inherited Longtail evidence. Phrase-level OE-001/OE-002 evidence is required later.

The adapter can query either a point-in-time Linux snapshot or the later authoritative Object Atlas DB without copying the dataset into Division01.

## 4. OE-003C — Human Atlas context retrieval

The Human Atlas canon defines an ontology/search space, not a fully enumerated context database. OE-B05 therefore introduces a small versioned `HUMAN_CONTEXT_REGISTRY_V1.json` as a **canon-seeded hypothesis registry**.

Every context is labeled `HYPOTHESIS`, with source-canon hashes. The initial six contexts are bounded examples aligned with current Cross-Join canon (remote-work cable organization, medication routine, indoor herb gardening, small-business packaging, education achievement, home ambience).

`retrieve_human_contexts.py`:

- supports supply-first retrieval by object name and demand-first anchors such as human/activity/place/industry/problem/commercial intent;
- caps results at 25;
- scores deterministic compatibility only;
- never labels compatibility as market demand;
- never materializes the 10D Cartesian product;
- returns a registry hash and retrieval receipt ID.

The registry is an extensible retrieval substrate. New contexts can be appended under version/hash control without changing the query contract.

## 5. Evidence boundary

```text
Object Atlas approved seed
        +
Human Atlas compatible HYPOTHESIS context
        +
typed modifiers / Product Expression
        ↓
Longtail candidate HYPOTHESIS
        ↓
REQUIRES PHRASE-LEVEL OE-001 SIGNALS
        ↓
OE-002 DEMAND SCORE
```

Neither Object Atlas approval nor Human context compatibility is market evidence.

## 6. Legacy Longtail v0 relation

The historical `longtail_expand.py` remains useful provenance for:

- canonical normalization;
- mandatory modifier classification;
- exact/parent-child dedupe;
- Jaccard near-duplicate controls;
- per-seed quotas;
- IP/trademark recheck;
- idempotent persistence.

Its small hard-coded `EXPANSIONS` dictionary is **not** the v1 generation strategy. OE-003D/E in OE-B06 will preserve useful guardrails while replacing hard-coded expansion as the core generator.

## 7. Handoff to OE-B06

OE-003D may only generate candidates from bounded Object retrieval + bounded Human context retrieval + typed modifiers. OE-003E then applies normalization/dedupe/IP/quota guardrails. OE-003F must request phrase-level OE-001 evidence and OE-002 score; parent demand inheritance remains forbidden.

## 8. OE-B06 completion

OE-003D-G are implemented and accepted by ENGINE_V1.md: bounded dynamic generation, structural/IP/quota guardrails, phrase-level OE-001/OE-002 integration, separate idempotent persistence, COMPLETE-only ranking, and deterministic synthetic canary replay. This foundation contract remains the retrieval/ontology layer and is not superseded in authority; it is consumed by the accepted engine.
