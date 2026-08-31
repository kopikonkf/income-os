# DIE Opportunity Intelligence Atomic Task Graph v1

Date: 2026-08-29
Status: EXECUTION CANON
Graph: `company/muxia-task-graph-v1.json`
Architecture: `docs/architecture/DIE_OPPORTUNITY_ENGINE_ARCHITECTURE_V1.md`
Audit: `docs/architecture/DIE_OPPORTUNITY_ENGINE_AUDIT_V1.md`

## 1. Purpose

This document seals the OE-001..OE-007 roadmap into executable atomic work. Architecture prose is not completion evidence. A milestone is complete only when its terminal atomic gate is complete and the milestone acceptance receipt exists.

## 2. Execution rules

- Build > Run > Verify > Refactor > Extend.
- STOP_ON_FIRST_FAILURE inside an atomic task.
- At most one minimal repair child `<task>-R1` unless a foundational assumption is falsified and Founder/Architect explicitly revises the graph.
- No atomic task may mark a downstream milestone DONE by documentation alone.
- A Kanban `done` card is workflow metadata, not intelligence-gate evidence.
- Exact typed receipts, principal IDs, source hashes and freshness rules govern Worth-Making/Blueprint progression.
- OE-001..OE-006 may be built while Windows remains authoritative and Linux migration stabilization continues.
- OE-007 is migration-gated and cannot start until `OE-006`, `DIE-204`, and `MX-070` are complete.
- `MX-071` now also depends on `OE-007`; the Chapter #4 cutover path cannot bypass the governed intelligence closed loop.

## 3. Milestone gates

| Milestone | Terminal atomic gate | Result required |
|---|---|---|
| OE-001 Opportunity Signals | OE-001G | normalized policy-bounded signals + failure suite |
| OE-002 Demand Score | OE-002F | evidence-backed deterministic ranking + regression |
| OE-003 Longtail | OE-003G | bounded Object+Human phrase generation + signal/ranking integration |
| OE-004 Worth-Making | OE-004F | Division01 AUTHOR + Executive review + failure paths |
| OE-005 Blueprint | OE-005F | Division01 authoring + Executive review + deterministic compile/hash |
| OE-006 Hermes Operator v2 | OE-006G | typed prerequisites + deterministic authority + replay/crash regression |
| OE-007 Full Governed Canary | OE-007G | complete signals-to-artifact/QA feedback lineage |

## 4. Authority gates

### Division01

Semantic AUTHOR for Worth-Making and Blueprint semantics, including buyer/JTBD, commercial thesis, Product Expression, master prompt, negative constraints and semantic variation plan.

### Executive

Second-line strategic reviewer. Review outcomes are `NO_VETO`, `REVISE`, `VETO_PENDING_EVIDENCE`, or `ESCALATE_FOUNDER`. Executive does not edit the Division artifact in place and does not command Workers.

### Hermes

Receipt-driven orchestrator/anti-macet only. Hermes detects the next missing prerequisite, routes work, follows stalls, validates lineage/freshness and drafts Founder gates. Hermes cannot originate Worth-Making or prompt semantics.

### Worker/OpenCode

Bounded collector/scorer/compiler/executor. Worker may serialize, validate, hash and execute authorized work, but must fail when required commercial/prompt semantics are missing.

### Founder

Sovereign exact-hash production/spend/account/submission authority.

## 5. Batch execution map

The graph remains atomic; these batches only reduce conversational overhead.

### OE-B01 — Signals contracts

- OE-001A signal taxonomy/source classes
- OE-001B receipt schema
- OE-001C acquisition/ToS boundary

Exit: contracts/schema fixtures pass; no external collection required yet.

### OE-B02 — Signals implementation

- OE-001D fixture adapter A
- OE-001E fixture adapter B
- OE-001F registry/dedupe/freshness
- OE-001G regression/failure suite
- OE-001 milestone acceptance

Exit: reusable normalized signal receipts exist.

### OE-B03 — Demand Score contracts

- OE-002A schema/model version
- OE-002B evidence normalization
- OE-002C UNKNOWN/freshness policy

### OE-B04 — Demand Score implementation

- OE-002D deterministic scorer
- OE-002E calibration fixtures
- OE-002F ranking/regression
- OE-002 acceptance

### OE-B05 — Longtail retrieval contracts

- OE-003A modifier ontology/phrase schema
- OE-003B Object Atlas retrieval
- OE-003C Human Atlas retrieval

### OE-B06 — Longtail engine

- OE-003D bounded expansion
- OE-003E dedupe/IP/redundancy guardrails
- OE-003F phrase signal/scoring loop
- OE-003G persistence/ranking tests
- OE-003 acceptance

### OE-B07 — Worth-Making author/review contracts

- OE-004A deterministic precheck/hard veto
- OE-004B Division01 author contract
- OE-004C Executive review contract

### OE-B08 — Worth-Making governed loop

- OE-004D revision/return loop
- OE-004E receipt validation/freshness
- OE-004F failure suite
- OE-004 acceptance

### OE-B09 — Blueprint cognition contracts

- OE-005A Division authoring schema
- OE-005B prompt/variation contract
- OE-005C Executive review contract

### OE-B10 — Blueprint compiler

- OE-005D deterministic compiler
- OE-005E provenance/hash lock
- OE-005F failure/determinism suite
- OE-005 acceptance

### OE-B11 — Operator v2 prerequisite/authority core

- OE-006A prerequisite registry
- OE-006B deterministic action authority map
- OE-006C intelligence-stage/next-required-receipt projection

### OE-B12 — Operator v2 integration

- OE-006D legacy Kanban cognition quarantine
- OE-006E OS-neutral prepare entrypoint
- OE-006F anti-macet routing/follow-up

### OE-B13 — Operator v2 acceptance

- OE-006G replay/crash/duplicate regression
- OE-006 acceptance

### Post-OE-B13 — Governed canary cognition chain

Starts only after `OE-006 + DIE-204 + MX-070`.

- OE-007A candidate/snapshot pin
- OE-007B signals-score-longtail chain
- OE-007C Worth-Making + Executive review
- OE-007D Blueprint + review + compile/hash

### OE-B14 — Governed canary execution/feedback

- OE-007E Founder exact-hash gate
- OE-007F Worker/MUXIA artifact execution
- OE-007G QA/feedback/lineage receipt
- OE-007 acceptance

Founder silence at OE-007E means BLOCKED, never implicit authorization.

## 6. Current standing point

`OE-000 = DONE` — graph/authority/batch seal.

`OE-001 = DONE` — Opportunity Signals evidence substrate accepted.

`OE-002 = DONE` — deterministic Demand Score v1 accepted.

`OE-003 = DONE` — bounded Object+Human Longtail engine accepted.

`OE-004 = DONE` — governed Worth-Making Gate v1 accepted.

`OE-005 = DONE` — deterministic governed Blueprint Engine v1 accepted.

`OE-006A/B/C = DONE` — Operator v2 typed prerequisite registry, deterministic action authority map and intelligence-stage projection are sealed.

`OE-006 = DONE` — Operator v2 typed prerequisites, authority map, cognition quarantine, OS-neutral preparation, anti-macet routing and crash-safe replay are accepted.

Parallel production-readiness has closed the reliability soak. `MX-060/MX-061/MX-062 = DONE`; the genuine Linux 24-hour MX-062 receipt passed with 99.7918% coverage, valid hash chain and zero failure counters. `MX-070 = READY`; `QA-001 = DONE` and `QC-001 = DONE`. `OE-007A` remains blocked until MX-070 is completed.

## 7. Migration integration

The engine build and migration stabilization intentionally converge late:

```text
OE-001 -> OE-002 -> OE-003 -> OE-004 -> OE-005 -> OE-006
                                                     |
DIE-200/201/202/203 -> DIE-204 ---------------------+
                                                     |
MX-060 -> MX-061 -> MX-062 -> MX-070 ---------------+
                                                     v
                                                  OE-007
                                                     |
                                                     v
                                                  MX-071
                                                     |
                                                     v
                                              cutover evidence
```

This permits productive intelligence-engine work during the one-month Windows overlap while preventing final Linux cutover before the closed-loop operating model is proven.

## 8. Production-assurance and market-loop continuation

After OE-005, first-class QA/QC and submission/distribution work continues under docs/architecture/DIE_PRODUCTION_ASSURANCE_DISTRIBUTION_TASK_GRAPH_V1.md. OE-007 is the governed production canary; CL-001 is the full marketplace submission/review feedback closed loop.
