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
FIRST100_COMPLETE=ROOT/'state'/'FIRST100_COMPLETE.json'
MAP_OUT=SESSION/'config'/'watercolor-presence-map-v1.jsonl'
PLAN_OUT=SESSION/'config'/'watercolor-rollout-plan-v1.jsonl'
SUMMARY_OUT=ROOT/'state'/'watercolor-rollout-plan-summary-v1.json'
LANE='WC-L0'

def norm(s:str)->str:
    s=unicodedata.normalize('NFKC',s or '').lower().strip()
    s=re.sub(r'[-_/]+',' ',s)
    s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def compact(s:str)->str:
    return norm(s).replace(' ','')

IRREGULAR_PLURALS={
    'child':'children','person':'people','man':'men','woman':'women',
    'mouse':'mice','louse':'lice','goose':'geese','tooth':'teeth',
    'foot':'feet','ox':'oxen','die':'dice'
}

def plural_forms(base:str)->set[str]:
    b=compact(base)
    out={b,b+'s',b+'es'}
    if b in IRREGULAR_PLURALS: out.add(IRREGULAR_PLURALS[b])
    if b.endswith('y') and len(b)>1 and b[-2] not in 'aeiou': out.add(b[:-1]+'ies')
    if b.endswith('f'): out.add(b[:-1]+'ves')
    if b.endswith('fe'): out.add(b[:-2]+'ves')
    if b.endswith('us') and len(b)>2: out.add(b[:-2]+'i')
    if b.endswith('is') and len(b)>2: out.add(b[:-2]+'es')
    if b.endswith('um') and len(b)>2: out.add(b[:-2]+'a')
    if b.endswith('on') and len(b)>2: out.add(b[:-2]+'a')
    if b.endswith('ix') or b.endswith('ex'): out.add(b[:-2]+'ices')
    if b.endswith('o'): out.add(b+'es')
    return out

def synset_heads(synsets:tuple[str,...])->set[str]:
    out=set()
    for syn in synsets:
        m=re.match(r'^(.*)\.n\.\d+$',str(syn))
        if m: out.add(compact(m.group(1).replace('_',' ')))
    return out

def morphological_head(surface:str,synsets:tuple[str,...])->str|None:
    c=compact(surface)
    for head in sorted(synset_heads(synsets)):
        if c in plural_forms(head): return head
    return None

def simple_variants(s:str)->set[str]:
    out={s}
    if len(s)>3 and s.endswith('ies'): out.add(s[:-3]+'y')
    if len(s)>3 and s.endswith('es'):
        out.add(s[:-2])
        out.add(s[:-1])
    if len(s)>2 and s.endswith('s') and not s.endswith('ss'): out.add(s[:-1])
    return out

def inflection_related(a:str,b:str)->bool:
    return b in simple_variants(a) or a in simple_variants(b)

def read_jsonl(path:Path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def write_jsonl(path:Path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    tmp.replace(path)

def load_atlas(rows):
    c=sqlite3.connect(str(ATLAS_DB)); c.row_factory=sqlite3.Row
    out={}
    try:
        for start in range(0,len(rows),700):
            ids=[str(x['candidate_id']) for x in rows[start:start+700]]
            q=','.join('?' for _ in ids)
            for r in c.execute(f'select id,canonical_name,wordnet_synsets,aliases from candidate_seeds where id in ({q})',ids):
                out[str(r['id'])]=dict(r)
    finally:c.close()
    return out

def build_presence_map():
    rows=read_jsonl(RESERVOIR)
    atlas=load_atlas(rows)
    by_syn=collections.defaultdict(list)
    for ordinal,row in enumerate(rows,1):
        a=atlas.get(str(row['candidate_id']),{})
        try:syn=tuple(sorted(set(json.loads(a.get('wordnet_synsets') or '[]'))))
        except Exception:syn=()
        by_syn[syn].append((ordinal,row,norm(str(row['noun']))))

    result=[]
    for syn,members in by_syn.items():
        parent=list(range(len(members)))
        def find(x):
            while parent[x]!=x:
                parent[x]=parent[parent[x]]; x=parent[x]
            return x
        def union(a,b):
            a,b=find(a),find(b)
            if a!=b: parent[b]=a
        heads=[morphological_head(m[2],syn) for m in members]
        for i in range(len(members)):
            for j in range(i+1,len(members)):
                ni,nj=members[i][2],members[j][2]
                same_head=heads[i] is not None and heads[i]==heads[j]
                if ni==nj or same_head or inflection_related(ni,nj): union(i,j)
        comps=collections.defaultdict(list)
        for i in range(len(members)): comps[find(i)].append(i)
        syn_hash=hashlib.sha256(('\n'.join(syn)).encode()).hexdigest()[:16] if syn else 'nosyn'
        for inds in comps.values():
            # Prefer shortest normalized surface: normally singular/common form.
            rep_i=sorted(inds,key=lambda i:(len(members[i][2]),members[i][2],members[i][0]))[0]
            rep_norm=members[rep_i][2]
            key=f'wcsem:{syn_hash}:{rep_norm}'
            rep_row=members[rep_i][1]
            for i in inds:
                ordinal,row,noun_norm=members[i]
                result.append({
                  'schema':'die.h01.nexaburst.presence-map.v1',
                  'candidate_id':str(row['candidate_id']),
                  'noun':str(row['noun']),
                  'noun_normalized':noun_norm,
                  'semantic_key':key,
                  'representative_candidate_id':str(rep_row['candidate_id']),
                  'representative_noun':str(rep_row['noun']),
                  'family_size':len(inds),
                  'ordinal':ordinal,
                  'wordnet_synsets':list(syn),
                  'dedup_policy':'NORMALIZED_SURFACE_PLUS_WORDNET_HEAD_MORPHOLOGY_WITH_IDENTICAL_SENSE_SET'
                })
    result.sort(key=lambda x:x['ordinal'])
    return result

def challenge_nouns():
    accepted=set()
    assets=set()
    if V2_DONE.is_file():
        for line in V2_DONE.read_text(encoding='utf-8').splitlines():
            try:
                x=json.loads(line)
                aid=str(x.get('asset_id') or '')
                if aid.startswith('NBVC-WC-') and x.get('status')=='WAITING_FOUNDER_QC': assets.add(aid)
            except Exception:pass
    if assets and RECEIPTS.is_dir():
        for p in RECEIPTS.glob('NBVC-WC-*.json'):
            try:
                x=json.loads(p.read_text(encoding='utf-8'))
                if x.get('asset_id') in assets and x.get('noun'): accepted.add(norm(str(x['noun'])))
            except Exception:pass
    return accepted

def accepted_candidates():
    if not MANIFEST_DB.is_file(): return set()
    c=sqlite3.connect(str(MANIFEST_DB))
    try:
        return {str(r[0]) for r in c.execute(
          "select candidate_id from manifestations where lane_id=? and status in ('WAITING_FOUNDER_QC','VAULT_VERIFIED')",(LANE,)
        )}
    finally:c.close()

def build_plan(cohort_size:int=500,checkpoint_size:int=100):
    pmap=build_presence_map()
    key_rows=collections.defaultdict(list)
    by_candidate={}
    for x in pmap:
        key_rows[x['semantic_key']].append(x)
        by_candidate[x['candidate_id']]=x

    challenge=challenge_nouns()
    challenge_keys={x['semantic_key'] for x in pmap if x['noun_normalized'] in challenge}
    accepted=accepted_candidates()
    accepted_keys={by_candidate[c]['semantic_key'] for c in accepted if c in by_candidate}
    covered=challenge_keys|accepted_keys

    selected=[]
    for key,rows in key_rows.items():
        if key in covered: continue
        rep=next((x for x in rows if x['candidate_id']==x['representative_candidate_id']),None)
        if rep is None: rep=sorted(rows,key=lambda x:x['ordinal'])[0]
        selected.append(rep)
    selected.sort(key=lambda x:x['ordinal'])

    plan=[]
    for i,row in enumerate(selected,1):
        cohort=((i-1)//cohort_size)+1
        pos=((i-1)%cohort_size)+1
        checkpoint=((pos-1)//checkpoint_size)+1
        plan.append({
          'schema':'die.h01.nexaburst.rollout-plan.v1',
          'plan_index':i,
          'cohort_id':f'WC-C{cohort:04d}',
          'cohort_position':pos,
          'checkpoint_id':f'WC-C{cohort:04d}-P{checkpoint:02d}',
          'checkpoint_position':((pos-1)%checkpoint_size)+1,
          'candidate_id':row['candidate_id'],
          'noun':row['noun'],
          'semantic_key':row['semantic_key'],
          'representative_noun':row['representative_noun'],
          'lane_id':LANE,
          'state':'PLANNED_NOT_AUTHORIZED'
        })
    summary={
      'schema':'die.h01.nexaburst.rollout-plan-summary.v1',
      'lane_id':LANE,
      'source_candidates':len(pmap),
      'semantic_presence_keys':len(key_rows),
      'dedup_rows_avoided':len(pmap)-len(key_rows),
      'challenge_presence_keys':len(challenge_keys),
      'accepted_manifestation_candidates':len(accepted),
      'accepted_manifestation_keys':len(accepted_keys),
      'covered_presence_keys':len(covered),
      'remaining_generation_keys':len(selected),
      'cohort_size':cohort_size,
      'checkpoint_size':checkpoint_size,
      'cohorts':(len(selected)+cohort_size-1)//cohort_size,
      'first100_complete_marker':FIRST100_COMPLETE.is_file(),
      'activation_allowed':False,
      'activation_requirement':'FIRST100_COMPLETE + explicit FULL_ROLLOUT_ARMED.json Founder authorization',
      'dedup_policy':'conservative: normalized punctuation/case + WordNet-head morphology/irregular plurals only when WordNet sense-set is identical; no broad synonym collapsing'
    }
    return pmap,plan,summary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cohort-size',type=int,default=500)
    ap.add_argument('--checkpoint-size',type=int,default=100)
    ap.add_argument('--write',action='store_true')
    args=ap.parse_args()
    pmap,plan,summary=build_plan(args.cohort_size,args.checkpoint_size)
    if args.write:
        write_jsonl(MAP_OUT,pmap); write_jsonl(PLAN_OUT,plan)
        SUMMARY_OUT.parent.mkdir(parents=True,exist_ok=True)
        SUMMARY_OUT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()