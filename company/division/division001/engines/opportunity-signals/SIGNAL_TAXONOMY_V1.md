# Division01 Opportunity Signal Taxonomy v1

Status: CANONICAL CONTRACT
Task: OE-001A
Owner: Division-01 Digital Asset Intelligence

## 1. Definition

An Opportunity Signal is a timestamped external or first-party observation about a seed, phrase, candidate, buyer-search surface, supply surface, trend surface, or platform-fit surface.

A signal is **evidence input**, not a Demand Score, Worth-Making decision, Blueprint decision, or production authority.

The collector MUST record what was observed and how it was acquired. It MUST NOT infer commercial worth merely because an observation exists.

## 2. Subject kinds

- `SEED_OBJECT` ? cleaned Object Atlas primitive.
- `PHRASE` ? longtail/search phrase hypothesis.
- `CANDIDATE` ? Human/Object commercial candidate or family hypothesis.

Every receipt has exactly one primary subject ID. Parent seed/candidate references may be carried as optional lineage.

## 3. Signal classes

### DEMAND

Visible evidence that buyers/users search for, request, or interact with a phrase/subject.

Types:
- `AUTOCOMPLETE_PRESENCE`
- `AUTOCOMPLETE_RANK`
- `RELATED_QUERY_PRESENCE`
- `SEARCH_INTEREST_INDEX`
- `SEARCH_INTEREST_DELTA`
- `VISIBLE_DOWNLOAD_COUNT`
- `VISIBLE_POPULARITY_COUNT`

### SUPPLY

Visible supply quantity or composition on a search/result surface.

Types:
- `SEARCH_RESULTS_COUNT`
- `VISIBLE_CONTRIBUTOR_COUNT`
- `ASSET_TYPE_MIX_RATIO`

### COMPETITION

Competition-specific observations that are not themselves a commercial judgment.

Types:
- `SPONSORED_RESULT_SHARE`
- `TOP_RESULT_CONCENTRATION_RATIO`
- `EXACT_PHRASE_RESULT_COUNT`

### COMMERCIAL_INTENT

Directly observable buyer-language or transaction-surface indicators.

Types:
- `BUYER_TERM_PRESENCE`
- `LICENSE_SURFACE_PRESENCE`
- `VISIBLE_PRICE_POINT`

### TREND

Time-series or seasonal observations from approved sources.

Types:
- `TREND_INDEX`
- `TREND_DELTA`
- `SEASONALITY_INDEX`

### PLATFORM_FIT

Observable platform-surface compatibility signals, separate from submission authorization.

Types:
- `CONTENT_TYPE_SURFACE_PRESENCE`
- `FILTER_OPTION_PRESENCE`
- `AI_LABEL_SURFACE_PRESENCE`

`PLATFORM_FIT` signals do not replace dated Platform Contracts or ToS decisions.

## 4. Value kinds

- `COUNT` ? non-negative integer.
- `RANK` ? integer >=1, lower is better only when the signal definition says so.
- `RATIO` ? normalized 0..1.
- `INDEX` ? normalized 0..100.
- `DELTA` ? signed normalized change from -100..100.
- `BOOLEAN` ? observed yes/no.
- `TEXT` ? bounded observed text/category when a numeric representation would fabricate precision.

Adapters MUST NOT convert UNKNOWN into zero.

## 5. Evidence labels

- `OBSERVED` ? directly visible through an approved acquisition lane.
- `VERIFIED` ? confirmed by an authoritative first-party/official source or governed receipt.
- `SYNTHETIC` ? fixture/test only; cannot feed production Demand Score as live evidence.

Inference belongs downstream. Raw signal receipts do not use `INFERRED` or `HYPOTHESIS` as evidence labels.

## 6. Freshness

Every signal carries `observed_at`, `recorded_at`, `expires_at`, and `freshness_window_seconds`.

A receipt is stale when evaluation time is at or after `expires_at`. Stale evidence may be preserved historically but MUST NOT be treated as current without an explicit downstream staleness policy.

## 7. Source classes

- `OFFICIAL_API`
- `PUBLIC_WEB_DOCUMENT`
- `PUBLIC_SEARCH_UI`
- `CONTRIBUTOR_UI`
- `MANUAL_OPERATOR`
- `OPERATOR_EVIDENCE_IMPORT`
- `SYNTHETIC_FIXTURE`

The acquisition method is not permission by itself. Every receipt also pins an approved acquisition policy profile/version.

## 8. Non-signals

The following are not valid Opportunity Signals unless converted into an explicit governed observation receipt:

- an LLM's unsupported estimate;
- a remembered search result;
- an old screenshot with unknown timestamp;
- a competitor-count guess;
- a score copied from Qwen-era research;
- a Kanban status;
- a Worth-Making score;
- a Blueprint recommendation.

## 9. Deduplication identity

Signal identity is source-scoped. A later observation of the same subject/type/source is a new observation when its `observed_at` differs; it is not additive evidence simply because it was collected twice.

OE-001F will implement registry-level dedupe and freshness behavior.
