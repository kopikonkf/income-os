# Factory Orchestration v2 — Task-Graph Design

Status: PLANNED / GRAPH-CANON ONLY
Date: 2026-09-04

## Purpose

Wire completed and emerging Factory Asset engines into one extensible Hermes production system. The design separates **semantic asset-expression selection** from **packaging derivative planning** so future producers can be added without refactoring the production chain.

## Two-router invariant

1. **Asset Expression Router (before Blueprint/producer)** selects PHOTO / ISOLATED_OBJECT / ICON / OUTLINE / PATTERN / ANIMATION as evidence-supported semantic products. A seed is not forced into every mode.
2. **Derivative Delivery Planner (after master)** selects JPEG / PNG / WebP / TIFF / PDF / vector/package representations required by a marketplace route. Derivatives never create additional semantic assets.

Motion is semantic expansion, not postprocessing. Motion eligibility depends on noun x product expression x temporal verb x buyer utility and must answer whether visual change over time communicates additional commercial meaning.

## Provider-original invariant

Provider outputs are sniffed from actual bytes. Gemini/ChatGPT/Qwen/etc. are never assumed to always return a specific format. Provider-original bytes remain immutable; master intake records magic/MIME/dimensions/alpha/bytes/SHA-256. JPEG->PNG conversion does not imply transparency, and PNG->JPEG requires explicit alpha flattening when transparency exists.

## Mandatory autonomous postproduction

`ARTIFACT_CREATED -> MASTER_VALIDATED -> UPSCALE_DECIDED -> DERIVATIVES_READY -> TECHNICAL_QA_PASS -> RIGHTS_SIGNAL_PASS_OR_REVIEW -> METADATA_READY -> PACKAGE_READY -> WAITING_FOUNDER_QC`

Hermes may notify `ARTIFACT_CREATED` immediately, but it may not park at `WAITING_FOUNDER_QC` before package readiness. Automated rights signals never replace Founder human clearance.

## Cognition routing

Reuse a compatible fixed Blueprint first. Division01 authors/revises missing or stale semantics. Executive challenges only new/material family strategy or explicit escalation. Neither actor gates every generated image.

## Producer routing

- provider raster producer: PHOTO / ISOLATED_OBJECT and other raster expressions;
- native procedural/vector producer: PATTERN and supported vector expressions;
- motion renderer: ANIMATION only after motion-capability eligibility and motion Blueprint;
- future layered-template/3D producers attach through the same registry-driven producer interface.

## Scale/governed canary consequence

FA-120 scale harness and FA-200 governed canary now depend on FA-140 orchestration acceptance so the project cannot scale or certify the obsolete seed->image->early-Founder-gate chain.
