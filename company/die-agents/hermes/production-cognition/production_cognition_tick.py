#!/usr/bin/env python3
"""Deterministic production cognition handoff: active card -> Division01 -> Executive -> fixed Blueprint."""
from __future__ import annotations
import argparse, datetime as dt, fcntl, hashlib, json, os, re, shutil, sqlite3, subprocess, sys
from pathlib import Path
from typing import Any
import jsonschema

HERE=Path(__file__).resolve().parent
DIE_HOME=HERE.parents[3]
BP_SCHEMA=HERE/'die.production.family-blueprint.v1.schema.json'
REVIEW_SCHEMA=HERE/'die.production.family-blueprint-review.v1.schema.json'
RECEIPT_SCHEMA=HERE/'die.production.cognition-receipt.v1.schema.json'
VALIDATOR=HERE/'validate_production_cognition.py'
DEFAULT_WORKSPACES=Path('/var/lib/die/workspaces')
DEFAULT_DB=Path('/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db')
DEFAULT_STATE_ROOT=Path('/var/lib/die/state/production-cognition')
DIV='die-lnx-division-001'; EXEC='die-lnx-executive-001'
MAX_SEMANTIC_ATTEMPTS=3; MAX_REVISIONS=2
FIELD_RE=re.compile(r'^-\s*([^:]+):\s*(.*)$'); SEED_RE=re.compile(r'\b(SEED-\d{6})\b(?:\s*\(([^)]+)\))?')

def now()->str:return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def parse_time(s:str)->dt.datetime:return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def canonical_bytes(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def csha(v:Any)->str:return sha_bytes(canonical_bytes(v))
def atomic_json(p:Path,v:Any): p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+f'.tmp-{os.getpid()}'); t.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); os.replace(t,p)
def read_json(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text(encoding='utf-8')); 
 if not isinstance(v,dict):raise RuntimeError(f'E_JSON_OBJECT:{p}')
 return v

def progress_fields(p:Path)->dict[str,str]:
 out={}
 for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
  m=FIELD_RE.match(line.strip())
  if m:out[m.group(1).strip().lower()]=m.group(2).strip()
 return out

def active_blueprint_card(root:Path)->tuple[Path,dict[str,str]]|None:
 rows=[]
 if not root.is_dir():return None
 for w in sorted(x for x in root.iterdir() if x.is_dir()):
  p=w/'PROGRESS.md'
  if not p.is_file():continue
  f=progress_fields(p)
  if f.get('state','').upper()=='BLUEPRINT_REQUIRED': rows.append((f.get('started','9999'),w.name,w,f))
 if not rows:return None
 rows.sort(key=lambda x:(x[0],x[1])); return rows[0][2],rows[0][3]

def update_progress(workspace:Path, *, state:str, blueprint_status:str, next_action:str):
 p=workspace/'PROGRESS.md'; lines=p.read_text(encoding='utf-8').splitlines(); updates={'state':state,'blueprint status':blueprint_status,'next action':next_action}; seen=set(); out=[]
 for line in lines:
  m=FIELD_RE.match(line.strip())
  if m and m.group(1).strip().lower() in updates:
   k=m.group(1).strip().lower(); label={'state':'State','blueprint status':'Blueprint status','next action':'Next action'}[k]; out.append(f'- {label}: {updates[k]}'); seen.add(k)
  else: out.append(line)
 for k in updates:
  if k not in seen: out.append(f'- '+{'state':'State','blueprint status':'Blueprint status','next action':'Next action'}[k]+f': {updates[k]}')
 p.write_text('\n'.join(out).rstrip()+'\n',encoding='utf-8')

def seed_snapshot(db:Path,seed_id:str,repo_sha:str)->dict[str,Any]:
 uri=f'file:{db.resolve()}?mode=ro'; c=sqlite3.connect(uri,uri=True); c.row_factory=sqlite3.Row
 try:r=c.execute('SELECT id,canonical_name,object_class,category_path,demand_score,demand_status,asset_tier,status FROM seeds WHERE id=?',(seed_id,)).fetchone()
 finally:c.close()
 if r is None:raise RuntimeError('E_SEED_NOT_FOUND')
 v=dict(r)
 if v['status']!='approved' or v['asset_tier']!='U1-raster' or v['demand_status'] not in {'validated_high','validated_medium'}:raise RuntimeError('E_SEED_NOT_ELIGIBLE')
 return {'schema':'die.production.seed-snapshot.v1','repository_sha':repo_sha,'seed':{k:v[k] for k in ['id','canonical_name','object_class','category_path','demand_score','demand_status','asset_tier']}}

def thread_generation(principal:str)->int:
 p=Path('/var/lib/die/division01/wake-thread.json' if principal==DIV else '/var/lib/die/executive/wake-thread.json'); v=read_json(p)
 if v.get('principal_id')!=principal or v.get('lifecycle_state')!='active':raise RuntimeError('E_THREAD_STATE')
 return int(v['generation'])

def request_id(task:str,kind:str,index:int)->str:
 safe=re.sub(r'[^A-Z0-9_-]','_',task.upper()); return f'COG-PROD_{kind}_{safe}_R{index:02d}'
def expiry(minutes=20):return (dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=minutes)).isoformat(timespec='seconds').replace('+00:00','Z')
def envelope(*,rid,task,action,target,prompt,response_schema,repo_sha,evidence):
 return {'schema':'die.cognition.outbox-request.v1','company_instance_id':'DIE-LINUX','request_id':rid,'task_id':task,'action_type':action,'target_principal_id':target,'thread_generation':thread_generation(target),'prompt':prompt,'expected_response_schema':response_schema,'repository_sha':repo_sha,'evidence_refs':evidence,'created_at':now(),'expires_at':expiry()}

def author_prompt(req_id:str,task:str,repo_sha:str,snap:dict[str,Any],revision:int=0,prior:dict|None=None,review:dict|None=None)->str:
 seed=snap['seed']; base=f'''You are the bound DIE Linux Division01 cognition principal `{DIV}`. This is an authorized autonomous internal cognition request from Hermes. First use your connected Runtime MCP `context_snapshot`; proceed only if principal/scope are correct, freshness is fresh, canon load is VERIFIED, and repository revision is `{repo_sha}`. If convergence fails, return exactly one JSON object: {{"schema":"die.cognition.blocked.v1","request_id":"{req_id}","principal_id":"{DIV}","reason_code":"E_CONTEXT_CONVERGENCE","reason":"bounded explanation"}}.\n\nAuthor a production family Blueprint for the exact Object Atlas seed below. This is a throughput production Blueprint, not an OE-005 market-evidence promotion. Do NOT invent external market evidence, sales, platform acceptance, or research. Commercial statements must remain hypotheses derived only from the Object Atlas seed. Existing zero-spend production authority is unchanged; you grant no submission, publication or spend authority. Return EXACTLY one JSON object, no markdown or prose.\n\nREQUEST_ID={req_id}\nTASK_ID={task}\nREPOSITORY_SHA={repo_sha}\nSEED_SNAPSHOT_SHA256={csha(snap)}\nSEED={json.dumps(seed,separators=(',',':'))}\n'''
 if prior is not None and review is not None:
  base+=f'''\nThis is revision {revision}. Preserve valid semantics but address every Executive required action.\nPRIOR_BLUEPRINT={json.dumps(prior,separators=(',',':'))}\nEXECUTIVE_REVIEW={json.dumps(review,separators=(',',':'))}\n'''
 template=f'''\nRequired response shape and constants:\n{{"schema_version":"die.production.family-blueprint.v1","request_id":"{req_id}","blueprint_id":"BP-PROD-<UPPERCASE_ID>","task_id":"{task}","mission_id":"M-001","repository_sha":"{repo_sha}","principal":{{"principal_id":"{DIV}","role":"AUTHOR"}},"seed":{{"id":"{seed['id']}","canonical_name":{json.dumps(seed['canonical_name'])},"object_class":{json.dumps(seed['object_class'])},"category_path":{json.dumps(seed['category_path'])},"asset_tier":"U1-raster","demand_status":"{seed['demand_status']}","demand_score":{seed['demand_score']}}},"family":{{"family_id":"FAM-PROD-<ID>","family_thesis":"...","buyer_persona":["..."],"use_cases":["..."],"commercial_use_hypothesis":"...","evidence_status":"OBJECT_ATLAS_ONLY_HYPOTHESIS"}},"production":{{"asset_type":"RASTER_IMAGE","batch_size":1,"engine":"MUXIA/chatgpt-linux-a","master_prompt":"80+ char exact image-generation prompt for one useful stock raster","negative_constraints":["no logos","no trademarks","no watermark"],"semantic_variation_plan":[{{"variation_id":"VAR-<ID>","dimension":"buyer_use_case","instruction":"...","commercial_rationale":"..."}}]}},"metadata_direction":{{"title_direction":"...","primary_keywords":["...","...","..."],"category_direction":["..."]}},"qa_requirements":{{"required_checks":["artifact integrity","technical QA","visual commercial QC"],"forbidden_elements":["logos","trademarks","watermarks"]}},"lineage":{{"seed_snapshot_sha256":"{csha(snap)}","source_kind":"OBJECT_ATLAS_SEED","external_market_evidence_claimed":false}},"authority":{{"effect":"NONE","existing_production_authority_unchanged":true,"submission_authorized":false,"publication_authorized":false,"spend_authorized":false}}}}'''
 return base+template

def review_prompt(req_id:str,task:str,repo_sha:str,bp:dict[str,Any])->str:
 h=csha(bp)
 return f'''You are the bound DIE Linux Executive cognition principal `{EXEC}`. This is an authorized autonomous internal review request from Hermes. First use Runtime MCP `context_snapshot`; proceed only with correct Executive principal, fresh context, VERIFIED canon, and repository revision `{repo_sha}`. If convergence fails, return exactly {{"schema":"die.cognition.blocked.v1","request_id":"{req_id}","principal_id":"{EXEC}","reason_code":"E_CONTEXT_CONVERGENCE","reason":"bounded explanation"}}.\n\nPerform READ_ONLY_CHALLENGE of this production family Blueprint. Do not edit or rewrite it. Check commercial coherence, obvious rights/safety risks, prompt/negative-constraint contradictions, family differentiation, and whether it stays truthful about OBJECT_ATLAS_ONLY_HYPOTHESIS evidence. This review grants no production, submission, publication or spend authority. For a usable routine Blueprint return NO_VETO; use REVISE only for material semantic defects; VETO_PENDING_EVIDENCE only when missing evidence makes production unsafe/misleading; ESCALATE_FOUNDER only for sovereignty/strategy decisions. Return exactly one JSON object, no markdown.\n\nREQUEST_ID={req_id}\nTASK_ID={task}\nREPOSITORY_SHA={repo_sha}\nBLUEPRINT_SHA256={h}\nBLUEPRINT={json.dumps(bp,separators=(',',':'))}\n\nResponse shape: {{"schema_version":"die.production.family-blueprint-review.v1","request_id":"{req_id}","review_id":"BP-REVIEW-PROD-<ID>","task_id":"{task}","repository_sha":"{repo_sha}","principal":{{"principal_id":"{EXEC}","role":"REVIEWER"}},"blueprint":{{"blueprint_id":"{bp['blueprint_id']}","sha256":"{h}"}},"outcome":"NO_VETO|REVISE|VETO_PENDING_EVIDENCE|ESCALATE_FOUNDER","rationale":"20+ chars","required_actions":[],"review_mode":"READ_ONLY_CHALLENGE","semantic_content_authored":false,"authority_effect":"NONE"}}'''

def validate_blocked_response(v:dict[str,Any],req:dict[str,Any])->list[str]:
 e=[]
 if v.get('schema')!='die.cognition.blocked.v1':e.append('E_BLOCKED_SCHEMA')
 if v.get('request_id')!=req.get('request_id'):e.append('E_BLOCKED_REQUEST')
 if v.get('principal_id')!=req.get('target_principal_id'):e.append('E_BLOCKED_PRINCIPAL')
 if not isinstance(v.get('reason_code'),str) or not v.get('reason_code'):e.append('E_BLOCKED_REASON_CODE')
 if not isinstance(v.get('reason'),str) or not v.get('reason'):e.append('E_BLOCKED_REASON')
 return e

def parse_response(text:str)->dict[str,Any]:
 s=text.strip()
 if s.startswith('```'):
  lines=s.splitlines()
  if len(lines)<3 or not lines[-1].strip().startswith('```'):raise RuntimeError('E_RESPONSE_FENCE')
  s='\n'.join(lines[1:-1]).strip()
 v=json.loads(s)
 if not isinstance(v,dict):raise RuntimeError('E_RESPONSE_OBJECT')
 return v

def run_transport(node:str,transport:Path,req:Path,response:Path,timeout=270)->dict[str,Any]:
 cp=subprocess.run([node,str(transport),str(req),str(response)],text=True,capture_output=True,timeout=timeout,check=False)
 if cp.returncode!=0:raise RuntimeError('E_TRANSPORT:'+((cp.stderr or cp.stdout).strip()[:600]))
 return json.loads(cp.stdout.strip().splitlines()[-1])

def validation(kind:str,artifact:Path,req:Path,*,seed:Path|None=None,bp:Path|None=None)->dict[str,Any]:
 cmd=[sys.executable,str(VALIDATOR),kind,str(artifact),'--request',str(req)]
 if seed:cmd+=['--seed-snapshot',str(seed)]
 if bp:cmd+=['--blueprint',str(bp)]
 cp=subprocess.run(cmd,text=True,capture_output=True,check=False)
 if not cp.stdout.strip(): raise RuntimeError('E_VALIDATOR_EXEC:'+((cp.stderr or '').strip()[:600]))
 out=json.loads(cp.stdout)
 return out

def write_receipt(workspace:Path,kind:str,req:dict,artifact:dict,transport_out:dict,validation_out:dict)->Path:
 cogn=workspace/'cognition'; recdir=cogn/'receipts'; recdir.mkdir(parents=True,exist_ok=True)
 tpath=Path(transport_out['receipt_ref']); vpath=recdir/f"{req['request_id']}.validation.json"; atomic_json(vpath,validation_out)
 artifact_id=artifact.get('blueprint_id') or artifact.get('review_id') or req['request_id']
 rec={'schema':'die.production.cognition-receipt.v1','kind':kind,'task_id':req['task_id'],'request_id':req['request_id'],'principal_id':req['target_principal_id'],'artifact_id':artifact_id,'artifact_sha256':csha(artifact),'transport_receipt_ref':str(tpath),'transport_receipt_sha256':sha_bytes(tpath.read_bytes()),'validation_ref':str(vpath),'validation_sha256':sha_bytes(vpath.read_bytes()),'status':'VALID','authority_effect':'NONE','recorded_at':now()}
 schema=json.loads(RECEIPT_SCHEMA.read_text()); jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(rec); p=recdir/f"{req['request_id']}.receipt.json"; atomic_json(p,rec); return p

def ensure_request(p:Path,v:dict):
 if p.exists():
  old=read_json(p)
  # created/expires may differ on regenerated state; a sent request is immutable.
  for k in ['schema','company_instance_id','request_id','task_id','action_type','target_principal_id','thread_generation','prompt','expected_response_schema','repository_sha','evidence_refs']:
   if old.get(k)!=v.get(k):raise RuntimeError('E_REQUEST_IMMUTABLE_DRIFT')
  return old
 atomic_json(p,v); return v

def fixed_lock(workspace:Path,bp:dict,review:dict,author_receipt:Path,review_receipt:Path)->Path:
 p=workspace/'blueprint.lock.json'; v={'schema':'die.production.fixed-blueprint-lock.v1','task_id':workspace.name,'blueprint_id':bp['blueprint_id'],'blueprint_sha256':csha(bp),'executive_review_id':review['review_id'],'executive_review_sha256':csha(review),'author_receipt_sha256':sha_bytes(author_receipt.read_bytes()),'review_receipt_sha256':sha_bytes(review_receipt.read_bytes()),'locked_at':now(),'authority_effect':'NONE'}; atomic_json(p,v); return p

def trigger_resume(hermes_bin:str,hermes_home:str,job_id:str,workspace:Path)->dict[str,Any]:
 log=workspace/'cognition'/'production-resume.log'; fh=open(log,'ab',buffering=0)
 try:
  p=subprocess.Popen([hermes_bin,'cron','run',job_id],env={**os.environ,'HERMES_HOME':hermes_home},stdout=fh,stderr=subprocess.STDOUT,start_new_session=True); fh.close(); return {'triggered':True,'pid':p.pid,'log':str(log)}
 except Exception as e: fh.close(); return {'triggered':False,'error':type(e).__name__}

def tick(args)->dict[str,Any]:
 found=active_blueprint_card(Path(args.workspaces))
 if not found:return {'schema':'die.production.cognition-tick.v1','status':'IDLE','reason':'NO_BLUEPRINT_REQUIRED_CARD'}
 workspace,fields=found; task=workspace.name; m=SEED_RE.search(fields.get('seed',''))
 if not m:raise RuntimeError('E_SEED_FIELD')
 seed_id=m.group(1); repo_sha=subprocess.check_output(['git','-c',f'safe.directory={args.repo}','-C',args.repo,'rev-parse','HEAD'],text=True).strip()
 cogn=workspace/'cognition'; outbox=cogn/'outbox'; responses=cogn/'responses'; outbox.mkdir(parents=True,exist_ok=True); responses.mkdir(parents=True,exist_ok=True)
 statep=cogn/'state.json'; state=read_json(statep) if statep.exists() else {'schema':'die.production.cognition-state.v1','task_id':task,'stage':'NEED_AUTHOR','author_attempt':0,'revision':0,'history':[]}
 snap_path=cogn/'seed-snapshot.json'
 if not snap_path.exists():atomic_json(snap_path,seed_snapshot(Path(args.db),seed_id,repo_sha))
 snap=read_json(snap_path)
 stage=state['stage']; revision=int(state.get('revision',0)); attempt=int(state.get('author_attempt',0))
 if stage in {'BLOCKED_EVIDENCE','WAITING_FOUNDER','READY'}:return {'schema':'die.production.cognition-tick.v1','status':'IDLE','task_id':task,'stage':stage}
 if stage in {'NEED_AUTHOR','NEED_REVISION'}:
  if attempt>=MAX_SEMANTIC_ATTEMPTS: state['stage']='WAITING_FOUNDER'; state['history'].append({'at':now(),'event':'AUTHOR_ATTEMPTS_EXHAUSTED'}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'BLOCKED','task_id':task,'reason':'E_AUTHOR_ATTEMPTS_EXHAUSTED'}
  kind='BP_REVISION' if stage=='NEED_REVISION' else 'BP_AUTHOR'; idx=(revision*10+attempt) if stage=='NEED_REVISION' else attempt
  rid=request_id(task,kind,idx); prior=read_json(cogn/'blueprint.author.json') if stage=='NEED_REVISION' else None; review=read_json(cogn/'blueprint.review.json') if stage=='NEED_REVISION' else None
  prompt=author_prompt(rid,task,repo_sha,snap,revision=revision,prior=prior,review=review)
  req=envelope(rid=rid,task=task,action='PRODUCTION_BLUEPRINT_REVISE' if stage=='NEED_REVISION' else 'PRODUCTION_BLUEPRINT_AUTHOR',target=DIV,prompt=prompt,response_schema='die.production.family-blueprint.v1',repo_sha=repo_sha,evidence=[{'ref':str(snap_path),'sha256':csha(snap)}]+([{'ref':str(cogn/'blueprint.review.json'),'sha256':csha(review)}] if review else [])); reqp=outbox/f'{rid}.json'; req=ensure_request(reqp,req); resp=responses/f'{rid}.txt'; tr=run_transport(args.node,Path(args.transport),reqp,resp); parsed=parse_response(resp.read_text(encoding='utf-8'))
  if parsed.get('schema')=='die.cognition.blocked.v1':
   be=validate_blocked_response(parsed,req)
   if be: raise RuntimeError('E_BLOCKED_RESPONSE_BINDING:'+','.join(be))
   state['stage']='WAITING_FOUNDER'; state['history'].append({'at':now(),'event':'PRINCIPAL_BLOCKED','request_id':rid,'reason':parsed.get('reason_code')}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'BLOCKED','task_id':task,'reason':parsed.get('reason_code')}
  art=cogn/'blueprint.author.json'; atomic_json(art,parsed); val=validation('blueprint',art,reqp,seed=snap_path)
  if val['status']!='PASS': attempt+=1; state['author_attempt']=attempt; state['stage']='NEED_REVISION' if stage=='NEED_REVISION' else 'NEED_AUTHOR'; state['history'].append({'at':now(),'event':'AUTHOR_INVALID','request_id':rid,'errors':val['errors'][:10]}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'RETRY','task_id':task,'stage':state['stage'],'errors':val['errors'][:10]}
  rec=write_receipt(workspace,'BLUEPRINT_AUTHOR',req,parsed,tr,val); state['stage']='NEED_REVIEW'; state['author_attempt']=0; state['latest_author_receipt']=str(rec); state['history'].append({'at':now(),'event':'AUTHOR_VALID','request_id':rid,'artifact_sha256':csha(parsed),'receipt':str(rec)}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'ADVANCED','task_id':task,'from':stage,'to':'NEED_REVIEW','request_id':rid}
 if stage=='NEED_REVIEW':
  bp=read_json(cogn/'blueprint.author.json'); rid=request_id(task,'BP_REVIEW',revision); prompt=review_prompt(rid,task,repo_sha,bp); req=envelope(rid=rid,task=task,action='PRODUCTION_BLUEPRINT_REVIEW',target=EXEC,prompt=prompt,response_schema='die.production.family-blueprint-review.v1',repo_sha=repo_sha,evidence=[{'ref':str(cogn/'blueprint.author.json'),'sha256':csha(bp)}]); reqp=outbox/f'{rid}.json'; req=ensure_request(reqp,req); resp=responses/f'{rid}.txt'; tr=run_transport(args.node,Path(args.transport),reqp,resp); parsed=parse_response(resp.read_text(encoding='utf-8'))
  if parsed.get('schema')=='die.cognition.blocked.v1':
   be=validate_blocked_response(parsed,req)
   if be: raise RuntimeError('E_BLOCKED_RESPONSE_BINDING:'+','.join(be))
   state['stage']='WAITING_FOUNDER'; state['history'].append({'at':now(),'event':'PRINCIPAL_BLOCKED','request_id':rid,'reason':parsed.get('reason_code')}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'BLOCKED','task_id':task,'reason':parsed.get('reason_code')}
  art=cogn/'blueprint.review.json'; atomic_json(art,parsed); val=validation('review',art,reqp,bp=cogn/'blueprint.author.json')
  if val['status']!='PASS': state['stage']='WAITING_FOUNDER'; state['history'].append({'at':now(),'event':'REVIEW_INVALID','request_id':rid,'errors':val['errors'][:10]}); atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'BLOCKED','task_id':task,'reason':'E_REVIEW_INVALID','errors':val['errors'][:10]}
  rec=write_receipt(workspace,'BLUEPRINT_EXEC_REVIEW',req,parsed,tr,val); outcome=parsed['outcome']; state['history'].append({'at':now(),'event':'REVIEW_VALID','request_id':rid,'outcome':outcome,'receipt':str(rec)})
  if outcome=='NO_VETO':
   final=workspace/'blueprint.json'; atomic_json(final,bp); author_rec=Path(state.get('latest_author_receipt',''));
   if not author_rec.is_file(): raise RuntimeError('E_AUTHOR_RECEIPT_MISSING')
   lock=fixed_lock(workspace,bp,parsed,author_rec,rec); state['stage']='READY'; atomic_json(statep,state); update_progress(workspace,state='BLUEPRINT_READY',blueprint_status=f"FIXED {bp['blueprint_id']} sha256={csha(bp)}",next_action='Dispatch bounded Worker from fixed Blueprint; then MUXIA generation.'); resume=trigger_resume(args.hermes_bin,args.hermes_home,args.production_job_id,workspace) if not args.no_resume else {'triggered':False,'reason':'NO_RESUME_TEST_MODE'}; return {'schema':'die.production.cognition-tick.v1','status':'BLUEPRINT_READY','task_id':task,'blueprint_id':bp['blueprint_id'],'blueprint_sha256':csha(bp),'lock_ref':str(lock),'resume':resume}
  if outcome=='REVISE':
   revision+=1
   if revision>MAX_REVISIONS:state['stage']='WAITING_FOUNDER'; reason='E_REVISION_LIMIT'
   else:state['stage']='NEED_REVISION'; state['revision']=revision; reason='EXECUTIVE_REVISE'
   atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'ADVANCED' if state['stage']=='NEED_REVISION' else 'BLOCKED','task_id':task,'to':state['stage'],'reason':reason}
  state['stage']='BLOCKED_EVIDENCE' if outcome=='VETO_PENDING_EVIDENCE' else 'WAITING_FOUNDER'; atomic_json(statep,state); return {'schema':'die.production.cognition-tick.v1','status':'BLOCKED','task_id':task,'reason':outcome}
 raise RuntimeError('E_COGNITION_STAGE:'+stage)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--workspaces',default=str(DEFAULT_WORKSPACES)); ap.add_argument('--db',default=str(DEFAULT_DB)); ap.add_argument('--repo',default='/srv/die'); ap.add_argument('--state-root',default=str(DEFAULT_STATE_ROOT)); ap.add_argument('--transport',default='/srv/die/company/browser/linux/cognition_roundtrip.mjs'); ap.add_argument('--node',default=shutil.which('node') or '/usr/bin/node'); ap.add_argument('--hermes-bin',default='/opt/die/hermes/venv/bin/hermes'); ap.add_argument('--hermes-home',default='/var/lib/die/hermes/income-operator'); ap.add_argument('--production-job-id',default='6c1d9f5c504e'); ap.add_argument('--no-resume',action='store_true'); a=ap.parse_args()
 root=Path(a.state_root); root.mkdir(parents=True,exist_ok=True); lock=open(root/'tick.lock','a+')
 try:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError: return 0
 try:
  out=tick(a);
  if out.get('status')!='IDLE': print(json.dumps(out,sort_keys=True))
  return 0
 except Exception as e: print(json.dumps({'schema':'die.production.cognition-tick.v1','status':'FAILED','error':type(e).__name__,'message':str(e)[:1000]},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
