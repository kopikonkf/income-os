# H03-RT-002 — Provider Worker Registry + Role Routing v1

Status: DONE / PASS
Date: 2026-09-09

Static provider capabilities are separate from dynamic runtime health/capacity. Qwen 3.8 Max and Gemini are first-class curator/researcher/producer candidates; Manus is an autonomous-research candidate; ChatGPT/Claude/Grok remain pluggable. Router selection requires role eligibility, required semantic capabilities, `READY` runtime state, and positive available slots. An unavailable Qwen slot can fall through to Gemini or another eligible worker without changing the Work Card.

No cookies/tokens/credential material belongs in the registry. Runtime may expose only sanitized profile shard identity.

Artifacts: `company/h03/runtime/provider-worker-registry.v1.json`, `company/h03/contracts/provider-worker-registry.v1.schema.json`, and `company/h03/lib/worker_router.py`.
