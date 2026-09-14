#!/usr/bin/env python3
"""Deterministic non-blocking daily noun selector for H01 standalone SVG production."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve();H01=HERE.parents[1]
sys.path.insert(0,str(H01/'lib'))
from evidence_prioritization import prioritize

DEFAULT_QUEUE=Path('/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl')
DEFAULT_RUNS=Path('/var/lib/die/h01/runs')
DEFAULT_PROVIDERS=('gemini','qwen','claude','chatgpt','manus','copilot')

def canonical_bytes(value:Any)->bytes:return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(value:Any)->str:return hashlib.sha256(canonical_bytes(value)).hexdigest()

def load_json(path:Path|None,default):
 if not path:return default
 try:return json.loads(path.read_text())
 except FileNotFoundError:return default

def load_queue(path:Path)->list[dict[str,Any]]:
 rows=[]
 with path.open(encoding='utf-8') as handle:
  for line in handle:
   if not line.strip():continue
   row=json.loads(line);source=row.get('source') or {}
   row=dict(row);row['canonical_name']=source.get('canonical_name') or row.get('canonical_name')
   if not row.get('queue_item_id') or not row.get('canonical_name'):raise ValueError('E_QUEUE_ROW')
   rows.append(row)
 return rows

def produced_ids(runs_root:Path)->set[str]:
 out=set()
 if not runs_root.exists():return out
 for receipt in runs_root.rglob('generation-complete.receipt.json'):
  try:j=json.loads(receipt.read_text())
  except Exception:continue
  if j.get('status')=='GENERATION_COMPLETE' and j.get('h01_103_status')=='PASS' and j.get('queue_item_id'):out.add(str(j['queue_item_id']))
 return out

def demand_map(value:Any)->dict[str,dict[str,Any]]:
 if isinstance(value,dict):
  if all(isinstance(v,dict) for v in value.values()):return {str(k):v for k,v in value.items()}
  value=value.get('records') or value.get('items') or []
 out={}
 for row in value if isinstance(value,list) else []:
  if isinstance(row,dict) and row.get('queue_item_id'):out[str(row['queue_item_id'])]=row
 return out

def connector_map(value:Any)->dict[str,list[dict[str,Any]]]:
 if isinstance(value,dict) and all(isinstance(v,list) for v in value.values()):return {str(k):v for k,v in value.items()}
 rows=value.get('records') or value.get('items') or [] if isinstance(value,dict) else value
 out={}
 for row in rows if isinstance(rows,list) else []:
  if isinstance(row,dict) and row.get('queue_item_id'):out.setdefault(str(row['queue_item_id']),[]).append(row)
 return out

def context_map(value:Any)->dict[str,dict[str,Any]]:
 if isinstance(value,dict) and all(isinstance(v,dict) for v in value.values()):return {str(k):v for k,v in value.items()}
 rows=value.get('records') or value.get('items') or [] if isinstance(value,dict) else value
 return {str(r['queue_item_id']):r for r in rows if isinstance(r,dict) and r.get('queue_item_id')} if isinstance(rows,list) else {}

def build_manifest(queue_rows:list[dict[str,Any]],*,produced:set[str],demand:dict[str,dict[str,Any]],connectors:dict[str,list[dict[str,Any]]],contexts:dict[str,dict[str,Any]],limit:int,providers:tuple[str,...],day_key:str)->dict[str,Any]:
 normalized=[]
 for raw in queue_rows:
  row=dict(raw);src=row.get('source') or {};row['canonical_name']=row.get('canonical_name') or src.get('canonical_name')
  if not row.get('canonical_name'):raise ValueError('E_CANONICAL_NAME:'+str(row.get('queue_item_id')))
  normalized.append(row)
 projection=prioritize(normalized,demand_records=demand,connector_evidence=connectors,produced_queue_item_ids=produced)
 source={r['queue_item_id']:r for r in normalized}
 queue_rows=normalized
 selected=[]
 for ranked in projection['remaining_ranked']:
  row=source[ranked['queue_item_id']]
  if not row.get('dispatch_eligible',True):continue
  if len(selected)>=limit:break
  position=len(selected)+1;src=row.get('source') or {};provider=providers[(position-1)%len(providers)]
  selected.append({
   'batch_position':position,'canonical_name':src.get('canonical_name') or row['canonical_name'],'queue_item_id':row['queue_item_id'],'queue_position':row.get('queue_position'),'source_candidate_id':src.get('id'),'source_tier':src.get('source_tier'),'suitability':src.get('suitability'),'idempotency_key':row.get('idempotency_key'),'planned_provider':provider,'adaptive_provider_redistribution_allowed':True,
   'selection_reason':'EVIDENCE_RANKED' if ranked.get('rank_state')=='RANKED' else 'SOURCE_ORDER_FALLBACK','priority_score':ranked.get('priority_score'),'priority_rank':ranked.get('priority_rank'),'priority_components':ranked.get('components'),'family_hypotheses':ranked.get('family_hypotheses') or [],'human_context':contexts.get(row['queue_item_id']),
  })
 if len(selected)<limit:raise ValueError(f'E_INSUFFICIENT_REMAINING_QUEUE:{len(selected)}<{limit}')
 identity={'day_key':day_key,'policy':'H01-133-V1','selected_queue_item_ids':[x['queue_item_id'] for x in selected],'produced_queue_item_ids':sorted(produced),'demand':demand,'connectors':connectors}
 ranked_count=sum(1 for x in selected if x['selection_reason']=='EVIDENCE_RANKED')
 return {'schema':'die.h01.daily-production-selector.v1','status':'FROZEN','day_key':day_key,'selection_id':'H01-DAILY-'+sha(identity)[:24].upper(),'source_queue':{'row_count':len(queue_rows),'produced_generation_complete_count':len(produced)},'evidence':{'demand_record_count':len(demand),'connector_queue_item_count':len(connectors),'human_context_count':len(contexts),'market_evidence_blocking':False,'no_evidence_policy':'SOURCE_ORDER_FALLBACK','ranking_policy':'H01-133-V1'},'selection':{'limit':limit,'ranked_selected':ranked_count,'fallback_selected':len(selected)-ranked_count,'produced_excluded_by':'GENERATION_COMPLETE_ONLY'},'provider_plan':{'cycle':list(providers),'adaptive_redistribution':True},'items':selected,'authority':{'production_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--queue',default=str(DEFAULT_QUEUE));ap.add_argument('--runs-root',default=str(DEFAULT_RUNS));ap.add_argument('--demand-records');ap.add_argument('--connector-evidence');ap.add_argument('--human-context');ap.add_argument('--limit',type=int,default=100);ap.add_argument('--provider-cycle',default=','.join(DEFAULT_PROVIDERS));ap.add_argument('--day-key',default='');ap.add_argument('--out');ns=ap.parse_args()
 providers=tuple(x.strip() for x in ns.provider_cycle.split(',') if x.strip())
 if not providers:raise SystemExit('E_PROVIDER_CYCLE')
 day_key=ns.day_key or datetime.now(timezone.utc).date().isoformat()
 queue=load_queue(Path(ns.queue));produced=produced_ids(Path(ns.runs_root));demand=demand_map(load_json(Path(ns.demand_records) if ns.demand_records else None,{}));connectors=connector_map(load_json(Path(ns.connector_evidence) if ns.connector_evidence else None,[]));contexts=context_map(load_json(Path(ns.human_context) if ns.human_context else None,[]))
 manifest=build_manifest(queue,produced=produced,demand=demand,connectors=connectors,contexts=contexts,limit=ns.limit,providers=providers,day_key=day_key)
 if ns.out:
  out=Path(ns.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','selection_id':manifest['selection_id'],'selected':len(manifest['items']),'ranked':manifest['selection']['ranked_selected'],'fallback':manifest['selection']['fallback_selected'],'produced_excluded':manifest['source_queue']['produced_generation_complete_count'],'out':ns.out},sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
