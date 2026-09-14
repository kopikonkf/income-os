# DIE H01 Demand Signal Materializer v1

Task: H01-130A

## Purpose

H01-130A converts normalized H01-131 market evidence into real `die.h01.demand-signal-ranking.v1` records keyed to immutable H01-101 queue identities. It is a ranking overlay only. It never changes Object Atlas validity, queue identity, rights, feasibility, generation validity, production eligibility, submission, publication, or spend authority.

The implementation is deterministic Python. No LLM is used in the materialization or scoring path.

## Matching boundary

Version 1 deliberately uses `EXACT_NORMALIZED_TEXT_ONLY` matching:

- an evidence `query` may match a queue noun exactly after case/punctuation normalization;
- explicit first-party `terms` / `popular_queries` / `queries` / `related_searches` may match exactly;
- explicit `trends` / `trend_labels` / `categories` / `labels` may match exactly;
- no fuzzy semantic matching, stemming, plural guessing, embeddings, autocomplete expansion, or LLM interpretation is allowed.

This makes false-positive demand inference much harder. Phase-0 nouns with no matched evidence remain valid standalone production candidates and are emitted honestly as `NO_EVIDENCE / UNRANKED`.

## Source hierarchy

The deterministic commercial-intent hierarchy is:

```text
DIRECT_MARKETPLACE_QUERY        0.95
MARKETPLACE_POPULAR_QUERY       0.75
MARKETPLACE_POPULARITY_PROXY    0.55
MACRO_SEARCH                    0.45
ATTENTION_PROXY                 0.30
LEGACY_PRIOR                    0.15
```

These coefficients are ranking weights, not probabilities and not fabricated search volume.

Normalized evidence semantics may **downgrade** a broad capability tier but may never promote above the source capability. Example: an Adobe capability may be broadly classified as a marketplace popularity proxy while a particular normalized record explicitly says `macro_trend=true`; that observation is scored as `MACRO_SEARCH`, not as a stronger marketplace-popularity signal.

`DISABLED` and `ADAPTER_PENDING` source capabilities never contribute even if diagnostic evidence files exist. `ACTIVE` and authorized-context source evidence may contribute when valid evidence has been materialized.

## Evidence strength

A contribution is bounded by:

```text
source tier weight
? declared evidence confidence
? freshness factor
? exact-match type factor
? bounded quantitative factor when the source actually exposes one
```

Important constraints:

- 123RF `UNRANKED_PRESENTATION_ORDER` is **not** converted into query magnitude or ranking strength. Exact matching terms receive equal source contribution.
- Wikimedia pageviews are treated only as attention strength. Pageviews are never re-labelled as commercial search demand.
- stale-only evidence is preserved for lineage but cannot produce a ranked record because the H01-130 contract requires fresh evidence for `RANKED`.
- corroborating fresh evidence combines through a bounded probabilistic union and can never exceed 1.0.

## Discoveries

H01-130A does not generate buyer, use-case, or family hypotheses. Those buckets remain empty in this phase. Evidence-grounded contextual expansion belongs to later pipeline stages; H01-130A must not hallucinate Human Atlas semantics.

## Runtime

Canonical Linux inputs:

- queue: `/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl`
- normalized signals: `/var/lib/die/h01/demand-intelligence/signals`

Canonical materialized output:

- `/var/lib/die/h01/demand-intelligence/materialized/demand-signal-ranking.v1.json`

Operational proof for H01-130A intentionally used only the canonical v1 prerequisites:

- `123rf_trending_search_v1`
- `wikimedia_pageviews_v1`

The materializer processed all 43,005 queue items from real live evidence and produced five ranked nouns: `cat`, `food`, `transportation`, `vintage`, and `animals`. Marketplace-native 123RF evidence scored above Wikimedia attention evidence, proving the hierarchy in real output rather than only in unit tests.

The existing H01-133 daily selector consumed the materialization without modification. After excluding 100 already-generated masters, it selected four evidence-ranked nouns and 96 source-order fallback nouns. Missing market evidence therefore remains non-blocking.
