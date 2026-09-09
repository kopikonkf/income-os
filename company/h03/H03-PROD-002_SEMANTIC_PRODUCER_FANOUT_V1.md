# H03-PROD-002 — Role-Separated Semantic Producer Fan-Out v1

Status: DONE / PASS
Date: 2026-09-09

## Purpose

Each Product Blueprint section becomes one bounded `PRODUCER` Work Card. Producer jobs are routed through the existing provider registry/profile-pool machinery and can fan out across Qwen, Gemini, Claude, ChatGPT or other eligible healthy slots.

```text
Product Blueprint
  section 1 -> PRODUCER job -> content-block batch 1
  section 2 -> PRODUCER job -> content-block batch 2
  section N -> PRODUCER job -> content-block batch N
```

Standard producer workers require web-AI cognition only. MCP, shell and local-filesystem access remain false.

## Provenance boundary

The model receives only assigned claim IDs and claim text. It does not receive evidence refs as a writable output responsibility. Returned blocks may cite only claim IDs from the assigned section; cross-section claims fail closed.

After model output returns, H03 deterministically attaches evidence refs from the accepted Knowledge Package. The producer therefore owns wording/semantic structure but never source provenance.

Supported semantic block kinds:

- `PARAGRAPH`
- `STEP`
- `BULLET`
- `CHECKLIST_ITEM`
- `CALLOUT`
- `INPUT_PROMPT`

Normalized batches carry `truth_status=DERIVED_SEMANTIC_CONTENT` and retain provider/model/profile/transport observations without credential/session material.

## Fan-out acceptance

A two-section test with one Qwen slot and one Gemini slot dispatches section 1 to Qwen and section 2 to Gemini. Slot consumption prevents a nominally high-priority provider from being over-selected beyond observed capacity.

No live provider call is claimed by this engineering acceptance; live organism dispatch belongs to the internal end-to-end canary frontier.

Artifacts:

- `company/h03/contracts/content-block-batch.v1.schema.json`
- `company/h03/lib/semantic_producer.py`
- `company/h03/tests/test_semantic_producer.py`
