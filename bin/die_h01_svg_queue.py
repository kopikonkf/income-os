#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, tempfile
from pathlib import Path

SCHEMA='die.h01.svg-production-queue.v1'
MANIFEST_SCHEMA='die.h01.svg-production-queue.manifest.v1'
EXPECTED_COUNT=43005
DEFAULT_DB=Path('/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db')
DEFAULT_OUT=Path('/var/lib/die/h01/queues/svg-standalone-v1')
PRODUCTION={'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'}
FIELDS=('id','raw_noun_id','canonical_name','source_tier','suitability','ip_risk','wave3_status')

class QueueExportError(RuntimeError):
    pass

def canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def stable_key(candidate_id:str)->str:
    payload='\0'.join([SCHEMA,candidate_id,PRODUCTION['media'],PRODUCTION['mode'],PRODUCTION['form'],PRODUCTION['preset']])
    return hashlib.sha256(payload.encode()).hexdigest()

def open_source(path:Path):
    con=sqlite3.connect(f'file:{path}?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    return con

def read_source(path:Path):
    con=open_source(path)
    try:
        qc=con.execute('PRAGMA quick_check').fetchone()[0]
        if qc!='ok': raise QueueExportError(f'E_SOURCE_DB_INVALID:{qc}')
        rows=con.execute("""SELECT id,raw_noun_id,canonical_name,source_tier,suitability,ip_risk,wave3_status
                            FROM candidate_seeds WHERE wave3_status='eligible'
                            ORDER BY raw_noun_id ASC,id ASC""").fetchall()
    finally: con.close()
    if len(rows)!=EXPECTED_COUNT: raise QueueExportError(f'E_SOURCE_COUNT:{len(rows)} expected={EXPECTED_COUNT}')
    ids=[r[0] for r in rows]; raw=[r[1] for r in rows]; names=[str(r[2]).strip().casefold() for r in rows]
    if len(set(ids))!=len(rows): raise QueueExportError('E_DUPLICATE_CANDIDATE_ID')
    if len(set(raw))!=len(rows): raise QueueExportError('E_DUPLICATE_RAW_NOUN_ID')
    if any(not n for n in names) or len(set(names))!=len(rows): raise QueueExportError('E_CANONICAL_NAME_IDENTITY')
    return qc,rows

def build(path:Path):
    qc,rows=read_source(path)
    selection=[]; queue=[]; rights={}; feas={}
    for pos,r in enumerate(rows,1):
        src=dict(zip(FIELDS,r)); ip=str(src['ip_risk'] or '').strip().lower(); suit=str(src['suitability'] or '').strip()
        rights_gate='PASS' if ip=='none' else 'HOLD'
        feasibility_gate='PASS' if src['wave3_status']=='eligible' and suit and suit not in {'pending','blocked'} else 'HOLD'
        rights[rights_gate]=rights.get(rights_gate,0)+1; feas[feasibility_gate]=feas.get(feasibility_gate,0)+1
        selected={k:src[k] for k in FIELDS}
        selection.append(selected)
        qid=f"H01-SVGQ-{src['id']}"
        key=stable_key(str(src['id']))
        queue.append({
            'schema':SCHEMA,'queue_position':pos,'queue_item_id':qid,'idempotency_key':key,
            'source':selected,'production':dict(PRODUCTION),
            'gates':{'rights':rights_gate,'feasibility':feasibility_gate},
            'dispatch_eligible':rights_gate=='PASS' and feasibility_gate=='PASS'
        })
    source_sha=sha_bytes(('\n'.join(canon(x) for x in selection)+'\n').encode())
    queue_bytes=('\n'.join(canon(x) for x in queue)+'\n').encode()
    queue_sha=sha_bytes(queue_bytes)
    manifest={
        'schema':MANIFEST_SCHEMA,'source_db':str(path),'source_query':"candidate_seeds.wave3_status='eligible'",
        'source_quick_check':qc,'source_row_count':len(rows),'source_selection_sha256':source_sha,
        'ordering':['raw_noun_id ASC','id ASC'],'identity':'queue_item_id = H01-SVGQ-<candidate_seed_id>',
        'idempotency_key_contract':'sha256(schema,candidate_seed_id,media,mode,form,preset)',
        'production':dict(PRODUCTION),'queue_row_count':len(queue),'queue_sha256':queue_sha,
        'rights_gate_counts':rights,'feasibility_gate_counts':feas,
        'dispatch_eligible_count':sum(1 for x in queue if x['dispatch_eligible']),
        'atlas_mutation':False,
    }
    return queue_bytes,(canon(manifest)+'\n').encode(),manifest

def atomic_write(path:Path,data:bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def export(db:Path,out:Path):
    qbytes,mbytes,manifest=build(db)
    qpath=out/'queue.jsonl'; mpath=out/'manifest.json'
    if qpath.exists() or mpath.exists():
        if not (qpath.exists() and mpath.exists()): raise QueueExportError('E_PARTIAL_EXISTING_QUEUE')
        if qpath.read_bytes()==qbytes and mpath.read_bytes()==mbytes:
            return 'UNCHANGED',manifest
        raise QueueExportError('E_EXISTING_QUEUE_CONFLICT')
    out.mkdir(parents=True,exist_ok=True)
    atomic_write(qpath,qbytes); atomic_write(mpath,mbytes)
    return 'CREATED',manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--db',type=Path,default=DEFAULT_DB); ap.add_argument('--out',type=Path,default=DEFAULT_OUT)
    ap.add_argument('--verify-only',action='store_true')
    a=ap.parse_args()
    try:
        if a.verify_only:
            _,_,m=build(a.db); status='VERIFIED'
        else: status,m=export(a.db,a.out)
        print(json.dumps({'status':status,'output':str(a.out),'manifest':m},sort_keys=True))
    except QueueExportError as e:
        print(json.dumps({'status':'ERROR','error':str(e)},sort_keys=True)); raise SystemExit(2)
if __name__=='__main__': main()
