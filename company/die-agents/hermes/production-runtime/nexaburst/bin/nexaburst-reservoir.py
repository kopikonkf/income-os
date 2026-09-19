#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, os, sqlite3, uuid
from pathlib import Path

ROOT=Path('/var/lib/die/h01/nexaburst')
DB=ROOT/'state'/'nexaburst-manifestation-ledger.db'
RESERVOIR=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001/config/object-atlas-wave3-pass-42667-isolated.jsonl')
PRIORITY=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001/config/market-canary-100-wave3pass-watercolor-source.jsonl')
LANE='WC-L0'
COMPLETE={'WAITING_FOUNDER_QC','VAULT_VERIFIED'}
CLAIMABLE={'PENDING','FAILED_RETRYABLE'}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(str(DB),timeout=30)
    c.row_factory=sqlite3.Row
    c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS manifestations(
      candidate_id TEXT NOT NULL,
      lane_id TEXT NOT NULL,
      canonical_name TEXT NOT NULL,
      suitability TEXT,
      source_status TEXT,
      source_tier TEXT,
      ip_risk TEXT,
      ordinal INTEGER NOT NULL,
      priority INTEGER NOT NULL DEFAULT 1000,
      status TEXT NOT NULL DEFAULT 'PENDING',
      claim_id TEXT,
      claimed_at TEXT,
      completed_at TEXT,
      raw_job_id TEXT,
      raw_sha256 TEXT,
      workspace TEXT,
      attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT,
      updated_at TEXT NOT NULL,
      PRIMARY KEY(candidate_id,lane_id)
    );
    CREATE INDEX IF NOT EXISTS ix_manifestations_lane_status_priority
      ON manifestations(lane_id,status,priority,ordinal);
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      candidate_id TEXT NOT NULL,
      lane_id TEXT NOT NULL,
      from_status TEXT,
      to_status TEXT NOT NULL,
      claim_id TEXT,
      detail_json TEXT,
      observed_at TEXT NOT NULL
    );
    ''')
    return c

def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]

def cmd_init(args):
    res=read_jsonl(args.reservoir)
    pri=read_jsonl(args.priority) if Path(args.priority).is_file() else []
    pri_ids={str(x['candidate_id']):i for i,x in enumerate(pri,1)}
    c=connect()
    try:
        c.execute('BEGIN IMMEDIATE')
        for i,r in enumerate(res,1):
            cid=str(r['candidate_id'])
            c.execute('''
              INSERT INTO manifestations(candidate_id,lane_id,canonical_name,suitability,source_status,source_tier,ip_risk,ordinal,priority,status,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?,'PENDING',?)
              ON CONFLICT(candidate_id,lane_id) DO UPDATE SET
                canonical_name=excluded.canonical_name,
                suitability=excluded.suitability,
                source_status=excluded.source_status,
                source_tier=excluded.source_tier,
                ip_risk=excluded.ip_risk,
                ordinal=excluded.ordinal,
                priority=excluded.priority,
                updated_at=excluded.updated_at
            ''',(cid,args.lane,r['noun'],r.get('suitability'),r.get('source_status'),r.get('source_tier','pass'),r.get('ip_risk','none'),i,pri_ids.get(cid,1000),now()))
        c.commit()
        total=c.execute('select count(*) from manifestations where lane_id=?',(args.lane,)).fetchone()[0]
        p100=c.execute('select count(*) from manifestations where lane_id=? and priority<1000',(args.lane,)).fetchone()[0]
        print(json.dumps({'status':'INITIALIZED','lane_id':args.lane,'rows':total,'priority_rows':p100,'db':str(DB)}))
    except Exception:
        c.rollback();raise
    finally:c.close()

def cmd_claim(args):
    c=connect()
    try:
        c.execute('BEGIN IMMEDIATE')
        q=",".join("?" for _ in CLAIMABLE)
        params=[args.lane,*sorted(CLAIMABLE)]
        priority_clause=''
        if args.max_priority is not None:
            priority_clause=' AND priority<=?'; params.append(args.max_priority)
        row=c.execute(f'''
          SELECT * FROM manifestations
          WHERE lane_id=? AND status IN ({q}) {priority_clause}
          ORDER BY priority ASC, ordinal ASC
          LIMIT 1
        ''',tuple(params)).fetchone()
        if not row:
            done=c.execute("select count(*) from manifestations where lane_id=? and status in ('WAITING_FOUNDER_QC','VAULT_VERIFIED')",(args.lane,)).fetchone()[0]
            total=c.execute("select count(*) from manifestations where lane_id=?",(args.lane,)).fetchone()[0]
            c.commit()
            print(json.dumps({'status':'EXHAUSTED' if done==total else 'NO_CLAIMABLE','lane_id':args.lane,'complete':done,'total':total}))
            return
        claim=args.claim_id or ('NBCL-'+uuid.uuid4().hex[:16])
        ts=now()
        c.execute('''UPDATE manifestations SET status='CLAIMED',claim_id=?,claimed_at=?,attempts=attempts+1,last_error=NULL,updated_at=? WHERE candidate_id=? AND lane_id=?''',
                  (claim,ts,ts,row['candidate_id'],args.lane))
        c.execute('''INSERT INTO events(candidate_id,lane_id,from_status,to_status,claim_id,detail_json,observed_at) VALUES(?,?,?,'CLAIMED',?,?,?)''',
                  (row['candidate_id'],args.lane,row['status'],claim,json.dumps({'ordinal':row['ordinal'],'priority':row['priority']}),ts))
        c.commit()
        out=dict(row);out.update({'status':'CLAIMED','claim_id':claim,'attempts':int(row['attempts'])+1})
        print(json.dumps(out,ensure_ascii=False))
    except Exception:
        c.rollback();raise
    finally:c.close()

def cmd_mark(args):
    allowed={'PENDING','CLAIMED','RAW_DONE','V2_QUEUED','WAITING_FOUNDER_QC','VAULT_VERIFIED','FAILED_RETRYABLE','BLOCKED'}
    if args.status not in allowed: raise SystemExit('E_STATUS')
    c=connect()
    try:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('select * from manifestations where candidate_id=? and lane_id=?',(args.candidate_id,args.lane)).fetchone()
        if not row: raise RuntimeError('E_MANIFESTATION_NOT_FOUND')
        if args.claim_id and row['claim_id'] and args.claim_id!=row['claim_id']: raise RuntimeError('E_CLAIM_MISMATCH')
        ts=now(); completed=ts if args.status in COMPLETE else row['completed_at']
        c.execute('''UPDATE manifestations SET status=?,completed_at=?,raw_job_id=coalesce(?,raw_job_id),raw_sha256=coalesce(?,raw_sha256),workspace=coalesce(?,workspace),last_error=?,updated_at=? WHERE candidate_id=? AND lane_id=?''',
                  (args.status,completed,args.raw_job_id,args.raw_sha256,args.workspace,args.error,ts,args.candidate_id,args.lane))
        c.execute('''INSERT INTO events(candidate_id,lane_id,from_status,to_status,claim_id,detail_json,observed_at) VALUES(?,?,?,?,?,?,?)''',
                  (args.candidate_id,args.lane,row['status'],args.status,row['claim_id'],json.dumps({'raw_job_id':args.raw_job_id,'workspace':args.workspace,'error':args.error}),ts))
        c.commit()
        print(json.dumps({'status':'MARKED','candidate_id':args.candidate_id,'lane_id':args.lane,'to':args.status}))
    except Exception:
        c.rollback();raise
    finally:c.close()

def cmd_stats(args):
    c=connect()
    try:
        rows=dict(c.execute('select status,count(*) from manifestations where lane_id=? group by status',(args.lane,)).fetchall())
        total=sum(rows.values()); complete=sum(rows.get(x,0) for x in COMPLETE)
        first100=c.execute("select count(*) from manifestations where lane_id=? and priority<1000 and status in ('WAITING_FOUNDER_QC','VAULT_VERIFIED')",(args.lane,)).fetchone()[0]
        print(json.dumps({'lane_id':args.lane,'total':total,'complete':complete,'remaining':total-complete,'first100_complete':first100,'by_status':rows},sort_keys=True))
    finally:c.close()

def main():
    ap=argparse.ArgumentParser()
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('init');p.add_argument('--lane',default=LANE);p.add_argument('--reservoir',default=str(RESERVOIR));p.add_argument('--priority',default=str(PRIORITY));p.set_defaults(fn=cmd_init)
    p=sp.add_parser('claim');p.add_argument('--lane',default=LANE);p.add_argument('--claim-id');p.add_argument('--max-priority',type=int);p.set_defaults(fn=cmd_claim)
    p=sp.add_parser('mark');p.add_argument('--lane',default=LANE);p.add_argument('--candidate-id',required=True);p.add_argument('--claim-id');p.add_argument('--status',required=True);p.add_argument('--raw-job-id');p.add_argument('--raw-sha256');p.add_argument('--workspace');p.add_argument('--error');p.set_defaults(fn=cmd_mark)
    p=sp.add_parser('stats');p.add_argument('--lane',default=LANE);p.set_defaults(fn=cmd_stats)
    a=ap.parse_args();a.fn(a)
if __name__=='__main__':main()
