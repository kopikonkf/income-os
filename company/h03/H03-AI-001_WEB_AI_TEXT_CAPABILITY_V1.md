# H03-AI-001 - web-ai-adapter Text Capability Contract v1

Status: DONE / PASS
Date: 2026-09-09
Reference web-ai-adapter canon: `a654f823ce1027951c0204a7b141120ab8607faf`

H03 consumes the existing OpenAI-compatible text bridge at `POST /v1/chat/completions`. H03 does not import provider adapters, browser profiles, cookies, OAuth/session tokens, CDP ports or provider-specific wire protocols into product truth.

Two semantic roles are normalized:

- `CURATOR`: compare, critique, classify, select and propose.
- `PRODUCER`: generate bounded semantic draft output.

Both roles produce `truth_status=UNVERIFIED_MODEL_OUTPUT`, `canonical_truth=false`, and `session_material_persisted=false`. Model output must pass Knowledge Factory evidence/provenance gates before it can participate in accepted knowledge.

Provider/model routing is a runtime hint (`model_route`) passed through the web-ai-adapter facade. Rate-limit fallback, provider auth and provider transport remain web-ai-adapter responsibilities. The H03 client contains no provider credential handling.

The contract recursively rejects credential/session-shaped fields such as cookies, tokens, OAuth material, browser profile paths and credentials.

Machine contracts: `web-ai-text-capability.v1.schema.json` (request) and `web-ai-text-capability-response.v1.schema.json` (normalized response).
