# DIE Linux Safe Wake Transport v1

Date: 2026-08-31
Status: IMPLEMENTATION ? bounded actuator foundation
Scope: `WAKE-LNX-001`

## Decision

Linux wake MUST NOT port the Windows private ChatGPT `backend-api`, Web JWT, Sentinel/PoW, or undocumented request flow. Current MCP `2026-07-28` is request/response oriented and does not provide an unsolicited server-to-ChatGPT cognition trigger. Therefore WAKE-LNX-001 separates a supported-safe actuator foundation from autonomous model submission.

The safe actuator may attach only to an already authenticated principal-dedicated Chrome through loopback dynamic CDP; bind exactly one active ChatGPT continuity thread per principal; bring that thread to the foreground; validate and stage a bounded wake briefing into the visible composer; and write a sanitized hash/metadata receipt.

It MUST NOT read/export cookies, localStorage, sessionStorage, OAuth tokens, Web JWTs, headers, or browser credential material; call `/backend-api/*`, `/api/auth/session`, Sentinel, proof-of-work, or other private ChatGPT endpoints; press Send, synthesize Enter, or otherwise submit a prompt automatically; scrape or extract model output; or expose wake as an inbound Runtime MCP authority tool.

`stage` intentionally leaves the prompt unsent. `canary` fills a synthetic marker, verifies the exact value and clears it without submission. A future supported provider actuator or separately Founder-ratified UI-submission policy is required before autonomous cognition delivery can be claimed.

## Thread invariant

Each Linux principal has one protected state file with `die.wake.thread.v2`: `principal_id -> exactly_one_active_thread`. Rotation increments `generation`; the previous conversation is retained only as bounded `superseded` metadata. Thread IDs are sensitive operational metadata, not credentials and not Company Truth.

All CDP listeners remain `127.0.0.1` only.
