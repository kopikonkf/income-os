# M-001 Reconciliation and Health Gate v1

Date: 2026-08-23
Mission: M-001
Division: DIVISION-01
Hard deadline: 2026-10-06

## Safety boundary

This runbook may reconcile projections and verify health. It does not authorize
asset production, marketplace submission, spend, secrets, DNS, services, wake,
P2, or Proxima changes. Marketplace submission remains Founder-approved A0.

## 1. Verify the canonical chain

Read the bounded mission surface:

```powershell
Set-Location C:\DIE\bridge
python -m income_os_bridge active_missions --status any
python -m income_os_bridge mission_get --mission_id M-001
```

Pass only if the M-001 row names DIVISION-01, reports `status=active`, cites
`last_decision_id=D-0022`, and preserves the D-0020/D-0021/D-0022 chain in the
mission-scoped detail.

Do not append a replacement acceptance decision just to populate a projection.

## 2. Materialize the Hermes mission root

Hermes creates/decomposes the durable operational mission card through its
supported Kanban interface. Do not write `kanban.db` directly and do not encode
mission linkage only in a title.

The materialization is valid only when either the bounded Kanban reader returns
a row whose `mission_id` is exactly `M-001`, or State Manager has committed an
event containing both `mission_id=M-001` and that card's exact `task_id`.
Re-run:

```powershell
python -m income_os_bridge active_missions --status active
python -m income_os_bridge mission_get --mission_id M-001
```

Pass only when:

- `lifecycle_state=materialized`;
- `reconcile_required=false`;
- `execution_ready=true`;
- `cards_open` counts only M-001 cards;
- unrelated Kanban cards are absent from `mission_get`.

If Hermes CLI cannot return `mission_id`, Hermes must submit the explicit
mission/task relation event through State Manager. Do not infer linkage.

```powershell
python C:\DIE\bin\die_event.py event --class NOTICE --source hermes-income-operator --summary "M-001 mission root materialized" --division-id DIVISION-01 --mission-id M-001 --task-id K-EXACT
```

Replace `K-EXACT` with the exact committed Kanban card ID returned by Hermes.

## 3. Repair and verify health

Run:

```powershell
python -m income_os_bridge system_health
```

Production gate requires all of:

- `gateway_running=true`;
- `source_trust` is not `DEGRADED`;
- no active CRITICAL alarm;
- `execution_readiness.ready=true`.

For the observed heartbeat `WinError 2`, first locate the verified Hermes
executable. If scheduled-task context cannot resolve it, the operator may set
the exact executable through `DIE_HERMES_EXE` in that task's authorized runtime
environment. Run the heartbeat once and require a successful Kanban read. The
cron emits a `resolved` event for `health:die-heartbeat:kanban-cli` only after
that success.

For legacy alarms such as provider 429, repair/re-probe the actual dependency.
Only after verified recovery, append a resolution through the State Writer:

```powershell
python C:\DIE\bin\die_event.py event --class INFO --source operator --summary "verified recovery evidence" --alarm-state resolved --resolves-event-id E-XXXXXX --detail-ref repo:/evidence/recovery.json
```

Use the exact alarm ID and a real evidence reference. Never emit a resolution
merely to make the readiness flag green.

If `gateway_running=false`, diagnose and recover the existing gateway under the
separate operational authorization. This runbook does not authorize starting,
installing, or reconfiguring a service.

## 4. Evidence ordering for future missions

The canonical order is:

1. Founder ratification committed by State Manager;
2. fresh division snapshot includes that exact decision evidence;
3. division submits `propose_mission` with byte-exact signed snapshot and exact
   evidence rows;
4. State Manager commits proposal;
5. Hermes commits operational acceptance;
6. Hermes materializes mission-linked Kanban work;
7. bounded projection proves lifecycle plus materialization;
8. health and A0 gates are checked before irreversible work.

Do not relay signed snapshot JSON through chat. Until one-use `snapshot_ref` is
implemented, use the byte-exact programmatic loopback lane.

## 5. Exit criteria

Reconciliation PASS requires:

```text
M-001 status=active
M-001 lifecycle_state=materialized
M-001 reconcile_required=false
M-001 execution_ready=true
system_health.execution_readiness.ready=true
active CRITICAL alarms=0
```

Anything else is BLOCKED, not implicitly healthy.
