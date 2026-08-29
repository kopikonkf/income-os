# Division01 Blueprint Engine v1 — OE-B09 Contract Foundation

Status: OE-005A/B/C/D/E/F DONE; milestone OE-005 ACCEPTED.

## Governed chain

```text
OE-004 governed Worth-Making result = PROMOTABLE_TO_BLUEPRINT
        ↓
Division01 Blueprint semantic AUTHOR
        ↓
semantic drift / completeness validation
        ↓
deterministic compile-boundary projection (no semantic mutation)
        ↓
Executive read-only Blueprint REVIEW
        ↓
OE-005D final compiler / OE-005E provenance hash lock / OE-005F failure suite
```

## Authority

Division01 owns Blueprint semantics. Workers/Hermes may validate, serialize and hash but may not invent, repair, paraphrase or silently fill missing buyer, family, prompt, variation, platform, metadata or QA semantics. Executive reviews exact hashes and challenges strategy; it does not edit the Blueprint. Founder production authority remains downstream and exact-hash scoped.

## Worth-Making drift boundary

Blueprint must preserve the governed Worth-Making candidate, family ID, commercial-use hypothesis, differentiation thesis, buyer JTBD/utility and Product Expression. Any material change to those fields must return to OE-004 and produce a new governed Worth-Making attempt.

## Compiler boundary

OE-005B creates only a deterministic compile-input projection. It re-runs semantic validation itself, copies exact authored semantics, hashes each semantic field and fixes `semantic_content_mutated=false`. The final compiled Blueprint artifact and Founder-gatable immutable hash are intentionally deferred to OE-005D/E.

## Executive review

Exactly six challenge domains are mandatory: Worth-Making thesis fidelity, family strategy coherence, constraint contradiction integrity, portfolio overlap/differentiation, Product Expression fit, and whether proposed production actually tests the Worth-Making thesis. Outcome semantics mirror the governed review pattern: `NO_VETO`, `REVISE`, `VETO_PENDING_EVIDENCE`, or `ESCALATE_FOUNDER`.

## OE-B10 acceptance

OE-005D/E/F are complete. `compile_blueprint.py` performs final deterministic compilation only after author semantic validation and exact Executive `NO_VETO` review. One v1 engine selection is required; ambiguous selection fails rather than allowing Worker choice. `BLUEPRINT_COMPILER_CAPABILITY_PROFILE_V1.json` maps the authored engine to MUXIA provider/capability contract and validates pinned MUXIA source/test evidence while explicitly refusing to claim runtime availability.

`lock_compiled_blueprint.py` recompiles from full source lineage before locking, requires exact canonical JSON bytes, and emits an immutable provenance receipt whose exact compiled-artifact SHA256 is eligible to be named in a future Founder authorization. The receipt itself fixes `authorization_granted=false` and `production_authority_granted=false`.

OE-005F proves deterministic replay, exact semantic survival, capability mismatch/ambiguous engine rejection, stale/REVISE review rejection, semantic-gap rejection, canonical-byte enforcement, hash tamper detection and post-lock mutation failure. `OE-006A` is next.
