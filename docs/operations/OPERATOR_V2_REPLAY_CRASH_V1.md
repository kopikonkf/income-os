# OPERATOR V2 REPLAY / CRASH V1

Date: 2026-08-30
Batch: OE-B13
Tasks: OE-006G / OE-006 acceptance

## Accepted recovery protocol

Operator v2 uses `dispatch-journal.json` as the durable authority for routing
recovery. `routing-state.json` is only a replaceable projection.

Every claim follows this order:

1. Validate the typed receipt snapshot and project the intelligence stage.
2. Validate and replay the hash-chained dispatch journal.
3. Recompute the exact deterministic routing plan.
4. Atomically persist a `DISPATCH_CLAIM` before any external side effect.
5. Only after that durable claim may a dispatcher perform the bounded action.
6. Rebuild `routing-state.json` from the journal after restart or state loss.

Planning remains pure. A crash after planning but before the claim has no
durable dispatch and no permitted side effect. A crash after the journal claim
but before the state projection is safe: replay restores the OPEN/BLOCKED
intent and suppresses a duplicate dispatch.

## Evidence and cognition binding

Each journal entry pins:

- exact full snapshot SHA-256 for audit;
- cognition receipt-chain SHA-256, excluding observation time and mutable
  Kanban metadata;
- deterministic routing-plan SHA-256;
- mission, subject, stage, action, principal target, decision and follow-up
  counter;
- previous-entry SHA-256 and its own entry SHA-256.

Only the currently validated typed receipt chain may restore an active intent.
Journal history cannot create a missing receipt, repair a stale receipt, change
a principal, grant Founder authority, or preserve `READY_FOR_PRODUCTION` after
authorization becomes invalid. Legacy T1/T2/T2-R2 changes are deliberately
excluded from the cognition fingerprint and therefore remain metadata-only.

## Deterministic outcomes

- first eligible action: `DISPATCH`;
- same OPEN claim before 30 minutes: `NO_OP_DUPLICATE`;
- same OPEN claim after 30 minutes: `FOLLOW_UP`;
- after three recorded follow-ups: `BLOCK_STALLED`;
- replay of a completed or blocked intent: `NO_OP_TERMINAL`;
- invalid receipt registry or invalid/tampered journal: fail closed;
- a lost or stale routing-state projection: rebuilt from the journal.

## Authority boundaries

- Hermes authors no market/Worth-Making/Blueprint/prompt semantics;
- runtime-model capability never substitutes for authority;
- production requires a current, exact Founder authorization receipt bound to
  the compiled Blueprint hash;
- no live Kanban, cognition principal, provider, submission, account, service,
  cron or credential is touched by OE-B13;
- no spend and no production authority expansion.

## Canonical files

- `company/die-agents/hermes/operator-v2/replay_recovery.py`
- `company/die-agents/hermes/operator-v2/die.operator-v2.dispatch-journal.v1.schema.json`
- `company/die-agents/hermes/operator-v2/prepare_operator_v2.py`
- `company/die-agents/hermes/operator-v2/route_followup.py`
- `bridge/tests/test_oe006_operator_v2_replay.py`

OE-006 is accepted only when the focused OE-006 suites, the full bridge suite,
Windows/Linux one-canon validation, secret scan and post-merge smoke are clean.
