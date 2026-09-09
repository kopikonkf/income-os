# H03-RT-006 — Mission Control ↔ H03 Batch Supervision Boundary v1

Status: DONE / PASS
Date: 2026-09-09

H03 reuses canonical Mission Protocol `mc-mission-v1`; it does not create a parallel orchestration authority.

References inspected read-only for this acceptance:

- Mission Control origin/main: `5557e3738cc11d82c53dfb68072b1f09a388e22a`
- Universal MCP origin/main: `07239a1ab00a9ad66f1e1b64c660c1f8e160d614`

Canonical methods reused:

```text
mission.task.get
mission.task.checkpoint
mission.task.complete
mission.task.block
mission.review.submit
mission.founder.request
```

H03 emits only batch/product-level intents for checkpoint, completion, block/escalation and Founder gates. Cognition microjobs remain owned by the H03 orchestrator and do not require Mission Protocol calls.

The supervision payload contains aggregate stage counts, product ids, microjob count, durable artifact refs, failure summary, and recovery summary. Worker prompts/messages, cookies, tokens, profile paths and Mission lease/review capabilities are forbidden from persisted H03 supervision state.

Mission lease capability is injected only at invocation time by the privileged principal/runtime. Recovery such as provider rate-limit → alternate-worker fallback is checkpointed as an aggregate recovery observation; Mission Control observes/recover-escalates the batch but does not execute each retry itself.

Artifacts:

- `company/h03/contracts/mission-batch-supervision.v1.schema.json`
- `company/h03/runtime/mission-control-boundary.v1.json`
- `company/h03/lib/supervision_boundary.py`
