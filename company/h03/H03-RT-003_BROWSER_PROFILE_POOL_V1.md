# H03-RT-003 — Persistent Browser Profile Worker Pool + Shard Contract v1

Status: DONE / PASS
Date: 2026-09-09

Persistent browser profiles are modeled as runtime shards, not semantic roles. A single initial shard can expose multiple authenticated providers. Sanitized runtime state contains only shard id, provider id, transport, health and available slots; profile paths, cookies, tokens and session bytes are forbidden. Alternate shards can be added when observed failure/capacity requires them.

The pool can route a job through the existing RT-002 provider registry. If shard A/Qwen is unavailable and shard B/Gemini is healthy, the same role request continues through Gemini without changing durable work.

Artifacts: `company/h03/contracts/browser-profile-pool.v1.schema.json` and `company/h03/lib/profile_pool.py`.
