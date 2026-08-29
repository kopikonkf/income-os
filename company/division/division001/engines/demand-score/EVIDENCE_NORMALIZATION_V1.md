# Division01 Demand Score Evidence Normalization v1

Status: CANONICAL CONTRACT
Task: OE-002B
Owner: Division-01 Digital Asset Intelligence

## 1. Rule

Demand Score v1 consumes **explicit evidence references**. It never manufactures a component value from a category name, object name, prior LLM opinion, or historical default merely because a score is desired.

Every component records one or more `evidence_refs`. Evidence can be:

- `OPPORTUNITY_SIGNAL` ? a validated OE-001 receipt;
- `DETERMINISTIC_EVIDENCE` ? a reproducible local calculation with its own version/hash;
- `CANON_EVIDENCE` ? a pinned canon/policy artifact suitable for eligibility, feasibility, risk, or structural context.

Only `OPPORTUNITY_SIGNAL` evidence may claim a market observation. Structural/canon evidence cannot masquerade as search demand.

## 2. Component mapping

| Component | Allowed evidence | Opportunity Signal classes | Notes |
|---|---|---|---|
| `external_demand` | OPPORTUNITY_SIGNAL | DEMAND | Search interest/autocomplete/visible demand proxies |
| `supply_competition` | OPPORTUNITY_SIGNAL | SUPPLY, COMPETITION | Supply density and competition observations |
| `commercial_intent` | OPPORTUNITY_SIGNAL | COMMERCIAL_INTENT | Observable buyer/license/price-surface evidence |
| `trend_seasonality` | OPPORTUNITY_SIGNAL | TREND | Optional if unavailable; UNKNOWN is allowed |
| `platform_fit` | OPPORTUNITY_SIGNAL or CANON_EVIDENCE | PLATFORM_FIT | Surface observation plus dated platform contract where appropriate |
| `niche_specificity` | DETERMINISTIC_EVIDENCE or CANON_EVIDENCE | none | Phrase/object/Human-context structure; not a market signal |
| `production_feasibility` | DETERMINISTIC_EVIDENCE or CANON_EVIDENCE | none | Reproducible capability/complexity evidence, never a name-based prior |
| `eligibility` | CANON/DETERMINISTIC or PLATFORM_FIT signal | PLATFORM_FIT | Dated platform/content/tool policy refs |
| `risk_penalty` | CANON_EVIDENCE or DETERMINISTIC_EVIDENCE | none | Explicit rights/IP/safety/uncertainty evidence; hard vetoes remain separate |

## 3. No hidden priors

Forbidden production-v1 behavior includes:

- `missing search signal -> 0.30`;
- `object class tools -> intent 0.60`;
- `name == candle -> trend 0.75`;
- `unknown seasonality -> 0.40`;
- any equivalent default not backed by an explicit versioned evidence artifact.

Historical v0 dictionaries may be retained only as calibration/provenance fixtures and must be labeled `LEGACY_HEURISTIC`, never current market evidence.

## 4. Evidence reuse / double counting

A single evidence receipt may not contribute independently to multiple components unless the model contract explicitly declares a multi-component transformation and records that transformation ID. Default v1 policy is one evidence contribution -> one component.

Multiple observations from the same source/query/time window require OE-001 dedupe semantics before scoring. Duplicate collection must never multiply evidence weight.

## 5. Normalization

Normalization into a 0..1 component value belongs to OE-002D. OE-002B only defines what evidence may feed each component and what provenance must survive the transformation.

Each normalized component must preserve:

- source evidence IDs/hashes;
- evidence kind;
- signal class/type where applicable;
- observed/effective timestamps;
- freshness state;
- normalization transform ID/version;
- component confidence.
