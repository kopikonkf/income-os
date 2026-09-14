# DIE H01 Freepik/Magnific Trending Vector Signal Adapter v1

Task: H01-131E

Status: **BLOCKED_COMPLIANCE / fail-soft scaffold implemented**

## Intended evidence semantics

H01-131E targets the first-party `Trending Vector Searches` surface associated with Freepik/Magnific vector discovery. If a compliant machine-readable acquisition surface becomes available, observations from that named section are classified as:

- evidence class: `MARKETPLACE_POPULAR_QUERY`;
- media type: `VECTOR`;
- signal class: `TREND`;
- provenance confidence: high when directly observed from an authorized first-party surface;
- commercial signal confidence: medium-high;
- quantitative confidence: none unless the source explicitly publishes a quantitative metric;
- query volume: unavailable / must remain null;
- visitor-query count: unavailable / must remain null.

This evidence is not `DIRECT_MARKETPLACE_QUERY` telemetry, not a content-popularity/content-needs proxy, and not a macro-search trend.

## Compliance finding

During implementation, the public Magnific vectors page was confirmed to expose a `Trending Vector Searches` section. However, Magnific's current Acceptable Use Policy states that Products must not be used through automation, bots, or external tools and prohibits scraping or automated extraction of content or metadata.

Official policy:

`https://www.magnific.com/in/legal/acceptable-use-policy`

The documented Magnific Stock Content API is an authenticated resource-search/list/download API. It requires `x-magnific-api-key`. The current API documentation index exposes Stock Content endpoints for resources/icons/videos but no documented endpoint for current trending search terms. `GET /v1/resources` accepts resource search/filter parameters and `order=relevance|recent`; that is resource discovery, not trending-query telemetry.

Official API references:

- `https://docs.magnific.com/llms.txt`
- `https://docs.magnific.com/api-reference/resources/images-and-templates-api`
- `https://docs.magnific.com/api-reference/resources/get-all-resources`

Therefore a public-page HTML scraper is not shipped. Substituting resource popularity/download statistics would also be semantically wrong for H01-131E because that would be `MARKETPLACE_POPULARITY_PROXY`, not `MARKETPLACE_POPULAR_QUERY` evidence.

## Current adapter behavior

The per-source capability is installed as `ADAPTER_PENDING`. The source-specific acquisition wrapper still routes through H01-131A `AcquisitionCore`. Because the capability is not active, the core returns `DEGRADED_ADAPTER_UNAVAILABLE` before any network request and records no raw/evidence payload.

This preserves H01-131A invariants:

- source outage/unavailability never blocks standalone production;
- no credential, cookie, browser session, marketplace account, submission, publication, or spend authority is used;
- cache/freshness/receipt semantics remain owned by the shared core;
- no fabricated search volume or visitor-query count exists;
- no shared H01-131A acquisition semantics are changed.

## Unblock condition

H01-131E can become ACTIVE only if a compliant first-party mechanism exists that actually exposes the target trending-search-term observations, for example:

1. Magnific publishes a documented API/feed for trending/popular search terms and its terms allow the intended automated acquisition; or
2. Magnific explicitly authorizes an equivalent machine-readable acquisition method for this use.

If that mechanism requires credentials, a separate explicit authority grant is required before H01 may read or use them. Possessing an API key alone is not sufficient if the endpoint does not provide the target evidence class.
