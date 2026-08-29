# Division01 Worth-Making AUTHOR Contract v1

Principal: `division-head-division01`
Role: `AUTHOR`
Schema: `die.division001.worth-making.v1`

## Authority

Division01 is the sole semantic AUTHOR for division-scoped Worth-Making. The author artifact may interpret evidence, state buyer/JTBD and commercial-use hypotheses, assess competition and differentiation, recommend Product Expression, score the nine canon factors, define cheapest falsification, state assumptions, and recommend `VALIDATE`, `RESEARCH`, or `DEFER`.

Hermes, Worker/OpenCode, Executive, deterministic validators, and compilers MUST NOT fill in missing Worth-Making semantics on behalf of Division01.

## Required upstream gate

Authoring requires a pinned deterministic precheck receipt with:

- `status=PASS`;
- `hard_veto=CLEAR`;
- matching Longtail candidate hash;
- matching OE-002 Demand Score ID/hash;
- fresh mandatory demand/supply/commercial-intent evidence;
- clear rights/IP, safety/deception, platform-expression eligibility, production-tool-rights, and spend gates;
- a structured upstream Human Atlas buyer/use-case hypothesis seed.

The hypothesis seed is input context only. Division01 must author the actual buyer/JTBD interpretation; no deterministic worker may copy the seed and claim cognition is complete.

## Factor model

The factor weights are pinned in `WORTH_MAKING_FACTOR_MODEL_V1.json`:

- Demand evidence 20;
- Commercial intent 15;
- Buyer utility 15;
- Competition gap 10;
- Differentiation 10;
- Production feasibility 10;
- Eligible-platform fit 10;
- Repurposing potential 5;
- Speed to cheapest falsification 5.

Every numeric factor requires evidence references and a non-`UNKNOWN` evidence label. `UNKNOWN` means score `null`; it is never imputed to zero. If any factor is unknown, total score must remain `null` and `VALIDATE` is forbidden.

When all factors are known, total score is deterministic weighted arithmetic. `VALIDATE` requires >=75. `RESEARCH` requires >=60 when a numeric total exists. Below 60 requires `DEFER`. Division01 may always choose a more conservative recommendation.

## Sovereignty boundary

`VALIDATE` means candidate for bounded validation **after downstream Executive review and Founder gate**. It does not grant production, spend, account action, submission, or publication authority. `production_authority_granted` is structurally fixed to `false`.

## Runtime Decision handoff

When the Division01 Runtime Decision line is available, the principal must emit the standalone schema-valid artifact with its own principal ID and fresh repository/snapshot provenance. The transport/session is not authority; the typed artifact is.