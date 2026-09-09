import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[3]
MOD=ROOT/'company/company-os/lib/economic_contracts.py'
spec=importlib.util.spec_from_file_location('econ_contracts',MOD)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
SQL=ROOT/'company/company-os/sql/economic-ledger-v1.sql'


def auth_ledger():
    return {'bank_integration':False,'payment_action':False,'spend_authorized':False,'capital_allocation_authorized':False,'credentials_embedded':False,'mutable_after_append':False}

def auth_attr():
    return {'creates_revenue':False,'spend_authorized':False,'submission_authorized':False,'model_inference_can_claim_revenue':False,'credentials_embedded':False}

def revenue(event_id='ECON-EVT-REV000001',idem='idem-rev-0001',amount=10000):
    return {'schema_version':'die.economic-ledger.event.v1','event_id':event_id,'observed_at':'2026-09-09T00:00:00Z','event_type':'REVENUE_REALIZED','holding_id':'H03','economic_trace_id':'TRACE-H03-001','parent_task_id':'H03-JOB-1','source_system':'manual-shadow-fixture','source_event_id':'sale-1','idempotency_key':idem,'provenance_ref':'receipt://sale-1','money':{'currency':'IDR','amount_minor':amount},'authority_boundary':auth_ledger()}

def test_reference_sql_is_append_only_and_idempotent():
    db=sqlite3.connect(':memory:');m.init_reference_db(db,SQL);e=revenue();m.insert_reference_event(db,e)
    with pytest.raises(sqlite3.IntegrityError):m.insert_reference_event(db,{**revenue('ECON-EVT-REV000002'), 'idempotency_key':e['idempotency_key']})
    with pytest.raises(sqlite3.DatabaseError) as x:db.execute("UPDATE economic_events SET holding_id='H99' WHERE event_id=?",(e['event_id'],))
    assert 'E_ECON_LEDGER_APPEND_ONLY_UPDATE_FORBIDDEN' in str(x.value)
    with pytest.raises(sqlite3.DatabaseError) as x:db.execute("DELETE FROM economic_events WHERE event_id=?",(e['event_id'],))
    assert 'E_ECON_LEDGER_APPEND_ONLY_DELETE_FORBIDDEN' in str(x.value)

def test_exact_reversal_is_append_not_mutation():
    original=revenue(amount=12500)
    reversal={'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-REVERSAL01','observed_at':'2026-09-09T00:01:00Z','event_type':'REVERSAL','holding_id':'H03','economic_trace_id':'TRACE-H03-001','source_system':'manual-shadow-fixture','idempotency_key':'idem-reversal-01','provenance_ref':'receipt://correction-1','reversal_of_event_id':original['event_id'],'authority_boundary':auth_ledger()}
    m.validate_reversal(original,reversal)
    db=sqlite3.connect(':memory:');m.init_reference_db(db,SQL);m.insert_reference_event(db,original);m.insert_reference_event(db,reversal)
    assert db.execute('select count(*) from economic_events').fetchone()[0]==2

def test_bad_reversal_payload_rejected():
    original=revenue(amount=12500)
    bad={'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-REVERSAL02','observed_at':'2026-09-09T00:01:00Z','event_type':'REVERSAL','holding_id':'H03','source_system':'fixture','idempotency_key':'idem-reversal-02','provenance_ref':'receipt://bad','reversal_of_event_id':original['event_id'],'money':{'currency':'IDR','amount_minor':12500},'authority_boundary':auth_ledger()}
    with pytest.raises(m.EconomicContractError) as x:m.validate_reversal(original,bad)
    assert x.value.code=='E_REVERSAL_REFERENCE_ONLY'

def test_effective_view_excludes_reversed_original():
    original=revenue(amount=12500)
    reversal={'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-REVERSAL03','observed_at':'2026-09-09T00:01:00Z','event_type':'REVERSAL','holding_id':'H03','source_system':'fixture','idempotency_key':'idem-reversal-03','provenance_ref':'receipt://reverse','reversal_of_event_id':original['event_id'],'authority_boundary':auth_ledger()}
    db=sqlite3.connect(':memory:');m.init_reference_db(db,SQL);m.insert_reference_event(db,original);m.insert_reference_event(db,reversal)
    assert db.execute('select count(*) from economic_events').fetchone()[0]==2
    assert db.execute('select count(*) from economic_events_effective').fetchone()[0]==0
def test_founder_time_unknown_not_zeroed():
    e={'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-TIME00001','observed_at':'2026-09-09T00:00:00Z','event_type':'FOUNDER_TIME','holding_id':'GLOBAL','source_system':'manual-shadow-fixture','idempotency_key':'idem-time-001','provenance_ref':'receipt://time','founder_time':{'duration_minutes':15,'precision':'UNKNOWN','category':'FOUNDER_ENGINEERING_ASSIST'},'authority_boundary':auth_ledger()}
    assert m.validate_ledger_event(e)['founder_time']['precision']=='UNKNOWN'

def test_resource_usage_requires_org001_class():
    e={'schema_version':'die.economic-ledger.event.v1','event_id':'ECON-EVT-USAGE0001','observed_at':'2026-09-09T00:00:00Z','event_type':'RESOURCE_USAGE','holding_id':'H01','source_system':'fixture','idempotency_key':'idem-usage-01','provenance_ref':'receipt://usage','resource_usage':{'resource_class':'P2','usage_quantity':35.5,'usage_unit':'cpu_second'},'authority_boundary':auth_ledger()}
    assert m.validate_ledger_event(e)['resource_usage']['resource_class']=='P2'

def claim(allocations,unknown_bps=0,policy=None):
    return {'schema_version':'die.revenue-attribution.claim.v1','claim_id':'ATTR-CLM-TEST0001','revenue_event_id':'ECON-EVT-REV000001','holding_id':'H03','currency':'IDR','amount_minor':10000,'source_sale_or_order_id':'sale-1','allocation_policy_id':policy,'allocations':allocations,'unknown_bps':unknown_bps,'provenance_refs':['receipt://sale-1'],'authority_boundary':auth_attr()}

def test_direct_attribution_is_full_10000_bps():
    c=claim([{'economic_trace_id':'TRACE-H03-001','allocation_bps':10000,'basis':'DIRECT_SOURCE_ID','evidence_refs':['order://sale-1']}])
    assert m.validate_attribution_claim(c)['unknown_bps']==0

def test_partial_attribution_preserves_unknown_residual():
    c=claim([{'economic_trace_id':'TRACE-H02-A','allocation_bps':6000,'basis':'DETERMINISTIC_JOIN','evidence_refs':['click://abc']}],unknown_bps=4000)
    assert m.validate_attribution_claim(c)['unknown_bps']==4000

def test_no_evidence_means_explicit_unknown_not_guess():
    c=claim([],unknown_bps=10000)
    assert m.validate_attribution_claim(c)['allocations']==[]

def test_bps_must_sum_exactly_10000():
    c=claim([{'economic_trace_id':'TRACE-A','allocation_bps':8000,'basis':'DIRECT_SOURCE_ID','evidence_refs':['x']}],unknown_bps=1000)
    with pytest.raises(m.EconomicContractError) as x:m.validate_attribution_claim(c)
    assert x.value.code=='E_ATTR_BPS_SUM'

def test_duplicate_trace_rejected():
    a={'economic_trace_id':'TRACE-A','allocation_bps':5000,'basis':'DIRECT_SOURCE_ID','evidence_refs':['x']}
    c=claim([a,{**a,'allocation_bps':5000}],0)
    with pytest.raises(m.EconomicContractError) as x:m.validate_attribution_claim(c)
    assert x.value.code=='E_ATTR_DUPLICATE_TRACE'

def test_policy_allocated_requires_policy_id():
    c=claim([{'economic_trace_id':'TRACE-A','allocation_bps':10000,'basis':'POLICY_ALLOCATED','evidence_refs':['policy-evidence']}],0,None)
    with pytest.raises(m.EconomicContractError) as x:m.validate_attribution_claim(c)
    assert x.value.code=='E_ATTR_POLICY_ID_REQUIRED'

def test_model_inference_cannot_claim_revenue():
    c=claim([],10000);c['authority_boundary']['model_inference_can_claim_revenue']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_attribution_claim(c)
    assert x.value.code=='E_ATTR_AUTHORITY_BOUNDARY'

def test_lineage_edge_requires_known_nodes():
    c=claim([],10000);c['lineage_nodes']=[{'node_id':'opp-1','node_type':'OPPORTUNITY','source_ref':'x'}];c['lineage_edges']=[{'from_node_id':'opp-1','to_node_id':'sale-1','relation':'CONVERTED_TO','evidence_refs':['x']}]
    with pytest.raises(m.EconomicContractError) as x:m.validate_attribution_claim(c)
    assert x.value.code=='E_ATTR_EDGE_NODE_MISSING'
