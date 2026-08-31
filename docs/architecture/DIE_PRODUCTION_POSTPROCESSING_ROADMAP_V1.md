# DIE Production Post-Processing Roadmap V1

Date: 2026-08-31
Scope: Worker model activation, technical upscale/recovery, metadata/keyword delivery, and rights/IP preflight before the governed real-artifact canary.

## Purpose

The production pipeline already has Division01-authored Blueprint semantics, MUXIA artifact execution, first-class QA, first-class QC, and a later submission framework. Four gaps remain before a representative governed production artifact can traverse the complete internal pre-submission chain:

1. OpenCode Worker-001 exists on Linux but real model-backed execution is not yet governed or bound to a zero-cost model.
2. Windows Object Asset Engine contains CPU RealESRGAN x4 reference behavior, while Linux has no executable upscale runtime.
3. Blueprint and QA already define metadata/keyword semantics and package validation, but no first-class compiler/injector/read-back engine exists.
4. QA has non-waivable rights hard vetoes, but it consumes structured rights evidence; it does not itself provide brand/copyright/IP risk detection or legal clearance.

## Pipeline target

```text
Division01 Blueprint
  -> Founder exact-hash authorization
  -> Worker-001 / MUXIA artifact execution
  -> technical preflight
  -> upscale/no-op recovery
  -> metadata + keyword compilation
  -> IPTC/XMP where supported + canonical sidecar
  -> final artifact rehash/read-back
  -> rights/brand/copyright/IP preflight evidence
  -> QA hard-veto/platform preflight
  -> QC
  -> immutable submission package
```

`PUBLISHED` is not an internal transition. Marketplace lifecycle remains PREPARED -> AUTHORIZED -> SUBMITTED -> REVIEW_PENDING -> APPROVED|REJECTED -> RECONCILED, and only external evidence may support a LIVE/PUBLISHED claim.

## WRK-001 — Model-backed Worker-001

Exact preferred Linux default while listed free: `opencode/muse-spark-1.2-contributor-free`.

Policy invariants:

- zero USD only;
- no paid fallback;
- unavailable/non-free model blocks;
- real model calls require a governed Worker job envelope;
- Worker cannot invent or rewrite Division01-authored commercial thesis, master prompt, semantic variations, metadata direction, or platform strategy;
- sanitized receipt records exact provider/model identity and bounded execution evidence.

## UP-001 — Upscale/Recovery Engine v1

Reference behavior is the migrated Windows Object Asset Engine RealESRGAN x4 CPU path using `realesr-general-x4v3`, with alpha resized/cleaned separately.

Linux implementation requirements:

- isolated CPU runtime;
- model weights external to Git and SHA-256 pinned;
- no automatic upscale when technical requirements are already satisfied;
- rights/safety failures are never recoverable by upscale;
- durable input/output/model hashes and dimensions;
- no-op recovery is a first-class receipt;
- quality/parity tests must detect unacceptable edge/detail regression.

## META-001 — Asset Metadata Engine v1

Division01 remains semantic author. Deterministic engines may normalize and serialize but may not invent keywords or commercial intent.

Canonical metadata output includes:

- title;
- description;
- ranked primary/secondary keywords;
- categories where applicable;
- AI disclosure;
- Blueprint/candidate/artifact lineage.

Delivery uses two channels:

1. embedded IPTC/XMP where format/platform handling supports it;
2. canonical sidecar metadata retained for submission adapters in all cases.

Because injection changes file bytes, final artifact hashing and QA occur after the final metadata transformation/read-back.

## RIGHTS-001 — Rights/IP Preflight Engine v1

This engine produces risk evidence; it does not provide legal advice or legal clearance.

Explicit classes include:

- brand/logo/trademark;
- copyrighted character/artwork;
- recognizable trade dress/product design risk;
- likeness/publicity risk;
- property/release-sensitive content;
- watermark/attribution conflict;
- uncertain or missing rights evidence.

Uncertain evidence maps to existing `RIGHTS_UNCLEAR` HARD_VETO. Confirmed failure maps to `RIGHTS_FAILED`. QA cannot waive either state, and upscale/remetadata cannot route around them.

## Canary dependency change

`OE-007F` now depends on `WRK-001`, because the governed Worker execution lane must have an accepted model-backed Worker contract before the canary production job.

`OE-007G` now depends on `UP-001 + META-001 + RIGHTS-001 + QA-001 + QC-001`, because QA/QC must evaluate the final post-processed delivery artifact and its rights evidence, not an earlier pre-transform byte stream.

## Execution order

The four lanes may be built in parallel while MX-062 completes because they use isolated Git worktrees and do not require `/srv/die` mutation.

Recommended first implementation order:

1. WRK-001A/B/C/D -> WRK-001;
2. UP-001A/B/C/D -> UP-001;
3. META-001A/B/C/D/E -> META-001;
4. RIGHTS-001A/B/C/D/E -> RIGHTS-001;
5. convergence at OE-007F/G after MX-070 and the existing governed canary dependencies are satisfied.
