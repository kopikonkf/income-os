# OPS-001 — Company Incident Escalation & Self-Healing Taxonomy v1

Status: ACCEPTED DOCTRINE / NO NEW RUNTIME AUTHORITY
Date: 2026-09-09
Authority: subordinate to `CONSTITUTION.md`, COS-002 control-plane reconciliation, and COS-003 Aether↔DIE bridge.

## 1. Purpose

Define one company-level incident model so transient errors, runtime failures, engineering defects, and authority-gated events are handled consistently across Mission Control, Factory Asset, MUXIA, holding runtimes, provider principals, retained specialists, and future Economic/Aether layers.

The desired Founder experience is:

```text
incident occurs
 -> system classifies
 -> bounded safe recovery runs automatically when authorized
 -> same durable work resumes
 -> evidence proves recovery
 -> Founder receives an incident report rather than a routine repair assignment
```

This doctrine does **not** grant new constitutional authority. At current DIE A0, any recovery requiring authority not already ratified must fail closed or escalate.

## 2. Two orthogonal dimensions

### Escalation level L0-L3

Answers: **what class of handler/authority is required?**

- `L0 TRANSIENT` — bounded retry/backoff/failover; no engineering mutation.
- `L1 OPERATIONAL` — deterministic allowlisted recovery playbook; no code/config/credential/authority change.
- `L2 ENGINEERING` — diagnosis/repair of repeatable code, schema, adapter or runtime-design defect.
- `L3 AUTHORITY` — Founder/constitutional/red-zone/security/ambiguous irreversible decision.

### Severity S0-S4

Answers: **how much business/system impact exists?**

- `S0 INFO` — no material interruption; diagnostic anomaly only.
- `S1 DEGRADED` — one task/provider/runtime degraded; alternate capacity exists.
- `S2 BLOCKED` — one production/revenue workflow is blocked or repeatedly failing.
- `S3 MAJOR` — multiple workflows/Holdings or a material revenue path are blocked; prolonged degradation or loss of redundancy.
- `S4 CRITICAL` — integrity/security/authority breach, data-loss risk, uncontrolled external side effect, or company control-plane unavailable without accepted rollback.

Level and severity must not be conflated. A severe outage can still have an L1 deterministic recovery; a low-impact credential request is still L3 because authority, not impact, controls the escalation.

## 3. Incident lifecycle

```text
DETECTED
  -> CLASSIFIED
  -> CONTAINED
  -> RECOVERING | WAITING_CAPACITY | REPAIR_REQUIRED | WAITING_AUTHORITY
  -> VERIFYING
  -> RESOLVED
     or ESCALATED
     or QUARANTINED
```

Every incident has one durable `incident_id`. Repeated observations with the same fingerprint update the existing incident rather than creating an unbounded stream of independent incidents.

A business task/job remains the same durable task unless the canonical business graph itself requires a new task. Recovery does not create a compensating seed/order/publication merely to make the queue move.

## 4. Stable incident fingerprint

Fingerprinting must exclude volatile timestamps/PIDs/attempt IDs unless they identify the failed resource itself.

Conceptual fingerprint input:

```text
policy_version
+ holding/runtime/component
+ operation
+ normalized failure_class/error_code
+ affected resource identity
+ side-effect class
```

Example:

```text
H01 | muxia-queue | wait-result | E_MUXIA_QUEUE_TIMEOUT | PRODSEED000035 | local-idempotent
```

The fingerprint is used for recurrence counting, anti-loop escalation, deduplication, and linking lessons to prior incidents.

## 5. L0 — TRANSIENT

### Typical classes

- provider high demand / temporary capacity unavailable;
- rate limit or bounded quota wait where policy allows waiting;
- transport dispatch timeout before acceptance;
- prompt/send not accepted with no side effect;
- observer/wake adapter failure proven not to have committed the action;
- temporary network/DNS/connectivity loss with no ambiguous external mutation;
- queue wait timeout when producer/runtime health is otherwise healthy and the request is idempotent/reconcilable.

### Allowed automatic actions

- bounded retry with jitter/backoff;
- wait for capacity without fabricating success;
- switch to an accepted alternate owner/provider where policy allows;
- re-observe/reconcile state;
- resume the **same durable task/job**;
- record attempt lineage.

### Forbidden at L0

- code/config changes;
- process/service repair that changes ownership/state beyond an accepted local retry primitive;
- credential/login mutation;
- spend;
- external submission/publication retry when the prior side effect is ambiguous;
- destructive cleanup;
- creating a replacement business task/seed to hide the failure.

### Budget

Use the subsystem's accepted bounded attempt budget; Mission Control currently defaults to 3 owner attempts and excludes capacity-wait observations from consumed attempt count. A subsystem may be stricter, never unbounded.

Attempt budgets persist across process restart. Restarting Mission Control, cron, Hermes, or a worker must not reset the logical retry budget.

### Promotion

Promote L0 -> L1 when evidence shows the failure is local operational state rather than external/transient capacity, or when the L0 budget/time horizon is exhausted.

Promote L0 -> L2 directly for a repeatable deterministic defect or failure class not proven retry-safe.

## 6. L1 — OPERATIONAL RECOVERY

L1 handles a known runtime fault using a deterministic, idempotent, allowlisted playbook with explicit preconditions and postconditions.

### Typical classes

- dead process/service with accepted restart semantics;
- stale queue worker whose ownership is unambiguous;
- stale lease with provable dead holder and accepted lease-recovery contract;
- browser/runtime component down while profile ownership is known;
- stuck local queue where request/result reconciliation proves no duplicate side effect;
- disk/temp/cache condition with a narrowly accepted safe cleanup playbook;
- boot/runtime watchdog recovery of an expected component.

### Required playbook contract

Each L1 playbook declares:

```text
playbook_id
version
applicable failure fingerprints/classes
preconditions
allowed mutations
forbidden mutations
idempotency/replay behavior
maximum recovery attempts
verification probes
rollback/containment action
```

### Core rules

1. **No guessing ownership.** Ambiguous PID/lease/profile/queue ownership -> `QUARANTINED` and escalate L2/L3 as appropriate.
2. **No false success.** A recovered crashed job remains FAILED until real artifact/evidence proves a successful new/reconciled attempt.
3. **Same durable work.** Repair the runtime then resume/reconcile the original task/job.
4. **No hidden authority expansion.** L1 cannot perform credential mutation, spend, external publication/submission, Git history rewrite, constitutional change, or unrestricted DEV work.
5. **Verify after recovery.** Process alive is insufficient; verify the component's functional health and the affected work's resumability.

### Default anti-loop budget

A company-level default is **maximum 2 automatic L1 playbook executions per stable incident fingerprint within a rolling 60-minute recurrence window**, unless a subsystem has a stricter accepted contract.

If the same fingerprint reappears after a reported L1 recovery inside that window, promote to L2 rather than restart repeatedly.

This counter is durable and does not reset on reboot/process restart.

## 7. L2 — ENGINEERING

L2 means the system likely needs cognition and an engineering change, not another restart.

### Typical classes

- repeatable code defect;
- adapter/protocol/schema mismatch;
- deterministic validation failure caused by implementation drift;
- producer/consumer queue contract defect;
- recurrence of the same L1 fingerprint after accepted recovery;
- unknown failure after retry-safe classes are exhausted;
- broken migration/config generator requiring source change;
- test/regression failure that blocks runtime restoration.

### L2 workflow

```text
incident
 -> contain affected work
 -> preserve logs/evidence/reproduction input
 -> runtime Architect cognition may diagnose/propose
 -> create/dedupe exactly one linked repair child when a code change is required
 -> acquire task-scoped delegated engineering authority if available
 -> isolated patch/worktree
 -> tests + review
 -> safe deploy
 -> functional verification
 -> resume original durable business task
 -> close incident only after recovery evidence
```

### Current A0 authority boundary

COS-002 established that `chief-executive-architect-dev` remains Founder-invoked/non-runtime and runtime `chatgpt-architect` does not inherit unrestricted DEV privilege.

Therefore **today**:

- automated L2 detection, diagnosis, evidence collection, deduped repair proposal/Work Card creation are allowed only where existing canon permits;
- unrestricted filesystem/Git/service mutation is **not** authorized merely because the incident is L2;
- autonomous L2 repair becomes valid only through an accepted task-scoped delegated-execution contract (`MC-009D`) and applicable ratified governance, or through explicit Founder-invoked DEV authority.

Future delegated L2 automation must remain bounded by task/resource scope and cannot widen into L3 authority.

### Repair-child rule

A repair child is an engineering artifact, **not a replacement business job**. Exactly one active repair child may exist per `(incident_id, repair_generation)` unless explicit evidence proves the repair strategy must fork.

The parent business task remains blocked/contained and resumes after repair acceptance. No compensating seed/task is created.

## 8. L3 — AUTHORITY / FOUNDER

L3 is not "too hard for AI". It means the required action crosses an authority, integrity, security, or irreversible boundary.

### Direct L3 classes

- Founder approval gate / constitutional ambiguity;
- spend, purchase, paid-plan/vendor commitment outside a ratified envelope;
- credential/password/token/key/account permission mutation or recovery;
- external marketplace submission/publication with uncertain or non-idempotent prior state;
- destructive filesystem/database action without an accepted reversible playbook;
- force-push/history rewrite unless separately authorized;
- identity/Northstar/mission/Constitution/Aether DNA change;
- ambiguous owner where acting could corrupt another task/profile/runtime;
- suspected secret/security compromise;
- data-loss/integrity decision requiring tradeoff rather than deterministic restore;
- disabling the last accepted company control/rollback path;
- unresolved conflict between Aether and DIE constitutional domains.

### L3 behavior

- contain/freeze the affected action where safe;
- preserve evidence;
- do not retry the risky side effect;
- notify Founder with a decision packet, not a vague error;
- state exactly what is blocked, what remains healthy, available safe options, rollback state, and required authority;
- silence/time passage never counts as approval.

## 9. Reconciliation-before-retry rule

For any action that might have created an external side effect, retry is forbidden until external state is reconciled.

This includes marketplace submission, publication, purchase, order, billing, account mutation, and any non-idempotent provider action.

Decision pattern:

```text
prior action definitely NOT committed -> normal retry policy may apply
prior action definitely committed     -> reconcile / NO duplicate action
external state ambiguous/unreachable  -> STOP_REVIEW / L3 if authority-impacting
```

Existing Submission Idempotency v1 is the reference pattern: `NOT_CHECKED`, `AMBIGUOUS`, and `UNREACHABLE` stop blind retry; a retry becomes mechanically eligible only after a positive `NOT_FOUND` observation, and mechanical eligibility is still not submission authority.

## 10. Stale/late/duplicate callback rules

- Every attempt is bound to task ID, attempt number, owner identity and lease/capability token.
- A late callback from a superseded attempt cannot mutate current work.
- Lease mismatch fails closed.
- Duplicate finalization callbacks are ignored but recorded.
- A process restart cannot make a prior attempt "current" again.
- Review independence remains intact across failover.

Mission Control already provides working evidence for these primitives in its owner-failover engine.

## 11. Recovery evidence contract

Every non-trivial incident resolution records at minimum:

```text
incident_id
fingerprint
policy_version
first_seen_at / last_seen_at
holding_id / runtime_id / component
parent_task_id / job_id
error_code / normalized_failure_class
level L0-L3
severity S0-S4
authority_basis
side_effect_class
attempt lineage
recovery playbook/repair ref
pre-recovery observations
post-recovery functional verification
resume_point / resumed_task_id
artifact/evidence refs
recurrence_count
resolution
resolved_at
```

For L1+, the receipt must answer:

1. What failed?
2. Why was this recovery authorized?
3. What exactly changed?
4. How was duplicate/ambiguous side effect excluded?
5. What functional evidence proves recovery?
6. Did the original durable work resume?
7. What will happen if the same fingerprint recurs?

## 12. Founder notification policy

Founder should not receive every transient retry.

### Normally silent / dashboard only

- L0 recovered inside budget with no material SLA/revenue impact.
- expected provider capacity wait that resolves inside policy.

### Notify after recovery

- L1 recovery that restored a business/runtime path;
- L0 that caused material delay or exhausted one provider and failed over;
- L2 repair completed and original work resumed.

Recommended notification semantics:

```text
RECOVERED | incident=<id> | level=L1 | severity=S2
started=<time> | recovered=<time>
component=muxia-queue
error=E_MUXIA_QUEUE_TIMEOUT
recovery=<playbook/ref>
evidence=<receipt/ref>
resumed=<original task/job>
```

### Notify immediately / decision required

- L3;
- S4;
- L2 unable to obtain valid delegated repair authority;
- loss of all control-plane/rollback paths;
- recovery budget/anti-loop guard exhausted while material production remains blocked.

## 13. Example: `E_MUXIA_QUEUE_TIMEOUT`

Current canonical production runtime waits up to 740 seconds for the exact result file and currently reports all exceptions as `retryable=yes`, then exits code 2 while preserving `next=retry same durable card; no compensating seed`.

OPS-001 refines that generic behavior:

### Case A — producer healthy, request exact/idempotent, temporary delay

```text
E_MUXIA_QUEUE_TIMEOUT
+ queue consumer healthy
+ same request hash still pending/reconcilable
+ no result/side-effect ambiguity
= L0 / usually S1
-> bounded wait/retry/reconcile same durable card
```

### Case B — queue consumer/process dead with known ownership and accepted restart playbook

```text
E_MUXIA_QUEUE_TIMEOUT
+ producer health probe FAILED
+ ownership unambiguous
+ no external side effect ambiguity
= L1 / S2
-> accepted restart/recovery playbook
-> verify consumer health
-> reconcile existing request
-> resume same durable card
```

### Case C — consumer healthy but identical fingerprint recurs after L1 recovery, or request/response contract is broken

```text
E_MUXIA_QUEUE_TIMEOUT
+ repeated deterministic recurrence / schema-producer defect
= L2 / S2
-> deduped engineering incident
-> Architect diagnosis
-> task-scoped repair if authorized
-> tests/deploy/verify
-> resume original card
```

### Case D — recovery would require credential/account/provider permission change or ownership is ambiguous

```text
E_MUXIA_QUEUE_TIMEOUT
+ required action crosses authority/integrity boundary
= L3
-> contain
-> preserve evidence
-> Founder decision packet
```

The error code alone never determines L0/L1/L2/L3.

## 14. Example: MUXIA crash recovery

Existing MX-041 policy already matches L1 doctrine:

- live recorded PID -> NOOP;
- dead PID + unambiguous owner/lease -> interrupted job FAILED, lease released, profile READY;
- ambiguous owner/state/PID -> `QUARANTINE_REQUIRED` rather than guessing;
- recovered interrupted job cannot become SUCCEEDED without durable artifact receipt.

OPS-001 adopts these principles as company-level invariants.

## 15. Example: provider cognition timeout

Existing Factory/Hermes timeout recovery uses durable versioned author/review attempts, converts response timeout into bounded retry state, and prevents infinite wait. This maps to L0 while retry-safe and within budget; exhaustion or deterministic recurrence promotes L2 rather than creating an infinite retry loop.

## 16. Incident learning bridge to Aether

After resolution, a sanitized `INCIDENT_LESSON` may cross the COS-003 Aether bridge.

Aether AX1 requires repeated failures to reference prior incidents, justify repetition, and record prevention/exception decisions. Therefore a recurrence fingerprint is useful learning evidence.

But:

```text
incident resolved
!= Aether belief automatically validated
```

The lesson remains evidence/candidate and follows Aether's governed belief/knowledge promotion lifecycle.

## 17. Conformance rules

A runtime claiming `DIE_INCIDENT_TAXONOMY_V1_CONFORMANT` must prove:

1. L0-L3 and S0-S4 are stored separately.
2. Retry/recovery budgets are durable across restart.
3. Stable fingerprint recurrence is counted.
4. same durable business task resumes after recovery; no compensating business task is fabricated.
5. stale/late/duplicate callbacks cannot mutate the current attempt.
6. ambiguous external side effects reconcile before retry.
7. L1 playbooks are allowlisted, bounded and functionally verified.
8. recurrence after L1 within policy window promotes L2.
9. L2 does not inherit unrestricted DEV privilege.
10. L3/red-zone/authority ambiguity fails closed to Founder.
11. no incident is closed merely because a process is alive; functional recovery evidence is required.
12. recovery produces durable evidence and an explicit next-recurrence action.

## 18. OPS-001 acceptance decision

**PASS.** L0 transient retry/backoff, L1 deterministic operational recovery, L2 engineering escalation, and L3 Founder/authority escalation are defined with separate severity, durable evidence, recurrence fingerprinting, anti-loop budgets, reconciliation-before-retry, stale callback protection, same-durable-work resume semantics, and current A0 Architect authority boundaries. No runtime code, Constitution, Aether, credential, provider, service or production state was mutated by this task.
