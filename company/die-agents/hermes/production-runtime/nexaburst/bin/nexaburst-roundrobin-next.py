#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, json, re
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
PLAN=SESSION/'config'/'watercolor-rollout-plan-v1.jsonl'
DEFAULT_OUT=SESSION/'config'/'watercolor-next500-roundrobin-preview-v1.jsonl'

def norm(s:str)->str:
    return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()

def bucket(noun:str)->str:
    n=norm(noun)
    if n and 'a'<=n[0]<='z': return n[0].upper()
    return 'OTHER'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--skip',type=int,default=500,help='Already-authorized prefix to exclude')
    ap.add_argument('--count',type=int,default=500)
    ap.add_argument('--out',type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()
    rows=[json.loads(x) for x in PLAN.read_text(encoding='utf-8').splitlines() if x.strip()]
    remaining=rows[a.skip:]
    q={k:collections.deque() for k in [chr(c) for c in range(ord('A'),ord('Z')+1)]+['OTHER']}
    for row in remaining:q[bucket(str(row.get('noun') or ''))].append(row)
    selected=[]
    letters=[chr(c) for c in range(ord('A'),ord('Z')+1)]
    while len(selected)<a.count and any(q[k] for k in letters):
        for k in letters:
            if q[k] and len(selected)<a.count:selected.append(q[k].popleft())
    while len(selected)<a.count and q['OTHER']:
        selected.append(q['OTHER'].popleft())
    if len(selected)!=min(a.count,len(remaining)):
        raise SystemExit(f'E_ROUNDROBIN_COUNT:{len(selected)}')
    cids=[x['candidate_id'] for x in selected]; sk=[x['semantic_key'] for x in selected]
    if len(cids)!=len(set(cids)):raise SystemExit('E_DUPLICATE_CANDIDATE')
    if len(sk)!=len(set(sk)):raise SystemExit('E_DUPLICATE_SEMANTIC_KEY')
    out=[]
    for i,row in enumerate(selected,1):
        out.append({
          'schema':'die.h01.nexaburst.roundrobin-cohort-preview.v1',
          'cohort_position':i,
          'source_plan_index':row['plan_index'],
          'letter_bucket':bucket(str(row.get('noun') or '')),
          'candidate_id':row['candidate_id'],
          'noun':row['noun'],
          'semantic_key':row['semantic_key'],
          'lane_id':row['lane_id'],
          'state':'PREPARED_NOT_AUTHORIZED'
        })
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in out),encoding='utf-8')
    counts=collections.Counter(x['letter_bucket'] for x in out)
    print(json.dumps({'status':'PREPARED_NOT_AUTHORIZED','source_plan_rows':len(rows),'skipped_prefix':a.skip,'remaining_pool':len(remaining),'selected':len(out),'candidate_unique':len(set(cids)),'semantic_unique':len(set(sk)),'bucket_counts':dict(sorted(counts.items())),'output':str(a.out)},sort_keys=True))
if __name__=='__main__':main()
