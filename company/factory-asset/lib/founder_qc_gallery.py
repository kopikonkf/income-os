from __future__ import annotations
import hashlib,json,mimetypes,re
from pathlib import Path
from typing import Any
EXT={'.png','.jpg','.jpeg','.webp','.tif','.tiff'}
WORK=Path('/var/lib/die/workspaces'); FA124=Path('/var/lib/die/state/fa124-cartoon-watercolor-100-r1'); THUMBS=Path('/var/tmp/die-founder-qc-gallery/thumbs')
def j(p):
 try:return json.loads(Path(p).read_text())
 except:return {}
def ok(p):return p.is_file() and p.suffix.lower() in EXT
def meta(p):return None,None,p.suffix[1:].upper()
def aid(g,job,p):return hashlib.sha256(f'{g}|{job}|{p}'.encode()).hexdigest()[:24]
def ws_seed(ws):
 d=j(ws/'seed-selection.json');s=d.get('seed') or {}
 if s:return s.get('id'),s.get('canonical_name')
 q=ws/'PROGRESS.md'
 if q.is_file():
  m=re.search(r'Seed:\s*([^\s]+)\s*\(([^)]+)\)',q.read_text(errors='ignore'))
  if m:return m.group(1),m.group(2)
 return None,None
def ws_provider(ws):
 d=j(ws/'provider'/'multi-cluster-dispatch.receipt.json')
 if d.get('provider_id'):return f"{d['provider_id']}@{d.get('cluster_id')}" if d.get('cluster_id') else d['provider_id']
 q=ws/'PROGRESS.md'
 if q.is_file():
  m=re.search(r'^- Provider:\s*(.+)$',q.read_text(errors='ignore'),re.M)
  if m:return m.group(1).strip()
 return None
def ws_state(ws):
 q=ws/'PROGRESS.md'
 if q.is_file():
  m=re.search(r'^- State:\s*(.+)$',q.read_text(errors='ignore'),re.M)
  if m:return m.group(1).strip()
 return 'UNKNOWN'
def ws_img(ws):
 rules=[('FOUNDER_QC_RENDER',ws/'qc'),('ACTIVE_MASTER',ws/'factory-v2'/'upscale'),('FINAL_MASTER',ws/'final'),('MASTER',ws/'master'),('PROVIDER_ORIGINAL',ws/'provider')]
 for kind,b in rules:
  if not b.is_dir():continue
  if kind=='ACTIVE_MASTER':cs=[b/'active-master.png']
  elif kind=='FINAL_MASTER':cs=[x for x in b.iterdir() if x.name.startswith('asset.')]
  elif kind=='MASTER':cs=[x for x in b.iterdir() if x.name.startswith('master.')]
  elif kind=='PROVIDER_ORIGINAL':cs=[x for x in b.iterdir() if x.name.startswith('source-original.')]
  else:cs=sorted([x for x in b.iterdir() if ok(x)],key=lambda x:x.stat().st_mtime,reverse=True)
  for x in cs:
   if ok(x):return x,kind
 return None,'NONE'

def model_lineage(provider_id, summary):
 p=str(provider_id or '').lower(); explicit=summary.get('model_id') or summary.get('model') or summary.get('model_name'); version=summary.get('model_version') or summary.get('version') if explicit else None
 if explicit:return {'model_name':str(explicit),'model_version':str(version) if version else 'NOT_RECORDED','model_evidence':'EXPLICIT_ATTEMPT_RECEIPT'}
 return {'model_name':'Provider-managed image model','model_version':'NOT_DISCLOSED_OR_NOT_CAPTURED','model_evidence':'NOT_DISCLOSED_BY_PROVIDER'}
def fa_items(root,cohort):
 plans={x.get('job_id'):x for x in j(cohort).get('jobs',[]) if x.get('job_id')};e4=j(root/'FA124-E4-final.json');out=[]
 for row in e4.get('technical_qa',[]):
  qa=row.get('technical_qa') or {}
  if row.get('status')!='SUCCEEDED' or qa.get('result')!='PASS':continue
  p=Path(str(qa.get('path') or ''))
  if not ok(p):continue
  job=str(row.get('job_id') or p.parent.parent.name);pl=plans.get(job,{})
  summary=j(root/'jobs'/job/'summary.json');ml=model_lineage(row.get('provider_id'),summary);out.append({'asset_id':aid('FA124_CANARY',job,p),'source_group':'FA124_CANARY','job_id':job,'seed_id':row.get('seed_id') or pl.get('seed_id'),'seed_name':row.get('seed_noun') or pl.get('seed_noun') or job,'provider_id':row.get('provider_id'),'cluster_id':row.get('cluster_id'),'provider_route':f"{row.get('provider_id')}@{row.get('cluster_id')}",**ml,'review_kind':'PROVIDER_ORIGINAL_ACCEPTED_MASTER','qc_state':'TECHNICAL_PASS','width_px':qa.get('width_px'),'height_px':qa.get('height_px'),'format':qa.get('format') or p.suffix[1:].upper(),'bytes':qa.get('bytes') or p.stat().st_size,'orientation_result':qa.get('orientation_result'),'created_at':summary.get('completed_at'),'_path':str(p)})
 return out
def ws_items(root):
 out=[]
 if not root.is_dir():return out
 for ws in sorted(root.iterdir()):
  if not ws.is_dir() or not ws.name.startswith('PROD'):continue
  p,kind=ws_img(ws)
  if p is None:continue
  sid,name=ws_seed(ws);w,h,fmt=meta(p);route=ws_provider(ws)
  out.append({'asset_id':aid('PRODUCTION_WORKSPACE',ws.name,p),'source_group':'PRODUCTION_WORKSPACE','job_id':ws.name,'seed_id':sid,'seed_name':name or ws.name,'provider_id':route,'cluster_id':None,'provider_route':route,'model_name':'NOT_RECORDED','model_version':'NOT_RECORDED','model_evidence':'LEGACY_WORKSPACE_NO_MODEL_RECEIPT','review_kind':kind,'qc_state':ws_state(ws),'width_px':w,'height_px':h,'format':fmt,'bytes':p.stat().st_size,'orientation_result':None,'created_at':None,'_path':str(p)})
 return out
def internal(repo,work=WORK,fa124=FA124):
 cohort=Path(repo)/'company/factory-asset/fixtures/scale/FA-124-cartoon-watercolor-cohort.json'
 return fa_items(Path(fa124),cohort)+ws_items(Path(work))
def build_gallery(repo_root:Path,*,workspaces_root:Path=WORK,fa124_root:Path=FA124)->dict[str,Any]:
 xs=internal(repo_root,workspaces_root,fa124_root);xs.sort(key=lambda x:(0 if x['source_group']=='FA124_CANARY' else 1,str(x.get('seed_name') or ''),x['job_id']));pub=[];counts={}
 for x in xs:
  y={k:v for k,v in x.items() if not k.startswith('_')};y['thumb_url']=f"/api/qc-image?id={x['asset_id']}&variant=thumb";y['full_url']=f"/api/qc-image?id={x['asset_id']}&variant=full";pub.append(y);counts[y['source_group']]=counts.get(y['source_group'],0)+1
 return {'schema':'die.factory-asset.founder-qc-gallery.v1','mode':'READ_ONLY_REVIEW','asset_count':len(pub),'source_counts':counts,'items':pub,'founder_qc_mutation_enabled':False}
def resolve(repo,asset_id,work=WORK,fa124=FA124):
 for x in internal(repo,work,fa124):
  if x['asset_id']==asset_id:return Path(x['_path'])
 raise KeyError('ASSET_NOT_FOUND')
def image_payload(repo_root:Path,asset_id:str,variant='full',*,workspaces_root:Path=WORK,fa124_root:Path=FA124):
 p=resolve(repo_root,asset_id,workspaces_root,fa124_root)
 if variant not in {'full','thumb'}:raise ValueError('INVALID_VARIANT')
 return p.read_bytes(),mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
