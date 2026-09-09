from __future__ import annotations

import pathlib
import sys

import pytest

ROOT=pathlib.Path(__file__).resolve().parents[3]
LIB=ROOT/'company'/'company-os'/'lib'
sys.path.insert(0,str(LIB))
import economic_admission as a  # noqa: E402


def auth():
    return {
      'bank_integration':False,'payment_action':False,'spend_authorized':False,
      'capital_allocation_authorized':False,'credentials_embedded':False,
      'mutable_after_append':False
    }


def event(holding='H03'):
    return {
      'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-H03PDF00001',
      'observed_at':'2026-09-09T09:00:00Z','event_type':'RESOURCE_USAGE',
      'holding_id':holding,'economic_trace_id':'TRACE-H03-PDF-001',
      'source_system':'h03-product-runtime','source_event_id':'build-001',
      'idempotency_key':'idem-h03-pdf-build-001','provenance_ref':'receipt://h03/build-001',
      'resource_usage':{'resource_class':'H2','usage_quantity':120,'usage_unit':'cpu_seconds'},
      'authority_boundary':auth()
    }


def test_prepare_admission_is_validated_not_committed():
    p=a.prepare_admission(event(),evidence_refs=['receipt://h03/build-001'],holding_id='H03')
    assert p['status']=='validated_not_committed'
    assert p['writer']=='die-state-manager'
    assert all(v is False for v in p['authority_boundary'].values())
    assert a.validate_admission(p) is p


def test_admission_requires_evidence():
    with pytest.raises(a.EconomicAdmissionError) as x:
        a.prepare_admission(event(),evidence_refs=[],holding_id='H03')
    assert x.value.code=='E_ECON_ADMISSION_EVIDENCE_REQUIRED'


def test_admission_requires_provenance_in_evidence_refs():
    with pytest.raises(a.EconomicAdmissionError) as x:
        a.prepare_admission(event(),evidence_refs=['receipt://other'],holding_id='H03')
    assert x.value.code=='E_ECON_ADMISSION_PROVENANCE_NOT_EVIDENCED'


def test_admission_rejects_holding_mismatch():
    with pytest.raises(a.EconomicAdmissionError) as x:
        a.prepare_admission(event('H03'),evidence_refs=['receipt://h03/build-001'],holding_id='H01')
    assert x.value.code=='E_ECON_ADMISSION_HOLDING_MISMATCH'


def test_admission_rejects_authority_widening():
    p=a.prepare_admission(event(),evidence_refs=['receipt://h03/build-001'],holding_id='H03')
    p['authority_boundary']['canonical_commit_authorized']=True
    with pytest.raises(a.EconomicAdmissionError) as x:a.validate_admission(p)
    assert x.value.code=='E_ECON_ADMISSION_AUTHORITY_WIDENING'


def test_admission_rejects_writer_or_status_mutation():
    p=a.prepare_admission(event(),evidence_refs=['receipt://h03/build-001'],holding_id='H03')
    p['writer']='mission-control'
    with pytest.raises(a.EconomicAdmissionError) as x:a.validate_admission(p)
    assert x.value.code=='E_ECON_ADMISSION_NOT_SHADOW'


def test_admission_reuses_econ002_authority_validation():
    e=event();e['authority_boundary']['spend_authorized']=True
    with pytest.raises(Exception):
        a.prepare_admission(e,evidence_refs=['receipt://h03/build-001'],holding_id='H03')


def test_admission_module_has_no_physical_writer_path():
    text=(LIB/'economic_admission.py').read_text(encoding='utf-8')
    assert 'die_event' not in text
    assert 'ECONOMICS.jsonl' not in text
    assert 'open(' not in text
    assert 'write_text' not in text
    assert 'write_bytes' not in text
