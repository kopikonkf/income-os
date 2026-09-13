# DIE H01 Marketplace Delivery Adapter v1

H01-134 is a deterministic local packaging layer after H01-105 vector postproduction. It does not replace the canonical SVG master and does not perform marketplace account actions.

## Truth layers

- `provider-original.svg`: immutable provider provenance.
- `canonical-master.svg`: canonical semantic truth.
- `optimized-master.svg`: optimized postproduction derivative.
- marketplace delivery package: marketplace-specific file selection or deterministic compatibility transform. It has `semantic_identity_effect=NONE` and never becomes canonical truth.

## Profiles

- Adobe: deterministic SVG delivery derived from optimized SVG, fallback canonical SVG. The adapter adds explicit ~16 MP width/height while preserving the original viewBox and geometry. Metadata and generative-AI disclosure remain sidecar/submission fields.
- Vecteezy: EPS plus local JPG preview. EPS must have a 4-25 MP BoundingBox. `ILLUSTRATOR_10_COMPATIBLE_TARGET` is a structural target only; `native_illustrator_save_certified=false` unless a future actual Illustrator finalizer proves otherwise.
- 123RF: same-basename EPS + JPG; JPG must be at least 1600x1600.
- Dreamstime: high-resolution JPG primary review file plus SVG additional vector, with EPS fallback.
- VectorStock: same-basename EPS + deterministic RGB JPG preview normalized to 1000-3000 px; deterministic ZIP contains EPS only.
- MotionElements: same-basename EPS + JPG; deterministic ZIP contains both.

## Eligibility gate

Local packages may be built before Founder QC. `submission_eligible=true` only when all three conditions are true:

1. marketplace compatibility = PASS;
2. rights signal = PASS;
3. Founder QC = PASS.

Otherwise the package remains local evidence only.

## Authority boundary

Every package and receipt must keep `login_action`, `upload_action`, `submission_action`, `publication_action`, and `spend_action` equal to `NONE`. The adapter reads no credentials and grants no publication authority.
