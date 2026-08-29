# Division01 Opportunity Signals Engine v1

Status: ACCEPTED ENGINE FOUNDATION
Milestone: OE-001

## Components

- `SIGNAL_TAXONOMY_V1.md` ? source-independent signal vocabulary.
- `ACQUISITION_CONTRACT_V1.md` ? fail-closed acquisition/ToS boundary.
- `die.division001.opportunity-signals.v1.schema.json` ? strict receipt schema.
- `validate_signal_receipt.py` ? semantic/policy/freshness validator.
- `adapters/public_search_ui_fixture.py` ? deterministic source-shaped public-search fixture adapter.
- `adapters/official_api_fixture.py` ? deterministic source-shaped official-API fixture adapter.
- `adapters/buyer_intent_fixture.py` ? deterministic synthetic BUYER_TERM_PRESENCE adapter used by Longtail phrase-level integration tests.
- `signal_registry.py` ? SQLite receipt registry with idempotent dedupe, conflict detection, freshness filtering and indexed queries.

## What OE-001 proves

OE-001 proves the reusable evidence substrate required by OE-002 Demand Score:

1. source observations normalize into one receipt contract;
2. timestamps and expiry are explicit;
3. policy/method mismatches fail closed;
4. synthetic fixtures cannot masquerade as live evidence;
5. duplicate observations do not inflate evidence count;
6. same dedupe identity with conflicting payload fails;
7. stale evidence is excluded from current queries by default;
8. consumers can query by subject, source, signal type and parent candidate.

## What OE-001 does not claim

OE-001 does **not** claim that Adobe Stock, Freepik, Shutterstock, Dreamstime, Google, Bing or any other external source has been queried live.

The fixture adapters are source-shape proofs only. None performs external collection. A future live adapter must have a separately reviewed acquisition policy profile and must reuse the exact receipt/registry contract without weakening it.

OE-001 also does not calculate Demand Score, Worth-Making, Blueprint semantics or production authorization.

## Handoff to OE-002

OE-002 consumes only validated signal receipts from this layer. Missing evidence remains missing/UNKNOWN; OE-002 may not replace absent signal receipts with hidden static priors.
