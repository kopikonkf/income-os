# DIE-H01 Semantic Family v1

Status: H01-120 ACCEPTANCE CANDIDATE
Date: 2026-09-12
Scope: semantic grouping contract for DIE-H01. It does not authorize production, submission, publication, or marketplace action.

## 1. Canonical meaning

A **Semantic Family** groups two or more canonical semantic members because they share one evidenced semantic relationship. The relationship class is exactly one of:

- `TAXONOMIC` — shared taxonomy/category relationship.
- `FUNCTIONAL` — shared practical function or job.
- `CONTEXTUAL` — shared use/context relationship.
- `VARIANT` — canonical object variants related without collapsing their underlying identities.
- `SYSTEM` — members belonging to one coherent system/ecosystem; this class can represent restricted/branded systems without making them production-eligible.

Family membership never rewrites Object Atlas identity. Every member carries a canonical `OBJECT_ATLAS` subject reference, and `identity_effect` is always `NONE`.

## 2. Boundary with adjacent concepts

These four concepts are deliberately distinct:

```text
SEMANTIC FAMILY
  = related semantic members

DESIGN SET
  = intentionally composed coherent collection/blueprint made from semantic members

DERIVATIVE BUNDLE
  = multiple file-format/size outputs from the same semantic master

LISTING PACKAGE
  = marketplace delivery metadata/files/evidence around one asset or set
```

A single semantic asset exported as SVG + PNG + JPEG + WebP is therefore **one semantic asset with derivatives**, not a multi-member family. Family v1 requires at least two semantic members and its `boundary` constants explicitly reject Design Set, Derivative Bundle, and Listing Package identity.

Existing Factory canon remains compatible: derivatives have `semantic_identity_effect = NONE`, and packaging variants do not create new semantic assets. H01-120 does not modify those contracts.

## 3. Identity and deterministic family ID

The stable family ID is:

```text
FAM-V1-<FAMILY_CLASS>-<24 uppercase SHA-256 hex chars>
```

Canonical key material is JSON with sorted keys and compact separators:

```json
{
  "family_class": "...",
  "family_version": "...",
  "canonical_subject_ids": ["... sorted ascending ..."],
  "semantic_key": "..."
}
```

Compute SHA-256 over the UTF-8 canonical JSON and take the first 24 hexadecimal characters, uppercase. Member order in persisted Family v1 artifacts is `canonical_subject_ref.subject_id ASC`. The canonical subject ID is the stable membership key; duplicate canonical subject IDs are invalid.

Evidence/rights updates do not silently mint a different semantic family identity; they are auditable classification/provenance state around the stable semantic grouping. A membership change, class change, semantic-key change, or family-version change changes the deterministic ID.

`lib/semantic_family_v1.py` is the canonical cross-field validator for invariants JSON Schema cannot express alone: canonical subject order/uniqueness, `member_id == canonical_subject_ref.subject_id`, unique evidence IDs, and deterministic `family_id` recomputation.

## 4. Provenance and rights

`source.evidence` must contain at least one evidence record. Canonical producers should preserve source refs/hashes sufficient for H01-121/H01-122 to audit why membership exists.

`rights_class` is exactly one of:

- `GENERIC_UNRESTRICTED`
- `REVIEW_REQUIRED`
- `BRAND_RESTRICTED`

The Family contract itself grants no production authority. `authority.production_authorized`, `submission_authorized`, and `publication_authorized` are always false. `BRAND_RESTRICTED` families are representable for discovery/audit, but `restricted_family_auto_eligible` is always false; H01-122 owns the later rights gate.

## 5. Compatibility with older `family` fields

Older Division01 / production-cognition artifacts contain `family_id` fields used for commercial hypotheses or candidate grouping. H01-120 does not rewrite historical receipts or silently reinterpret those objects as Semantic Family v1. A record is canonical Family v1 only when it validates against `contracts/h01-semantic-family.v1.schema.json` and has `artifact_kind=SEMANTIC_FAMILY`.

This preserves legacy evidence while giving H01-121 a precise target contract for deterministic family mapping.

## 6. Acceptance examples

`fixtures/h01-semantic-family-v1.examples.json` contains one schema-valid fixture for each of the five required classes. The `SYSTEM` fixture is intentionally `BRAND_RESTRICTED` to prove restricted systems can be represented without acquiring production authority.

H01-120 defines only the contract. It does not implement H01-121 mapping, H01-122 rights gating, or H01-123 Design Set composition.
