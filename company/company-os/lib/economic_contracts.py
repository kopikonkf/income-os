from __future__ import annotations

import json
import sqlite3
from pathlib import Path

LEDGER_EVENT_TYPES = {
    'REVENUE_REALIZED','REVENUE_REFUND','REVENUE_CHARGEBACK',
    'COST_DIRECT_VARIABLE','COST_SHARED_VARIABLE','COST_GLOBAL_FIXED','COST_OTHER_NONVARIABLE',
    'FOUNDER_TIME','RESOURCE_USAGE','FX_RATE_OBSERVED','REVERSAL'
}
ATTRIBUTION_BASES = {'DIRECT_SOURCE_ID','DETERMINISTIC_JOIN','POLICY_ALLOCATED'}

class EconomicContractError(ValueError):
    def __init__(self, code: str, message: str = ''):
        super().__init__(f'{code}:{message}' if message else code)
        self.code = code


def validate_ledger_event(e: dict) -> dict:
    required = ['schema_version','event_id','observed_at','event_type','holding_id','source_system','idempotency_key','provenance_ref','authority_boundary']
    for k in required:
        if k not in e: raise EconomicContractError('E_LEDGER_REQUIRED', k)
    if e['schema_version'] != 'die.economic-ledger.event.v1': raise EconomicContractError('E_LEDGER_SCHEMA')
    if e['event_type'] not in LEDGER_EVENT_TYPES: raise EconomicContractError('E_LEDGER_EVENT_TYPE')
    auth=e['authority_boundary']
    for k in ['bank_integration','payment_action','spend_authorized','capital_allocation_authorized','credentials_embedded','mutable_after_append']:
        if auth.get(k) is not False: raise EconomicContractError('E_LEDGER_AUTHORITY_BOUNDARY', k)
    money_types={'REVENUE_REALIZED','REVENUE_REFUND','REVENUE_CHARGEBACK','COST_DIRECT_VARIABLE','COST_SHARED_VARIABLE','COST_GLOBAL_FIXED','COST_OTHER_NONVARIABLE'}
    if e['event_type'] in money_types:
        m=e.get('money')
        if not isinstance(m,dict) or not isinstance(m.get('amount_minor'),int) or m.get('amount_minor') < 0 or not isinstance(m.get('currency'),str):
            raise EconomicContractError('E_LEDGER_MONEY_REQUIRED')
    if e['event_type']=='FOUNDER_TIME':
        ft=e.get('founder_time')
        if not isinstance(ft,dict) or ft.get('precision') not in {'MEASURED','ESTIMATED','UNKNOWN'} or ft.get('duration_minutes') is None:
            raise EconomicContractError('E_LEDGER_FOUNDER_TIME_REQUIRED')
        if float(ft['duration_minutes']) < 0: raise EconomicContractError('E_LEDGER_NEGATIVE_DURATION')
    if e['event_type']=='RESOURCE_USAGE':
        u=e.get('resource_usage')
        if not isinstance(u,dict) or u.get('resource_class') not in {'G0','H1','H2','P1','P2','P3','P4','A1'}:
            raise EconomicContractError('E_LEDGER_RESOURCE_USAGE_REQUIRED')
    if e['event_type']=='FX_RATE_OBSERVED' and not isinstance(e.get('fx'),dict):
        raise EconomicContractError('E_LEDGER_FX_REQUIRED')
    if e['event_type']=='REVERSAL':
        if not e.get('reversal_of_event_id'): raise EconomicContractError('E_LEDGER_REVERSAL_REF_REQUIRED')
    elif e.get('reversal_of_event_id') is not None:
        raise EconomicContractError('E_LEDGER_REVERSAL_REF_FORBIDDEN')
    return e


def validate_reversal(original: dict, reversal: dict) -> None:
    validate_ledger_event(original); validate_ledger_event(reversal)
    if reversal['event_type']!='REVERSAL': raise EconomicContractError('E_NOT_REVERSAL')
    if reversal.get('reversal_of_event_id') != original.get('event_id'): raise EconomicContractError('E_REVERSAL_TARGET_MISMATCH')
    if reversal.get('holding_id') != original.get('holding_id'): raise EconomicContractError('E_REVERSAL_HOLDING_MISMATCH')
    if any(reversal.get(k) is not None for k in ['money','founder_time','resource_usage','fx']):
        raise EconomicContractError('E_REVERSAL_REFERENCE_ONLY')


def validate_attribution_claim(c: dict) -> dict:
    required=['schema_version','claim_id','revenue_event_id','holding_id','currency','amount_minor','allocations','unknown_bps','provenance_refs','authority_boundary']
    for k in required:
        if k not in c: raise EconomicContractError('E_ATTR_REQUIRED',k)
    if c['schema_version']!='die.revenue-attribution.claim.v1': raise EconomicContractError('E_ATTR_SCHEMA')
    if not isinstance(c['amount_minor'],int) or c['amount_minor'] < 0: raise EconomicContractError('E_ATTR_AMOUNT')
    auth=c['authority_boundary']
    for k in ['creates_revenue','spend_authorized','submission_authorized','model_inference_can_claim_revenue','credentials_embedded']:
        if auth.get(k) is not False: raise EconomicContractError('E_ATTR_AUTHORITY_BOUNDARY',k)
    allocs=c.get('allocations') or []
    seen=set(); total=0; policy_allocated=False
    for a in allocs:
        tid=a.get('economic_trace_id')
        if not tid: raise EconomicContractError('E_ATTR_TRACE_REQUIRED')
        if tid in seen: raise EconomicContractError('E_ATTR_DUPLICATE_TRACE',tid)
        seen.add(tid)
        bps=a.get('allocation_bps')
        if not isinstance(bps,int) or not 1 <= bps <= 10000: raise EconomicContractError('E_ATTR_BPS')
        if a.get('basis') not in ATTRIBUTION_BASES: raise EconomicContractError('E_ATTR_BASIS')
        if not a.get('evidence_refs'): raise EconomicContractError('E_ATTR_EVIDENCE_REQUIRED')
        if a.get('basis')=='POLICY_ALLOCATED': policy_allocated=True
        total += bps
    unknown=c.get('unknown_bps')
    if not isinstance(unknown,int) or not 0 <= unknown <= 10000: raise EconomicContractError('E_ATTR_UNKNOWN_BPS')
    if total + unknown != 10000: raise EconomicContractError('E_ATTR_BPS_SUM',str(total+unknown))
    if policy_allocated and not c.get('allocation_policy_id'): raise EconomicContractError('E_ATTR_POLICY_ID_REQUIRED')
    if not allocs and unknown != 10000: raise EconomicContractError('E_ATTR_EMPTY_MUST_BE_UNKNOWN')
    nodes={n.get('node_id') for n in (c.get('lineage_nodes') or [])}
    for edge in c.get('lineage_edges') or []:
        if edge.get('from_node_id') not in nodes or edge.get('to_node_id') not in nodes:
            raise EconomicContractError('E_ATTR_EDGE_NODE_MISSING')
        if not edge.get('evidence_refs'): raise EconomicContractError('E_ATTR_EDGE_EVIDENCE_REQUIRED')
    return c


def init_reference_db(db: sqlite3.Connection, sql_path: Path) -> None:
    db.executescript(sql_path.read_text(encoding='utf-8'))


def insert_reference_event(db: sqlite3.Connection, e: dict) -> None:
    validate_ledger_event(e)
    m=e.get('money') or {}; ft=e.get('founder_time') or {}; u=e.get('resource_usage') or {}; fx=e.get('fx') or {}
    db.execute('''INSERT INTO economic_events(
      event_id,schema_version,observed_at,event_type,holding_id,economic_trace_id,parent_task_id,incident_id,
      source_system,source_event_id,idempotency_key,provenance_ref,reversal_of_event_id,currency,amount_minor,
      duration_minutes,precision,founder_time_category,resource_class,usage_quantity,usage_unit,
      fx_quote_currency,fx_rate_text,fx_rate_timestamp,fx_rate_source,metadata_json
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
      e['event_id'],e['schema_version'],e['observed_at'],e['event_type'],e['holding_id'],e.get('economic_trace_id'),e.get('parent_task_id'),e.get('incident_id'),
      e['source_system'],e.get('source_event_id'),e['idempotency_key'],e['provenance_ref'],e.get('reversal_of_event_id'),m.get('currency') or fx.get('base_currency'),m.get('amount_minor'),
      ft.get('duration_minutes'),ft.get('precision'),ft.get('category'),u.get('resource_class'),u.get('usage_quantity'),u.get('usage_unit'),
      fx.get('quote_currency'),fx.get('rate_text'),fx.get('rate_timestamp'),fx.get('rate_source'),json.dumps(e.get('metadata') or {},sort_keys=True)
    ))
    db.commit()


def validate_economic_work_card(card: dict) -> dict:
    req=['schema_version','economic_work_card_id','holding_id','economic_trace_id','measurement_window','hypothesis','expected','actual','decision_conditions','authority_boundary']
    for k in req:
        if k not in card: raise EconomicContractError('E_EWC_REQUIRED',k)
    if card['schema_version']!='die.economic-work-card.v1': raise EconomicContractError('E_EWC_SCHEMA')
    auth=card['authority_boundary']
    for k in ['spend_authorized','capital_requested_is_authority','external_commitment_authorized','provider_plan_change_authorized','credentials_embedded']:
        if auth.get(k) is not False: raise EconomicContractError('E_EWC_AUTHORITY_BOUNDARY',k)
    h=card['hypothesis']
    if not h.get('evidence_refs') or not h.get('falsifier'): raise EconomicContractError('E_EWC_HYPOTHESIS_EVIDENCE')
    exp=card['expected']
    calc=exp['revenue_minor']-exp['direct_variable_cost_minor']-exp['shared_variable_cost_minor']
    if exp['contribution_profit_minor'] != calc: raise EconomicContractError('E_EWC_EXPECTED_CONTRIBUTION_MATH')
    margin=exp.get('contribution_margin_bps')
    expected_margin=None if exp['revenue_minor']==0 else round(exp['contribution_profit_minor']*10000/exp['revenue_minor'])
    if margin != expected_margin: raise EconomicContractError('E_EWC_EXPECTED_MARGIN_MATH')
    cap=exp['capital_requested_minor']; roic=exp.get('roic_bps')
    if cap==0 and roic is not None: raise EconomicContractError('E_EWC_EXPECTED_ROIC_WITH_ZERO_CAPITAL')
    if cap>0 and roic is not None:
        expected_roic=round(exp['contribution_profit_minor']*10000/cap)
        if roic != expected_roic: raise EconomicContractError('E_EWC_EXPECTED_ROIC_MATH')
    act=card['actual']; status=act['status']; refs=act.get('ledger_event_refs') or []
    numeric=['capital_observed_minor','revenue_minor','direct_variable_cost_minor','shared_variable_cost_minor','contribution_profit_minor','contribution_margin_bps','founder_active_minutes','cash_profit_minor','economic_profit_minor','payback_days','roic_bps']
    if status=='NOT_MEASURED':
        if refs or act.get('attribution_claim_refs') or any(act.get(k) is not None for k in numeric) or act.get('currency') is not None:
            raise EconomicContractError('E_EWC_NOT_MEASURED_HAS_ACTUALS')
        if act.get('completeness')!='NO': raise EconomicContractError('E_EWC_NOT_MEASURED_COMPLETENESS')
    else:
        if not refs: raise EconomicContractError('E_EWC_ACTUAL_LEDGER_EVIDENCE_REQUIRED')
        if act.get('currency') is None: raise EconomicContractError('E_EWC_ACTUAL_CURRENCY_REQUIRED')
        if status=='MEASURED' and act.get('completeness')!='YES': raise EconomicContractError('E_EWC_MEASURED_COMPLETENESS')
        if all(act.get(k) is not None for k in ['revenue_minor','direct_variable_cost_minor','shared_variable_cost_minor','contribution_profit_minor']):
            actual_calc=act['revenue_minor']-act['direct_variable_cost_minor']-act['shared_variable_cost_minor']
            if act['contribution_profit_minor'] != actual_calc: raise EconomicContractError('E_EWC_ACTUAL_CONTRIBUTION_MATH')
            expected_amargin=None if act['revenue_minor']==0 else round(act['contribution_profit_minor']*10000/act['revenue_minor'])
            if act.get('contribution_margin_bps') != expected_amargin: raise EconomicContractError('E_EWC_ACTUAL_MARGIN_MATH')
        acap=act.get('capital_observed_minor'); aroic=act.get('roic_bps'); aprofit=act.get('contribution_profit_minor')
        if acap==0 and aroic is not None: raise EconomicContractError('E_EWC_ACTUAL_ROIC_WITH_ZERO_CAPITAL')
        if acap and aroic is not None and aprofit is not None:
            expected_ar=round(aprofit*10000/acap)
            if aroic != expected_ar: raise EconomicContractError('E_EWC_ACTUAL_ROIC_MATH')
    dc=card['decision_conditions']
    if not all(dc.get(k) for k in ['kill_condition','scale_condition','hold_condition']): raise EconomicContractError('E_EWC_DECISION_CONDITION_REQUIRED')
    return card


def validate_shadow_budget_envelope(b: dict) -> dict:
    req=['schema_version','scenario_id','period','currency','observed_capital_base_minor','reserve_floor_minor','shadow_distributable_minor','envelopes','authority_boundary']
    for k in req:
        if k not in b: raise EconomicContractError('E_BUDGET_REQUIRED',k)
    if b['schema_version']!='die.budget-envelope.shadow.v1': raise EconomicContractError('E_BUDGET_SCHEMA')
    auth=b['authority_boundary']
    if auth.get('simulation_only') is not True: raise EconomicContractError('E_BUDGET_NOT_SHADOW')
    for k in ['spend_authorized','payment_action','capital_transfer','provider_plan_change','infrastructure_purchase','new_vendor_commitment','credentials_embedded']:
        if auth.get(k) is not False: raise EconomicContractError('E_BUDGET_AUTHORITY_BOUNDARY',k)
    if not b.get('capital_evidence_refs'): raise EconomicContractError('E_BUDGET_CAPITAL_EVIDENCE_REQUIRED')
    base=b['observed_capital_base_minor']; floor=b['reserve_floor_minor']; dist=b['shadow_distributable_minor']
    if floor>base: raise EconomicContractError('E_BUDGET_RESERVE_EXCEEDS_BASE')
    if dist != base-floor: raise EconomicContractError('E_BUDGET_DISTRIBUTABLE_MATH')
    envs=b['envelopes']; classes=[e['class'] for e in envs]
    required={'RESERVE','INFRASTRUCTURE','PRODUCTION','EXPERIMENT'}
    if set(classes)!=required or len(classes)!=4: raise EconomicContractError('E_BUDGET_CLASSES_EXACTLY_ONCE')
    ids=[e['envelope_id'] for e in envs]
    if len(ids)!=len(set(ids)): raise EconomicContractError('E_BUDGET_DUPLICATE_ENVELOPE_ID')
    for e in envs:
        if e.get('authorized_amount_minor') != 0: raise EconomicContractError('E_BUDGET_AUTHORIZED_AMOUNT_NONZERO')
        if e.get('simulated_amount_minor',-1)<0 or not e.get('basis'): raise EconomicContractError('E_BUDGET_ENVELOPE_INVALID')
    reserve=next(e for e in envs if e['class']=='RESERVE')
    if reserve['simulated_amount_minor'] < floor: raise EconomicContractError('E_BUDGET_RESERVE_SHORTFALL')
    allocated=sum(e['simulated_amount_minor'] for e in envs if e['class']!='RESERVE')
    if allocated>dist: raise EconomicContractError('E_BUDGET_OVERALLOCATED')
    return b

GOVERNOR_RECOMMENDATIONS = {'SCALE','HOLD','OPTIMIZE','KILL'}


def capital_priority_score(return_signal_bps: int | None, evidence_strength_bps: int, strategic_fit_bps: int, learning_value_bps: int, risk_penalty_bps: int) -> tuple[int, int]:
    dims=[evidence_strength_bps,strategic_fit_bps,learning_value_bps,risk_penalty_bps]
    if any(not isinstance(v,int) or v < 0 or v > 10000 for v in dims):
        raise EconomicContractError('E_GOVERNOR_DIMENSION_BPS')
    risk_retention=10000-risk_penalty_bps
    r=max(int(return_signal_bps or 0),0)
    score=(r*evidence_strength_bps*strategic_fit_bps*learning_value_bps*risk_retention)//(10000**4)
    return score,risk_retention


def derive_capital_recommendation(e: dict) -> str:
    required=['actual_status','completeness','kill_condition','scale_condition','hold_condition','actual_contribution_profit_minor','actual_roic_bps','expected_roic_bps','evidence_strength_bps','strategic_fit_bps','learning_value_bps','risk_penalty_bps']
    for k in required:
        if k not in e: raise EconomicContractError('E_GOVERNOR_EVALUATION_REQUIRED',k)
    if e['actual_status'] not in {'NOT_MEASURED','PARTIAL','MEASURED'}: raise EconomicContractError('E_GOVERNOR_ACTUAL_STATUS')
    if e['completeness'] not in {'YES','PARTIAL','NO'}: raise EconomicContractError('E_GOVERNOR_COMPLETENESS')
    for k in ['kill_condition','scale_condition','hold_condition']:
        if e[k] not in {'TRUE','FALSE','UNKNOWN'}: raise EconomicContractError('E_GOVERNOR_PREDICATE',k)
    if e['actual_status']!='MEASURED' or e['completeness']!='YES':
        return 'HOLD'
    profit=e.get('actual_contribution_profit_minor')
    if profit is None: return 'HOLD'
    if e['kill_condition']=='TRUE' or profit <= 0:
        return 'KILL'
    if e['scale_condition']=='TRUE':
        return 'SCALE'
    if e['hold_condition']=='TRUE':
        return 'HOLD'
    return 'OPTIMIZE'


def validate_capital_governor_shadow_decision(d: dict) -> dict:
    req=['schema_version','decision_id','economic_work_card_id','holding_id','economic_trace_id','budget_envelope_class','evaluation','recommendation','score','allocation_cap_minor','simulated_allocation_minor','evidence_refs','dimension_evidence','falsifier','basis','authority_boundary']
    for k in req:
        if k not in d: raise EconomicContractError('E_GOVERNOR_REQUIRED',k)
    if d['schema_version']!='die.capital-governor.shadow-decision.v1': raise EconomicContractError('E_GOVERNOR_SCHEMA')
    if d['budget_envelope_class'] not in {'INFRASTRUCTURE','PRODUCTION','EXPERIMENT'}: raise EconomicContractError('E_GOVERNOR_ENVELOPE_CLASS')
    auth=d['authority_boundary']
    if auth.get('shadow_only') is not True: raise EconomicContractError('E_GOVERNOR_NOT_SHADOW')
    for k in ['spend_authorized','payment_action','capital_transfer','provider_plan_change','infrastructure_purchase','new_vendor_commitment','external_submission','credentials_embedded']:
        if auth.get(k) is not False: raise EconomicContractError('E_GOVERNOR_AUTHORITY_BOUNDARY',k)
    if not d.get('evidence_refs') or not d.get('falsifier') or not d.get('basis'): raise EconomicContractError('E_GOVERNOR_EVIDENCE_REQUIRED')
    de=d.get('dimension_evidence') or {}
    for k in ['evidence_strength','strategic_fit','learning_value','risk_penalty']:
        if not de.get(k): raise EconomicContractError('E_GOVERNOR_DIMENSION_EVIDENCE',k)
    e=d['evaluation']
    expected_rec=derive_capital_recommendation(e)
    if d['recommendation'] != expected_rec: raise EconomicContractError('E_GOVERNOR_RECOMMENDATION_MISMATCH')
    return_signal=e.get('actual_roic_bps') if e.get('actual_status')=='MEASURED' and e.get('actual_roic_bps') is not None else e.get('expected_roic_bps')
    expected_score,risk_retention=capital_priority_score(return_signal,e['evidence_strength_bps'],e['strategic_fit_bps'],e['learning_value_bps'],e['risk_penalty_bps'])
    s=d['score']
    if s.get('formula_version')!='capital-governor-v1-multiplicative-bps': raise EconomicContractError('E_GOVERNOR_SCORE_VERSION')
    if s.get('return_signal_bps') != int(return_signal or 0): raise EconomicContractError('E_GOVERNOR_RETURN_SIGNAL')
    if s.get('risk_retention_bps') != risk_retention or s.get('priority_score') != expected_score: raise EconomicContractError('E_GOVERNOR_SCORE_MATH')
    cap=d['allocation_cap_minor']; alloc=d['simulated_allocation_minor']
    if not isinstance(cap,int) or cap<0 or not isinstance(alloc,int) or alloc<0: raise EconomicContractError('E_GOVERNOR_ALLOCATION_VALUE')
    if alloc>cap: raise EconomicContractError('E_GOVERNOR_ALLOCATION_OVER_CAP')
    if d['recommendation'] in {'HOLD','KILL'} and alloc!=0: raise EconomicContractError('E_GOVERNOR_NONDEPLOY_RECOMMENDATION_ALLOCATED')
    if expected_score==0 and alloc!=0: raise EconomicContractError('E_GOVERNOR_ZERO_SCORE_ALLOCATED')
    return d


def allocate_shadow_capital(decisions: list[dict], available_minor: int) -> list[dict]:
    if not isinstance(available_minor,int) or available_minor < 0: raise EconomicContractError('E_GOVERNOR_AVAILABLE_CAPITAL')
    for d in decisions: validate_capital_governor_shadow_decision(d)
    eligible=[d for d in decisions if d['recommendation'] in {'SCALE','OPTIMIZE'} and d['score']['priority_score']>0]
    eligible.sort(key=lambda x:(0 if x['recommendation']=='SCALE' else 1,-x['score']['priority_score'],x['economic_work_card_id']))
    remaining=available_minor
    allocations={d['decision_id']:0 for d in decisions}
    for d in eligible:
        amount=min(d['allocation_cap_minor'],remaining)
        allocations[d['decision_id']]=amount
        remaining-=amount
        if remaining<=0: break
    out=[]
    for d in decisions:
        nd=dict(d); nd['simulated_allocation_minor']=allocations[d['decision_id']]
        validate_capital_governor_shadow_decision(nd); out.append(nd)
    return out
