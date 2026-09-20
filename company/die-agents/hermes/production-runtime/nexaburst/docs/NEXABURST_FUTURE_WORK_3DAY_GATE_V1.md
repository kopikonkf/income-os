# NexaBurst Future Work — 3-Day Durability Gate V1

## Trigger

Do not activate the work in this file immediately.

Activate only if NexaBurst remains operationally healthy through the next three days of durability testing, including sustained bulk generation and no material account restriction.

The durability gate should consider:

- authenticated session remains stable
- Unlimited entitlement remains active while purchased
- no account suspension or provider block
- no persistent HTTP 429 / rate-limit regime
- raw latency does not show sustained severe degradation
- terminal provider failure rate remains bounded
- duplicate provider jobs remain zero
- browser recovery remains single-owner and bounded
- Telegram Founder controls remain reachable
- H01 storage and control-plane health remain stable

## Future Work A — Dedicated Gemini Native SVG / Vector Lane

Evidence already exists that Gemini web can return a native editable SVG through the provider UI Download SVG control.

Before scaling a vector lane:

1. Build a fresh isolated lane, separate from WC-L0 raster state.
2. Use a dedicated provider/browser identity only after the three-day gate is positive.
3. Require one-to-one semantic binding between requested noun and returned SVG.
4. Reject cross-bound or reused provider output by:
   - provider-original SHA uniqueness checks across different requested nouns
   - semantic subject validation
   - exact job/request lineage
5. Validate:
   - XML/SVG syntax
   - no embedded raster unless explicitly allowed
   - editable vector geometry
   - no logo/trademark/readable text unless intended
   - no clipped geometry
   - commercial composition
   - derivative render consistency
6. Preserve immutable provider-original SVG.
7. Treat post-processing as vector QA/normalization, not raster upscaling.

Historical H01-108 evidence shows Gemini SVG capability is real, but also shows old pipeline cross-binding risk: identical SVG hashes appeared under unrelated noun runs. A new lane must close this before production use.

## Future Work B — NexaBurst-First Producer Strategy

If the three-day durability gate is positive, Founder may pause the operational plan to manually log in and maintain approximately 100 Brave web-AI profiles.

Evaluate concentrating production on NexaBurst/provider-backed lanes first, including:

- raster isolated object
- native SVG/vector
- motion
- video
- pattern
- outline
- template-oriented outputs
- other Factory Asset V1 requirement families where provider-native output is cheaper or simpler than local synthesis

Factory Asset V1/V2 should remain useful for:

- deterministic QA
- lineage
- metadata
- format normalization
- derivatives
- rights/IP checks
- submission packaging
- provider-native output validation

The decision should be based on economics:

- provider throughput
- post-production CPU cost
- account durability
- output acceptance rate
- storage cost
- manual maintenance burden
- marketplace usefulness

## Decision Gate

After three days, produce a Founder decision memo comparing:

1. NexaBurst raster economics.
2. Gemini native SVG/vector economics.
3. Existing multi-web-AI profile strategy.
4. Local Factory V1/V2 synthesis cost.

No future lane should be mass-armed only because a small canary looks visually good.

## Evidence Update — 2026-09-20 Nexabot SVG Modality Canary

The current NexaBurst production adapter uses Nexabot `/api/v1/generate` with `mode=img`.

An isolated canary explicitly requested an actual editable native SVG file (paper-airplane vector). Nexabot completed the provider job successfully but returned:

- MIME: `image/jpeg`
- detected format: `JPEG`
- provider download filename: `.jpg`
- native_svg_pass: `false`
- queued_for_v2: `false`
- latency: approximately 17 seconds

A second isolated SVG-requirement canary terminated with Nexabot provider error `fetch failed` before producing an artifact. It was not retried in the modality experiment and did not enter V2.

Operational conclusion:

- Native SVG does **not** pass through the currently observed Nexabot `mode=img` path merely by requesting SVG in the prompt.
- Do not create a dedicated Nexabot-native-SVG lane unless a separate official/backend modality or endpoint is discovered and verified to return `image/svg+xml` / actual SVG bytes.
- Nexabot may still be useful for raster assets rendered in vector-like styles (flat, outline, icon, pattern, etc.), but those remain raster assets unless a separate vectorization workflow is intentionally introduced.
- Direct Gemini web native-SVG capability remains a separate future lane and must use the repaired semantic/hash binding guards.
