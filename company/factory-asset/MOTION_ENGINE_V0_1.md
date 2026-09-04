# Motion Engine v0.1 Acceptance

Task: `FA-043`
Status: PASS
Date: 2026-09-04

Motion Engine v0.1 consists of FA-040 contract, FA-041 real Remotion renderer, and FA-042 adversarial motion QA.

Accepted properties:
- semantic mode `ANIMATION`, native representation `TIMED_FRAMES`, `conversion_from_raster=false`;
- deterministic H.264 MP4 and PNG preview from the canonical composition;
- bounded runtime: max 3840x2160, 3600 frames, 60 seconds, 60 FPS, concurrency 1, 300s command timeout;
- typed pre-render cancellation with no partial final output;
- retry after injected failure: first attempt cleans fully, second attempt succeeds and reproduces the accepted master/preview SHA-256;
- atomic temp cleanup on success/failure;
- codec/container/pixel/FPS/exact-frame-count/exact-duration/audio checks;
- sampled visual integrity rejects mislabeled, truncated, blank and frozen renders;
- marketplace compatibility remains evidence-bounded and UNKNOWN profiles are never promoted.

The accepted engine is a local zero-spend production primitive. This acceptance does not assert production-scale Remotion licensing, marketplace upload authority, provider generation authority, credential access or publication authority.