# Division01 Longtail / Cross-Join Engine v1

Status: ACCEPTED ENGINE v1
Milestone: OE-003

## Components

- `generate_longtail.py` — deterministic bounded Object×Human candidate generation; no object-specific expansion dictionary.
- `guard_longtail.py` — normalization, exact/parent/near-duplicate controls, per-seed quota and IP review routing.
- `guardrails/IP_GUARDRAIL_V1.json` — high-confidence protective review terms; not complete legal clearance.
- `phrase_signal_score.py` — validates/ingests phrase-level OE-001 receipts, strips registry-only metadata, and invokes OE-002 Demand Score.
- `longtail_registry.py` — separate Longtail candidate registry, score attachment, idempotency/conflict detection, and COMPLETE-only ranking.
- `fixtures/synthetic-canary-v1.json` — deterministic no-network end-to-end canary.
- `run_synthetic_canary.py` — executable idempotent fixture runner using caller-supplied state directory.

## Execution chain

```text
Object Atlas read-only receipt
        +
Human Atlas hypothesis-context receipt
        |
        v
bounded dynamic candidate generation
        |
        v
normalization / duplicate / quota / IP review guardrails
        |
        +-- REVIEW / REJECTED -> deferred
        |
        v ACCEPTED
phrase-level OE-001 receipts
        |
        v
OE-001 validator + signal registry
        |
        v
OE-002 Demand Score
        |
        +-- PARTIAL / INSUFFICIENT / HARD_VETO -> deferred
        |
        v COMPLETE
Longtail registry ranking
```

## Dynamic expansion

The generator is not a semantic LLM and does not claim that every phrase is commercially good. It creates cheap, bounded, falsifiable hypotheses using generic typed combinations of cleaned object seed + compatible Human Atlas context. Commercial quality is established later by phrase evidence, Demand Score and Worth-Making cognition.

Default hard maximums are inherited from the foundation: 50 generated candidates per invocation/seed, at most four typed modifiers per candidate, and bounded Human/Object retrieval upstream.

## Guardrail semantics

- structural parent redundancy, exact duplicates, severe near-duplicates and quota overflow are REJECTED;
- moderate near-duplicates are REVIEW;
- high-confidence trademark/reserved-term hits are REVIEW, not silently deleted;
- IP denylist is protective and explicitly not exhaustive legal clearance;
- candidate ID is deterministic over seed + Human context + normalized phrase + Product Expression and is revalidated before guard evaluation.

## Phrase-level evidence

Production scoring accepts only canonical OE-001 receipts whose subject exactly matches the child phrase and whose parent seed/candidate IDs match the Longtail candidate. Registry metadata such as `registry_freshness` is transport metadata and is removed before strict OE-001 receipt validation by OE-002.

For no-network tests/canaries, three fixture-only adapters produce synthetic DEMAND, SUPPLY and COMMERCIAL_INTENT receipts. Synthetic fixtures remain `SYNTHETIC_ONLY` and never claim live collection. Missing/stale required evidence still yields no numeric score.

## Persistence boundary

Longtail v1 persists into its own caller-supplied SQLite registry. It never writes to the Object Atlas database. The registry stores candidate/hash/guard lineage and optional OE-002 score lineage. Exact replays are idempotent; conflicting candidate or score identities fail closed.

## Ranking

Only candidates with:

`guard_status=ACCEPTED AND OE-002 score_status=COMPLETE AND final_score numeric`

are ranked. REVIEW, REJECTED, unscored, PARTIAL, INSUFFICIENT_EVIDENCE and HARD_VETO remain deferred with counts/reasons.

## Authority

Longtail ranking is opportunity evidence organization only. It is not Worth-Making, Blueprint, production, QA/QC, submission, publication or spend authority.

## Live-acquisition boundary

OE-B06 performs no external network collection. The synthetic canary proves wiring only. Real phrase-level collectors remain governed by OE-001 acquisition policies and platform/source-specific authorization.
