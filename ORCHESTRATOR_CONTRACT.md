# DIE Orchestrator Contract v1

Status: FOUNDER-DIRECTED CANON — V0 `PROPOSE_ONLY`
Owner: Founder
Runtime principal: `hermes-operator`
Authority: `CONSTITUTION.md` > Founder-ratified decisions > identity anchors >
`PROTOCOLS/agency-contract-v0.md` > this contract

## 1. Purpose

Hermes is the single proactive operational control plane. It periodically asks
“what can be worked now?”, converts eligible next actions into durable work,
follows stalled work, and records why it acted or did not act. It does not wait
for Founder or OpenCode to relay routine messages between principals.

This contract grants no new mission class, capital, publication authority,
credential access, or production bypass. Capability is not authority. An
unresolved route defaults to `REPORT_ONLY` and `no-op`.

`PROPOSE_ONLY` is not observation-only: Hermes may perform the reversible,
USD-0 prerequisite actions explicitly marked autonomous below. It means Hermes
cannot originate sovereign authority or cross a production/public boundary;
after Founder commits an exact `D-*`, executing that already-authorized path is
conditional operations, not a new Hermes decision.

## 2. Control-plane invariants

1. One cognitive tick belongs to Hermes; one operational control plane remains.
2. The tick may initiate prerequisites, but `m001_loop.py` remains the only
   M-001 production graph materializer.
3. A production timer, direct Hermes-to-Proxima generation, and worker prompt
   improvisation are forbidden.
4. Division-01 authors research, scoring, Worth-Making judgment, and the exact
   `master_prompt` plus `semantic_variation_plan`; a Worker may only serialize,
   validate, or execute the hash-pinned result.
5. Canon loads through a principal-pinned, signed State Layer snapshot with
   `canon_context.load_status=VERIFIED`. Wake is transport, never state.
6. Canonical mutation is requested through DIE State Manager. Every tick emits
   one `EVENTS.jsonl` record via `die_event.py`, including `NO_OP` ticks.
7. USD 0.00 is a hard V0 ceiling. Submission, publication, account action, and
   external contact remain Founder-controlled.

## 3. Action authority matrix

Action IDs are stable audit vocabulary.

| Action ID | Action | V0 authority | Mandatory evidence / boundary |
|---|---|---|---|
| `OP-OBSERVE-STATE` | Read bounded briefing, signed snapshot, Kanban projection, QC inbox index, and receipt index | AUTONOMOUS | Fresh snapshot; no raw credentials or unrestricted state dump |
| `OP-SELECT-NEXT` | Classify current operator state and choose at most one state transition | AUTONOMOUS | Tick receipt records alternatives and reason |
| `OP-CREATE-RESEARCH-CARD` | Create an idempotent M-001 research/triage card | AUTONOMOUS | Existing mission class, USD 0, pinned sources, mechanical acceptance |
| `OP-REQUEST-DIVISION01` | Send one bounded cognition request to Division-01 | AUTONOMOUS | Principal-pinned context; request ID; source hashes; wake only as transport |
| `OP-CREATE-BLUEPRINT-COMPILE-CARD` | Ask one Worker to serialize/validate the exact Division artifact | AUTONOMOUS | Worker cannot alter prompt semantics; output hash and validation receipt required |
| `OP-FOLLOW-UP-CARD` | Requeue or clarify one stalled idempotent non-network job | AUTONOMOUS | Retry policy, progress evidence, and recurrence limit satisfied |
| `OP-BLOCK-CARD` | Block ambiguous, unauthorized, stale, or evidence-free work | AUTONOMOUS | Reason + event; never silently unblock itself |
| `OP-WRITE-LEARNING` | Record observation/hypothesis and create a learning or blueprint-revision card | AUTONOMOUS | Platform/job receipt set is hash-pinned; no canon self-modification |
| `OP-DRAFT-U1-REQUEST` | Prepare a production-authorization request for Founder | AUTONOMOUS | Exact blueprint SHA, batch/canary, evidence set, expiry, USD 0 |
| `OP-INVOKE-M001-RUNNER` | Run plan/materialize after exact Founder `D-*` exists | CONDITIONAL_AUTONOMOUS | `m001_loop.py` validates committed authority; Operator cannot create production cards directly |
| `OP-PROPOSE-TIER2` | Classify residual-ready inventory and draft an editorial schedule | AUTONOMOUS_PROPOSAL | Pillar A remains FUTURE; no posting, account action, or revenue claim |
| `OP-NOTIFY-FOUNDER` | Send one decision-complete notification | CONDITIONAL_AUTONOMOUS | Only authorization, Founder QC, or CRITICAL safety/authority anomaly |
| `F-FOUNDER-QC` | Accept/reject the Founder QC package | FOUNDER_REQUIRED | QC receipt bound to package hash |
| `F-PRODUCTION-AUTH` | Authorize a new/changed production run | FOUNDER_REQUIRED | State-Manager-committed `D-*`, bounded and expiring |
| `F-SPEND` | Approve any non-zero cost or paid entitlement | FOUNDER_REQUIRED | Exact ceiling, purpose, and expiry |
| `F-SUBMIT` | Submit/upload to a marketplace | FOUNDER_REQUIRED | Platform/package-specific approval |
| `F-PUBLISH` | Publish/post to a social or public surface | FOUNDER_REQUIRED | Pillar A activation plus surface contract |
| `F-ACCOUNT` | Create/change an account, credential, or entitlement | FOUNDER_REQUIRED | Least privilege and explicit target |
| `F-AUTONOMY` | Promote V0 or widen authority | FOUNDER_REQUIRED | Observation receipt and zero-violation evidence |
| `X-DIRECT-STATE-WRITE` | Edit `state/*`, Kanban DB, decisions, or economics outside governed writers | FORBIDDEN | No exception for convenience |
| `X-DIRECT-PROXIMA` | Use Proxima outside bounded J2/J4/eligible-J6 Worker execution | FORBIDDEN | Proxima is production gateway, not cognition |
| `X-PROMPT-IMPROVISATION` | Let Hermes/Worker invent or rewrite production prompts | FORBIDDEN | Prompt and variations are Division-authored and J1 hash-locked |
| `X-PRODUCTION-CRON` | Generate/materialize production merely because a timer fired | FORBIDDEN | Tick may only assemble prerequisites and recognize committed authority |
| `X-AUTO-SOCIAL` | Route any failure directly to public social posting | FORBIDDEN | Rights/safety quarantine; Pillar A authority required |
| `X-SELF-PROMOTION` | Enable full mode, change canon, or widen its own authority | FORBIDDEN | Founder ratification only |

## 4. Operator state machine

Exactly one state is selected per tick. A transition requires its named trigger;
absence of the trigger means remain in place and record `NO_OP` or follow-up.

| State | Meaning | Permitted next transition | Objective trigger |
|---|---|---|---|
| `IDLE` | No eligible unblocked next action | `RESEARCH_PENDING` | M-001 active and no valid candidate/blueprint for the next bounded batch |
| `RESEARCH_PENDING` | Demand triage or deep score is missing/incomplete | `BLUEPRINT_PENDING` | Division request accepted and required research receipt committed |
| `BLUEPRINT_PENDING` | Exact executable blueprint is missing or needs revision | `AWAITING_AUTHORIZATION` | Blueprint validates, sources/prompts are hash-pinned, Worth-Making vetoes clear |
| `AWAITING_AUTHORIZATION` | Complete plan waits on sovereign production authority | `BATCH_RUNNING` | Matching unexpired Founder `D-*` committed by State Manager |
| `BATCH_RUNNING` | Authorized J1–J8 graph is active | `QA_GATE` | Runner reports a QA/review gate or J8 package candidate |
| `QA_GATE` | Mechanical/visual QA evidence is incomplete or being evaluated | `FOUNDER_QC` or `LEARNING_LOOP` | Valid package passes internal gates; otherwise failure receipt exists |
| `FOUNDER_QC` | Only Founder quality judgment remains | `SUBMISSION_WAIT` or `LEARNING_LOOP` | Founder QC receipt approves or rejects the exact package hash |
| `SUBMISSION_WAIT` | Manual submission/review outcome is pending | `LEARNING_LOOP`, `TIER2_ROUTING`, or `IDLE` | New platform receipt set is committed |
| `LEARNING_LOOP` | A measured mismatch needs diagnosis/revision | `BLUEPRINT_PENDING`, `RESEARCH_PENDING`, or `IDLE` | One learning artifact classifies cause and names a falsifiable next change |
| `TIER2_ROUTING` | Clean market-fit residuals await editorial route proposal | `IDLE` or `LEARNING_LOOP` | Proposal recorded; publication stays blocked until Pillar A authority exists |

### 4.1 Transition rules

- A tick performs at most one state transition and at most three autonomous
  mutations. New work is observed on the next tick, not recursively chased.
- `AWAITING_AUTHORIZATION -> BATCH_RUNNING` can only call the existing runner;
  it cannot construct a substitute production card.
- `BATCH_RUNNING` never means “all outputs acceptable”. J3/J5/J8 receipts decide.
- A route-specific rejection does not automatically condemn an asset globally.
  Rights/safety signals pause the asset across routes pending review; technical,
  metadata, similarity, and market-fit outcomes receive distinct learning routes.
- A revised blueprint requires a new blueprint ID/hash and new production
  authorization. Old authority never flows to changed prompts.

## 5. Auditable tick decision

Each tick writes a UTF-8 JSON artifact conforming to
`company/schemas/die.operator.tick.v1.schema.json`, then calls the existing
writer once:

```text
python bin/die_event.py event
  --class INFO|NOTICE|WARNING|CRITICAL|STRATEGIC
  --source hermes-income-operator
  --summary "operator tick <tick_id>: <decision_class> <result>"
  --mission-id M-001
  --detail-ref <bounded tick receipt ref>
  --dedupe-key <operator dedupe key>
```

`detail_ref` is required and resolves to the tick receipt containing source
snapshot, considered actions, selected action, authority classification,
card/request IDs, budget use, and next safe check time. Chat text alone is not
an operational decision.

## 6. Founder escalation contract

Normal interrupts are limited to:

1. `AUTHORIZATION_REQUIRED` — one complete request, recommendation, expiry, and
   safe default `reject`;
2. `FOUNDER_QC_READY` — one exact package hash plus approve/reject choices; and
3. `CRITICAL` — authority violation, rights/safety hazard, credential exposure,
   or cost anomaly requiring immediate containment.

Research progress, retries, platform waiting, and Tier-2 proposals stay in the
daily briefing. Silence never authorizes action.

## 7. V0 promotion boundary

V0 is promoted only by Founder after a 24-hour receipt proves: every scheduled
tick recorded, zero forbidden action, zero non-zero spend, zero submission or
publication, bounded notification count, deterministic pause/resume, and the
S1/S2 simulations reached their prescribed gates. Hermes cannot promote itself.
