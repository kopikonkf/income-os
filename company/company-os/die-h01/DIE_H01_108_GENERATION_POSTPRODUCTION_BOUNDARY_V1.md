# DIE H01-108 — Generation / Postproduction Boundary v1

Date: 2026-09-14
Founder clarification: H01-108 is a production/generation acceptance, not a rights-acceptance task.

## H01-108 terminal boundary

H01-108 is complete when exactly 100 unique noun positions have a valid technical semantic master. A counted position requires immutable provider-original lineage and H01-103 technical PASS with a native-editable canonical SVG. Duplicate semantic masters do not count.

Provider behavior is not fully controllable. A provider may ignore a native-SVG instruction or return the wrong modality. That is a provider-output failure taxonomy, not a rights failure. A committed provider result must never be blindly resubmitted. Recovery of the committed answer is preferred. If the committed answer is conclusively the wrong modality and the frozen batch item permits adaptive redistribution, one bounded generation on another READY provider may be used with a new globally unique attempt identity.

The first-100 live batch reached 100/100 technical semantic masters. Position 090 Houseplant produced a Copilot PNG despite the vector instruction; that committed turn was classified as wrong modality and not misread as the following Candy Cane SVG. One bounded adaptive Claude A2 generation produced a native-editable SVG and H01-103 PASS.

## Postproduction is separate

After a technical master exists, derivatives, metadata, visual-rights analysis, rights classification, Founder QC, marketplace compatibility, packaging and submission eligibility belong to downstream postproduction state.

A technically valid master must not be regenerated merely because postproduction ends in REVIEW_REQUIRED or BLOCKED_RIGHTS. Those are honest postproduction outcomes. Rights thresholds must not be lowered to increase the batch pass count.

Postproduction may continue asynchronously after H01-108 is complete. Its aggregate counters must be reported separately from H01-108 generation counters.

Recommended terminal postproduction classifications per asset are PASS, REVIEW_REQUIRED and BLOCKED_RIGHTS. Submission eligibility remains fail-closed and requires the relevant downstream gates, including rights PASS and Founder QC PASS.

## State separation

Generation state:

`PENDING -> DISPATCH_COMMITTED -> ARTIFACT_CREATED -> H01_103_PASS -> GENERATION_COMPLETE`

Postproduction state:

`H01_103_PASS -> DERIVATIVES/METADATA -> RIGHTS_CLASSIFICATION -> FOUNDER_QC -> PACKAGE/SUBMISSION_ELIGIBILITY`

The two state machines share immutable asset identity and lineage, but neither may overwrite the other's terminal meaning.

## Scaling dependencies

Production-scale generation should depend on the H01-108 technical production proof and concurrency/runtime readiness, not on a marketplace acceptance outcome. Marketplace upload/moderation acceptance remains a parallel downstream proof and gates publication/submission rollout, not the ability to generate the next technical batch.

## Non-negotiable invariants

- No duplicate provider dispatch after a committed attempt unless the original output has been conclusively classified terminal and an explicitly bounded redistribution policy applies.
- Never acquire an SVG from another conversation turn to satisfy the current noun.
- Preserve provider-original bytes and hashes.
- H01-103 technical PASS is the H01-108 generation-count boundary.
- Rights REVIEW/BLOCK never causes automatic regeneration of an already-valid technical master.
- Rights and Founder-QC gates remain fail-closed for submission eligibility.
- Submission, publication and spend authority remain separate from H01-108.
