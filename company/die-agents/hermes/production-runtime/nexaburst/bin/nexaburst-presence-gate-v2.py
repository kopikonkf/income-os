#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, sqlite3, unicodedata
from pathlib import Path

SESSION=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
ROOT=Path('/var/lib/die/h01/nexaburst')
RESERVOIR=SESSION/'config'/'object-atlas-wave3-pass-42667-isolated.jsonl'
ATLAS_DB=Path('/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db')
MANIFEST_DB=ROOT/'state'/'nexaburst-manifestation-ledger.db'
V2_DONE=ROOT/'state'/'v2-done.jsonl'
RECEIPTS=ROOT/'receipts'
LANE='WC-L0'
MAP_OUT=SESSION/'config'/'watercolor-presence-map-v2-preview.jsonl'
PLAN_OUT=SESSION/'config'/'watercolor-rollout-plan-v2-preview.jsonl'
SUMMARY_OUT=ROOT/'state'/'watercolor-rollout-plan-summary-v2-preview.json'

def norm(s:str)->str:
    s=unicodedata.normalize('NFKC',s or '').lower().strip()
    s=re.sub(r'[-_/]+',' ',s); s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def compact(s:str)->str:return norm(s).replace(' ','')

def read_jsonl(path:Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def write_jsonl(path:Path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    tmp.replace(path)

def load_atlas(rows):
    c=sqlite3.connect(str(ATLAS_DB));c.row_factory=sqlite3.Row;out={}
    try:
        for i in range(0,len(rows),700):
            ids=[str(x['candidate_id']) for x in rows[i:i+700]];q=','.join('?' for _ in ids)
            for r in c.execute(f'select id,canonical_name,wordnet_synsets,aliases from candidate_seeds where id in ({q})',ids):out[str(r['id'])]=dict(r)
    finally:c.close()
    return out

def synset_heads(syn):
    out=[]
    for x in syn:
        m=re.match(r'^(.*)\.n\.\d+$',str(x))
        if m:out.append(compact(m.group(1).replace('_',' ')))
    return set(out)

def build_map():
    rows=read_jsonl(RESERVOIR);atlas=load_atlas(rows);groups=collections.defaultdict(list)
    for ordinal,row in enumerate(rows,1):
        a=atlas.get(str(row['candidate_id']),{})
        try:syn=tuple(sorted(set(json.loads(a.get('wordnet_synsets') or '[]'))))
        except Exception:syn=()
        if syn:
            key='wcsem2:'+hashlib.sha256(('\n'.join(syn)).encode()).hexdigest()[:20]
        else:
            key='wclex2:'+norm(str(row['noun']))
        groups[key].append((ordinal,row,norm(str(row['noun'])),syn))
    out=[]
    for key,members in groups.items():
        syn=members[0][3];heads=synset_heads(syn)
        exact=[m for m in members if compact(m[2]) in heads]
        pool=exact or members
        rep=sorted(pool,key=lambda m:(len(m[2]),m[2],m[0]))[0]
        for ordinal,row,noun_norm,_ in members:
            out.append({
              'schema':'die.h01.nexaburst.presence-map.v2-preview',
              'candidate_id':str(row['candidate_id']),'noun':str(row['noun']),'noun_normalized':noun_norm,
              'semantic_key':key,'representative_candidate_id':str(rep[1]['candidate_id']),
              'representative_noun':str(rep[1]['noun']),'family_size':len(members),'ordinal':ordinal,
              'wordnet_synsets':list(syn),
              'dedup_policy':'EXACT_WORDNET_SENSE_SET_ELSE_NORMALIZED_LEXICAL_SURFACE'
            })
    out.sort(key=lambda x:x['ordinal']);return out

def challenge_nouns():
    accepted=set();assets=set()
    if V2_DONE.is_file():
        for line in V2_DONE.read_text().splitlines():
            try:
                x=json.loads(line);aid=str(x.get('asset_id') or '')
                if aid.startswith('NBVC-WC-') and x.get('status')=='WAITING_FOUNDER_QC':assets.add(aid)
            except:pass
    for p in RECEIPTS.glob('NBVC-WC-*.json') if RECEIPTS.is_dir() else []:
        try:
            x=json.loads(p.read_text())
            if x.get('asset_id') in assets and x.get('noun'):accepted.add(norm(str(x['noun'])))
        except:pass
    return accepted

def manifested_candidates():
    if not MANIFEST_DB.is_file():return set()
    c=sqlite3.connect(str(MANIFEST_DB))
    try:
        # Any acquired/accepted manifestation is already a presence for future planning.
        return {str(r[0]) for r in c.execute(
          "select candidate_id from manifestations where lane_id=? and status in ('RAW_DONE','WAITING_FOUNDER_QC','VAULT_VERIFIED')",(LANE,)
        )}
    finally:c.close()

def build_plan(cohort_size=500,checkpoint_size=100):
    pmap=build_map();keyrows=collections.defaultdict(list);byid={}
    for x in pmap:keyrows[x['semantic_key']].append(x);byid[x['candidate_id']]=x
    challenge=challenge_nouns();covered={x['semantic_key'] for x in pmap if x['noun_normalized'] in challenge}
    manifested=manifested_candidates();covered|={byid[c]['semantic_key'] for c in manifested if c in byid}
    reps=[]
    for key,rows in keyrows.items():
        if key in covered:continue
        rep=next((x for x in rows if x['candidate_id']==x['representative_candidate_id']),rows[0]);reps.append(rep)
    reps.sort(key=lambda x:x['ordinal'])
    plan=[]
    for i,row in enumerate(reps,1):
        cohort=((i-1)//cohort_size)+1;pos=((i-1)%cohort_size)+1;ck=((pos-1)//checkpoint_size)+1
        plan.append({'schema':'die.h01.nexaburst.rollout-plan.v2-preview','plan_index':i,'cohort_id':f'WC2-C{cohort:04d}',
          'cohort_position':pos,'checkpoint_id':f'WC2-C{cohort:04d}-P{ck:02d}','checkpoint_position':((pos-1)%checkpoint_size)+1,
          'candidate_id':row['candidate_id'],'noun':row['noun'],'semantic_key':row['semantic_key'],'representative_noun':row['representative_noun'],
          'lane_id':LANE,'state':'PREVIEW_NOT_AUTHORIZED'})
    summary={'schema':'die.h01.nexaburst.rollout-plan-summary.v2-preview','source_candidates':len(pmap),
      'semantic_presence_keys':len(keyrows),'dedup_rows_avoided':len(pmap)-len(keyrows),'covered_presence_keys':len(covered),
      'manifested_candidates_observed':len(manifested),'remaining_generation_keys':len(plan),'cohort_size':cohort_size,
      'checkpoint_size':checkpoint_size,'cohorts':(len(plan)+cohort_size-1)//cohort_size,
      'activation_allowed':False,'dedup_policy':'exact WordNet synset-set; lexical fallback only when synset absent',
      'note':'PREVIEW ONLY. Recompute after current authorized cohort reaches its boundary before activation.'}
    return pmap,plan,summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
    pmap,plan,summary=build_plan()
    if a.write:
        write_jsonl(MAP_OUT,pmap);write_jsonl(PLAN_OUT,plan);SUMMARY_OUT.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
