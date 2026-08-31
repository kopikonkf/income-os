from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'die-agents'/'hermes'/'operator-v2'

def load(name: str, path: Path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

S=load('followup_outbox_scheduler',ENGINE/'linux_scheduler_tick.py')

def configure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state=tmp_path/'die-state'
    (state/'state'/'operator-v2'/'receipt-inbox').mkdir(parents=True)
    monkeypatch.setenv('DIE_STATE_ROOT',str(state))
    monkeypatch.setenv('DIE_COMPANY_INSTANCE','DIE-LINUX')
    monkeypatch.setenv('DIE_OPERATOR_V2_SUBJECT_ID','M001-FOLLOWUP-TEST')
    return state

def outboxes(state: Path) -> list[Path]:
    return sorted((state/'state'/'operator-v2'/'outbox').glob('*.json'))

def test_followup_same_intent_materializes_distinct_claim_outbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state=configure(tmp_path,monkeypatch)
    times=iter(['2026-08-31T10:00:00Z','2026-08-31T10:31:00Z','2026-08-31T10:31:30Z'])
    monkeypatch.setattr(S,'_utcnow',lambda: next(times))

    first=S.run()
    assert first['claim_status']=='CLAIMED'
    assert first['routing_decision']=='DISPATCH'
    assert first['action_type']=='OP-CREATE-RESEARCH-CARD'
    assert len(outboxes(state))==1

    follow=S.run()
    assert follow['claim_status']=='CLAIMED'
    assert follow['routing_decision']=='FOLLOW_UP'
    assert follow['action_type']=='OP-FOLLOW-UP-CARD'
    files=outboxes(state)
    assert len(files)==2
    assert files[0].name != files[1].name
    payloads=[json.loads(x.read_text(encoding='utf-8')) for x in files]
    assert {x['claim_sequence'] for x in payloads}=={1,2}
    assert {x['action_request']['action_type'] for x in payloads}=={'OP-CREATE-RESEARCH-CARD','OP-FOLLOW-UP-CARD'}
    assert len({x['dedupe_key'] for x in payloads})==1
    assert all(x['external_side_effect_performed'] is False for x in payloads)

    duplicate=S.run()
    assert duplicate['claim_status']=='SUPPRESSED'
    assert duplicate['routing_decision']=='NO_OP_DUPLICATE'
    assert len(outboxes(state))==2

def test_missing_local_outbox_is_recovered_from_durable_claim_without_new_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state=configure(tmp_path,monkeypatch)
    times=iter(['2026-08-31T10:00:00Z','2026-08-31T10:05:00Z'])
    monkeypatch.setattr(S,'_utcnow',lambda: next(times))
    first=S.run()
    assert first['claim_status']=='CLAIMED'
    files=outboxes(state); assert len(files)==1
    files[0].unlink()
    assert outboxes(state)==[]

    recovery=S.run()
    assert recovery['claim_status']=='SUPPRESSED'
    assert recovery['routing_decision']=='NO_OP_DUPLICATE'
    assert recovery['outbox_recovered_count']==1
    files=outboxes(state); assert len(files)==1
    payload=json.loads(files[0].read_text(encoding='utf-8'))
    journal=json.loads((state/'state'/'operator-v2'/'dispatch-journal.json').read_text(encoding='utf-8'))
    assert len(journal['entries'])==1
    assert payload['claim_entry_sha256']==journal['entries'][0]['entry_sha256']
    assert payload['claim_sequence']==1

def test_legacy_dedupe_outbox_is_recognized_only_for_exact_claim_action(tmp_path: Path) -> None:
    outbox=tmp_path/'outbox'; outbox.mkdir()
    entry={
        'sequence':1,'entry_sha256':'a'*64,'recorded_at':'2026-08-31T10:00:00Z','dedupe_key':'d'*64,
        'decision':'DISPATCH','action_type':'OP-CREATE-RESEARCH-CARD','projection_stage':'SIGNALS',
        'target_principal_id':'approved-signal-collector','evidence_receipt_types':[],'next_required_receipt':'OPPORTUNITY_SIGNALS',
    }
    legacy={
        'dedupe_key':entry['dedupe_key'],
        'action_request':{'action_type':entry['action_type'],'projection_stage':entry['projection_stage'],'target_principal_id':entry['target_principal_id']}
    }
    (outbox/(entry['dedupe_key']+'.json')).write_text(json.dumps(legacy),encoding='utf-8')
    assert S._legacy_outbox_matches(outbox,entry) is True
    follow=dict(entry,sequence=2,entry_sha256='b'*64,action_type='OP-FOLLOW-UP-CARD',target_principal_id=None)
    assert S._legacy_outbox_matches(outbox,follow) is False
