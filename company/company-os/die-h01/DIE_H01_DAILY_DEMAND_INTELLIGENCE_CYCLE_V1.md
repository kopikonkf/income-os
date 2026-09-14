# DIE H01 Daily Demand Intelligence Cycle v1

Task: H01-133A

## Purpose

H01-133A is the operational, deterministic daily cycle that turns the already-separated demand-intelligence stages into one bounded run:

```text
first-party refresh/cache
        ↓
H01-130A demand materialization
        ↓
H01-133 evidence prioritization
        ↓
frozen daily selector manifest
        ↓
durable immutable cycle receipt
```

It is a ranking and planning cycle only. It has no production-dispatch, submission, publication, or spend authority.

## Scheduler boundary

H01-016 established Mission Control as the single business scheduler. H01-133A therefore does **not** install a cron job, systemd timer, or competing Linux scheduler. The operational entry point is:

`company/company-os/die-h01/engineering/h01_133a_daily_demand_cycle.py`

Mission Control may invoke that bounded entry point according to business policy.

## Daily refresh

Default v1 refresh sources are the operational H01-130A prerequisite lane:

- `123rf_trending_search_v1` — marketplace-native trending labels;
- `wikimedia_pageviews_v1` — low-confidence attention proxy;
- `google_ads_keyword_historical_v1` — auth-aware macro search path.

The Wikimedia window is computed as the seven complete UTC days immediately preceding `day_key`.

Each source refresh is fail-soft. A source exception is reduced to `DEGRADED_REFRESH_EXCEPTION`; normal source-level degraded statuses such as `DEGRADED_AUTH_REQUIRED`, `DEGRADED_NO_EVIDENCE`, or stale-cache operation do not abort the daily cycle.

Refresh-attempt receipts are separate from the frozen daily cycle because `ACQUIRED` versus `CACHE_HIT_FRESH` is operational history, not daily-plan identity.

## Materialization and ranking

H01-133A consumes normalized H01-131 evidence through the merged H01-130A deterministic materializer. It does not create a second scoring engine.

The resulting `die.h01.demand-signal-ranking.v1` records are then passed unchanged into the merged H01-133 prioritization and H01 daily selector.

If there is no usable evidence:

```text
NO_EVIDENCE / UNRANKED
        ↓
H01-133 priority_score = null
        ↓
SOURCE_ORDER_FALLBACK
```

No-evidence is therefore a ranking state, not a production-blocking state.

## Frozen state layout

Canonical Linux state root:

`/var/lib/die/h01/demand-intelligence/daily`

Each content-addressed cycle is stored as:

```text
<day_key>/
  <cycle_id>/
    demand-signal-ranking.v1.json
    daily-selector.frozen.json
    cycle.receipt.json
  refresh-attempts/
    <refresh_attempt_id>.json
  latest.json
```

`cycle_id` is determined from the day, H01-130A materialization identity, H01-133 selector identity, queue identities, and produced-master set. Identical effective inputs therefore replay to the same immutable cycle.

`latest.json` is only a mutable pointer. Frozen cycle artifacts are collision-checked and cannot be silently overwritten with different content.

## Non-blocking invariants

The cycle records all of the following as immutable policy truth:

- source refresh failure does not block the cycle;
- missing market evidence does not block standalone production;
- queue identity is not mutated;
- Object Atlas validity is not mutated;
- rights and feasibility are not mutated;
- existing generation validity is not mutated;
- no production, submission, publication, or spend authority is granted.

## 2026-09-14 live acceptance

The final candidate was executed on DIE H01 Linux against the real 43,005-row H01-101 queue.

Operational refresh result:

- 123RF: `CACHE_HIT_FRESH`;
- Wikimedia: `CACHE_HIT_FRESH`;
- Google Ads: `DEGRADED_AUTH_REQUIRED`;
- refresh receipt: `PASS_WITH_DEGRADED_SOURCES`;
- daily cycle: `PASS`.

Frozen operational cycle:

- cycle: `H01-DCYCLE-AC9AEEDEA79D6F52BA60FF98`;
- H01-130A materialized ranked records: 5;
- unranked records: 43,000;
- daily selected: 100;
- evidence-ranked selected: 4;
- source-order fallback selected: 96;
- selector: `H01-DAILY-52BA25C07ED0E582F7D47BFB`.

The same operational inputs were replayed and produced the same frozen cycle and selector identity while generating a separate refresh-attempt receipt.

A separate isolated acceptance used an empty signal store with refresh disabled. It produced:

- cycle: `H01-DCYCLE-6C23E6BF801CF91113F27365`;
- ranked materialized: 0;
- evidence-ranked selected: 0;
- source-order fallback selected: 100;
- selector: `H01-DAILY-AE6001AE68881004255CAF53`;
- status: `PASS`.

This proves that complete evidence unavailability does not block standalone production planning.
