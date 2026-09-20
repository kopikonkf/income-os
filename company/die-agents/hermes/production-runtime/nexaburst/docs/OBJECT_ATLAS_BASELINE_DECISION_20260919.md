# NexaBurst Object Atlas production-baseline decision

Status: PROPOSED_FOR_POC / MASS_PRODUCTION_HOLD

## Canonical universe vs production queue

DIE-203 canonical Linux runtime seed_library.db is the promoted final Object Atlas universe:
- 475,560 unique lower(trim(word))
- not_in_wordnet: 401,121
- wave3_eligible: 41,725
- h4_capital: 32,542
- eligible_control: 172

The 433,835 database is a historical pre-Wave3 checkpoint, not the active Linux baseline.

The final universe is broader than the immediate production-safe cohort. Gemini OBJECT means representable object/figure/symbolic item; it is not equivalent to commercial stock safety.

## H4 audit

Audit queue h4_capital:
- OBJECT: 32,471
- REJECT: 52,760
- UNSURE: 1,301

Active final seed library contains 32,542 h4_capital rows, therefore 71 h4 rows are outside audited OBJECT. Examples include encoding/proper-name/person/brand/concept forms. Do not use h4 as the first NexaBurst mass-production baseline without an additional production-suitability/IP/person/proper-name gate.

not_in_wordnet:
- audited OBJECT: 401,107
- final seed rows: 401,121
- 14 rows are outside audited OBJECT.

## Recommended NexaBurst Product Line #1 source

Use object_asset_engine.db candidate_seeds with:
- wave3_status = eligible
- source_tier = pass
- ip_risk = none

Observed count: 42,667 unique canonical names.

This is the first-source reservoir. It still requires morphology/semantic-family de-duplication before marketplace-scale production because singular/plural and lexical variants can represent the same commercial asset.

The full 43,005 Wave3 eligible cohort remains preserved; 338 are source_tier=review.

## Runtime trace

Hermes Production Cycle v1 reads /var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db through production_seed_selector.py and production_seed_replenisher.py.

Factory Orchestration v2 is seed-DB agnostic. It consumes an already-selected workspace/source/blueprint and performs postproduction through Founder QC.

## Prompt authority

NexaBurst canary template prompts are NOT the desired mass-production prompt authority.

Mass production should consume the canonical typed chain:
Object Atlas seed -> Subject Specification -> Production Preset -> Visual Requirement Spec -> deterministic Compiled Provider Prompt.

The current production-preset registry contains the historical accepted watercolor-cartoon preset and a Founder-design candidate premium semi-realistic illustration preset. Activation changes require their own bounded acceptance; NexaBurst must not silently turn NOT_LIVE presets into production defaults.

## Safety

- full queue remains HOLD
- no marketplace submission authority
- no publication authority
- no spend authority
- >100 batch requires explicit PRODUCTION_ARMED runtime marker
