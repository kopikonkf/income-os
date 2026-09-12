# DIE-H01 Family / Set Rights Gate v1

Task: `H01-122`
Status: ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-122 is the **pre-production semantic rights-routing gate** for Semantic Family and future Design Set candidates. It complements, rather than replaces, the existing FA-136 post-artifact detector gate.

The governing invariant is:

> Brand/trademark-restricted systems may remain discoverable and auditable, but they cannot silently route into normal stock production.

The gate is not legal clearance and never grants production, submission, or publication authority.

## Input contract

`contracts/h01-family-set-rights-candidate.v1.schema.json` accepts exactly two candidate kinds:

- `SEMANTIC_FAMILY`
- `DESIGN_SET`

Derivative bundles and listing packages are intentionally outside this contract. Every candidate contains an explicit declared rights class, constituent rights classifications, auditable evidence, and a fixed route request of `NORMAL_STOCK_PRODUCTION`.

Gate-level rights classes are:

- `GENERIC_UNRESTRICTED`
- `REVIEW_REQUIRED`
- `UNKNOWN`
- `BRAND_RESTRICTED`

H01-120 Semantic Family v1 supplies the first three canonical family classifications (`GENERIC_UNRESTRICTED`, `REVIEW_REQUIRED`, `BRAND_RESTRICTED`). `UNKNOWN` exists only at the gate boundary so incomplete future set aggregation fails closed rather than defaulting to unrestricted.

## Deterministic aggregation

The gate computes the strongest constituent classification using this order:

```text
GENERIC_UNRESTRICTED < REVIEW_REQUIRED < UNKNOWN < BRAND_RESTRICTED
```

The candidate's declared class must equal the computed aggregate. A caller therefore cannot relabel a set containing a `BRAND_RESTRICTED` constituent as generic. Missing referenced evidence, duplicate constituents, duplicate evidence IDs, or rights-class drift fail closed.

A `BRAND_RESTRICTED` aggregate additionally requires at least one explicit `RIGHTS_EVIDENCE` record. Discovery is preserved, but the normal-stock route is blocked.

## Routing table

| Aggregate rights class | Decision | Next route | Normal-stock route |
| --- | --- | --- | --- |
| `GENERIC_UNRESTRICTED` | `PASS_TO_NEXT_GATE` | `NORMAL_STOCK_CANDIDATE` | candidate only |
| `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | `RIGHTS_REVIEW_HOLD` | blocked pending review |
| `UNKNOWN` | `REVIEW_REQUIRED` | `RIGHTS_REVIEW_HOLD` | blocked pending evidence |
| `BRAND_RESTRICTED` | `BLOCK_NORMAL_STOCK` | `RESTRICTED_RIGHTS_REVIEW` | blocked |

`PASS_TO_NEXT_GATE` means only that H01-122 found no semantic family/set rights classification blocking the *next* gate. The decision always returns:

```text
production_authorized = false
submission_authorized = false
publication_authorized = false
rights_gate_bypass_allowed = false
legal_clearance_claimed = false
```

## Family v1 adapter

`lib/family_set_rights_gate.py::candidate_from_semantic_family` validates a canonical H01-120 Semantic Family and creates the gate envelope without rewriting family or Object Atlas identity. The H01-120 `SYSTEM / BRAND_RESTRICTED` fixture is the acceptance proof that a restricted system remains representable while being barred from normal stock routing.

Future H01-123 Design Set composition may produce the same gate envelope from its constituent families. H01-122 does not define or start H01-123.

## Relationship to existing rights controls

FA-136 operates after artifact generation from OCR/logo/watermark/safety detector observations. `RIGHTS-001` also produces artifact-bound rights/IP evidence. H01-122 runs earlier, on semantic Family/Set candidate classification and provenance. Passing H01-122 cannot bypass those downstream artifact gates or Founder-controlled submission authority.
