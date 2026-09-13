# DIE H01 Human Atlas Demand Context Join v1

Task: H01-132

H01-132 joins bounded Human Atlas context to an existing H01-101 queue item without changing queue identity, Object Atlas validity, rights, feasibility, or standalone production eligibility.

The join reuses the canonical bounded Human Atlas retrieval engine under Division-01. H01 does not create a second Human Atlas corpus.

## Contract

Input is one existing `queue_item_id`, canonical noun, optional source candidate ID, and a bounded result limit. H01 applies a stricter maximum of 12 contexts even though the legacy retrieval engine permits up to 25.

Output schema: `die.h01.human-atlas-demand-context.v1`.

Each returned context preserves:

- Human Atlas `context_id` and deterministic context hash;
- compatibility score;
- human/persona hypothesis;
- activity;
- problem;
- industry;
- commercial intent;
- target buyers and buyer jobs;
- product-expression hints.

## Non-blocking boundary

Human Atlas context is hypothesis context, not observed market demand. Every output therefore states:

- `market_evidence=false`;
- `rank_authority=NONE`;
- `supply_first_independent=true`;
- all identity/rights/feasibility/production-blocking effects = `NONE`;
- production/submission/publication/spend authority = false.

A noun with no compatible Human Atlas context emits `NO_CONTEXT` and remains valid for supply-first standalone production.

H01-133 may later combine this bounded context with H01-131 external signal evidence. H01-132 itself does not compute demand rank and does not promote a semantic family.

## No Cartesian expansion

The operational direction is supply-first:

`existing H01-101 noun -> bounded Human Atlas retrieval -> top-K context hypotheses`

It never materializes `Object Atlas × Human Atlas` or any 10D Cartesian product.
