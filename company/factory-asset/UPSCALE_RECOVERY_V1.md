# Conditional Upscale / Recovery Adapter v1

Task: `FA-135`
Status: PASS
Date: 2026-09-04

The adapter separates a deterministic decision from execution. If the validated master already satisfies route dimensions and has no recoverable technical defect, the result is `NOOP_SUFFICIENT`; the immutable source master is reused byte-for-byte. Dimension shortfall yields `UPSCALE_REQUIRED`; classified technical softness/compression defects may yield `RECOVERY_REQUIRED`. Rights/safety/lineage/integrity uncertainty and unclassified defects are never recoverable by upscale.

Execution writes only to a separate temporary output, validates dimensions/hash, atomically finalizes, and never overwrites the provider-original master. A sidecar receipt binds source hash, target dimensions and engine configuration for idempotent reuse. Engine failure deletes partial temp output.

Production engines are pluggable. Any `production_engine=true` adapter must pin `model_sha256`; the FA-135 acceptance uses `PILLOW_LANCZOS_REFERENCE` only as a deterministic local contract fixture. This task does **not** certify Linux RealESRGAN production runtime/model parity.