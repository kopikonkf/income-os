from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'WAKE-LNX-001-safe-linux-transport.acceptance.receipt.json'
def test_wake_lnx001_safe_transport_live_acceptance_and_release() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['WAKE-LNX-001']['status']=='DONE'
    assert tasks['WAKE-LNX-002']['status']=='READY'
    assert 'no-send canary' in tasks['WAKE-LNX-001']['acceptance']
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['status']=='DONE'
    for principal in ('executive','division01'):
        assert d['live_bind'][principal]['generation']==1
        assert d['live_bind'][principal]['browser_pid_before']==d['live_bind'][principal]['browser_pid_after']
        c=d['no_send_canary'][principal]
        assert c['composer_prefilled'] is True and c['canary_cleared'] is True
        assert c['submitted'] is False and c['output_extracted'] is False
        assert c['credential_material_accessed'] is False and c['private_backend_called'] is False
        assert d['browser_postcondition'][principal]['state']=='READY'
    assert d['no_send_canary']['executive_followup_draft_protection']=='E_COMPOSER_NOT_EMPTY'
    assert d['architecture']['autonomous_prompt_submission'] is False
    assert d['architecture']['private_backend_transport'] is False
    assert d['isolation']['mx062_pid']==200975
    assert d['isolation']['production_source_mutated'] is False
