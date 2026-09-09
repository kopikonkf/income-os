#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt,json,os,re,sqlite3
from pathlib import Path
from typing import Any
DEFAULT_LEDGER=Path('/var/lib/die/state/production-runtime/production_seed_ledger.db')
DEFAULT_FA124=Path('/var/lib/die/state/fa124-cartoon-watercolor-100-r1/FA124-E4-final.json')

def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def normalize_noun(v:str)->str:return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v).casefold()).split())
def _connect(p:Path):
 p.parent.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(str(p),timeout=30);c.row_factory=sqlite3.Row
 try:os.chmod(p,0o660)
 except PermissionError:pass
 c.executescript('''PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
 CREATE TABLE IF NOT EXISTS production_seed_consumption(normalized_noun TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,first_seed_id TEXT,first_source_scope TEXT NOT NULL,first_source_ref TEXT NOT NULL,first_seen_at TEXT NOT NULL,status TEXT NOT NULL);
 CREATE UNIQUE INDEX IF NOT EXISTS uq_consumption_seed_id ON production_seed_consumption(first_seed_id) WHERE first_seed_id IS NOT NULL;
 CREATE TABLE IF NOT EXISTS production_seed_consumption_evidence(evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,normalized_noun TEXT NOT NULL REFERENCES production_seed_consumption(normalized_noun),seed_id TEXT,source_scope TEXT NOT NULL,source_ref TEXT NOT NULL,status TEXT NOT NULL,artifact_sha256 TEXT,observed_at TEXT NOT NULL,UNIQUE(source_scope,source_ref));''')
 return c
def _record(c,*,seed_id,name,scope,ref,status,sha=None,observed=None,identity_seed_id=True):
 n=normalize_noun(name)
 if not n:return False
 ts=observed or now();row=c.execute('SELECT normalized_noun FROM production_seed_consumption WHERE normalized_noun=?',(n,)).fetchone()
 if row is None:c.execute('INSERT INTO production_seed_consumption VALUES(?,?,?,?,?,?,?)',(n,str(name),seed_id if identity_seed_id else None,scope,ref,ts,status))
 c.execute('INSERT OR IGNORE INTO production_seed_consumption_evidence(normalized_noun,seed_id,source_scope,source_ref,status,artifact_sha256,observed_at) VALUES(?,?,?,?,?,?,?)',(n,seed_id,scope,ref,status,sha,ts));return True

def _workspace_seed(w:Path)->tuple[str|None,str|None]:
 for rel in ('seed-selection.json','blueprint.json','qa/blueprint.json'):
  p=w/rel
  if not p.is_file():continue
  try:d=json.loads(p.read_text());seed=d.get('seed') or {}
  except Exception:continue
  sid=seed.get('id');name=seed.get('canonical_name')
  if sid and name:return str(sid),str(name)
 p=w/'PROGRESS.md'
 if p.is_file():
  m=re.search(r'^- Seed:\s*(SEED-\d{6})\s*\(([^)]+)\)',p.read_text(errors='ignore'),re.M)
  if m:return m.group(1),m.group(2).strip()
 return None,None

def bootstrap_seed_ledger(workspaces:Path,*,ledger_path:Path=DEFAULT_LEDGER,fa124_e4:Path=DEFAULT_FA124)->dict[str,Any]:
 c=_connect(ledger_path);added=0
 try:
  c.execute('BEGIN IMMEDIATE')
  if workspaces.is_dir():
   for w in sorted(x for x in workspaces.iterdir() if x.is_dir()):
    sid,name=_workspace_seed(w)
    if name and _record(c,seed_id=sid,name=name,scope='PRODUCTION_WORKSPACE',ref=w.name,status='CLAIMED'):added+=1
  if fa124_e4.is_file():
   try:e=json.loads(fa124_e4.read_text())
   except Exception:e={}
   for r in e.get('technical_qa',[]):
    qa=r.get('technical_qa') or {}
    if r.get('status')!='SUCCEEDED' or qa.get('result')!='PASS':continue
    if _record(c,seed_id=r.get('seed_id'),name=r.get('seed_noun') or r.get('job_id'),scope='FA124_ACCEPTED',ref=str(r.get('job_id')),status='ACCEPTED',sha=qa.get('sha256'),identity_seed_id=False):added+=1
  c.commit()
  counts=dict(c.execute('SELECT source_scope,count(*) FROM production_seed_consumption_evidence GROUP BY source_scope').fetchall())
  return {'schema':'die.production-seed-ledger-bootstrap.v1','status':'PASS','consumed_nouns':c.execute('SELECT count(*) FROM production_seed_consumption').fetchone()[0],'evidence_rows':c.execute('SELECT count(*) FROM production_seed_consumption_evidence').fetchone()[0],'evidence_by_scope':counts}
 except Exception:c.rollback();raise
 finally:c.close()
def claim_workspace_seed(ledger_path:Path,selection:dict[str,Any],workspace_id:str)->dict[str,Any]:
 s=selection.get('seed') or {};name=s.get('canonical_name');sid=s.get('id')
 c=_connect(ledger_path)
 try:
  c.execute('BEGIN IMMEDIATE');_record(c,seed_id=sid,name=name,scope='PRODUCTION_WORKSPACE',ref=workspace_id,status='CLAIMED');c.commit();return {'status':'CLAIMED','seed_id':sid,'normalized_noun':normalize_noun(name),'workspace_id':workspace_id}
 except Exception:c.rollback();raise
 finally:c.close()
def consumed(ledger_path:Path|None)->tuple[set[str],set[str]]:
 if ledger_path is None or not Path(ledger_path).is_file():return set(),set()
 c=sqlite3.connect(str(ledger_path))
 try:return ({str(r[0]) for r in c.execute('SELECT first_seed_id FROM production_seed_consumption WHERE first_seed_id IS NOT NULL')},{str(r[0]) for r in c.execute('SELECT normalized_noun FROM production_seed_consumption')})
 finally:c.close()
