# DIE H01 First 100 Market-Informed SVG Batch v1

Status: **H01-108 RUNNING — Founder authorized 2026-09-12**

H01-108 converts the first 100 H01-101 eligible Object Atlas nouns into real standalone native-SVG semantic masters. This is a production proof, not a disposable synthetic soak. The frozen manifest contains 60 evergreen commercial objects, 30 current market-opportunity/momentum objects, and 10 Q4 seasonal objects. Every row retains its canonical H01-101 queue ID, source candidate ID, rights/feasibility lineage and idempotency key.

The 10 seasonal nouns are: `snowman`, `reindeer`, `stocking`, `ornament`, `snowflake`, `sleigh`, `holly`, `mistletoe`, `candy cane`, and `firework`. Market observations are bounded prioritization evidence only; they do not implement or bypass H01-130..133 Demand Intelligence and do not mutate Object Atlas validity.

Provider targets are weighted rather than flat: Gemini 24, Qwen 20, Claude 20, ChatGPT 12, Manus 12 and Copilot 12. Adaptive redistribution is allowed only among READY providers if capacity/quota blocks a planned provider. Grok and Duck.ai remain excluded from this initial batch. Qwen uses a long progress-aware completion budget and late-completion recheck policy. Default provider cooldown is 180 seconds and overlaps work on other eligible providers.

Current profile readiness remains honest: only `h01-web-p001` is READY. Therefore the first batch runs sequentially within `h01-web-s01`; provisioned but unauthenticated siblings are never promoted implicitly. H01-026 owns local provider/profile leasing and H01-025 remains the sole browser owner.

Each generated asset must preserve provider-original bytes and lineage, pass H01-103 SVG validation, H01-105 deterministic postproduction/read-back QA, metadata generation and the visual-rights observation/gate. A rights result of `REVIEW_REQUIRED` may still count as a technically accepted semantic master because H01-109 owns Founder-QC/upload readiness; it must remain `submission_eligible=false` and may never be represented as marketplace-ready. `BLOCK` does not count toward the 100 accepted semantic masters.

No marketplace submission, publication, credential mutation or spend is authorized by H01-108.

## Three-stage working-state boundary

H01-108 follows the accepted Factory Asset v2 separation instead of treating postproduction as part of provider generation.

1. **PRE_PRODUCTION** — H01-026/H01-025 verify profile readiness, UDD ownership, provider/browser readiness and exactly-once dispatch eligibility. Failure here may prevent that provider generation attempt.
2. **PRODUCTION** — provider prompt dispatch and output acquisition end durably at `ARTIFACT_CREATED`. The immutable provider-original SVG and its hash are written before `browser-job-result.json` becomes terminal `SUCCEEDED`. H01-025 then closes Brave and H01-026 releases the UDD/provider lease. No H01-103/H01-105/rights/metadata work is allowed to hold this generation lease.
3. **POST_PRODUCTION** — a separate resumable worker consumes `ARTIFACT_CREATED` workspaces and runs H01-103 validation, H01-104 lineage receipt, H01-105 vector derivatives/read-back QA, metadata, visual-rights signals and Founder-QC parking. A postproduction failure becomes `PARKED_POSTPRODUCTION_RETRY` for that exact artifact and never invalidates its generation receipt or blocks a later independent noun/provider generation.

This mirrors the proven Factory v2 boundary where `ARTIFACT_CREATED` hands off to the durable postproduction state machine and `WAITING_FOUNDER_RIGHTS_REVIEW` / `WAITING_FOUNDER_QC` are parked states rather than global production blockers.
