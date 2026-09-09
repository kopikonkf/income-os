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

def ewc(actual_status='NOT_MEASURED'):
    actual={'status':'NOT_MEASURED','ledger_event_refs':[],'attribution_claim_refs':[],'currency':None,'capital_observed_minor':None,'revenue_minor':None,'direct_variable_cost_minor':None,'shared_variable_cost_minor':None,'contribution_profit_minor':None,'founder_active_minutes':None,'cash_profit_minor':None,'economic_profit_minor':None,'payback_days':None,'roic_bps':None,'completeness':'NO'}
    if actual_status!='NOT_MEASURED':
        actual={'status':actual_status,'ledger_event_refs':['ECON-EVT-ACTUAL001'],'attribution_claim_refs':['ATTR-CLM-ACTUAL001'],'currency':'IDR','capital_observed_minor':5000,'revenue_minor':12000,'direct_variable_cost_minor':2000,'shared_variable_cost_minor':1000,'contribution_profit_minor':9000,'contribution_margin_bps':7500,'founder_active_minutes':10,'cash_profit_minor':7000,'economic_profit_minor':None,'payback_days':3,'roic_bps':18000,'completeness':'YES' if actual_status=='MEASURED' else 'PARTIAL'}
    return {'schema_version':'die.economic-work-card.v1','economic_work_card_id':'EWC-H03-TEST0001','holding_id':'H03','economic_trace_id':'TRACE-H03-001','parent_task_id':'TASK-1','measurement_window':{'starts_at':'2026-09-09T00:00:00Z','ends_at':'2026-09-16T00:00:00Z'},'hypothesis':{'statement':'Product can return positive contribution in one week','evidence_refs':['receipt://hypothesis'],'confidence_basis':'bounded prior evidence','falsifier':'No realized revenue by window end'},'expected':{'currency':'IDR','capital_requested_minor':5000,'revenue_minor':10000,'direct_variable_cost_minor':2000,'shared_variable_cost_minor':1000,'contribution_profit_minor':7000,'contribution_margin_bps':7000,'payback_days':5,'roic_bps':14000},'actual':actual,'decision_conditions':{'kill_condition':'Contribution profit <= 0 at measurement end','scale_condition':'Measured contribution positive and falsifier not triggered','hold_condition':'Data incomplete at window end'},'authority_boundary':{'spend_authorized':False,'capital_requested_is_authority':False,'external_commitment_authorized':False,'provider_plan_change_authorized':False,'credentials_embedded':False}}

def test_economic_work_card_forecast_math_and_authority():
    c=ewc(); assert m.validate_economic_work_card(c)['expected']['roic_bps']==14000

def test_work_card_not_measured_cannot_smuggle_actuals():
    c=ewc(); c['actual']['revenue_minor']=1
    with pytest.raises(m.EconomicContractError) as x:m.validate_economic_work_card(c)
    assert x.value.code=='E_EWC_NOT_MEASURED_HAS_ACTUALS'

def test_work_card_measured_requires_ledger_and_math():
    c=ewc('MEASURED'); assert m.validate_economic_work_card(c)['actual']['contribution_profit_minor']==9000
    c['actual']['ledger_event_refs']=[]
    with pytest.raises(m.EconomicContractError) as x:m.validate_economic_work_card(c)
    assert x.value.code=='E_EWC_ACTUAL_LEDGER_EVIDENCE_REQUIRED'

def test_work_card_expected_math_rejected():
    c=ewc(); c['expected']['contribution_profit_minor']=9999
    with pytest.raises(m.EconomicContractError) as x:m.validate_economic_work_card(c)
    assert x.value.code=='E_EWC_EXPECTED_CONTRIBUTION_MATH'

def shadow_budget():
    return {'schema_version':'die.budget-envelope.shadow.v1','scenario_id':'BUD-SHADOW-TEST0001','period':{'starts_at':'2026-09-09T00:00:00Z','ends_at':'2026-10-01T00:00:00Z'},'currency':'IDR','observed_capital_base_minor':100000,'reserve_floor_minor':40000,'shadow_distributable_minor':60000,'capital_evidence_refs':['ECON-EVT-CAPITAL001'],'envelopes':[{'envelope_id':'ENV-RESERVE-001','class':'RESERVE','holding_id':None,'simulated_amount_minor':40000,'authorized_amount_minor':0,'basis':'Explicit shadow reserve floor','work_card_refs':[]},{'envelope_id':'ENV-INFRA-001','class':'INFRASTRUCTURE','holding_id':None,'simulated_amount_minor':20000,'authorized_amount_minor':0,'basis':'Simulated capacity need','work_card_refs':['EWC-H03-TEST0001']},{'envelope_id':'ENV-PROD-001','class':'PRODUCTION','holding_id':'H01','simulated_amount_minor':30000,'authorized_amount_minor':0,'basis':'Simulated production allocation','work_card_refs':['EWC-H01-TEST0001']},{'envelope_id':'ENV-EXP-001','class':'EXPERIMENT','holding_id':'H03','simulated_amount_minor':10000,'authorized_amount_minor':0,'basis':'Bounded experiment simulation','work_card_refs':['EWC-H03-TEST0001']}],'authority_boundary':{'simulation_only':True,'spend_authorized':False,'payment_action':False,'capital_transfer':False,'provider_plan_change':False,'infrastructure_purchase':False,'new_vendor_commitment':False,'credentials_embedded':False}}

def test_shadow_budget_valid_and_zero_authority():
    b=shadow_budget(); assert m.validate_shadow_budget_envelope(b)['shadow_distributable_minor']==60000

def test_shadow_budget_rejects_overallocation():
    b=shadow_budget(); b['envelopes'][1]['simulated_amount_minor']=40000
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_budget_envelope(b)
    assert x.value.code=='E_BUDGET_OVERALLOCATED'

def test_shadow_budget_rejects_nonzero_authorized_amount():
    b=shadow_budget(); b['envelopes'][2]['authorized_amount_minor']=1
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_budget_envelope(b)
    assert x.value.code=='E_BUDGET_AUTHORIZED_AMOUNT_NONZERO'

def test_shadow_budget_rejects_reserve_shortfall():
    b=shadow_budget(); b['envelopes'][0]['simulated_amount_minor']=39999
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_budget_envelope(b)
    assert x.value.code=='E_BUDGET_RESERVE_SHORTFALL'

def test_shadow_budget_requires_capital_evidence():
    b=shadow_budget(); b['capital_evidence_refs']=[]
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_budget_envelope(b)
    assert x.value.code=='E_BUDGET_CAPITAL_EVIDENCE_REQUIRED'
