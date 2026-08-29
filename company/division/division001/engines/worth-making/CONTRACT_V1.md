# Division01 Worth-Making Gate v1 — OE-B07 Contracts

Status: CONTRACT FOUNDATION COMPLETE
Batch: OE-B07
Milestone: OE-004 remains pending OE-B08

## 1. Separation of concerns

Worth-Making is hybrid:

```text
Deterministic precheck / hard veto
        ↓
Division01 semantic AUTHOR
        ↓
Executive read-only REVIEW
        ↓
OE-B08 revision/freshness/failure loop
```

The first stage validates prerequisites and vetoes only. It never authors buyer/JTBD, commercial thesis, differentiation, Product Expression judgment, factor scores, or recommendation.

## 2. OE-004A — deterministic precheck

`precheck_worth_making.py` consumes the full Longtail child candidate and OE-002 Demand Score plus explicit hard-gate evidence.

It verifies:

- candidate schema;
- exact Longtail guard candidate ID/hash binding;
- OE-002 schema **and semantic arithmetic/model validation**;
- exact score/candidate lineage;
- score freshness;
- fresh mandatory demand/supply/commercial-intent evidence;
- Longtail guard state;
- rights/IP/trademark gate;
- safety/deception gate;
- platform/Product Expression eligibility gate;
- production-tool commercial-rights gate;
- spend authorization semantics;
- presence of a structured, falsifiable Human Atlas buyer/use-case hypothesis seed.

Outputs are only `PASS`, `BLOCKED`, or `WAITING_EVIDENCE`. `worth_making_semantics_authored` is structurally `false`.

A Human Atlas hypothesis seed is not the Division buyer thesis; it only proves a bounded hypothesis exists for cognition to evaluate.

## 3. OE-004B — Division01 AUTHOR

`die.division001.worth-making.v1` is owned by principal `division-head-division01` with role `AUTHOR`.

The artifact owns buyer/JTBD, commercial-use hypothesis, competition interpretation, differentiation thesis, feasibility, Product Expression recommendation, assumptions, cheapest falsification, factor judgments and final recommendation.

Canon nine-factor weights are pinned in `WORTH_MAKING_FACTOR_MODEL_V1.json` and sum to 100. `UNKNOWN` factor = `score:null`; unknown is never zero. Numeric factors require evidence references. If any factor is unknown, total score is null and `VALIDATE` is forbidden.

When complete, total score is deterministic weighted arithmetic. Aggressiveness ceilings are:

- `VALIDATE` requires >=75;
- `RESEARCH` requires >=60 when total is numeric;
- below 60 requires `DEFER`;
- a more conservative Division recommendation is always allowed.

The artifact cannot grant production authority.

## 4. OE-004C — Executive REVIEW

`die.executive.worth-making-review.v1` is owned by `chatgpt-plus-executive`, role `REVIEWER`, mode `READ_ONLY_CHALLENGE`.

It pins the exact hash of the Division artifact and must review exactly six domains:

1. evidence weakness/contradiction;
2. score inflation/double counting;
3. portfolio overlap/cannibalization;
4. strategic opportunity cost;
5. Product Expression fit;
6. assumptions that remain hypotheses.

Allowed outcomes:

- `NO_VETO` — no material concern or unknown;
- `REVISE` — concern + explicit actions, returned to Division01;
- `VETO_PENDING_EVIDENCE` — unknown evidence + explicit actions;
- `ESCALATE_FOUNDER` — explicit sovereignty/policy/material strategic reason.

Executive cannot edit the Division artifact in place and cannot grant production authority.

## 5. What OE-B07 does not yet complete

OE-004 is **not** accepted yet. OE-B08 must still implement:

- immutable Division01↔Executive revision/return lineage (`OE-004D`);
- cross-receipt principal/hash/freshness validator (`OE-004E`);
- governed canary and pass/revise/veto/stale/forged-review failure suite (`OE-004F`);
- final OE-004 milestone acceptance.

No live Division01 or Executive cognition session is claimed by OE-B07; this batch builds and tests the executable contracts that those principals must satisfy once authenticated runtime lines are used.