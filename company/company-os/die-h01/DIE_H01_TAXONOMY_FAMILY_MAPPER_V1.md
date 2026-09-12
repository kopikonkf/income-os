# DIE-H01 Deterministic Taxonomy-First Family Mapper v1

Status: H01-121 ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-121 implements the first deterministic mapper from eligible Object Atlas standalone nouns into **candidate Semantic Family v1** artifacts. It does not replace or rewrite standalone noun identity.

```text
Object Atlas eligible canonical subjects
        ↓ read-only
stored primary WordNet noun synset
        ↓ exact shared-synset grouping
TAXONOMIC Semantic Family v1 candidates
```

This is deliberately taxonomy-first. FUNCTIONAL, CONTEXTUAL, VARIANT and SYSTEM family discovery require evidence beyond the exact primary taxonomy relation and are not inferred from noun spelling.

## Live source truth

The live Object Atlas has 43,005 `candidate_seeds.wave3_status='eligible'` rows. For those rows:

- `category_path` is NULL/blank for all 43,005;
- aliases are currently empty for all eligible rows;
- every eligible row has at least one stored `wordnet_synsets` entry;
- Wave-3 suitability is 42,667 `lexname=noun.*` and 338 `physical_entity_path`.

Therefore H01-121 does **not** invent a category path or infer a category from noun text. Its taxonomy key is the exact first stored WordNet noun synset, the same primary-sense evidence family used by earlier Object Atlas filtering.

## Mapping rule

For every eligible Object Atlas candidate:

1. preserve `candidate_seeds.id` as canonical `subject_id` / family `member_id`;
2. preserve the canonical name exactly apart from whitespace normalization;
3. parse stored `wordnet_synsets` and select index `0` as `primary_synset`;
4. group subjects only when two or more subjects share the exact same primary synset;
5. emit one `family_class=TAXONOMIC` Semantic Family v1 artifact per shared primary synset;
6. leave one-member synsets standalone and emit no artificial family.

The semantic key is a deterministic schema-safe slug of the primary synset, e.g.:

```text
book.n.01          -> wordnet.primary.book.n.01
adam's-needle.n.01 -> wordnet.primary.adam-s-needle.n.01
```

The original unslugged synset remains preserved in family definition and taxonomy evidence.

## Identity boundary

Family membership has `identity_effect=NONE`. A family never changes:

- standalone Object Atlas candidate ID;
- canonical noun identity;
- semantic asset count;
- H01-101 standalone SVG queue identity;
- provider or production routing.

Plural/synonym peers such as `book` / `books` or `backpack` / `rucksack` remain separate canonical members even when they share one primary synset.

## Evidence

Every generated family carries:

- one `OBJECT_ATLAS_TAXONOMY` evidence record naming the exact primary synset and the read-only Object Atlas source;
- one `OBJECT_ATLAS_RECORD` evidence record for every member, binding candidate ID and raw noun ID;
- the full eligible-source projection fingerprint as taxonomy evidence SHA-256.

The live maximum family size is 34, so taxonomy evidence plus every member record remains safely inside Semantic Family v1's 100-evidence limit. The mapper fails closed if a future group would exceed its evidence budget rather than dropping member provenance.

## Duplicate and alias controls

The mapper fails closed on:

- duplicate canonical subject IDs;
- duplicate raw noun IDs;
- duplicate normalized canonical names;
- malformed aliases/synset arrays;
- eligible rows missing a primary noun synset;
- a member appearing in more than one primary-synset family.

Aliases are never merge authority. If an alias term collides with another canonical subject or alias owner, the mapper emits an alias observation with `merge_authorized=false` and preserves all identities. Shared primary synset itself is family evidence, not authorization to collapse synonyms into one canonical noun.

## Rights and production authority

H01-121 assigns `rights_class=REVIEW_REQUIRED` to every candidate family. Individual eligible nouns having `ip_risk=none` is not enough to silently declare a new multi-member family unrestricted. H01-122 owns the brand/trademark family rights gate.

All Family v1 authority flags remain false. H01-121 does not authorize production, submission, publication, Design Set creation or listing packaging.

## Live canary result

The mapper ran read-only over the live 43,005 eligible nouns and produced:

```text
candidate families       14,718
family members           41,658
standalone singletons     1,347
maximum family size          34
alias collision records       0
```

The full deterministic family JSONL SHA-256 is:

`d89fb71efa3fb8d791712b2b7c0c513f4392bd8fa68422599f114b102095d0e8`

The eligible-source projection fingerprint is:

`0e6996366d5201f11163af36b9c49ab6fd36e1b08854b88942216416cc933a56`

Object Atlas DB SHA-256 before and after mapping remained identical:

`e56bdbbba1e70cca74f5f1b59439802d929f66a9fcb730278bc67d637901bf2e`

The full ~38 MB derived canary output is intentionally not committed to Git; it is deterministic/regenerable from Object Atlas plus this mapper. Canon stores executable logic, hashes/counts and representative validated family samples instead.

## Parallel H01-304 canary boundary

This H01-121 execution is Worker A of H01-304 attempt #2. It uses only:

- browser resource `architect-primary`;
- worktree `/home/kopiko/die-sessions/H01-121`;
- branch `canary/h01-121-parallel-20260912`;
- its own H01-303 mutable-worktree claim.

It does not touch H01-122's worktree, files or task state and does not touch `/srv/die`. Remote publication remains serialized separately through `income-os.repo-write + company-os.H01-121`.
