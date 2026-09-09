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

def governor_auth():
    return {'shadow_only':True,'spend_authorized':False,'payment_action':False,'capital_transfer':False,'provider_plan_change':False,'infrastructure_purchase':False,'new_vendor_commitment':False,'external_submission':False,'credentials_embedded':False}

def gov_decision(card='EWC-H03-GOV00001', status='MEASURED', completeness='YES', profit=9000, actual_roic=18000, expected_roic=14000, kill='FALSE', scale='TRUE', hold='FALSE', evidence=9000, strategic=9000, learning=8000, risk=2000, rec=None, cap=5000, klass='PRODUCTION'):
    e={'actual_status':status,'completeness':completeness,'kill_condition':kill,'scale_condition':scale,'hold_condition':hold,'actual_contribution_profit_minor':profit,'actual_roic_bps':actual_roic,'expected_roic_bps':expected_roic,'evidence_strength_bps':evidence,'strategic_fit_bps':strategic,'learning_value_bps':learning,'risk_penalty_bps':risk}
    recommendation=rec or m.derive_capital_recommendation(e)
    return_signal=actual_roic if status=='MEASURED' and actual_roic is not None else expected_roic
    score,ret=m.capital_priority_score(return_signal,evidence,strategic,learning,risk)
    return {'schema_version':'die.capital-governor.shadow-decision.v1','decision_id':'CAP-SHADOW-'+card.replace('EWC-',''),'economic_work_card_id':card,'holding_id':'H03','economic_trace_id':'TRACE-'+card,'budget_envelope_class':klass,'evaluation':e,'recommendation':recommendation,'score':{'return_signal_bps':int(return_signal or 0),'risk_retention_bps':ret,'priority_score':score,'formula_version':'capital-governor-v1-multiplicative-bps'},'allocation_cap_minor':cap,'simulated_allocation_minor':0,'evidence_refs':['ledger://observed','attr://claim'],'dimension_evidence':{'evidence_strength':['ledger://complete'],'strategic_fit':['strategy://fit'],'learning_value':['experiment://lesson'],'risk_penalty':['risk://assessment']},'falsifier':'Contribution economics fail at measurement window','basis':'Shadow recommendation from measured unit economics','authority_boundary':governor_auth()}

def test_governor_complete_positive_scale():
    d=gov_decision(); assert d['recommendation']=='SCALE'; assert m.validate_capital_governor_shadow_decision(d)['score']['priority_score']>0

def test_governor_incomplete_evidence_holds_even_if_expected_good():
    d=gov_decision(status='PARTIAL',completeness='PARTIAL',profit=None,actual_roic=None,scale='TRUE')
    assert d['recommendation']=='HOLD'; m.validate_capital_governor_shadow_decision(d)

def test_governor_complete_nonpositive_kills():
    d=gov_decision(profit=0,actual_roic=0,scale='FALSE')
    assert d['recommendation']=='KILL'; m.validate_capital_governor_shadow_decision(d)

def test_governor_positive_without_scale_or_hold_optimizes():
    d=gov_decision(scale='FALSE',hold='FALSE')
    assert d['recommendation']=='OPTIMIZE'; m.validate_capital_governor_shadow_decision(d)

def test_governor_score_cannot_override_recommendation_lattice():
    d=gov_decision(status='PARTIAL',completeness='PARTIAL',profit=None,actual_roic=None,scale='TRUE',rec='SCALE')
    with pytest.raises(m.EconomicContractError) as x:m.validate_capital_governor_shadow_decision(d)
    assert x.value.code=='E_GOVERNOR_RECOMMENDATION_MISMATCH'

def test_governor_rejects_score_tampering():
    d=gov_decision(); d['score']['priority_score']+=1
    with pytest.raises(m.EconomicContractError) as x:m.validate_capital_governor_shadow_decision(d)
    assert x.value.code=='E_GOVERNOR_SCORE_MATH'

def test_governor_rejects_authority_widening():
    d=gov_decision(); d['authority_boundary']['spend_authorized']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_capital_governor_shadow_decision(d)
    assert x.value.code=='E_GOVERNOR_AUTHORITY_BOUNDARY'

def test_shadow_allocator_scale_before_optimize_and_never_hold_kill():
    scale=gov_decision(card='EWC-H03-SCALE001',scale='TRUE',cap=5000)
    optimize=gov_decision(card='EWC-H03-OPT00001',scale='FALSE',hold='FALSE',cap=5000,evidence=10000,strategic=10000,learning=10000,risk=0)
    hold=gov_decision(card='EWC-H03-HOLD0001',status='PARTIAL',completeness='PARTIAL',profit=None,actual_roic=None,cap=5000)
    kill=gov_decision(card='EWC-H03-KILL0001',profit=-100,actual_roic=-100,scale='FALSE',cap=5000)
    out=m.allocate_shadow_capital([optimize,hold,kill,scale],7000)
    by={d['recommendation']:d['simulated_allocation_minor'] for d in out}
    assert by['SCALE']==5000 and by['OPTIMIZE']==2000 and by['HOLD']==0 and by['KILL']==0

def test_shadow_allocator_respects_available_and_caps():
    a=gov_decision(card='EWC-H03-A0000001',cap=3000)
    b=gov_decision(card='EWC-H03-B0000001',cap=4000)
    out=m.allocate_shadow_capital([a,b],5000)
    assert sum(x['simulated_allocation_minor'] for x in out)==5000
    assert all(x['simulated_allocation_minor']<=x['allocation_cap_minor'] for x in out)

def test_zero_score_never_allocated():
    d=gov_decision(card='EWC-H03-ZERO0001',evidence=0,cap=5000)
    out=m.allocate_shadow_capital([d],5000)
    assert out[0]['simulated_allocation_minor']==0

def reinv_auth():
    return {'shadow_only':True,'money_moved':False,'spend_authorized':False,'tax_payment_authorized':False,'provider_plan_change':False,'infrastructure_purchase':False,'capital_transfer':False,'new_vendor_commitment':False,'credentials_embedded':False}

def reinvestment_waterfall(realized=100000,tax=10000,reserve=20000,retained=30000,complete='YES',status='READY_FOR_SHADOW_ALLOCATION',pool=40000,allocs=None,infra=None):
    return {'schema_version':'die.reinvestment-waterfall.shadow.v1','waterfall_id':'REINV-SHADOW-TEST0001','period':{'starts_at':'2026-09-01T00:00:00Z','ends_at':'2026-10-01T00:00:00Z'},'currency':'IDR','profit_basis':{'basis':'CASH_OPERATING_PROFIT','realized_profit_minor':realized,'completeness':complete},'set_asides':{'tax_liability_minor':tax,'reserve_topup_minor':reserve,'retained_earnings_minor':retained,'tax_basis_ref':None if tax is None else 'policy://tax-shadow','reserve_basis_ref':'policy://reserve-floor','retained_earnings_basis_ref':'policy://retained'},'reinvestment_pool_minor':pool,'governor_decision_refs':['CAP-SHADOW-H03-INFRA01','CAP-SHADOW-H01-PROD001'],'simulated_reinvestment_allocations':allocs or [],'infrastructure_scaling_recommendations':infra or [],'evidence_refs':['ledger://cash-operating-profit'],'status':status,'authority_boundary':reinv_auth()}

def test_reinvestment_waterfall_math_and_shadow_authority():
    w=reinvestment_waterfall(); assert m.validate_reinvestment_waterfall(w)['reinvestment_pool_minor']==40000

def test_reinvestment_unknown_tax_holds_zero_pool():
    w=reinvestment_waterfall(tax=None,status='HOLD_INCOMPLETE_EVIDENCE',pool=0)
    assert m.validate_reinvestment_waterfall(w)['status']=='HOLD_INCOMPLETE_EVIDENCE'

def test_reinvestment_incomplete_profit_holds_zero_pool():
    w=reinvestment_waterfall(complete='PARTIAL',status='HOLD_INCOMPLETE_EVIDENCE',pool=0)
    m.validate_reinvestment_waterfall(w)

def test_reinvestment_nonpositive_profit_has_zero_pool():
    w=reinvestment_waterfall(realized=0,status='NO_POSITIVE_PROFIT_TO_REINVEST',pool=0)
    m.validate_reinvestment_waterfall(w)

def test_reinvestment_rejects_overallocation():
    w=reinvestment_waterfall(allocs=[{'decision_id':'CAP-SHADOW-H01-PROD001','class':'PRODUCTION','holding_id':'H01','simulated_amount_minor':40001}])
    with pytest.raises(m.EconomicContractError) as x:m.validate_reinvestment_waterfall(w)
    assert x.value.code=='E_REINV_OVERALLOCATED'

def test_reinvestment_rejects_live_authority():
    w=reinvestment_waterfall(); w['authority_boundary']['money_moved']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_reinvestment_waterfall(w)
    assert x.value.code=='E_REINV_AUTHORITY_BOUNDARY'

def test_reinvestment_infra_recommendation_is_non_live():
    infra=[{'decision_id':'CAP-SHADOW-H03-INFRA01','recommendation':'SCALE','simulated_amount_minor':10000,'evidence_refs':['capacity://queue-pressure','econ://positive'],'live_change_authorized':False}]
    w=reinvestment_waterfall(infra=infra); m.validate_reinvestment_waterfall(w)

def pilot_plan():
    return {'schema_version':'die.economic-shadow-pilot.v1','pilot_id':'PILOT-H01-H03-E0-001','mode':'READ_ONLY_SHADOW','flows':[{'holding_id':'H01','flow_id':'H01-L0-ISOLATED-ASSET-LINEAGE-V1','lineage':['OPPORTUNITY_SEED','BLUEPRINT','PRODUCTION_JOB','PRODUCT_ASSET','PACKAGE_LISTING','ORDER_SALE','REVENUE_EVENT'],'measurement_requirements':['production-cost','resource-usage','founder-time','listing-sale-revenue-when-observed','attribution-completeness'],'evidence_refs':['canon://factory-asset','canon://production-runtime'],'live_revenue_assumed':False},{'holding_id':'H03','flow_id':'H03-KNOWLEDGE-PRODUCT-DIRECT-SALE-V1','lineage':['OPPORTUNITY','PRODUCT_HYPOTHESIS','KNOWLEDGE_PRODUCT','LISTING_PAGE','ORDER_SALE','REVENUE_EVENT'],'measurement_requirements':['build-cost','founder-time','product-lineage-readiness','order-revenue-only-when-observed'],'evidence_refs':['canon://econ003-h03-mapping'],'live_revenue_assumed':False}],'evidence_window_gate':{'gate_id':'SUFFICIENT_SHADOW_EVIDENCE_WINDOW','satisfied':False,'requirements':['H01 closed measurement window with required completeness','H03 closed measurement window with required completeness or explicit UNPROVEN revenue','Founder-time observed','cash-cost observed','no material unknown treated as zero','shadow recommendations compared with outcomes']},'authority_boundary':{'read_only':True,'live_ingestion':False,'spend_authorized':False,'external_submission':False,'payment_action':False,'provider_plan_change':False,'credential_mutation':False}}

def test_pilot_plan_exact_h01_h03_and_gate_not_satisfied():
    p=pilot_plan(); assert m.validate_shadow_pilot_plan(p)['evidence_window_gate']['satisfied'] is False

def test_pilot_plan_h02_is_not_in_v1_pilot():
    p=pilot_plan(); p['flows'][1]['holding_id']='H02'
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_pilot_plan(p)
    assert x.value.code=='E_PILOT_EXACT_H01_H03_ORDER'

def test_pilot_plan_cannot_assume_live_revenue():
    p=pilot_plan(); p['flows'][1]['live_revenue_assumed']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_pilot_plan(p)
    assert x.value.code=='E_PILOT_LIVE_REVENUE_ASSUMED'

def test_pilot_plan_cannot_prematurely_open_e1_gate():
    p=pilot_plan(); p['evidence_window_gate']['satisfied']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_pilot_plan(p)
    assert x.value.code=='E_PILOT_GATE_PREMATURE'

def test_shadow_observations_validate_from_canon_files():
    import json
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    for name in ['ECON-009A_H01_SHADOW_OBSERVATION_V1.json','ECON-009B_H03_SHADOW_OBSERVATION_V1.json']:
        o=json.load(open(base/'observations'/name,encoding='utf-8'))
        m.validate_shadow_observation(o)

def test_shadow_observation_cannot_close_without_ewc():
    import json
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    o=json.load(open(base/'observations'/'ECON-009A_H01_SHADOW_OBSERVATION_V1.json',encoding='utf-8'))
    o['closed_measurement_window']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_observation(o)
    assert x.value.code=='E_OBS_CLOSED_WITHOUT_EWC'

def test_evidence_window_current_gate_is_not_satisfied():
    import json
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    e=json.load(open(base/'observations'/'ECON-009C_SHADOW_EVIDENCE_WINDOW_EVALUATION_V1.json',encoding='utf-8'))
    m.validate_shadow_evidence_window_evaluation(e)
    assert e['gate_satisfied'] is False
    assert 'H01_CLOSED_MEASUREMENT_WINDOW' in e['blocking_requirements']
    assert 'H03_CLOSED_MEASUREMENT_WINDOW' in e['blocking_requirements']

def test_evidence_window_cannot_claim_pass_with_failed_requirements():
    import json
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    e=json.load(open(base/'observations'/'ECON-009C_SHADOW_EVIDENCE_WINDOW_EVALUATION_V1.json',encoding='utf-8'))
    e['gate_satisfied']=True
    with pytest.raises(m.EconomicContractError) as x:m.validate_shadow_evidence_window_evaluation(e)
    assert x.value.code=='E_GATE_BOOLEAN_MISMATCH'
