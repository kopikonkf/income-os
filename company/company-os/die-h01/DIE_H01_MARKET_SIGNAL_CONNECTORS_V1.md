# DIE-H01 Bounded Official Market Signal Connectors v1

Status: H01-131 acceptance candidate
Date: 2026-09-13

H01-131 adds a bounded connector layer underneath the non-blocking H01-130 Demand Signal Engine. The layer accepts supported structured sources and does not make autocomplete scraping, search-result DOM scraping, marketplace DOM scraping, or undocumented endpoints a core dependency.

## Connector registry

### `wikimedia_pageviews_v1`

Source: Wikimedia Analytics API, an official open structured API. The connector uses per-article pageview metrics as a `TREND` proxy, not proof of marketplace purchase demand. Requests are bounded to 12 per run, sequential at no faster than one request per second, cacheable for 24 hours, and must carry an identifiable User-Agent. No credential is required.

### `google_ads_keyword_historical_v1`

Source: Google Ads API `KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics`, an official structured API. This connector normalizes historical keyword metrics including average monthly searches, competition index and top-of-page bid ranges. It is `AUTH_REQUIRED`: OAuth2 plus a Google Ads developer token/customer context must be supplied by an authorized runtime. H01-131 does not provision, read or export credentials. Requests are bounded to 12 per run, no faster than one request per second per CID, and cacheable for 30 days.

## Hard safety boundary

Both connectors emit `die.h01.market-signal-evidence.v1` receipts and preserve H01-130 invariants:

- Object Atlas validity effect is `NONE`.
- Standalone production blocking effect is `NONE`.
- Production, submission, publication and spend authority are all false.
- Connector outage, missing authentication or no result means missing evidence, not zero demand.
- No autocomplete endpoint is a core dependency.
- No browser or marketplace DOM scraping is a core dependency.
- No cookies, browser session values, credentials or provider tokens are read by this connector layer.

The connector layer normalizes official structured responses into deterministic evidence IDs and hashes. `to_h01_130_ref()` projects an evidence receipt into the exact evidence-reference shape consumed by H01-130.

## Boundedness and failure behavior

Connector calls are bounded by registry policy. A transport may fail, be unavailable, require authentication, return no results or be rate-limited. Those outcomes degrade the H01-130 demand overlay to `NO_EVIDENCE`, `PARTIAL` or `STALE`; they never invalidate Object Atlas nouns, queue items or already-produced semantic masters.

Wikimedia pageviews are explicitly treated as a trend/attention proxy and must not be re-labeled as commercial purchase demand. Google Ads historical metrics are the preferred structured search-demand signal when an authorized Google Ads context exists.

## Non-actions

H01-131 authorizes connector contracts and deterministic normalization only. It does not authorize account enrollment, credential provisioning, advertising spend, browser automation, autocomplete scraping, marketplace scraping, marketplace submission or publication.

## Current source verification

The connector policy was checked against current official documentation on 2026-09-13:

- Wikimedia Analytics API documents open JSON analytics endpoints, requires identifiable client User-Agent headers, and advises bounded request rates.
- Google Ads Keyword Planning documents `GenerateKeywordHistoricalMetrics` for historical search volume/competition data, requires the `adwords` OAuth scope and developer-token/customer context, and limits keyword-planning methods to 1 request/second per CID.

These external facts inform connector policy only; canonical evidence remains the repository contract and receipts.
