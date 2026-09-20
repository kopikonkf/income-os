#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, sqlite3, unicodedata
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
DEFAULT_MAP=SESSION/'config'/'watercolor-presence-map-v2-preview.jsonl'
DEFAULT_LEDGER=Path('/var/lib/die/h01/nexaburst/state/nexaburst-manifestation-ledger.db')
COVERED_STATUSES=('RAW_DONE','WAITING_FOUNDER_QC','VAULT_VERIFIED')

def norm(s:str)->str:
    s=unicodedata.normalize('NFKC',s or '').lower().strip()
    s=re.sub(r'[-_/]+',' ',s);s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def bucket(noun:str)->str:
    n=norm(noun)
    return n[0].upper() if n and 'a'<=n[0]<='z' else 'OTHER'

def read_jsonl(path:Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def atomic_jsonl(path:Path,rows:list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_name(path.name+'.tmp')
    with t.open('w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    t.replace(path)

def sha256_path(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def representative_rows(pmap:list[dict])->dict[str,dict]:
    groups=collections.defaultdict(list)
    for x in pmap:groups[x['semantic_key']].append(x)
    reps={}
    for key,rows in groups.items():
        rep=next((x for x in rows if x['candidate_id']==x['representative_candidate_id']),None)
        reps[key]=rep or sorted(rows,key=lambda x:(x.get('ordinal',10**9),x['noun']))[0]
    return reps

def covered_keys(pmap:list[dict],ledger:Path,lane_id:str)->set[str]:
    by_cid={x['candidate_id']:x['semantic_key'] for x in pmap}
    if not ledger.is_file():return set()
    c=sqlite3.connect(str(ledger))
    try:
        marks=','.join('?' for _ in COVERED_STATUSES)
        rows=c.execute(f"select candidate_id from manifestations where lane_id=? and status in ({marks})",
                       (lane_id,*COVERED_STATUSES)).fetchall()
    except sqlite3.Error:
        return set()
    finally:c.close()
    return {by_cid[str(r[0])] for r in rows if str(r[0]) in by_cid}

def select_roundrobin(reps:dict[str,dict],covered:set[str],count:int):
    q={k:collections.deque() for k in [chr(c) for c in range(ord('A'),ord('Z')+1)]+['OTHER']}
    remaining=[r for k,r in reps.items() if k not in covered]
    remaining.sort(key=lambda x:(x.get('ordinal',10**9),norm(x['representative_noun'])))
    for row in remaining:q[bucket(row['representative_noun'])].append(row)
    selected=[];letters=[chr(c) for c in range(ord('A'),ord('Z')+1)]
    while len(selected)<count and any(q[k] for k in letters):
        for k in letters:
            if q[k] and len(selected)<count:selected.append(q[k].popleft())
    while len(selected)<count and q['OTHER']:selected.append(q['OTHER'].popleft())
    return selected,remaining

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--lane',required=True)
    ap.add_argument('--cohort-id',required=True)
    ap.add_argument('--count',type=int,default=500)
    ap.add_argument('--presence-map',type=Path,default=DEFAULT_MAP)
    ap.add_argument('--ledger',type=Path,default=DEFAULT_LEDGER)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--summary-out',type=Path)
    a=ap.parse_args()
    pmap=read_jsonl(a.presence_map);reps=representative_rows(pmap);covered=covered_keys(pmap,a.ledger,a.lane)
    selected,remaining=select_roundrobin(reps,covered,a.count)
    seen_keys=set();seen_cids=set();out=[]
    for i,row in enumerate(selected,1):
        key=row['semantic_key'];cid=row['candidate_id']
        if key in seen_keys:raise SystemExit('E_DUPLICATE_SEMANTIC_KEY')
        if cid in seen_cids:raise SystemExit('E_DUPLICATE_CANDIDATE')
        seen_keys.add(key);seen_cids.add(cid)
        out.append({
          'schema':'die.h01.nexaburst.object-cohort.v1',
          'cohort_id':a.cohort_id,'cohort_position':i,'lane_id':a.lane,
          'letter_bucket':bucket(row['representative_noun']),
          'candidate_id':cid,'noun':row['representative_noun'],'semantic_key':key,
          'source_ordinal':row.get('ordinal'),'state':'PREPARED_NOT_AUTHORIZED'
        })
    atomic_jsonl(a.out,out)
    counts=collections.Counter(x['letter_bucket'] for x in out)
    summary={
      'schema':'die.h01.nexaburst.object-cohort-summary.v1','lane_id':a.lane,'cohort_id':a.cohort_id,
      'semantic_universe':len(reps),'covered_semantic_keys':len(covered),
      'remaining_before_selection':len(remaining),'selected':len(out),
      'remaining_after_selection':max(0,len(remaining)-len(out)),
      'candidate_unique':len(seen_cids),'semantic_unique':len(seen_keys),
      'bucket_counts':dict(sorted(counts.items())),'selection':'A_Z_ROUNDROBIN',
      'presence_map_sha256':sha256_path(a.presence_map),'ledger':str(a.ledger),
      'output':str(a.out),'output_sha256':sha256_path(a.out),
      'activation':'PREPARED_NOT_AUTHORIZED'
    }
    if a.summary_out:
        a.summary_out.parent.mkdir(parents=True,exist_ok=True)
        a.summary_out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
