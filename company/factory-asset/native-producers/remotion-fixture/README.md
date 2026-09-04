# FA-041 Remotion Motion Producer Fixture

This directory is the first real renderer implementation behind the FA-040 motion contract. It is a bounded local acceptance fixture, not the production batch renderer.

## Pinned runtime

- Remotion / CLI / renderer / bundler: `4.0.520`
- React / React DOM: `19.2.8`
- `esbuild@0.28.1` is the only install-script package explicitly allowlisted in `package.json`.
- Remotion-managed Chrome Headless Shell is used; no global FFmpeg/FFprobe installation is required.

## Contract source

`src/composition-contract.json` must remain byte-semantically equal to the `shopping-bag-bounce-mp4` composition in `company/factory-asset/fixtures/motion-composition/fixture-plan.v1.json`. Tests fail if it drifts.

The accepted render is 1080x1080, 30 FPS, 180 frames / 6 seconds, MP4 H.264, `yuv420p`, and no audio stream. `ANIMATION`, `TIMED_FRAMES`, seed and renderer identity come from FA-040.

## Reproduce

```powershell
npm install --no-audit --no-fund
node render-worker.mjs --self-test-cleanup
node render-worker.mjs --output-dir D:\FACTORY_ASSET\canaries\FA-041\manual-run
```

The worker stages into a sibling `.fa041-tmp-*` directory and atomically renames the completed directory into place. The temporary directory is removed on failure. Existing final output directories are never overwritten.

## Scope

FA-041 performs a real local Remotion render and preview render. It does not perform provider calls, marketplace upload/publication, credential access, or production-scale automation. Codec/container/frame visual-integrity and compatibility hardening continues in FA-042. Production-scale Remotion licensing is not asserted by this fixture.