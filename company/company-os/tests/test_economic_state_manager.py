from __future__ import annotations

import pathlib
import sys

import pytest

ROOT=pathlib.Path(__file__).resolve().parents[3]
BIN=ROOT/'bin'
sys.path.insert(0,str(BIN))
import die_event  # noqa: E402


def auth():
    return {
      'bank_integration':False,'payment_action':False,'spend_authorized':False,
      'capital_allocation_authorized':False,'credentials_embedded':False,
      'mutable_after_append':False
    }


def revenue(event_id='ECON-EVT-H03SALE0001', idem='idem-h03-sale-0001', amount=12000):
    return {
      'schema_version':'die.economic-ledger.event.v1','event_id':event_id,
      'observed_at':'2026-09-09T09:00:00Z','event_type':'REVENUE_REALIZED',
      'holding_id':'H03','economic_trace_id':'TRACE-H03-PDF-001',
      'source_system':'h03-shadow-fixture','source_event_id':'sale-fixture-001',
      'idempotency_key':idem,'provenance_ref':'receipt://h03/sale-fixture-001',
      'money':{'currency':'IDR','amount_minor':amount},'authority_boundary':auth()
    }


def reversal(original):
    return {
      'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-H03REV00001',
      'observed_at':'2026-09-09T09:05:00Z','event_type':'REVERSAL',
      'holding_id':original['holding_id'],'economic_trace_id':original.get('economic_trace_id'),
      'source_system':'h03-shadow-fixture','source_event_id':'correction-fixture-001',
      'idempotency_key':'idem-h03-reversal-0001','provenance_ref':'receipt://h03/correction-001',
      'reversal_of_event_id':original['event_id'],'authority_boundary':auth()
    }


def test_state_manager_commits_economic_event_and_exact_replay(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    e=revenue()
    first=die_event.commit_economic_event(e)
    second=die_event.commit_economic_event(e)
    assert first['replayed'] is False and second['replayed'] is True
    assert first['committed_by']=='die-state-manager'
    rows=die_event._json_lines(tmp_path/'ECONOMICS.jsonl')
    assert rows==[e]


def test_state_manager_rejects_wrong_writer(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    with pytest.raises(ValueError,match='E_ECON_WRITER_ID_FORBIDDEN'):
        die_event.commit_economic_event(revenue(),writer_id='mission-control')
    assert not (tmp_path/'ECONOMICS.jsonl').exists()


def test_state_manager_rejects_idempotency_conflict(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    die_event.commit_economic_event(revenue())
    changed=revenue(amount=99999)
    with pytest.raises(ValueError,match='E_ECON_IDEMPOTENCY_CONFLICT'):
        die_event.commit_economic_event(changed)
    assert len(die_event._json_lines(tmp_path/'ECONOMICS.jsonl'))==1


def test_state_manager_rejects_event_id_conflict(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    die_event.commit_economic_event(revenue())
    changed=revenue(idem='idem-h03-sale-0002',amount=13000)
    with pytest.raises(ValueError,match='E_ECON_EVENT_ID_CONFLICT'):
        die_event.commit_economic_event(changed)


def test_state_manager_reversal_is_append_only(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    original=revenue(); rev=reversal(original)
    die_event.commit_economic_event(original)
    result=die_event.commit_economic_event(rev)
    assert result['replayed'] is False
    rows=die_event._json_lines(tmp_path/'ECONOMICS.jsonl')
    assert [x['event_type'] for x in rows]==['REVENUE_REALIZED','REVERSAL']
    assert rows[0]==original


def test_state_manager_rejects_missing_reversal_target(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    with pytest.raises(ValueError,match='E_ECON_REVERSAL_TARGET_NOT_FOUND'):
        die_event.commit_economic_event(reversal(revenue()))


def test_state_manager_rejects_second_reversal(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    original=revenue(); rev=reversal(original)
    die_event.commit_economic_event(original);die_event.commit_economic_event(rev)
    second=dict(rev);second['event_id']='ECON-EVT-H03REV00002';second['idempotency_key']='idem-h03-reversal-0002';second['source_event_id']='correction-fixture-002'
    with pytest.raises(ValueError,match='E_ECON_ALREADY_REVERSED'):
        die_event.commit_economic_event(second)


def test_state_manager_rejects_authority_widening(monkeypatch,tmp_path):
    monkeypatch.setattr(die_event,'STATE',tmp_path)
    e=revenue();e['authority_boundary']['spend_authorized']=True
    with pytest.raises(Exception):
        die_event.commit_economic_event(e)
    assert not (tmp_path/'ECONOMICS.jsonl').exists()
