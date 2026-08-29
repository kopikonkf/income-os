# Division01 Blueprint AUTHOR + Compile Boundary v1

## Authority

`division-head-division01` is the sole semantic AUTHOR of the division-scoped Blueprint. Blueprint authoring starts only from a current governed Worth-Making bundle whose decision is `PROMOTABLE_TO_BLUEPRINT`.

The Blueprint must preserve the accepted Worth-Making thesis. Candidate, family ID, commercial-use hypothesis, differentiation thesis, buyer JTBD/utility and Product Expression are lineage-bound to OE-004. If those semantics need to change, the workflow returns to Worth-Making and produces a new governed attempt; Blueprint is not a loophole for changing an accepted commercial decision.

Division01 owns all new production semantics: family thesis, buyer persona/use cases, visual constraints, exact master prompt, negative constraints, semantic variation plan, platform strategy, metadata direction, QA/Blueprint-adherence/falsification rules, and economics hypotheses.

## Master prompt / variation contract

`master_prompt` is exact authored content. Workers/Hermes may not rewrite it. `negative_constraints` and each variation instruction/rationale/distinctness test are also authored semantics. Duplicate variation IDs/instructions, unresolved placeholders, variation plans larger than the bounded batch, and primary/secondary keyword overlap fail validation.

Semantic variations must express meaningful changes along typed dimensions such as object, activity, buyer use case, problem, place, composition, Product Expression, commercial intent, material or state. Shallow byte/prompt perturbation is not a semantic variation contract.

## Deterministic compiler boundary

OE-005B does **not** implement the final Blueprint compiler; that remains OE-005D. `prepare_compile_input.py` creates a deterministic semantic projection only after the author artifact passes validation. It copies exact authored semantic fields, hashes each field, records the exact author-artifact hash, fixes `semantic_content_mutated=false`, and declares `compiler_role=SERIALIZE_VALIDATE_HASH_ONLY`.

A Worker/OpenCode implementation may serialize/validate/hash this projection, but missing or invalid semantics fail closed. It may not invent buyer logic, rewrite prompts, fill missing variations, or silently change platform/QA directions.

`production_authority_granted=false` remains fixed. Blueprint validity is not Founder production authorization.