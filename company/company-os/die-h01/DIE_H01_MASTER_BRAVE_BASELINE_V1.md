# DIE H01 Master Brave Profile Baseline v1

Status: **READY FOR FOUNDER ACCEPTANCE**
Task: `H01-022`
Date: 2026-09-12

## Scope

H01-022 accepts one master Brave profile under real Web-AI use before any broad profile rollout. The Founder already supplied manual authentication for `h01-web-p001`; Architect evidence must not read or export cookie, token, credential or session bytes.

The accepted baseline candidate is:

- profile: `h01-web-p001`
- UDD: `h01-web-s01`
- CDP: `127.0.0.1:9201`
- launcher: `/opt/die/h01/bin/h01-brave-profile`
- authentication policy: Founder-provided, persistent, incremental/on-demand

## Acceptance evidence

### Persistence and restart

A fresh post-H01-107 launch on 2026-09-12 reopened ChatGPT with document state `complete`, a usable composer and no visible login/sign-in prompt. No cookie, token or session bytes were read. The H01-025 lifecycle closed the browser after a durable telemetry receipt and verified process exit, CDP close and UDD lock release.

H01-107 independently exercised the same p001 profile repeatedly across Claude, ChatGPT, Qwen, Gemini, Grok, Manus, Copilot and Duck.ai, demonstrating that the Founder-provided authenticated browser state survives real provider switching and restart cycles.

### Loopback CDP and page cardinality

The live baseline exposed CDP only on `127.0.0.1:9201`, with exactly one committed ChatGPT page after H01-025 enforcement.

### Output acquisition and provider completion

H01-107 is the real Web-AI output proof used by H01-022:

- Claude, ChatGPT, Qwen, Manus and Copilot: valid `TEXT_SVG` provider output acquired and H01-103 validated.
- Gemini: provider-native `Download SVG` file acquired and H01-103 validated.
- Qwen: slow/late provider completion was recovered by reopening the exact persisted conversation rather than falsely classifying capability failure.
- Grok and Duck.ai prove honest bounded non-success handling (`UNSUPPORTED` and `DEFERRED`) rather than synthetic PASS.

### Live RAM / renderer / disk telemetry

Fresh p001 telemetry while ChatGPT was open:

- Brave process count: 13
- aggregate Brave RSS: 1,262,516 KiB (~1,232.93 MiB)
- renderer processes: 3
- GPU processes: 2
- utility processes: 3
- p001 bytes: 66,876,367
- s01 UDD bytes: 204,035,628
- filesystem available: 82,488,520,704 bytes (~76.82 GiB)
- filesystem used: 35%

H01-024 additionally measured populated-profile growth and accepted the storage/janitor capacity gate. Its cache-only janitor reclaimed approximately 258.4 MB from closed p001 while authentication/session stores remained protected.

## Founder boundary

Architect evidence is complete. This document does **not** self-authorize H01-022 DONE. The task remains `FOUNDER_REQUIRED` until the Founder accepts this baseline. No pre-authentication of all 100 profiles is requested or implied.
