from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'ID-LNX-002-operator-v2-linux.acceptance.receipt.json'

def test_id_lnx002_live_scheduler_acceptance_is_done_and_fail_closed() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['ID-LNX-002']['status']=='DONE'
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['status']=='DONE'
    assert d['live_runtime']['cron_mode']=='no-agent'
    assert d['live_runtime']['company_instance_id']=='DIE-LINUX'
    assert d['controlled_tick_1']['claim_status']=='CLAIMED'
    assert d['controlled_tick_1']['outbox_written'] is True
    assert d['controlled_tick_1']['network_request_performed'] is False
    assert d['controlled_tick_2']['routing_decision']=='NO_OP_DUPLICATE'
    assert d['controlled_tick_2']['claim_status']=='SUPPRESSED'
    assert d['durability']=={'outbox_count':1,'journal_entries':1,'routing_intents':1}
    assert d['scheduler_proof']['status']=='completed'
    assert d['isolation']['production_source_mutated'] is False
    assert d['isolation']['mx062_pid']==200975
