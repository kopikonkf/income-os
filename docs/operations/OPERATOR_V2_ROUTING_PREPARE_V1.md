# OPERATOR V2 ROUTING / PREPARE V1

Date: 2026-08-30
Batch: OE-B12
Tasks: OE-006D / OE-006E / OE-006F

## Locked behavior

Operator v2 is receipt-driven. Kanban remains workflow metadata only and cannot create cognition authority. The only source of intelligence-stage progress is the typed prerequisite receipt chain defined by `INTELLIGENCE_PREREQUISITE_REGISTRY_V1.json`.

## OE-006D — legacy Kanban cognition quarantine

`LEGACY_KANBAN_QUARANTINE_RULE_V1.json` explicitly quarantines historical `T1`, `T2`, and `T2-R2`. A `done` status never creates, upgrades, or substitutes a typed prerequisite receipt. A legacy card may optionally declare backing receipt types for historical corroboration, but the card's `cognition_effect` remains `NONE`; stage projection continues to be computed only from validated typed receipts. Silent grandfathering is forbidden.

## OE-006E — canonical OS-neutral prepare entrypoint

Canonical entrypoint: `bin/die_operator_prepare.py`.

Modes:

- `v1-compat` (default): preserves the current PROPOSE_ONLY tick behavior by delegating to canonical `die_operator_tick.py prepare`.
- `v2`: invokes `company/die-agents/hermes/operator-v2/prepare_operator_v2.py`.

The v2 prepare path uses the existing DIE path-root abstraction (`resolve_die_path_roots`) and therefore supports Windows/Linux roots through `DIE_HOME`, `DIE_STATE_ROOT`, `MUXIA_ROOT`, `DIE_CONFIG_ROOT`, and `DIE_INSTALL_ROOT` rather than encoding a machine drive. Default v2 state lives below `<DIE_STATE_ROOT>/state/operator-v2/`; explicit fixture/snapshot paths may be supplied for deterministic tests.

The canonical profile delegate template `hermes_profile_prepare_wrapper.py` contains no `C:\DIE` or `/srv/die` literal. It resolves `DIE_HOME`, or falls back to the cron job workdir, and delegates to `bin/die_operator_prepare.py`. Linux activation can call the canonical entrypoint directly and does not depend on mutable Windows profile glue.

For safety OE-B12 does not mutate protected live `C:\DIE` or replace the currently scheduled Windows profile wrapper in-place; Windows control-host deployment remains a separate activation operation once canonical source is present at the selected live root.

## OE-006F — anti-macet routing and follow-up

`route_followup.py` is deterministic and default-deny through `validate_action_authority.py`.

Routing rules:

1. Project earliest missing typed receipt.
2. Route exactly the action/principal mapped by the projection.
3. Compute a stable dedupe key from mission + subject + stage + missing receipt + requested action.
4. New intent -> `DISPATCH`.
5. Same OPEN intent before 30 minutes -> `NO_OP_DUPLICATE` / read-only observation.
6. Same OPEN intent after 30 minutes -> `FOLLOW_UP` through `OP-FOLLOW-UP-CARD`.
7. After 3 dispatched follow-ups without progress -> `BLOCK_STALLED` through `OP-BLOCK-CARD`.
8. A Founder production-authorization draft is due only at `AUTHORIZATION`, after `BLUEPRINT_COMPILE_HASH_LOCK` is active.
9. Production runner invocation is due only at `READY_FOR_PRODUCTION`, after exact Founder authorization is active.
10. Hermes never authors buyer thesis, Worth-Making semantics, Blueprint semantics, prompt content, or production authority.

Routing state is explicit (`die.operator-v2.routing-state.v1`). Planning is pure; state is advanced only by a separate recorded outcome (`DISPATCHED`, `COMPLETED`, `FAILED`, `BLOCKED`). This prevents a prepare invocation from falsely marking work as dispatched.

## Boundaries

- no live Kanban mutation in OE-B12 implementation;
- no live semantic principal invocation;
- no network request;
- no credential read/copy;
- no production provider call;
- no production authority widening;
- no spend.

OE-006G remains responsible for replay/restart/crash and duplicate-work regression before the OE-006 umbrella acceptance may become DONE.