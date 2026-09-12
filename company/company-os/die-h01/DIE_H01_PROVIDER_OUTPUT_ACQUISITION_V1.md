# DIE H01 Provider Output Acquisition v1

Status: H01-104A IMPLEMENTED / ACCEPTANCE CANDIDATE
Date: 2026-09-12

## Purpose

H01-104A closes the gap between a provider reaching a stable terminal response and H01-104 receiving a normalized native-SVG candidate. The core is provider-independent and deterministic. It does not log in, dispatch prompts, own browser lifecycle, inspect cookies/tokens/session databases, or select providers.

```text
H01-025 Brave/CDP runtime + provider completion detector
        -> sanitized final provider payload
        -> H01-104A output acquisition core
        -> immutable provider-original.svg + acquisition receipt
        -> H01-103 validation
        -> H01-104 terminal native-SVG receipt
        -> H01-105 postproduction
```

Live provider/CDP canaries remain H01-107. This task can therefore be implemented and accepted without bypassing the still-gated H01-025 runtime dependency.

## SVG-first acquisition contract

For the initial SVG factory, the universal provider output is text. A provider does not need filesystem tools or a download button. The acquisition core accepts the final assistant response captured by the runtime, extracts exactly one complete `<svg>...</svg>` payload, writes the exact UTF-8 bytes as immutable `provider-original.svg`, and records hashes and normalized metadata.

Accepted presentation forms include raw SVG, one fenced SVG/XML code block, or one SVG embedded in surrounding provider prose. Multiple SVG roots are ambiguous and fail closed. No candidate is synthesized, repaired, traced or converted from raster during acquisition.

H01-104A performs a cheap intake guard against script, `foreignObject`, embedded `<image>`, `<text>` and `<style>`, requires finite-size intent through `viewBox` or width+height, and caps extracted bytes at 1 MiB. H01-103 remains authoritative for full safety/editability/geometry/render validation.

## Immutability and idempotency

The first accepted payload is written as `provider-original.svg`. Repeating the same bytes is `UNCHANGED`; attempting to overwrite the path with different bytes fails `ARTIFACT_CONFLICT`. The acquisition receipt contains both the raw provider-response SHA-256 and extracted payload SHA-256, so Markdown/prose stripping never destroys provider lineage.

The H01-104 success helper now optionally accepts `candidate_svg_text`. When supplied, the candidate must occur in the raw provider response. This preserves the original response hash while allowing H01-104 to use the extracted candidate hash.

## Safety boundary

The acquisition receipt mechanically records:

- `cookies_read=false`
- `tokens_read=false`
- `session_bytes_read=false`
- `browser_profile_copied=false`

H01-104A has no provider-call, browser-start/stop, scheduling, submission, publication or route-promotion authority. Authentication remains Founder-owned and host-local.

## Failure behavior

Fail closed on empty output, no complete SVG, multiple SVG candidates, missing size intent, forbidden SVG features, oversized SVG, schema mismatch, immutable artifact conflict, or a candidate not present in the raw provider response.

## Files

- implementation: `engineering/provider_output_acquisition.py`
- schema: `contracts/h01-provider-output-acquisition-v1.schema.json`
- fixtures: `fixtures/h01-104a/provider-output-cases.json`
- tests: `bridge/tests/test_h01_provider_output_acquisition_v1.py`
- runtime descriptor: `runtime/h01-provider-output-acquisition.v1.json`
