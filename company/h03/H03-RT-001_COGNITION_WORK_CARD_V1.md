# H03-RT-001 — Cognition Work Card + Durable Handoff v1

Status: DONE / PASS
Date: 2026-09-09

A standard web-AI cognition worker receives a role Work Card plus durable input artifact refs and returns a typed terminal result plus durable output artifact refs. MCP, shell and local-filesystem access are `false` in the standard capability profile; they remain optional future grants. Continuity is independent of a specific provider conversation.

Logical roles include seed curator, market/knowledge researcher, synthesizer, product architect, producer, reviewer and growth producer. The existing normalized web-AI capability is extended backward-compatibly to accept these roles.

Contracts: `cognition-work-card.v1.schema.json` and `cognition-worker-result.v1.schema.json`. Validator: `company/h03/lib/cognition_work_card.py`.
