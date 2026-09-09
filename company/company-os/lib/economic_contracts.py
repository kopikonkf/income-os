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
