# DIE-H01 Non-blocking Demand Signal Engine Contract v1

Status: H01-130 acceptance candidate
Date: 2026-09-13

Demand Signal Engine v1 is an optional ranking and discovery overlay on the deterministic H01-101 standalone SVG queue. It may prioritize remaining nouns and surface buyer, use-case, and semantic-family hypotheses. It is not an Object Atlas validator, rights gate, production gate, or replacement scheduler.

The canonical supply frontier remains the 43,005 H01-101 queue items. Demand intelligence never changes queue identity, Atlas membership, rights/feasibility evidence, or the ability of standalone production to continue without demand evidence.

## Inputs and outputs

One evaluation targets exactly one existing H01-101 `queue_item_id`. It may consume zero or more external signal receipts plus deterministic context. Signal classes may include DEMAND, SUPPLY, COMPETITION, COMMERCIAL_INTENT, TREND, and PLATFORM_FIT. This contract authorizes no connector; H01-131 owns bounded acquisition.

The output is an overlay keyed to the existing queue item. It may contain rank score, evidence state, confidence, buyer hypotheses, use-case hypotheses, and family hypotheses. Family hypotheses are discovery suggestions only; they are not canonical H01-120 Semantic Families.

## Hard non-blocking invariants

Every output states `queue_identity_effect=NONE`, `object_atlas_validity_effect=NONE`, `rights_effect=NONE`, `feasibility_effect=NONE`, and `standalone_production_blocking_effect=NONE`. Production, submission, publication, and spend authority flags are always false.

Therefore no evidence is not zero demand; stale evidence is not invalid Atlas truth; low rank is not a production rejection; missing connectors cannot block standalone production; demand cannot flip H01-101 `dispatch_eligible`; and demand cannot mutate the 43,005-item queue or Object Atlas source truth.

Ranked views may reorder remaining work for convenience, but stable H01-101 IDs and source queue bytes remain unchanged. Produced semantic masters remain valid if demand evidence later changes.

## Evidence and freshness

Signal references preserve evidence identity/hash, class, and freshness. UNKNOWN, absent, or stale evidence remains explicit and must not be silently converted to zero. `NO_EVIDENCE` requires `UNRANKED` with `rank_score=null`. A ranked result requires at least one fresh evidence reference. Partial coverage may lower confidence but cannot alter Atlas validity or standalone production eligibility.

## Discovery boundary

Demand intelligence may propose buyer/persona candidates, activities/problems/jobs-to-be-done, use contexts, commercial-intent contexts, and candidate family relationships. These are hypotheses with evidence refs. H01-132 may later join bounded Human Atlas context. Cartesian expansion is not required for supply-first standalone production.

## Failure behavior

Connector outage, no evidence, stale evidence, partial coverage, ranking-model failure, or discovery-model failure degrades to an auditable unranked/partial overlay. It never blocks or invalidates the standalone production lane. Malformed demand artifacts fail only this overlay contract and have no authority over Object Atlas validity or H01-101 queue eligibility.
