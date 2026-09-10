# H03-RT-007 — Dedicated Browser Workforce v1

Status: DONE / PASS
Date: 2026-09-10

H03 now owns three dedicated persistent browser identities: `H03-KNOWLEDGE-A`, `H03-REVIEW-A`, and `H03-GROWTH-A`. They are logical H03 resources, not Mission Control principal-primary resources. Browser processes and provider tabs are ephemeral; authenticated session state remains host-local in dedicated profile storage.

The required lifecycle is `COLD -> WAKE_HEADFUL -> OPEN_ASSIGNED_PROVIDER -> BUSY -> DURABLE_HANDOFF -> CLOSE_PROVIDER -> SLEEP_WHEN_QUEUE_EMPTY`. Headless launch is forbidden.

Controlled restart acceptance proved session persistence for seven Knowledge providers (Qwen, Gemini, Manus, Claude, ChatGPT, Grok, Copilot), two independent Review providers (Claude, ChatGPT), and the ready Growth surfaces Facebook, Instagram, Threads, Pinterest and X. YouTube remains `AUTH_REQUIRED`; Reddit is `UNKNOWN`; TikTok has a Founder-reported India-IP regional constraint.

No browser profile path, CDP port, cookie, token, credential value or session byte is canonical H03 product truth. Those bindings remain host-local Mission Control runtime configuration. Commerce remains a separate not-yet-provisioned profile.
