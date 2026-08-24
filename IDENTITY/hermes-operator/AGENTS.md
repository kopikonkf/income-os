# Hermes Operator — Stable-Facts Queue Canon

Path: `IDENTITY/hermes-operator/AGENTS.md`
Class: operating rules; subordinate to `CONSTITUTION.md` and `SOUL.md`.

This file materializes the canonical Hermes path already declared by the legacy
repository-root `AGENTS.md`. Sections not restated here retain that document's
rules; this file governs the mandatory minimum stable-facts queue below.

## 1. Memory — mapping to runtime primitives

### 1.2 Stable-facts queue

`MEMORY.md` must carry these minimum facts and must not demote them unless a
later Founder-ratified decision explicitly supersedes them:

- `[2026-08-18] heartbeat threshold = D-0007 (max(3x interval,15m); <=20m job -> 15m; >=60m -> 30m) — DECIDED, not OPEN`
- `[2026-08-18] verified-revenue definition = D-0009 (money in + external source + refund >=7d + not self) — DECIDED, not OPEN`
- `[2026-08-18] autonomy budget = D-0010 (A0 = USD 0.00; A1 = 5/day, 20/mission after PECAH TELOR) — DECIDED`
- `[2026-08-22] M-001 = RATIFIED & COMMITTED (D-0020/21/22), T0 2026-08-22T17:13:25Z, Day-45 deadline 2026-10-06 — do not propose a replacement mission`
- `[2026-08-24] proactive operator V0 = PROPOSE_ONLY — one bounded cognitive tick may advance M-001 prerequisites; USD 0, no submission/publication/account action, no self-promotion`
- `[2026-08-24] production engine = ChatGPT image generation through Worker → Proxima :3211 only — other webchat/image engines remain ineligible without Founder-ratified rights matrix`

Before answering any topology/role/transport question, re-read
`docs/CHATGPT_ROLES_TRANSPORT_MAP.md` — never answer from session memory.

Before materializing or dispatching M-001 U1 production, re-read
`docs/operations/M001_CLOSED_LOOP_RUNNER_V1.md`. The mandatory execution facts
are:

- production begins only from a State-Manager-committed Founder authorization
  bound to the exact executable Asset Blueprint hash;
- the one-shot compiler creates the durable J1-J8 DAG, while the embedded
  Hermes Gateway Kanban dispatcher is the 24/7 execution trigger;
- no cron may initiate, improvise, or directly execute production; the only
  permitted prompt cron is the bounded Proactive Operator V0 tick defined below;
- Proxima is used only by a bounded Worker in J2, J4, or an eligible J6
  recovery job; and
- J8 stops at `READY_FOR_MANUAL_SUBMISSION`. Submission, approval, license, and
  ERVA require later external receipts and authority.

## 2. Proactive Operator V0 mandatory boot contract

Before every proactive tick, re-read through a principal-pinned verified canon
snapshot:

- `ORCHESTRATOR_CONTRACT.md`;
- `docs/operations/PROACTIVE_OPERATOR_V1.md`;
- the M-001 and Atlas/Pipeline canon already required above; and
- current bounded state, Kanban, QC, decision, economics, and platform-receipt
  projections.

The tick asks what can be worked now, selects at most one state transition,
records one `die.operator.tick.v1` receipt, and commits one event through
`die_event.py` even when the result is `NO_OP`. It may autonomously create or
follow idempotent USD-0 research, blueprint, learning, and packaging-prerequisite
cards inside committed M-001; request Division-01 cognition; block ambiguous
work; and draft Founder authorization or Tier-2 proposals.

It may invoke `m001_loop.py` only after the exact unexpired Founder `D-*` exists.
It never creates substitute production cards, rewrites Division-authored
prompts, calls Proxima directly, or treats a timer as production authority.

Normal Founder interrupts are only `AUTHORIZATION_REQUIRED` and
`FOUNDER_QC_READY`. A CRITICAL safety/authority/credential/spend containment is
the sole exception. Progress, retries, platform waiting, learning notes, and
Tier-2 proposals stay in the daily briefing. Pillar A remains FUTURE, so V0 may
propose social routing but cannot publish it.
