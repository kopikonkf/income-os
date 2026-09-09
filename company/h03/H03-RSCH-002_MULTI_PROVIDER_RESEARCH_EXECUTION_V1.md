# H03-RSCH-002 — Parallel Multi-Provider Research Execution v1

Status: DONE / PASS
Date: 2026-09-09

The research executor converts a bounded Research Plan into routed web-AI Work Cards. Allocation consumes observed worker slots, so a three-job fan-out can distribute across Qwen, Gemini and Manus instead of repeatedly selecting one provider beyond its available capacity.

Worker-returned source text is ingested through KF-002 into hashed external-source snapshots with `PENDING_REVIEW`, `canonical_truth=false`, and rights `UNKNOWN`; the resulting research packet remains `UNVERIFIED_RESEARCH_PACKET`. Findings must resolve to source-derived evidence units.

Artifacts: `company/h03/contracts/research-packet.v1.schema.json` and `company/h03/lib/research_executor.py`.
