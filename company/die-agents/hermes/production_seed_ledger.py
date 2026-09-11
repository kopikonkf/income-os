#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt,hashlib,json,os,re,sqlite3
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
 CREATE TABLE IF NOT EXISTS production_seed_consumption_evidence(evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,normalized_noun TEXT NOT NULL REFERENCES production_seed_consumption(normalized_noun),seed_id TEXT,source_scope TEXT NOT NULL,source_ref TEXT NOT NULL,status TEXT NOT NULL,artifact_sha256 TEXT,observed_at TEXT NOT NULL,UNIQUE(source_scope,source_ref));
 CREATE TABLE IF NOT EXISTS production_expression_consumption(expression_fingerprint TEXT PRIMARY KEY,seed_id TEXT NOT NULL,normalized_noun TEXT NOT NULL,semantic_mode TEXT NOT NULL,normalized_commercial_expression TEXT NOT NULL,preset_id TEXT NOT NULL,preset_revision TEXT NOT NULL,first_source_scope TEXT NOT NULL,first_source_ref TEXT NOT NULL,first_seen_at TEXT NOT NULL,status TEXT NOT NULL);
 CREATE UNIQUE INDEX IF NOT EXISTS uq_expression_source ON production_expression_consumption(first_source_scope,first_source_ref);
 CREATE TABLE IF NOT EXISTS production_expression_consumption_evidence(evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,expression_fingerprint TEXT NOT NULL,source_scope TEXT NOT NULL,source_ref TEXT NOT NULL,status TEXT NOT NULL,artifact_sha256 TEXT,observed_at TEXT NOT NULL,UNIQUE(source_scope,source_ref));
 CREATE TABLE IF NOT EXISTS production_expression_quarantine(quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,candidate_fingerprint TEXT NOT NULL,existing_fingerprint TEXT NOT NULL,seed_id TEXT NOT NULL,semantic_mode TEXT NOT NULL,preset_id TEXT NOT NULL,preset_revision TEXT NOT NULL,similarity REAL NOT NULL,source_scope TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at TEXT NOT NULL,UNIQUE(source_scope,source_ref));
 CREATE TABLE IF NOT EXISTS production_expression_legacy_replay(normalized_noun TEXT PRIMARY KEY,canonical_name TEXT NOT NULL,legacy_first_seed_id TEXT,legacy_status TEXT NOT NULL,replayed_at TEXT NOT NULL,identity_scope TEXT NOT NULL);''')
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


def normalize_expression(v:str)->str:
 return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v).casefold()).split())

def expression_identity(*,seed_id:str,noun:str,semantic_mode:str,commercial_expression:str,preset_id:str,preset_revision:str)->dict[str,str]:
 sid=str(seed_id).strip();mode=str(semantic_mode).strip().upper();pid=str(preset_id).strip();prev=str(preset_revision).strip();nn=normalize_noun(noun);expr=normalize_expression(commercial_expression)
 if not all((sid,nn,mode,expr,pid,prev)):raise ValueError('E_EXPRESSION_IDENTITY_FIELD_REQUIRED')
 payload={'seed_id':sid,'normalized_noun':nn,'semantic_mode':mode,'normalized_commercial_expression':expr,'preset_id':pid,'preset_revision':prev}
 fp=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return {'expression_fingerprint':fp,**payload}

def _token_set(v:str)->set[str]:return set(normalize_expression(v).split())
def expression_similarity(a:str,b:str)->float:
 A=_token_set(a);B=_token_set(b)
 if not A and not B:return 1.0
 if not A or not B:return 0.0
 return len(A&B)/len(A|B)

def expression_consumed(ledger_path:Path,identity:dict[str,str])->bool:
 if not Path(ledger_path).is_file():return False
 c=_connect(Path(ledger_path))
 try:return c.execute('SELECT 1 FROM production_expression_consumption WHERE expression_fingerprint=? AND status IN (\'CLAIMED\',\'ACCEPTED\')',(identity['expression_fingerprint'],)).fetchone() is not None
 finally:c.close()

def claim_expression(ledger_path:Path,identity:dict[str,str],*,source_scope:str,source_ref:str,status:str='CLAIMED',artifact_sha256:str|None=None,near_duplicate_threshold:float=0.85,observed:str|None=None)->dict[str,Any]:
 if status not in {'CLAIMED','ACCEPTED'}:raise ValueError('E_EXPRESSION_STATUS')
 if not (0.0<=near_duplicate_threshold<=1.0):raise ValueError('E_NEAR_DUPLICATE_THRESHOLD')
 ts=observed or now();c=_connect(Path(ledger_path))
 try:
  c.execute('BEGIN IMMEDIATE')
  fp=identity['expression_fingerprint'];row=c.execute('SELECT * FROM production_expression_consumption WHERE expression_fingerprint=?',(fp,)).fetchone()
  if row is not None:
   c.execute('INSERT OR IGNORE INTO production_expression_consumption_evidence(expression_fingerprint,source_scope,source_ref,status,artifact_sha256,observed_at) VALUES(?,?,?,?,?,?)',(fp,source_scope,source_ref,status,artifact_sha256,ts));c.commit()
   return {'status':'ALREADY_CLAIMED','expression_fingerprint':fp,'idempotent_replay':True}
  peers=c.execute('SELECT expression_fingerprint,normalized_commercial_expression FROM production_expression_consumption WHERE seed_id=? AND semantic_mode=? AND preset_id=? AND preset_revision=? AND status IN (\'CLAIMED\',\'ACCEPTED\')',(identity['seed_id'],identity['semantic_mode'],identity['preset_id'],identity['preset_revision'])).fetchall()
  best=None
  for peer in peers:
   sim=expression_similarity(identity['normalized_commercial_expression'],peer['normalized_commercial_expression'])
   if best is None or sim>best[0]:best=(sim,str(peer['expression_fingerprint']))
  if best is not None and best[0]>=near_duplicate_threshold:
   c.execute('INSERT OR IGNORE INTO production_expression_quarantine(candidate_fingerprint,existing_fingerprint,seed_id,semantic_mode,preset_id,preset_revision,similarity,source_scope,source_ref,observed_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(fp,best[1],identity['seed_id'],identity['semantic_mode'],identity['preset_id'],identity['preset_revision'],best[0],source_scope,source_ref,ts));c.commit()
   return {'status':'QUARANTINED_NEAR_DUPLICATE','expression_fingerprint':fp,'existing_fingerprint':best[1],'similarity':round(best[0],6),'idempotent_replay':False}
  c.execute('INSERT INTO production_expression_consumption VALUES(?,?,?,?,?,?,?,?,?,?,?)',(fp,identity['seed_id'],identity['normalized_noun'],identity['semantic_mode'],identity['normalized_commercial_expression'],identity['preset_id'],identity['preset_revision'],source_scope,source_ref,ts,status))
  c.execute('INSERT OR IGNORE INTO production_expression_consumption_evidence(expression_fingerprint,source_scope,source_ref,status,artifact_sha256,observed_at) VALUES(?,?,?,?,?,?)',(fp,source_scope,source_ref,status,artifact_sha256,ts));c.commit()
  return {'status':status,'expression_fingerprint':fp,'idempotent_replay':False}
 except Exception:c.rollback();raise
 finally:c.close()

def bootstrap_expression_legacy_replay(ledger_path:Path)->dict[str,Any]:
 c=_connect(Path(ledger_path));added=0
 try:
  c.execute('BEGIN IMMEDIATE')
  rows=c.execute('SELECT normalized_noun,canonical_name,first_seed_id,status FROM production_seed_consumption ORDER BY normalized_noun').fetchall()
  for r in rows:
   before=c.total_changes
   c.execute('INSERT OR IGNORE INTO production_expression_legacy_replay(normalized_noun,canonical_name,legacy_first_seed_id,legacy_status,replayed_at,identity_scope) VALUES(?,?,?,?,?,?)',(r['normalized_noun'],r['canonical_name'],r['first_seed_id'],r['status'],now(),'LEGACY_NOUN_ONLY'))
   if c.total_changes>before:added+=1
  c.commit();return {'schema':'die.production-expression-legacy-replay.v1','status':'PASS','legacy_rows':len(rows),'added':added,'identity_scope':'LEGACY_NOUN_ONLY','blocks_new_semantic_expressions':False}
 except Exception:c.rollback();raise
 finally:c.close()


def legacy_noun_consumed(ledger_path:Path|None,noun:str)->bool:
 if ledger_path is None or not Path(ledger_path).is_file():return False
 n=normalize_noun(noun)
 c=_connect(Path(ledger_path))
 try:
  if c.execute('SELECT 1 FROM production_expression_legacy_replay WHERE normalized_noun=?',(n,)).fetchone() is not None:return True
  return c.execute('SELECT 1 FROM production_seed_consumption WHERE normalized_noun=?',(n,)).fetchone() is not None
 finally:c.close()

def expression_available(ledger_path:Path|None,identity:dict[str,str],*,legacy_baseline_compatibility:bool=False)->bool:
 if ledger_path is None or not Path(ledger_path).is_file():return True
 if expression_consumed(Path(ledger_path),identity):return False
 if legacy_baseline_compatibility and legacy_noun_consumed(Path(ledger_path),identity['normalized_noun']):return False
 return True
