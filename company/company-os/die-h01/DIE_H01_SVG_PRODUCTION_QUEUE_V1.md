# DIE-H01 Standalone SVG Production Queue v1

Status: H01-101 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

Export the Founder-locked H01-100 supply frontier into one deterministic, read-only production queue without changing Object Atlas source truth.

Source selection is exactly:

```text
/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db
candidate_seeds.wave3_status = eligible
```

At H01-101 acceptance this is exactly **43,005** rows.

Every queue row carries the fixed production contract:

```text
media  = VECTOR
mode   = VECTOR_OBJECT
form   = SINGLE
preset = CLEAN_STOCK_VECTOR_V1
```

Demand scores, families, sets and Product Expression do not affect this initial order.

## Stable identity and order

Each source `candidate_seeds.id` is preserved. Queue identity is:

```text
queue_item_id = H01-SVGQ-<candidate_seed_id>
```

The idempotency key is SHA-256 over queue schema + candidate ID + the fixed production contract. It does not depend on queue position.

Queue order is deterministic and intentionally non-intelligent:

```sql
ORDER BY raw_noun_id ASC, id ASC
```

This avoids silently introducing demand/model judgment into H01-101. Later demand intelligence may rank remaining work without changing queue item identity or invalidating produced semantic masters.

## Rights and feasibility gates

H01-101 does not reclassify Atlas nouns. It projects the accepted Wave-3 gate evidence:

- `rights=PASS` requires `ip_risk=none`.
- `feasibility=PASS` requires `wave3_status=eligible` and a non-pending/non-blocked Wave-3 `suitability` result.
- `dispatch_eligible=true` requires both gates PASS.

Wave-3 eligibility already applied trademark/IP and isolated-object suitability gates. A Wave-2 `source_tier=review` does **not** become a new H01 hold when Wave-3 has explicitly promoted the row to `eligible`; 338 such rows exist and retain their source-tier evidence in the queue.

The exporter fails closed if the eligible row count is not exactly 43,005, IDs/raw IDs/names are not unique, a canonical name is blank, the source DB fails `PRAGMA quick_check`, or an existing queue differs from the deterministic export.

## Source immutability

The exporter opens SQLite using `mode=ro` plus `PRAGMA query_only=ON`. Queue generation writes only under:

```text
/var/lib/die/h01/queues/svg-standalone-v1/
```

The accepted export proved the source DB SHA-256 and size/mtime/ctime tuple unchanged before and after export.

## Idempotency

First accepted run: `CREATED`.

Repeated run against the same source selection and production contract: `UNCHANGED`, with identical queue and manifest bytes.

If only one output file exists or existing bytes differ, export fails closed (`E_PARTIAL_EXISTING_QUEUE` / `E_EXISTING_QUEUE_CONFLICT`). It never silently rewrites a production queue.

## Accepted artifacts

```text
/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl
/var/lib/die/h01/queues/svg-standalone-v1/manifest.json
```

The files are read-only mode `0444`. Mutable dispatch/progress state belongs to later scheduler/runtime state, not inside this source queue.
