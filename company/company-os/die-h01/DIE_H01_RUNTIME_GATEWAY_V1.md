# DIE-H01 Runtime Gateway Contract v1

Status: H01-012 ACCEPTANCE CANDIDATE
Date: 2026-09-12
Scope: logical cross-VPS contract between the global `die-control` plane and the `die-h01` execution plane. This task defines the boundary; it does not deploy a gateway service or cut over runtime traffic.

## 1. Authority boundary

`die-control` owns the one global Mission Control, queue/lease truth, Work Card authority and business scheduling. `die-h01` owns execution. The H01 Runtime Gateway is not a scheduler, task-graph evaluator, browser driver, filesystem proxy, arbitrary RPC endpoint or second Mission Control.

```text
die-control / Mission Control
        |
        |  WORK_DISPATCH (durable, authenticated, coarse-grained)
        v
H01 Runtime Gateway
        |
        v
local durable execution journal -> H01 local executor/factory
        |                         -> Brave/CDP/provider waits LOCAL
        |                         -> SVG/download/QA/conversion LOCAL
        |                         -> artifact storage LOCAL
        |
        +-- WORK_CHECKPOINT -----> control-side Mission bridge
        +-- WORK_RESULT ---------> control-side Mission bridge
                                    |
                                    +-> mission.task.checkpoint
                                    +-> mission.task.complete / block
```

Mission lease/review capabilities are injected only by the privileged control-side bridge when invoking Mission Protocol. They are never persisted in the H01 job journal or gateway message payload.

## 2. The only cross-VPS business messages

### `WORK_DISPATCH` — die-control -> H01

A bounded Work Card containing business/execution intent, not UI instructions. Required identity is `mission_task_id`, `dispatch_id`, `attempt_no`, `principal_id`, `idempotency_key`, `work_card_sha256` and the sanitized `work_card` object.

The gateway MUST durably record the accepted dispatch before acknowledging it. The acknowledgement binds a stable `execution_id` to the dispatch.

### `WORK_CHECKPOINT` — H01 -> die-control

A bounded aggregate progress event containing `execution_id`, `mission_task_id`, monotonic `sequence`, stable `event_id`, progress, summary, safe structured payload and artifact references/hashes when useful. It MUST NOT contain browser actions, screenshots, profile paths, provider session material, filesystem reads/writes or raw artifact bytes.

The control-side bridge maps the event to `mission.task.checkpoint` using the current task-scoped capability.

### `WORK_RESULT` — H01 -> die-control

One terminal durable result per accepted execution. Terminal outcome is `COMPLETED` or `BLOCKED`. The result is written locally before WAN delivery and is immutable after commit. `COMPLETED` maps to `mission.task.complete`; `BLOCKED` maps to `mission.task.block`.

Results carry sanitized structured result data plus logical artifact references and hashes. Artifact bytes remain on the H01 data plane unless a separate governed artifact-transfer contract is introduced later.

## 3. Authentication and secret boundary

Every cross-VPS message requires an encrypted authenticated transport and peer identity binding for `die-control` <-> `die-h01`. The concrete carrier (private overlay, tunnel, mTLS-capable reverse proxy, or equivalent) is a deployment choice gated by H01-011; it may not weaken these requirements.

Application requests MUST be replay-resistant and authenticated to the expected peer. Service credentials are host-local secret configuration and MUST NOT appear in Git, Work Cards, gateway durable state, receipts or normal logs.

Mission owner/reviewer lease tokens, OAuth tokens, cookies, browser session bytes and provider credentials are forbidden gateway-payload fields. The control-side Mission bridge owns ephemeral Mission capability injection.

## 4. Durability and idempotency

The gateway is store-before-ack:

1. authenticate and validate message;
2. compute/verify canonical payload digest;
3. atomically persist local dispatch/event state;
4. only then acknowledge over the network.

`dispatch_id + idempotency_key + work_card_sha256` identifies one execution attempt. Replaying the same tuple MUST return the existing `execution_id` and MUST NOT start another job. Reusing the same `dispatch_id` with a different digest is `E_IDEMPOTENCY_CONFLICT` and starts nothing.

Each H01 event has stable `event_id` and monotonic `sequence`. Retry after ambiguous network failure is safe. A terminal local result remains authoritative for reconciliation even if its first WAN delivery was not acknowledged.

Transient WAN loss MUST NOT trigger a second H01 execution. H01 continues a safely accepted local job, journals checkpoints/results locally, and retries delivery when connectivity returns. If control-side standing is uncertain after reconnect, reconciliation is by `mission_task_id + dispatch_id + execution_id + digest`, never by blindly redispatching the job.

## 5. Locality hard boundary

The following stay H01-local and are not gateway RPC methods:

- Brave lifecycle, tabs and provider navigation;
- CDP ports, targets, click/type/evaluate/screenshot operations;
- UDD/profile paths and selection internals;
- provider wait/completion detection and retries;
- cookies, tokens, credentials and session stores;
- shell/process execution;
- arbitrary filesystem read/write/list/glob;
- SVG/raw download bytes and intermediate files;
- canonicalization, QA, conversion, metadata and package assembly;
- artifact byte storage and cache janitor operations.

A Work Card may say **what outcome is required** (for example noun, asset mode, preset, target package), but die-control MUST NOT remote-drive **how each browser click or local file operation occurs**.

## 6. Bounded payload doctrine

Cross-VPS state is control metadata, not data-plane transport. Work Cards carry bounded structured intent. Checkpoints carry summary/progress/aggregate evidence. Results carry final standing and artifact references/hashes.

Absolute browser profile paths, CDP endpoints, arbitrary local filesystem paths, raw prompts/messages intended for click-by-click browser driving, binary/base64 artifact payloads and secrets are forbidden. Logical artifact identifiers may resolve locally on H01.

## 7. Failure semantics

- bad/expired service authentication -> reject before durable dispatch (`E_AUTH`);
- invalid envelope/schema -> reject (`E_CONTRACT`);
- same dispatch and same digest -> replay-safe existing acknowledgement;
- same dispatch and different digest -> reject (`E_IDEMPOTENCY_CONFLICT`);
- H01 local executor unavailable after accepted dispatch -> durable checkpoint/block, not redispatch by browser click;
- WAN loss after accepted dispatch -> continue locally if safe and spool events;
- ambiguous terminal delivery -> reconcile control standing before replaying terminal event;
- H01 reboot -> recover accepted nonterminal executions from local journal according to local executor policy; never infer a fresh business task;
- control-plane outage -> no new business scheduling on H01; already accepted local work may finish and queue its result.

## 8. Mission Protocol mapping

H01 does not invent a parallel business protocol. The control-side bridge projects gateway events onto canonical `mc-mission-v1`:

| Gateway event | Mission Protocol |
|---|---|
| accepted/running progress | `mission.task.checkpoint` |
| terminal `COMPLETED` | `mission.task.complete` |
| terminal `BLOCKED` | `mission.task.block` |
| control-side reconciliation | `mission.task.get` |

Founder requests/reviews remain Mission Control concerns and are not added to the H01 Runtime Gateway v1 surface.

## 9. Non-goals

V1 intentionally has no browser-control API, no remote shell, no generic filesystem API, no arbitrary provider API proxy, no raw artifact upload/download, no queue feeder, no recovery scheduler, no Founder UI API and no generalized microservice bus. H01-015 may build a recovery-only Supervisor, but it must remain local and bounded by this authority boundary.

## 10. Acceptance invariants

H01-012 is contract-complete when canon contains:

- this normative boundary;
- a machine-readable boundary manifest;
- a JSON Schema for the three gateway message types;
- regression checks proving only dispatch/checkpoint/result are admitted and browser/CDP/filesystem/secret surfaces are forbidden;
- explicit replay-safe dispatch and store-before-ack semantics;
- explicit Mission Control singleton and control-side Mission capability ownership.

No live service deployment, port exposure, tunnel mutation, browser restart, `/srv/die` mutation or business cutover is part of H01-012.
