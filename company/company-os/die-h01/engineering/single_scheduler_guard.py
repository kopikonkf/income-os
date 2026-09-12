from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

class GuardError(ValueError):
    pass

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise GuardError(msg)

def evaluate(proof: dict[str,Any], gateway: dict[str,Any], supervisor: dict[str,Any]) -> dict[str,Any]:
    require(proof.get('schema')=='die.h01.single-scheduler-proof.v1','E_PROOF_SCHEMA')
    cp=proof['control_plane']; require(cp['business_scheduler']=='die-control/Mission Control','E_SCHEDULER_OWNER')
    f=cp['canonical_feeder']; require(f['enabled'] is True and f['deterministic'] is True,'E_FEEDER_NOT_DETERMINISTIC')
    require(int(f['max_cards_per_run'])==1,'E_FEEDER_BUDGET')
    require(f['h01_016_dedupe_reason']=='SOURCE_NODE_ALREADY_INGESTED','E_FEEDER_DEDUPE')
    db=cp['live_db']
    for k in ('source_key_duplicates','task_id_duplicates','active_source_node_duplicates','active_task_multi_lease','active_task_duplicate_open_owner_attempts'):
        require(int(db[k])==0,f'E_DB_DUPLICATE:{k}')
    # Historical imported lineage may be imperfect, but must be terminal and outside active dispatch authority.
    for row in db.get('historical_nonactive_anomalies',[]):
        require(row.get('task_status') in {'DONE','FAILED','CANCELLED'},'E_HISTORICAL_ANOMALY_ACTIVE')
        require(row.get('active_lease') is False,'E_HISTORICAL_ANOMALY_LEASE')
    lin=proof['legacy_linux']
    require(lin['die_business_cron_entries']==0,'E_LINUX_CRON_COMPETITOR')
    require(lin['enabled_business_timers']==[],'E_LINUX_TIMER_ENABLED')
    require(lin['active_business_timers']==[],'E_LINUX_TIMER_ACTIVE')
    require(lin['hermes_scheduled_jobs']==0,'E_LINUX_HERMES_SCHEDULER')
    win=proof['legacy_windows']
    require(win['default_profile_kanban_dispatch_in_gateway'] is False,'E_WIN_DEFAULT_KANBAN_DISPATCH')
    require(win['income_operator_kanban_dispatch_in_gateway'] is False,'E_WIN_INCOME_KANBAN_DISPATCH')
    require(win['proactive_operator_job_status']=='paused','E_WIN_PROACTIVE_OPERATOR')
    require(win['legacy_ready_card_runs']==0,'E_WIN_LEGACY_CARD_EXECUTION')
    require(win['business_scheduler_scheduled_tasks']==[],'E_WIN_TASK_SCHEDULER_COMPETITOR')
    require(supervisor['authority']['supervisor_is_scheduler'] is False,'E_SUPERVISOR_SCHEDULER')
    require(supervisor['execution_model']['background_poll_loop'] is False,'E_SUPERVISOR_POLL_LOOP')
    require(supervisor['execution_model']['queue_feeder'] is False,'E_SUPERVISOR_QUEUE_FEEDER')
    require(gateway['gateway_is_scheduler'] is False,'E_GATEWAY_SCHEDULER')
    d=gateway['durability']
    require(d['dispatch_store_before_ack'] is True,'E_DISPATCH_STORE_BEFORE_ACK')
    require(d['duplicate_same_dispatch_same_digest']=='RETURN_EXISTING_EXECUTION','E_REPLAY_SAME')
    require(d['duplicate_same_dispatch_different_digest']=='E_IDEMPOTENCY_CONFLICT','E_REPLAY_CONFLICT')
    require(d['terminal_result_immutable'] is True and d['terminal_result_store_before_send'] is True,'E_TERMINAL_MUTABLE')
    require(d['wan_loss_starts_new_execution'] is False,'E_WAN_DUPLICATE')
    tests=proof['anti_duplicate_tests']; require(tests['mission_control_targeted']=='35/35 PASS','E_MC_TEST_PROOF')
    return {
        'schema':'die.h01.single-scheduler-decision.v1','task_id':'H01-016','status':'PASS',
        'business_scheduler':'die-control/Mission Control','competing_business_schedulers':0,
        'active_duplicate_dispatch_paths':0,'legacy_scheduler_quarantine':'PASS','gateway_replay_safety':'PASS'
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--proof',required=True); ap.add_argument('--gateway',required=True); ap.add_argument('--supervisor',required=True); ns=ap.parse_args()
    result=evaluate(json.loads(Path(ns.proof).read_text()),json.loads(Path(ns.gateway).read_text()),json.loads(Path(ns.supervisor).read_text()))
    print(json.dumps(result,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
