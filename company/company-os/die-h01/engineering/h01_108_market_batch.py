#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SCHEMA='die.h01.h01-108-market-batch.v1'
EVERGREEN='book|chair|lamp|clock|cup|bottle|pen|pencil|scissors|key|lock|hammer|screwdriver|keyboard|umbrella|shoe|shirt|dress|watch|toothbrush|mirror|soap|towel|bucket|broom|mop|vacuum cleaner|box|envelope|clipboard|apple|orange|lemon|strawberry|banana|bread|building|airplane|phone|wallet|suitcase|briefcase|refrigerator|oven|blender|flashlight|compass|globe|stapler|mouse|drill|pliers|paintbrush|shovel|sunflower|rose|fish|turtle|stethoscope|robot'.split('|')
MOMENTUM='capacitor|breadboard|ice cube|cactus|microphone|ladder|zebra|bacteria|toilet|moon|flower|tree|car|cloud|coffee|dog|cat|pizza|rabbit|camera|balloon|butterfly|brain|bicycle|shopping bag|shopping cart|headphones|backpack|notebook|houseplant'.split('|')
SEASONAL='snowman|reindeer|stocking|ornament|snowflake|sleigh|holly|mistletoe|candy cane|firework'.split('|')
PROVIDER_CYCLE=['gemini','qwen','claude','chatgpt','manus','copilot','gemini','qwen','claude','gemini','qwen','claude','chatgpt','manus','copilot','gemini','qwen','claude','gemini','qwen','claude','chatgpt','manus','copilot','gemini']
TREND_GROWTH={'capacitor':102,'ice cube':13,'coffee':16,'rabbit':22,'breadboard':98,'zebra':63,'toilet':42,'microphone':249,'bacteria':121,'cactus':263,'car':283,'ladder':92,'moon':1329,'apple':155}

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def load_queue(path:Path):
    by={}
    raw=path.read_bytes()
    for line in raw.splitlines():
        if not line.strip():continue
        j=json.loads(line); by[j['source']['canonical_name'].strip().lower()]=j
    return by,sha_bytes(raw)

def score(noun:str,bucket:str):
    if bucket=='SEASONAL_Q4':
        parts={'cross_market_recurrence':32,'current_search_momentum':25,'competition_opportunity':12,'commercial_reuse':13,'portfolio_diversity':5}
        evidence=['SHUTTERSTOCK_SEASONAL_20260912','VECTEEZY_POPULAR_SVG_20260912','VECTEEZY_GIFTBOX_20260912','123RF_POPULAR_YEARLY_20260912']
    elif bucket=='MOMENTUM':
        g=TREND_GROWTH.get(noun)
        parts={'cross_market_recurrence':28 if noun in {'cactus','coffee','rabbit','tree','flower','car','cat','dog','butterfly','brain','bicycle','cloud'} else 23,'current_search_momentum':25 if g and g>=200 else 21 if g and g>=90 else 16 if g is not None else 12,'competition_opportunity':15,'commercial_reuse':13,'portfolio_diversity':5}
        evidence=['SHUTTERSTOCK_TRENDS_20260912','123RF_POPULAR_YEARLY_20260912'] + (['VECTEEZY_POPULAR_SVG_20260912'] if noun in {'flower','tree'} else [])
    else:
        parts={'cross_market_recurrence':27,'current_search_momentum':6,'competition_opportunity':13,'commercial_reuse':15,'portfolio_diversity':5}
        evidence=['123RF_POPULAR_YEARLY_20260912']
        if noun=='apple': evidence.insert(0,'SHUTTERSTOCK_TRENDS_20260912'); parts['current_search_momentum']=21
    return sum(parts.values()),parts,evidence

def build(queue:Path,evidence_path:Path):
    by,qsha=load_queue(queue); evidence=json.loads(evidence_path.read_text()); selected=[]; names=[]
    for bucket,items in [('EVERGREEN',EVERGREEN),('MOMENTUM',MOMENTUM),('SEASONAL_Q4',SEASONAL)]:
        for noun in items:
            if noun not in by: raise SystemExit(f'E_NOUN_NOT_IN_QUEUE:{noun}')
            q=by[noun]
            if not q.get('dispatch_eligible') or q.get('gates')!={'feasibility':'PASS','rights':'PASS'}: raise SystemExit(f'E_NOUN_NOT_ELIGIBLE:{noun}')
            if noun in names: raise SystemExit(f'E_DUPLICATE:{noun}')
            names.append(noun); sc,parts,refs=score(noun,bucket); pos=len(selected)+1; provider=PROVIDER_CYCLE[(pos-1)%len(PROVIDER_CYCLE)]
            selected.append({'batch_position':pos,'bucket':bucket,'canonical_name':noun,'queue_item_id':q['queue_item_id'],'queue_position':q['queue_position'],'source_candidate_id':q['source']['id'],'source_tier':q['source']['source_tier'],'suitability':q['source']['suitability'],'idempotency_key':q['idempotency_key'],'market_score':sc,'score_components':parts,'market_evidence_refs':refs,'planned_provider':provider,'adaptive_provider_redistribution_allowed':True})
    assert len(selected)==100 and len(set(names))==100
    counts={b:sum(1 for x in selected if x['bucket']==b) for b in ['EVERGREEN','MOMENTUM','SEASONAL_Q4']}
    providers={p:sum(1 for x in selected if x['planned_provider']==p) for p in set(PROVIDER_CYCLE)}
    return {'schema':SCHEMA,'task_id':'H01-108','status':'FROZEN','queue':{'path':str(queue),'sha256':qsha,'source_rows':43005},'market_evidence':{'path':str(evidence_path),'schema':evidence['schema'],'observed_at':evidence['observed_at']},'selection_policy':{'bucket_counts':counts,'hard_gates':['H01-101 dispatch_eligible=true','feasibility=PASS','rights=PASS','unique canonical noun','standalone VECTOR/VECTOR_OBJECT/SINGLE/CLEAN_STOCK_VECTOR_V1'],'scoring':evidence['scoring']},'provider_plan':{'planned_counts':providers,'cycle':PROVIDER_CYCLE,'cooldown_seconds_default':180,'adaptive_redistribution':True,'excluded':['grok','duckai'],'qwen_completion_policy':'LONG_PROGRESS_AWARE_WAIT_PLUS_LATE_COMPLETION_RECHECK'},'items':selected,'authority':{'founder_approved_h01_108_start':True,'submission_authorized':False,'publication_authorized':False,'spend_authorized':False}}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--queue',default='/var/lib/die/h01/queues/svg-standalone-v1/queue.jsonl'); ap.add_argument('--evidence',required=True); ap.add_argument('--out',required=True); ns=ap.parse_args(); out=build(Path(ns.queue),Path(ns.evidence)); p=Path(ns.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':'PASS','items':len(out['items']),'buckets':out['selection_policy']['bucket_counts'],'providers':out['provider_plan']['planned_counts'],'sha256':sha_bytes(p.read_bytes())},sort_keys=True))
if __name__=='__main__':main()
