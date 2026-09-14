# DIE H01 Shutterstock Search Trends adapter v1

Task: H01-131B

## Scope

Source-specific adapter for the first-party Shutterstock Search Trends surface:

`https://www.shutterstock.com/trends`

The page publicly labels each observed trending search with:

- search term;
- Results;
- Demand;
- Growth.

Shutterstock contributor guidance separately describes Trending Keywords as keywords with the highest increase in customer search frequency. The adapter therefore treats published Demand/Growth as marketplace-native customer-search telemetry while preserving the important distinction that `Results` is a content/result-count supply metric, not a customer query count.

The adapter never synthesizes search volume, visitor-query counts, or hidden customer-query counts.

## Evidence semantics

Each normalized row uses:

- `signal_class = DEMAND`;
- `evidence_class = DIRECT_CUSTOMER_SEARCH_TELEMETRY`;
- `commercial_intent_tier = DIRECT_MARKETPLACE_QUERY`;
- `result_count_semantics = CONTENT_RESULT_COUNT_NOT_CUSTOMER_QUERY_COUNT`;
- `demand_band_semantics = SOURCE_PUBLISHED_SEARCH_DEMAND_BAND`;
- `growth_percent_semantics = SOURCE_PUBLISHED_SEARCH_FREQUENCY_GROWTH_PERCENT`;
- `customer_query_count = null`;
- `visitor_query_count = null`.

This is stronger than a popular-query ranking or generic popularity/content-needs proxy, and much stronger than a macro attention trend, but it is not equivalent to an exposed absolute search-volume count.

## H01-131A integration

The source owns:

- `runtime/market-signal-sources/shutterstock_search_trends_v1.json`;
- `lib/shutterstock_search_trends_v1.py`;
- source-specific tests.

When the capability is operational, acquisition flows through the unchanged H01-131A core for host/header guards, request budget, persistent rate limiting, cache TTL/freshness, immutable raw bytes, immutable normalized evidence, and acquisition receipts.

The parser reads static response text only. It does not use an authenticated browser, cookies, session values, browser profile state, autocomplete, or a browser DOM.

## Current compliance hold

As verified on 2026-09-14, Shutterstock's public Terms of Use prohibit data mining, robots, or similar data/image gathering and extraction methods in connection with the Site or Shutterstock Content. The public `/trends` page also returns HTTP 403 to direct unauthenticated HTTP probes from DIE Linux.

For that reason the canonical capability is intentionally:

`adapter_state = DISABLED`

This is a fail-soft source state. It must not block standalone production and it grants no credential, production, submission, publication, or spend authority.

Do not switch the capability to `ACTIVE` merely because the public page renders in a normal browser. Activation requires a compliant programmatic access path or explicit authorization/permission that covers automated acquisition.

## Extensibility correction

H01-131A documented H01-131B..H01-131H as per-source plug-ins, but the shared evidence schema enumerated only the two H01-131 baseline connectors and the H01-131A registry test required exactly those two files. H01-131B proves those constraints prevented the documented extension path.

The minimal compatible correction is:

- add `shutterstock_search_trends_v1` to the existing `connector_id` enum;
- require the two H01-131A baseline capabilities as a subset rather than the entire registry.

No acquisition-core behavior or shared cache/rate-limit/persistence semantics are changed.
