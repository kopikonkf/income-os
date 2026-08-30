# Hermes Operator v2 Foundation — OE-B11

Status: `OE-006A/B/C = DONE`; `OE-006D = READY`; live Operator v1 integration intentionally deferred.

## 1. Purpose

Operator v2 replaces implicit Kanban cognition with deterministic typed prerequisite state. Hermes remains the anti-macet orchestrator: it observes which receipt is missing, routes the correct principal/engine, and never substitutes its own reasoning for Division01, Executive, deterministic engines, or Founder authority.

## 2. Typed intelligence prerequisite chain

The canonical ordered chain is:

```text
OPPORTUNITY_SIGNALS
  -> DEMAND_SCORE
  -> WORTH_MAKING_AUTHOR          (Division01)
  -> WORTH_MAKING_EXEC_REVIEW     (Executive)
  -> BLUEPRINT_AUTHOR             (Division01)
  -> BLUEPRINT_EXEC_REVIEW        (Executive)
  -> BLUEPRINT_COMPILE_HASH_LOCK  (deterministic compiler)
  -> FOUNDER_PRODUCTION_AUTHORIZATION
```

Every observed receipt pins artifact ID/SHA, issuer kind/ID, artifact schema, source reference, validation proof receipt and stage-specific claims. Freshness-sensitive receipts become incomplete when stale. `SUPERSEDED` history never competes with the current active receipt. Conflicting current receipts fail closed.

Founder authorization is valid only when `authorized_compiled_blueprint_sha256` exactly equals the compiled hash exposed by the current Blueprint hash-lock receipt and the decision is committed by `die-state-manager`.

Kanban is workflow metadata only. `kanban.status=done` cannot satisfy any cognition or authority prerequisite.

## 3. Deterministic action authority map

`ACTION_AUTHORITY_MAP_V1.json` is default-deny. Authority classification comes only from the canonical map, never from runtime-model output.

Key v2 routes:

- missing Signals -> `OP-CREATE-RESEARCH-CARD`;
- missing Demand Score -> `OP-DISPATCH-DEMAND-SCORE`;
- missing Division Worth-Making -> `OP-REQUEST-DIVISION01-WORTH-MAKING`;
- missing Executive Worth-Making review -> `OP-REQUEST-EXECUTIVE-WORTH-MAKING-REVIEW`;
- missing Division Blueprint -> `OP-REQUEST-DIVISION01-BLUEPRINT`;
- missing Executive Blueprint review -> `OP-REQUEST-EXECUTIVE-BLUEPRINT-REVIEW`;
- missing compile/hash-lock -> `OP-CREATE-BLUEPRINT-COMPILE-CARD`;
- missing Founder authorization -> `OP-DRAFT-U1-REQUEST`;
- all typed prerequisites valid -> conditional `OP-INVOKE-M001-RUNNER`.

Founder actions remain `FOUNDER_REQUIRED`; forbidden action IDs remain forbidden even if a runtime model or another principal asks for them. Capability is not authority.

## 4. Intelligence-stage projection

`project_intelligence_stage.py` deterministically emits:

- `intelligence_stage`;
- `next_required_receipt`;
- `next_action_type`;
- `required_principal`;
- canonical `action_authority`;
- active/missing receipt types;
- chain-gap diagnostics;
- `production_authorized` and `can_invoke_production_runner`.

The earliest missing prerequisite always wins. Later receipts cannot skip a gap. Invalid issuer/hash/authorization relationships project `BLOCKED_INVALID_RECEIPTS` and `OP-BLOCK-CARD`.

`READY_FOR_PRODUCTION` exists only after the exact Founder production-authorization receipt is present and correctly bound to the current compiled Blueprint hash.

## 5. Scope boundary

OE-B11 does not modify `bin/die_operator_tick.py`, the Windows profile-local Hermes cron wrapper, Hermes Kanban, or any production/runtime service. Live integration, legacy-card quarantine, OS-neutral prepare entrypoint, routing/follow-up, and replay/crash acceptance remain OE-006D/E/F/G.