# H03-KF-003 — Research Synthesis Fan-In v1

Status: DONE / PASS
Date: 2026-09-09

Multiple `UNVERIFIED_RESEARCH_PACKET` artifacts can now be assigned to a `SYNTHESIZER` Work Card. The synthesis request exposes only packet findings, evidence refs, question identity and source identity; it does not depend on prior provider chat history.

The normalized output is split into two durable artifacts:

- `Knowledge Map` — supported findings, contradictions, unresolved gaps and market/WTP findings with `truth_status=UNVERIFIED_SYNTHESIS`.
- `Knowledge Package Candidate` — candidate product claims with resolved evidence refs, `canonical_truth=false`, and an explicit promotion state.

Every model-produced finding/claim must resolve to an evidence unit from the input research packets. Unknown evidence refs fail closed. Critical gaps and unresolved contradictions block promotion before source governance. Even when all source packets are governed, the candidate becomes only `ELIGIBLE_FOR_KNOWLEDGE_VALIDATION`; it does not become canonical truth automatically.

Promotion states:

```text
AWAITING_GAP_RESOLUTION
AWAITING_CONTRADICTION_RESOLUTION
AWAITING_SOURCE_GOVERNANCE
ELIGIBLE_FOR_KNOWLEDGE_VALIDATION
```

Artifacts:

- `company/h03/contracts/knowledge-map.v1.schema.json`
- `company/h03/contracts/knowledge-package-candidate.v1.schema.json`
- `company/h03/lib/knowledge_synthesis.py`
