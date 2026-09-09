# Factory Asset Scale Foundation Batch V1

This batch closes the pre-1K infrastructure foundation without authorizing 1,000 masters/day or any storage/network spend.

## FA-310 management ingress

The guest listens on SSH port 22 while the proven public management ingress is upstream NAT port 25013. Root login remains disabled and `kopiko` retains two independent management recovery paths: public-key authentication plus provider-password break-glass. Password recovery is intentionally preserved because the Founder has no independent provider/OOB console and Linux management must not depend on the Windows MCP bridge. Current bounded controls are `MaxAuthTries 6`, `LoginGraceTime 60`, and `MaxStartups 10:30:30`. Browser/broker CDP/control ports 39121, 39122, 39221, and 39222 remain loopback. Cloudflare linux-mcp exposes only the cognition/management origins backed by loopback 8891/8892; no browser/CDP port is tunneled.

## FA-311 persistent profile storage

Historical 2026-09-07 baselines were 341 MiB (A) and 349 MiB (B), with 656 MiB shared Chromium cost once. Current 2026-09-09 measured footprints are 1,069,231,786 bytes and 1,085,365,202 bytes. Conservative 100-profile inventory at the current maximum footprint plus one shared 656 MiB Chromium copy is 101.723 GiB. Planning envelopes are 100.641 GiB at 1 GiB/profile and 200.641 GiB at 2 GiB/profile. Current VPS free capacity is insufficient for 100 current-size profiles, so profile creation must be storage-budgeted.

Cache cleanup is allowlist-only. Authentication/session stores such as Accounts, Cookies/Login Data, Local Storage, Session Storage, Sessions, IndexedDB, Service Worker, WebStorage and related unknown paths are preserve-by-default. Tests prove synthetic cache cleanup leaves protected session-state sentinels intact.

## FA-312 active browser capacity

The VPS has 33,654,259,712 bytes RAM. Historical accepted two-cluster live peak is 5,048.15 MiB combined. Current attach-only idle measurement is 1,467.46 MiB A plus 1,492.80 MiB B. A 13-sample passive measurement during real FA-124 Qwen/Gemini/Manus generation observed a current combined peak of 4,798.97 MiB without adding provider calls. The capacity model reserves 8 GiB for system/recovery and one browser-owner recovery slot; this yields a raw RAM limit of 9 and a governed active-browser-owner ceiling of 8. Production remains at two owners today. Persistent profiles above the ceiling stay cold/parked until leased. This is a ceiling, not a throughput authorization.

## FA-313 Hermes multi-cluster routing

The legacy blueprint engine value `MUXIA/chatgpt-linux-a` is retained as a compatibility input and is not rewritten. Production handoff is no longer pinned to ChatGPT A: it becomes `AUTO / governed-multi-cluster`, routes through the FA-306 scheduler using live broker readiness/tab capacity, persistent cluster fairness and circuits, and executes the selected provider via the leased provider worker. Pre-dispatch reroute is bounded; a committed unresolved attempt fails closed and cannot be silently retried. Actual provider/cluster/provider-original SHA lineage is carried into postprocessing and Founder-QC parking remains unchanged.

## FA-314 hot/archive storage

Nineteen real postprocessed workspaces measure 33,052,549 bytes median, 50,045,853 bytes p95, and 61,297,900 bytes max. At 1,000 masters/day this corresponds to 30.783 GiB/day median, 46.609 GiB/day p95 and 57.088 GiB/day at the observed max. Thirty-day local retention would require about 0.902 TiB median to 1.673 TiB max, far beyond the current VPS free space.

The architecture therefore separates hot local production/QC state from immutable content-addressed archive. Provider originals, active masters and lineage/metadata/QA/rights receipts are archive-required. Marketplace derivatives, web previews and cognition intermediates are recreatable/evictable only after archive and policy gates. Restore must target a new workspace and verify SHA-256 before promotion. External object-storage provisioning or spend remains Founder-authorized separately.
