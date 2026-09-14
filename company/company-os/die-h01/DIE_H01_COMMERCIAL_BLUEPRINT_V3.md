# DIE H01 Commercial Blueprint v3

Task: H01-102A

## Purpose

Commercial Blueprint v3 is the deterministic Phase-0 bridge from H01-132A production intent into the existing Blueprint -> Master Instruction -> Provider Prompt chain.

```text
H01-132A frozen production intent
        ↓
Commercial Blueprint v3
        ↓
Master Instruction v2
        ↓
Provider Prompt v2
```

The Blueprint remains provider-independent WHAT. Provider phrasing remains downstream HOW.

## Deterministic commercial semantics

Blueprint v3 does not ask an LLM to invent buyer or use-case semantics. Commercial fields are selected deterministically from the H01-132A `commercial_basis`:

- marketplace demand evidence -> generic stock-marketplace asset utility for the exact noun;
- macro search evidence -> broad design reuse without purchase-intent claims;
- attention evidence -> baseline reuse while explicitly denying buyer-intent inference;
- source-order fallback -> baseline standalone vector utility with no market-demand claim;
- unclassified ranked evidence -> standalone utility without unsupported specialization.

No industry, demographic, named buyer, Human Atlas context, longtail, or Object×Human specialization is introduced in Phase 0.

## Evidence lineage

`die.h01.svg-blueprint.v3` extends the v2 WHAT contract with `commercial_evidence` containing:

- H01-132A intent ID and SHA-256;
- selection reason;
- commercial basis mode and source tiers;
- demand rank state/score/confidence;
- immutable evidence references;
- buyer/use-case scope boundaries;
- queue/selector/materialization lineage hashes.

These fields affect the Blueprint hash and therefore the Master Instruction hash, but raw evidence IDs are not inserted into provider prompt text. The provider receives semantic requirements, not internal provenance identifiers.

## Runtime integration

The existing H01-108 generation path remains backward-compatible:

- without `--intent-manifest`, `h01_108_blueprint.py` continues to build legacy Blueprint v2;
- with `--intent-manifest`, it resolves the selected H01-132A intent, verifies its frozen manifest SHA, queue identity and batch position, then emits Blueprint v3;
- `h01_108_run_one.py`, `h01_108_generation_cycle.py`, and `h01_108_autonomous_supervisor.py` forward the explicit intent manifest.

A modified intent whose SHA no longer matches the frozen H01-132A manifest is rejected before Blueprint generation.

## Live acceptance 2026-09-14

Input Phase-0 intent manifest:

`H01-P0MAN-6267BB795752A51868B0EEE0`

Result Blueprint manifest:

`H01-BP3MAN-D6250B990ECE1B8B2D57031F`

Manifest SHA-256:

`c93c7e5c5e357329e52aa85d5b4c06022e5a3932848b6ba2f9d91c26affedb01`

Acceptance:

- 100/100 selected Phase-0 intents compiled;
- 4 evidence-ranked Blueprints;
- 96 fallback Blueprints;
- 100/100 Blueprint v3 schema-valid;
- replay produced the same Blueprint manifest ID and SHA;
- ranked `food` Blueprint used `MARKETPLACE_DEMAND_EVIDENCE`;
- fallback `pies` Blueprint used `FALLBACK_NO_DEMAND_EVIDENCE`;
- Gemini ranked sample produced a valid 3,570-character provider prompt;
- Manus fallback sample produced a valid 1,804-character compact provider prompt;
- evidence IDs did not appear in provider prompt text;
- all production/submission/publication/spend authority remained false.

H01-102B remains intentionally deferred by Founder directive. Blueprint v3 is deterministic Python baseline only.
