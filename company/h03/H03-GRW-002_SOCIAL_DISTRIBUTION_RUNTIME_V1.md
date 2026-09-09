# H03-GRW-002 — Social Distribution Runtime + Separate Growth Profile Pool v1

Status: DONE / PASS
Date: 2026-09-09

Growth uses a dedicated `GROWTH_WORKFORCE` browser-profile pool, not the Knowledge workforce pool. Initial transport is `BROWSER_CDP`; future adapter families are pluggable official APIs or social-manager integrations. No credential, cookie, session bytes, user-data path or profile path are persisted.

Current real account state is intentionally unprovisioned: all 9 social intents are `WAITING_ACCOUNT_PREFLIGHT`, with zero slots. A synthetic READY slot can only progress to `READY_FOR_FOUNDER_GATE`; publication remains false.

Canonical acquisition surfaces: X, Threads, Instagram, Facebook Page, Facebook Group, TikTok, YouTube, Pinterest, Reddit.

Direct destination architecture also records that a custom domain is not required to start. Hosted checkout/link routes and Lynk.id can operate first; custom domain is recommended later for brand control, first-party analytics, SEO, portability and checkout routing. Global English is primary; Indonesia QRIS is secondary; multilingual expansion is deferred.
