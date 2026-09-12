# DIE-H01 Single Business Scheduler and Anti-Duplicate Dispatch Proof v1

Status: **H01-016 PASS / ACCEPTANCE CANDIDATE**
Date: 2026-09-12

## 1. Decision

The accepted DIE V2 control topology has exactly one business scheduler: **`die-control / Mission Control`**. H01 is an execution plane. The H01 Runtime Gateway, Recovery Supervisor, Linux Hermes, MUXIA dispatch worker, browser owners and retained Windows Hermes runtime are not permitted to originate competing business work.

H01-016 closes two real legacy scheduler gaps discovered during live acceptance rather than merely asserting the architecture:

1. Linux FA-124 acceptance timers were inactive but still enabled for future activation/reboot. Both were disabled and stopped.
2. Windows Hermes still had an active proactive-operator cron and an embedded Kanban dispatcher. The proactive job was paused and Kanban gateway dispatch was disabled in both default and `income-operator` profiles; the running `income-operator` gateway was restarted and its log confirmed the dispatcher stayed disabled.

Messaging, health/reporting and rollback unit files were preserved. `/srv/die` was not mutated.

## 2. Mission Control authority

Live accepted runtime during proof:

```text
Mission Control     0.8.49
release HEAD        a2e113e5f5717cfd236209f7e0ee95831189f713
listen              127.0.0.1:8891
health              ok=true
Canonical Feeder    enabled
interval            60000 ms
max_cards_per_run   1
deterministic       true
```

A live feeder observation on canonical commit `7bd176a82d9fbf68f7b8413886dabb5ba22f7103` created zero new cards and classified H01-016 as `SOURCE_NODE_ALREADY_INGESTED`. This is the intended scheduler boundary: canonical Git readiness is ingested by Mission Control once; H01 does not independently infer or manufacture work.

The exact live Mission Control v0.8.49 release passed **35/35** targeted feeder/intake/dispatcher/owner-attempt/failover tests. These cover second-tick feeder dedupe, stable source-key uniqueness, rejection of concurrent owner attempts, immutable terminal attempts, stale/late callback rejection, failover on the same logical task, bounded attempts and idempotent duplicate callbacks.

## 3. Live durable duplicate invariants

Read-only inspection of `D:\MISSION_CONTROL\state\mission-control.db` returned `PRAGMA quick_check=ok` and:

```text
source_key duplicates on tasks                     0
task id duplicates                                 0
active source-node duplicates                      0
active tasks with multiple leases                  0
active tasks with multiple open owner attempts     0
```

`idx_tasks_source_key` is a UNIQUE partial index over non-null canonical source keys.

One historical imported anomaly remains visible and is not concealed: cancelled task `MC004C-LIVE-QWEN` contains two legacy owner-attempt rows whose `ended_at` fields were never backfilled. The task itself is `CANCELLED`, has no active lease and is outside current dispatch authority. H01-016 therefore classifies it as historical migration residue, not an active duplicate-execution path. Any equivalent anomaly on an active task or with an active lease fails the H01-016 guard.

## 4. Linux legacy scheduler quarantine

There are no user/system DIE business cron entries on H01. Linux Hermes reports zero scheduled jobs.

The following legacy acceptance timers were discovered as `enabled` but inactive:

```text
die-fa124-cluster-a.timer
die-fa124-cluster-b.timer
```

Their oneshot services execute `run_fa124_cluster_slot.mjs`, so future timer activation would constitute competing business scheduling. H01-016 executed:

```text
systemctl disable --now die-fa124-cluster-a.timer die-fa124-cluster-b.timer
```

Postcondition:
- both timers `disabled`;
- both timers `inactive`;
- no DIE/H01/Factory/MUXIA business timers remain in `systemctl list-timers`;
- timer unit files remain installed for rollback;
- browser/broker/runtime services were not stopped;
- `/srv/die` was not changed.

`die-muxia-dispatch.service` remains a bounded queue consumer/executor. It does not become a business scheduler merely because it consumes already-authorized work.

## 5. Windows Hermes legacy scheduler quarantine

The retained Windows Hermes `income-operator` profile exposed one active business-generation cron:

```text
job id      da0e4bcbcbb9
name        die-proactive-operator-v1
schedule    */30 * * * *
script      die_operator_prepare.py
```

It was paused, not deleted, preserving rollback and audit history.

A second hidden competing path existed because Hermes gateway embeds a Kanban dispatcher by default. H01-016 set:

```text
kanban.dispatch_in_gateway = false
```

for both the default and `income-operator` profiles. The running `income-operator` gateway was cleanly restarted. Its current gateway log records:

```text
kanban dispatcher: disabled via config kanban.dispatch_in_gateway=false
```

The retained legacy M-001 Kanban card `t_3d062e86` remains `ready` for historical continuity but has **zero runs**. Therefore its existence no longer grants automatic dispatch authority.

Four active Hermes cron jobs remain: `die-heartbeat`, `die-briefing`, `die-summary` and `die-audit`. They are health/reporting mechanics and do not create or dispatch business work. Heartbeat may block stale legacy cards as a health action; it is not a business-work generator.

Windows Scheduled Tasks named for Hermes, Brave wake and Mission Control boot/watchdog are runtime bootstrap/recovery surfaces, not business schedulers. Mission Control Canonical Feeder remains the sole source of automatic business Work Cards.

## 6. H01 local components cannot become schedulers

H01-015 Recovery Supervisor is explicit-incident-only. Its canonical manifest states:
- `supervisor_is_scheduler=false`;
- no background poll loop;
- no graph reader;
- no queue feeder;
- no task/provider selection.

H01-012 Runtime Gateway likewise states `gateway_is_scheduler=false`. Its only cross-VPS business messages remain `WORK_DISPATCH`, `WORK_CHECKPOINT` and `WORK_RESULT`.

## 7. Same durable job cannot commit twice

The Runtime Gateway contract binds one accepted execution to:

```text
dispatch_id + idempotency_key + work_card_sha256
```

Required semantics are:
- same dispatch + same digest -> return the existing execution;
- same dispatch + different digest -> `E_IDEMPOTENCY_CONFLICT`, start nothing;
- dispatch is stored before acknowledgement;
- terminal result is stored before send and immutable after commit;
- WAN loss never creates another execution;
- reconciliation uses the original mission/dispatch/execution/digest identity rather than blind redispatch.

Mission Control independently enforces canonical `source_key` uniqueness, one current task identity, one active lease per task and one active owner attempt per active task. The live v0.8.49 targeted suite proves late and duplicate callbacks cannot create a second logical task/attempt commit path.

## 8. Executable fail-closed proof

`engineering/single_scheduler_guard.py` validates the live-proof snapshot together with the canonical H01-012 and H01-015 manifests. It refuses PASS if any of the following regress:

- a Linux business timer or Hermes scheduled job becomes active;
- Windows Hermes Kanban gateway dispatch is re-enabled;
- proactive operator becomes active;
- a legacy ready card gains an autonomous run;
- active source/lease/owner-attempt duplication appears;
- historical anomalies become active/leased;
- Runtime Gateway replay/terminal-result semantics weaken;
- Recovery Supervisor acquires scheduler/poll/feeder authority.

## 9. Cutover boundary

H01-016 does not claim the entire production pipeline is cut over. It proves scheduler sovereignty and anti-duplicate dispatch. `H01-200` remains BLOCKED because `H01-027` and `H01-109` are still BLOCKED. Full MC -> H01 -> provider -> SVG -> derivatives -> QA/package production remains a later governed acceptance.

No provider generation, marketplace submission, spend, credential mutation, legacy-data deletion, `/srv/die` mutation or arbitrary service retirement was performed by H01-016.
