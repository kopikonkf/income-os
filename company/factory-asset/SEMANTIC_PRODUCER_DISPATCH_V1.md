# Semantic Producer Dispatch Router v1

Task: `FA-133`
Status: PASS
Date: 2026-09-04

## Purpose

Select exactly one governed **master producer route** from a validated asset-expression selection plus its frozen Asset Blueprint v2. This router sits after semantic planning/Blueprint freeze and before any provider/native producer execution.

## Accepted routes

- `PHOTO` / `ISOLATED_OBJECT` + `RASTER_GENERATIVE` -> `FA104_PROVIDER_ROUTER`. The semantic router does not choose a concrete provider; FA-104 still applies policy/capacity/capability ranking.
- `PATTERN` + `PROCEDURAL_VECTOR` -> `PROCEDURAL_PATTERN_V0_1`, accepted by FA-034.
- `ANIMATION` + `MOTION_RENDERER` -> `MOTION_ENGINE_V0_1`, accepted by FA-043.

`ICON` / `OUTLINE` native-vector routes are recognized but intentionally remain unavailable until a generic native-vector engine is separately accepted. Schema permission is not sufficient evidence of engine readiness.

## Frozen-input invariants

Dispatch requires:

- valid FA-129 asset-expression plan with decision `SELECT`;
- exactly one expression for the requested `semantic_asset_id`;
- exact SHA-256 match to the frozen Blueprint payload;
- matching semantic asset ID, semantic mode, producer class, native representation and marketplace profile;
- accepted producer-engine evidence in the registry.

Any mismatch fails closed before dispatch.

## Two-router boundary

This component routes **semantic master production only**. It does not produce packaging derivatives and never treats an existing static master as the source for pattern or motion generation.

Every route requires:

`master_generation_mode = DIRECT_FROM_BLUEPRINT`

and:

`post_hoc_conversion_allowed = false`

Derivative planning remains downstream after validated master intake.

## Authority

FA-133 itself performs zero provider calls, native renders, credential access, marketplace upload, publication or spend. It emits a deterministic dispatch decision only.