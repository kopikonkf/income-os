# DIE H01 Founder Console Demand Telemetry v1

Task: H01-141A

## Purpose

H01-141A replaces the Founder Console's status-only Demand Intelligence projection with a live, read-only projection of the canonical H01-133A daily state. It does not call or modify the Demand Engine, H01-130A materializer, H01-133 prioritizer, or daily selector.

The projection reads only immutable/pointer artifacts already produced by H01-133A:

```text
/var/lib/die/h01/demand-intelligence/daily/<day>/latest.json
  -> cycle.receipt.json
  -> demand-signal-ranking.v1.json
  -> daily-selector.frozen.json
  -> refresh-attempts/<attempt>.json
```

For source freshness and last-refresh timestamps it resolves the acquisition IDs already recorded by the H01-133A refresh attempt into the existing H01-131 immutable acquisition receipts under the signal state root. No source refresh is triggered by Console reads.

## Exposed telemetry

`GET /api/die/v1/demand` exposes:

- per-source health, acquisition status, effective freshness, evidence count and observed refresh time;
- effective evidence record count and connector distribution;
- queue size, materialized coverage, ranked/unranked counts and ranked coverage;
- confidence and signal-state distributions from the frozen materialization;
- top ranked noun projection directly from frozen selector `priority_rank` / `priority_score` rows;
- daily selection counts and selection-reason distribution;
- explicit zero-evidence state and `SOURCE_ORDER_FALLBACK` state;
- last refresh attempt status/time and provenance paths.

The Founder UI renders these as Demand Intelligence metric cards plus source-health and top-ranked-noun rows.

## Read-only boundary

The route remains GET-only. POST/PUT/PATCH/DELETE continue to fail closed. The projection has no production, submission, publication, spend, credential, refresh, materializer or selector authority.

Missing/incomplete daily state fails soft as an explicit unavailable/zero-evidence read state. It does not alter production validity or fallback policy.

## Performance boundary

The materialization is immutable and may contain tens of thousands of records. Derived confidence/top-rank telemetry is therefore cached in-process by immutable materialization path. New daily cycles use a new content-addressed path and naturally produce a new projection.

## Live acceptance — 2026-09-14

A shadow canary was run on isolated loopback port `20129` while the existing H01-141 shadow on `20128` and Factory Console on `8876` remained untouched.

The live H01-133A cycle `H01-DCYCLE-AC9AEEDEA79D6F52BA60FF98` reported:

- source health: 123RF FRESH/HEALTHY, Wikimedia FRESH/HEALTHY, Google Ads DEGRADED_AUTH_REQUIRED/UNKNOWN freshness;
- evidence records: 2;
- queue coverage: 43,005 / 43,005 materialized (100%);
- ranked/unranked: 5 / 43,000;
- confidence: MEDIUM 4, LOW 1, NONE 43,000;
- top ranked selected nouns from canonical selector priority ranks: food, transportation, vintage, animals;
- materialization-ranked count remains 5, while ranked-selected count is 4 because selector eligibility/produced-state semantics remain authoritative;
- daily selection: 4 `EVIDENCE_RANKED`, 96 `SOURCE_ORDER_FALLBACK`;
- zero evidence: false;
- fallback: ACTIVE, 96 selected;
- last refresh attempt: `H01-DREFRESH-E523A604A943925BC90C14AD`, `PASS_WITH_DEGRADED_SOURCES`.

A POST to the demand endpoint returned HTTP 405. The canary was terminated, port 20129 closed, and ports 8876 and 20128 remained listening.
