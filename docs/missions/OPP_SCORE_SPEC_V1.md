# OPP-SCORE-001 — Demand Score and Opportunity Score Specification V1

Status: `FOUNDER-REVIEW`
Scope: TASK-A + TASK-B only (`spec-only`, non-activating)
Mission: `M-001` / `DIVISION-01`
Schema: `die.opportunity.score.v1`
Calibration: `opp-score-v1`
Normative source: `docs/missions/M001_BLUEPRINT_BATCH1_V2.md` §§5.1-5.4

## 1. Purpose and boundary

This specification converts the ratified Worth-Making Opportunity Score into a
deterministic decision instrument. It does not authorize production, spending,
submission, publication, or account actions.

The V1 scorer must:

- consume a candidate record plus hash-pinned signal files;
- perform no network call and invoke no LLM;
- assign only rubric-defined integer points;
- reduce missing or weak evidence rather than inventing a favorable default;
- produce the same score core for byte-identical inputs; and
- emit a hash-pinned receipt before any production envelope is created.

The scorer is additive to the §5.1 hard vetoes. A score of 75 or more never
clears a veto and never substitutes for Founder authorization.

## 2. Ratified V1 decisions

1. The weights and decision bands remain exactly as Blueprint v2 §§5.2-5.3.
2. Thresholds `75` and `60` are frozen for V1. Calibration requires a new
   version after at least 30 calendar days of receipts or another
   Founder-ratified sample threshold. Historical receipts are immutable.
3. TASK-D starts with Adobe Stock public storefront autocomplete because it is
   inside the active marketplace cohort and needs no contributor login for
   ordinary public use. This is an experimental storefront adapter, not a
   promised or official API contract.
4. A static eligible-platform matrix may contribute with label `HYPOTHESIS`.
   Platform approval/rejection receipts later upgrade route evidence to
   `OBSERVED`; current official policy evidence may be `VERIFIED`.
5. Magnific is a production/recovery lane and is excluded from the five-route
   marketplace-fit denominator.

## 3. Opportunity Score formula

| Factor key | Factor | Weight |
|---|---|---:|
| `demand_evidence` | Demand evidence | 20 |
| `commercial_intent` | Commercial intent | 15 |
| `buyer_utility` | Buyer utility | 15 |
| `competition_gap` | Competition gap | 10 |
| `visual_scarcity` | Visual scarcity / differentiation | 10 |
| `production_feasibility` | Production feasibility | 10 |
| `eligible_platform_fit` | Eligible-platform fit | 10 |
| `repurposing_potential` | Repurposing potential | 5 |
| `speed_to_falsification` | Speed to cheapest falsification | 5 |
|  | **Total** | **100** |

For each factor `f`:

```text
raw_score(f)       = integer selected by the factor rubric, 0..weight(f)
evidence_ceiling(f)= floor(weight(f) * ceiling_ratio(governing_label(f)))
factor_score(f)    = min(raw_score(f), evidence_ceiling(f))
total_score        = sum(factor_score(f))
```

No floating-point score is permitted. If a rubric calculation produces a
fraction, V1 rounds down.

`demand_score` is exactly `factor_score(demand_evidence)` on a 0-20 scale. V1
does not introduce a second hidden demand formula. `opportunity_score` is
exactly `total_score` on a 0-100 scale.

### 3.1 Evidence labels and ceilings

| Label | Meaning | Ceiling ratio |
|---|---|---:|
| `OBSERVED` | Directly visible in a marketplace or executed receipt | 1.00 |
| `VERIFIED` | Supported by a current official source or executed verification | 1.00 |
| `INFERRED` | Mechanically derived from cited evidence, not directly measured | 0.70 |
| `HYPOTHESIS` | Explicit claim waiting to be falsified | 0.40 |
| `UNKNOWN` | Required evidence unavailable | 0.00 |

Every nonzero component must cite at least one `evidence_id`. The governing
label is the lowest ceiling among the evidence records required to support
that factor. Evidence not used by the calculation cannot lower or raise it.

Special rule: `demand_evidence` and `competition_gap` accept only
`OBSERVED`/`VERIFIED`. If any required input is merely `INFERRED`,
`HYPOTHESIS`, or missing, the affected component is zero. When the minimum
required dataset is absent, the complete factor is `0` with label `UNKNOWN`.

### 3.2 Decision bands

| Total | Band | Machine decision | Effect |
|---:|---|---|---|
| 75-100 | `VALIDATION_CANDIDATE` | `PROCEED_TO_FOUNDER_GATE` | Score gate passes; hard veto and Founder gate still apply |
| 60-74 | `RESEARCH_BACKLOG` | `NO_OP_ACQUIRE_EVIDENCE` | No production; collect missing evidence or narrow/merge candidate |
| 0-59 | `DEFER` | `NO_OP_SCORE_BELOW_THRESHOLD` | No production capacity is allocated |

## 4. Factor rubrics

### 4.1 Demand evidence — 20

Required data source: public marketplace observations or executed marketplace
receipts. Candidate aliases must be declared before collection; the scorer may
not invent synonyms.

| Component | Deterministic rule | Points |
|---|---|---:|
| Suggestion rank | Normalized candidate/declared alias appears at rank 1-3 in at least two probes | 8 |
|  | Appears at rank 4-10 in at least two probes, or rank 1-3 in one probe | 5 |
|  | Appears once at rank 4-10 | 2 |
|  | No match | 0 |
| Suggestion recurrence | Hit ratio across 3-5 pinned probes is at least 0.60 / 0.40 / 0.20 | 4 / 3 / 1 |
| Marketplace badges | At least 3 / 1 distinct sampled assets carry an observed `popular`/`bestseller`-equivalent badge | 4 / 2 |
| Visible downloads | At least 3 / 1 distinct sampled assets show a positive visible download count | 4 / 2 |

Components are additive and capped at 20. TASK-D autocomplete alone can supply
at most 12 points; badges and download counts require separate raw evidence.

Normalization is fixed: Unicode NFKC, Unicode case-fold, punctuation converted
to spaces, whitespace collapsed, and leading/trailing whitespace removed.
Matching is exact normalized phrase or an exact predeclared alias—never a
semantic or LLM similarity judgment.

### 4.2 Commercial intent — 15

Five independent checks contribute 3 points each:

1. a target buyer class is explicitly recorded;
2. a falsifiable job-to-be-done is explicitly recorded;
3. a commercial use context is explicitly recorded;
4. an intent phrase appears in observed suggestions/tags or an official
   marketplace category; and
5. the requested asset form is licensable under a cited current platform rule.

Each check requires its own evidence reference. Candidate declarations without
external support are `HYPOTHESIS`, so the factor ceiling is 6/15.

### 4.3 Buyer utility — 15

Award 3 points for each distinct supported buyer job, up to five jobs. A job
record requires `buyer_class`, `job_code`, `use_context`, `expected_asset_form`,
and `evidence_id`. Duplicate `job_code + buyer_class + use_context` tuples count
once. A candidate statement without external support remains `HYPOTHESIS`.

### 4.4 Competition gap — 10

Minimum dataset:

- one observed result count for the candidate query;
- at least three observed comparator result counts;
- identical marketplace, locale, media type, filters, and collection window;
- all counts labeled `OBSERVED` or `VERIFIED`; and
- effective Demand Evidence score of at least 8.

```text
supply_ratio = candidate_result_count / median(comparator_result_counts)
```

| Supply ratio | Points |
|---:|---:|
| `<= 0.10` | 10 |
| `<= 0.25` | 8 |
| `<= 0.50` | 6 |
| `<= 0.75` | 4 |
| `<= 1.00` | 2 |
| `> 1.00` | 0 |

If result counts are hidden, approximate, incompatible, stale outside the
collection window, or fewer than three comparators exist, the factor is
`0/10 UNKNOWN`. Low supply without demand is not a competition gap.

### 4.5 Visual scarcity / differentiation — 10

Minimum dataset: a pinned top-result sample of at least 20 assets and a
predeclared mechanical classification rule for whether each result matches the
candidate's proposed visual treatment.

```text
visual_match_ratio = matching_visual_count / sample_size
```

| Visual match ratio | Raw points |
|---:|---:|
| `<= 0.10` | 10 |
| `<= 0.25` | 8 |
| `<= 0.40` | 6 |
| `<= 0.60` | 3 |
| `> 0.60` | 0 |

A human-coded sample is normally `INFERRED` and capped at 7/10 unless a
ratified deterministic classifier and verification receipt exists. No sample
means `0/10 UNKNOWN`.

### 4.6 Production feasibility — 10

Award 2 points for each verified check:

1. eligible production engine is live with a current probe receipt;
2. required raster format, dimensions, and file-size target are achievable;
3. commercial output rights and AI disclosure path are known;
4. required spend is within the current Founder budget; and
5. deterministic QA rules and a recovery/quarantine route exist.

An unresolved commercial-rights condition is also a hard veto; scoring cannot
override it.

### 4.7 Eligible-platform fit — 10

The denominator is the five M-001 Tier-1 marketplaces: Adobe Stock,
Dreamstime, 123RF, Vecteezy, and MotionElements. Award 2 raw points for each
route whose current matrix record says the candidate's asset type is eligible.

The factor's governing label is the weakest label among the counted routes.
Therefore a matrix made entirely of `HYPOTHESIS` records can contribute at
most 4/10. An observed platform acceptance/rejection receipt supersedes the
static hypothesis for its route. Magnific never contributes to this factor.

### 4.8 Repurposing potential — 5

Award 1 raw point for each distinct, documented, rights-safe recovery format,
up to five. A route plan is evidence of potential, not permission to publish.
Because Tier-2 remains proposal-only, untested route plans are `HYPOTHESIS`
and the V1 factor ceiling is normally 2/5.

### 4.9 Speed to cheapest falsification — 5

| Lowest documented test path | Raw points |
|---|---:|
| USD 0 and `<=24h` | 5 |
| USD 0 and `<=72h` | 4 |
| USD 0 and `<=7d` | 3 |
| Within Founder-authorized budget and `<=7d` | 2 |
| Otherwise or unknown | 0 |

The time/cost record must identify the test action, owner, dependency, maximum
elapsed hours, and maximum spend. Estimates remain `HYPOTHESIS` until an
executed cycle receipt exists.

## 5. Scorer input and receipt contracts

### 5.1 Deterministic input

TASK-C accepts one candidate JSON file and one or more signal JSON files. The
candidate file contains no free-form scoring instruction. Its factor inputs
use these fixed fields:

```json
{
  "schema": "die.opportunity.candidate.v1",
  "mission_id": "M-001",
  "division_id": "DIVISION-01",
  "input": {
    "candidate": {
      "candidate_id": "MASTER-13",
      "keyword": "isolated strawberry watercolor",
      "object": "ripe strawberry",
      "context": "isolated on white",
      "buyer_classes": ["designer"],
      "commercial_intent_codes": ["DESIGN_ELEMENT"],
      "aliases": []
    },
    "hard_vetoes_clear": false
  },
  "factor_inputs": {
    "demand_evidence": {
      "suggest_probe_evidence_ids": [],
      "badge_evidence_ids": [],
      "download_evidence_ids": []
    },
    "commercial_intent": {
      "checks": [
        {"code": "TARGET_BUYER", "passed": true, "evidence_ids": []}
      ]
    },
    "buyer_utility": {"jobs": []},
    "competition_gap": {
      "candidate_result_count": null,
      "comparator_result_counts": [],
      "collection_group": null,
      "evidence_ids": []
    },
    "visual_scarcity": {
      "sample_size": 0,
      "matching_visual_count": 0,
      "classifier_id": null,
      "evidence_ids": []
    },
    "production_feasibility": {"checks": []},
    "eligible_platform_fit": {"routes": []},
    "repurposing_potential": {"routes": []},
    "speed_to_falsification": {
      "test_action": null,
      "owner": null,
      "dependency": null,
      "max_elapsed_hours": null,
      "max_spend_usd": null,
      "evidence_ids": []
    }
  },
  "evidence": [],
  "hard_vetoes_clear": false
}
```

Allowed commercial-intent check codes are `TARGET_BUYER`, `JOB_TO_BE_DONE`,
`COMMERCIAL_USE_CONTEXT`, `OBSERVED_INTENT_PHRASE`, and
`LICENSABLE_ASSET_FORM`. Allowed production-feasibility check codes are
`ENGINE_LIVE`, `OUTPUT_SPEC_FEASIBLE`, `COMMERCIAL_RIGHTS_KNOWN`,
`WITHIN_FOUNDER_BUDGET`, and `QA_RECOVERY_ROUTE_READY`.

Each buyer-utility job uses `buyer_class`, `job_code`, `use_context`,
`expected_asset_form`, and `evidence_ids`. Each platform route uses
`platform_id`, `eligible`, and `evidence_ids`. Each repurposing route uses a
predeclared `route_code`, `format_code`, `rights_safe`, and `evidence_ids`.
Unknown fields, unknown codes, duplicate IDs, or values outside their declared
ranges fail schema validation.

### 5.2 Receipt — `die.opportunity.score.v1`

The scorer output is one UTF-8 JSON object. No wall-clock value is generated
inside the deterministic score core. Collection timestamps are input evidence;
the append-only event timestamp is added separately by `die_event.py`.

```json
{
  "schema": "die.opportunity.score.v1",
  "calibration_version": "opp-score-v1",
  "receipt_id": "OPP-<24 uppercase hex chars>",
  "mission_id": "M-001",
  "division_id": "DIVISION-01",
  "candidate": {
    "candidate_id": "MASTER-13",
    "keyword": "isolated strawberry watercolor",
    "object": "ripe strawberry",
    "context": "isolated on white",
    "buyer_classes": ["designer"],
    "commercial_intent_codes": ["DESIGN_ELEMENT"],
    "aliases": []
  },
  "pins": {
    "candidate_sha256": "<64 lowercase hex>",
    "signal_files": [
      {"path": "<repo-relative-or-workspace-ref>", "sha256": "<64 lowercase hex>"}
    ],
    "score_input_sha256": "<64 lowercase hex>",
    "scorer_sha256": "<64 lowercase hex>"
  },
  "evidence": [
    {
      "evidence_id": "EV-001",
      "factor": "demand_evidence",
      "label": "OBSERVED",
      "source_type": "MARKETPLACE_SUGGEST",
      "source_ref": "<signal-file>#/parsed/suggestions/0"
    }
  ],
  "factors": {
    "demand_evidence": {
      "weight": 20,
      "raw_score": 8,
      "governing_label": "OBSERVED",
      "ceiling": 20,
      "score": 8,
      "evidence_ids": ["EV-001"],
      "reason_codes": ["SUGGEST_RANK_TOP3_TWO_PROBES"],
      "missing": ["POPULAR_BADGE_SAMPLE", "VISIBLE_DOWNLOAD_SAMPLE"]
    },
    "commercial_intent": {"weight": 15, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["COMMERCIAL_INTENT_CHECKS"]},
    "buyer_utility": {"weight": 15, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["BUYER_JOBS"]},
    "competition_gap": {"weight": 10, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["COMPARABLE_RESULT_COUNTS"]},
    "visual_scarcity": {"weight": 10, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["VISUAL_SAMPLE_20"]},
    "production_feasibility": {"weight": 10, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["FEASIBILITY_CHECKS"]},
    "eligible_platform_fit": {"weight": 10, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["PLATFORM_MATRIX_ROUTES"]},
    "repurposing_potential": {"weight": 5, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["REPURPOSING_ROUTES"]},
    "speed_to_falsification": {"weight": 5, "raw_score": 0, "governing_label": "UNKNOWN", "ceiling": 0, "score": 0, "evidence_ids": [], "reason_codes": [], "missing": ["FALSIFICATION_PLAN"]}
  },
  "demand_score": 8,
  "opportunity_score": 8,
  "total_score": 8,
  "band": "DEFER",
  "decision": "NO_OP_SCORE_BELOW_THRESHOLD",
  "evidence_summary": {
    "observed_verified_points": 8,
    "inferred_points": 0,
    "hypothesis_points": 0,
    "unknown_weight": 80,
    "confidence": "LOW"
  },
  "score_core_sha256": "<64 lowercase hex>"
}
```

All nine factor objects are required even when their score is zero. Valid
factor fields are:

- `weight`: the immutable V1 weight;
- `raw_score`: rubric points before evidence ceiling;
- `governing_label`: one of the five canonical labels;
- `ceiling`: integer evidence ceiling for this factor;
- `score`: `min(raw_score, ceiling)`;
- `evidence_ids`: sorted unique references into the receipt evidence array;
- `reason_codes`: sorted enumerated machine codes; and
- `missing`: sorted enumerated missing-input codes.

`hard_vetoes_clear` is an externally supplied, hash-pinned fact. The scoring
engine does not infer or mutate it. TASK-E must require both score pass and
the existing hard-veto/Founder authority chain.

### 5.3 Deterministic hashing and idempotency

1. JSON canonicalization uses UTF-8, lexicographically sorted object keys,
   compact separators, Unicode preserved, and no NaN/Infinity.
2. `candidate_sha256` hashes the canonical candidate object.
3. Every signal-file hash is over the exact raw file bytes.
4. `score_input_sha256` hashes calibration version, candidate hash, sorted
   signal hashes, evidence records, and hard-veto input.
5. `receipt_id = "OPP-" + upper(score_input_sha256[0:24])`.
6. `score_core_sha256` hashes the completed receipt excluding only
   `score_core_sha256` itself.
7. Identical inputs produce identical factor objects, total, band, decision,
   receipt ID, and core hash.

The runtime receipt path is content-addressed, for example:

```text
workspaces/M001-OPPSCORE/receipts/<receipt_id>.json
```

If the file already exists with the same core hash, the operation is an
idempotent replay. A different body under the same receipt ID is a critical
collision and must fail closed.

### 5.4 Append-only event boundary

TASK-C writes the receipt atomically, then calls the existing `die_event.py`
writer with a deterministic dedupe key:

```text
class       NOTICE
source      die-opportunity-score
mission_id  M-001
division_id DIVISION-01
summary     opportunity score <candidate_id> = <total>/<band>
detail_ref  <receipt path>
dedupe_key  opp-score:<receipt_id>
```

The scorer must not directly append to `state/EVENTS.jsonl`. Event-write
failure leaves the receipt intact but blocks TASK-E dispatch until the event
chain is reconciled.

## 6. Signal collector contract — TASK-B

### 6.1 Minimal V1 source decision

Source: Adobe Stock public storefront autocomplete under the
`https://stock.adobe.com` origin.

Rationale:

- it belongs to the active M-001 marketplace cohort;
- ordinary storefront search is publicly reachable without contributor login;
- suggestions represent directly observed query completion behavior; and
- Shutterstock's documented public API requires authentication, making it
  unsuitable for the zero-credential TASK-D constraint.

The Adobe autocomplete transport is not treated as stable canon. TASK-D must
isolate it behind an adapter. It may use only a public request observed from
the storefront. It must never scrape authenticated contributor pages, bypass
a challenge, rotate proxies, or replay private cookies.

### 6.2 Raw signal object — `die.market.signal.v1`

```json
{
  "schema": "die.market.signal.v1",
  "collector_version": "adobe-suggest-v1",
  "source": {
    "marketplace": "adobe_stock",
    "surface": "public_search_autocomplete",
    "origin": "https://stock.adobe.com",
    "authentication": "NONE"
  },
  "query": {
    "raw": "isolated strawberry",
    "normalized": "isolated strawberry",
    "locale": "en-US",
    "media_type": "images",
    "filters": {}
  },
  "collected_at": "<RFC3339 UTC supplied by collector>",
  "status": "OK",
  "transport": {
    "http_status": 200,
    "content_type": "application/json",
    "attempts": 1
  },
  "parsed": {
    "suggestions": [
      {"rank": 1, "text": "isolated strawberry", "normalized_text": "isolated strawberry"}
    ]
  },
  "raw_artifact": {
    "path": "<workspace-relative raw response path>",
    "sha256": "<64 lowercase hex>",
    "bytes": 0
  },
  "redaction": {
    "credentials_present": false,
    "response_cookies_saved": false,
    "sensitive_query_values_removed": true
  }
}
```

Valid status values:

- `OK`: public response parsed and raw bytes persisted;
- `NO_SUGGESTIONS`: valid public response with an empty suggestion list;
- `SOURCE_UNAVAILABLE`: endpoint/UI shape unavailable or changed;
- `RATE_LIMITED`: HTTP 429 or explicit throttling response;
- `CHALLENGE_BLOCKED`: CAPTCHA, login, bot challenge, or consent barrier;
- `NETWORK_ERROR`: bounded transport failure; and
- `PARSE_ERROR`: raw response stored but deterministic parser rejected it.

Only `OK` and `NO_SUGGESTIONS` are demand observations. All failure statuses
map to `UNKNOWN` in TASK-C; they never map to zero-demand evidence disguised
as an observed empty result.

### 6.3 Collection method and rate limits

TASK-D must use one process and one in-flight request. The default schedule is:

- randomized 8-15 second delay between requests using an OS randomness source;
- maximum 30 requests per rolling hour;
- maximum two transport attempts per query;
- backoff of 60 seconds then 180 seconds for retryable 5xx/network failures;
- immediate stop for the run on a second 429; and
- no retry for `CHALLENGE_BLOCKED` or deterministic `PARSE_ERROR`.

`Retry-After` overrides the local backoff when it is longer. Tests use injected
clock/random functions and fixtures; CI performs no live marketplace request.

### 6.4 Storage, provenance, and redaction

For every attempt, TASK-D stores:

1. exact response body bytes in a raw artifact;
2. SHA-256 and byte length of that artifact;
3. an adjacent parsed `die.market.signal.v1` manifest;
4. UTC collection time, locale, query, filter set, status, and attempt count;
5. an allowlisted request-header summary only; and
6. no cookie, authorization header, account identifier, session token, proxy
   credential, or full signed URL.

The collector must reject a configured header named `Authorization`, `Cookie`,
`X-API-Key`, or equivalent. Redirects outside an allowlisted Adobe Stock host
fail closed. Raw filenames are content-addressed; query text belongs in the
manifest, not the filename.

### 6.5 TASK-D acceptance fixture

The minimal collector milestone is complete only when one fixture-backed and
one explicitly authorized live query demonstrate:

- public unauthenticated request;
- raw response persistence;
- raw SHA-256 reproducibility;
- ordered suggestion parsing;
- `NO_SUGGESTIONS` distinct from transport failure;
- rate-limit/backoff behavior under injected tests; and
- absence of credentials in source, logs, raw artifact, and manifest.

Live collection remains an integrator action. The spec and tests must work
offline.

## 7. Confidence summary

The receipt summarizes where effective points came from:

- `observed_verified_points`: points whose governing label is
  `OBSERVED`/`VERIFIED`;
- `inferred_points`: points governed by `INFERRED`;
- `hypothesis_points`: points governed by `HYPOTHESIS`; and
- `unknown_weight`: sum of weights for factors scored zero due to missing
  required evidence.

Confidence is deterministic:

| Condition | Confidence |
|---|---|
| Observed/verified points `>=60` and unknown weight `<=10` | `HIGH` |
| Observed/verified points `>=35` and unknown weight `<=30` | `MEDIUM` |
| Otherwise | `LOW` |

Confidence does not modify the score in V1; evidence ceilings already perform
that function.

## 8. Required fail-closed behavior

- Missing signal file, hash mismatch, malformed schema, unknown label, unknown
  reason code, weight mismatch, duplicate evidence ID, or score arithmetic
  mismatch: reject the receipt; do not dispatch.
- Missing Demand Evidence or Competition Gap prerequisites: score the affected
  factor zero as `UNKNOWN`; do not infer.
- Signal collector failure: persist failure status and let the scorer map it to
  missing evidence; do not reuse stale data silently.
- Hard veto unresolved or Founder authority absent: no production regardless
  of score.
- Scorer/event-chain uncertainty: report status and stop.

## 9. Versioning and calibration

Weights, evidence ceilings, factor rubrics, normalization, bands, and reason
codes are calibration-controlled. Any change creates `opp-score-v2` (or later),
a new scorer hash, and new receipts. V1 is not retroactively rewritten.

Calibration review may be proposed after 30 days using observed approval,
rejection, license, ERVA, and score-distribution receipts. Until Founder
ratifies a new version, `75/60` remains mandatory.

## 10. Handoff to later atomic tasks

- TASK-C implements this score core and receipt validator without network/LLM.
- TASK-D implements only the Adobe public-suggest adapter and fixtures above.
- TASK-E inserts the score receipt before operator envelope materialization.
- TASK-F recomputes MASTER-13 without altering its existing Founder decision.

This document does not activate any of those tasks at runtime.

## 11. References

- `docs/missions/M001_BLUEPRINT_BATCH1_V2.md` §§5.1-5.4
- `docs/atlas/HUMAN_CENTRIC_ATLAS_CANON.md`
- `docs/pipeline/MATRIX_6_PLATFORM_TOS_STRICTNESS.md`
- `ORCHESTRATOR_CONTRACT.md`
- Adobe Stock public search surface: `https://stock.adobe.com/search`
- Shutterstock API authentication reference:
  `https://api-reference.shutterstock.com/`
