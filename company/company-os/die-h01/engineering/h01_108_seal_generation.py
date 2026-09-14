#!/usr/bin/env python3
"""Seal historical H01-108 technical masters into generation-only terminal receipts.

No provider dispatch, no browser action, no rights/postproduction read is required for
acceptance. Existing immutable provider-original bytes + H01-103 PASS are authoritative.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,tempfile,time
from pathlib import Path


def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def slug(s):return str(s).replace(' ','-')
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
 fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as h:h.write(data);h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def candidate(workspace:Path,item:dict):
 v=load(workspace/'final/h01-103-validation.json');src=workspace/'final/provider-original.svg'
 if v.get('status')!='PASS' or not src.is_file():return None
 actual=sha_file(src)
 if v.get('input_sha256')!=actual:return None
 if v.get('native_editable') is not True or v.get('conversion_from_raster') is not False:return None
 created=load(workspace/'artifact-created.receipt.json');browser=load(workspace/'browser-job-result.json');lease=load(workspace/'scheduler-lease.sanitized.json')
 if created.get('provider_original_sha256') and created.get('provider_original_sha256')!=actual:return None
 provider=created.get('provider_id') or browser.get('provider_id') or re.sub(r'^.*?-([a-z]+)-a\d+$',r'\1',workspace.name)
 profile=created.get('profile_id') or browser.get('profile_id') or lease.get('profile_id')
 udd=created.get('udd_id') or browser.get('udd_id') or lease.get('udd_id')
 job=created.get('job_id') or browser.get('job_id') or f"H01-108-SEAL-P{item['batch_position']:03d}"
 created_at=created.get('created_at') or browser.get('completed_at') or ''
 return {'workspace':workspace,'validation':v,'provider_original_sha256':actual,'provider_id':provider,'profile_id':profile,'udd_id':udd,'job_id':job,'created_at':created_at}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--progress-file',default='/var/lib/die/h01/runs/H01-108/autonomous-progress.json');ap.add_argument('--dry-run',action='store_true');ns=ap.parse_args()
 manifest=json.loads(Path(ns.manifest).read_text());items=manifest['items'];root=Path(ns.runs_root);rows=[]
 for item in items:
  prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-";valid=[]
  for w in root.glob(prefix+'*'):
   c=candidate(w,item)
   if c:valid.append(c)
  if not valid:raise SystemExit(f"E_NO_TECHNICAL_MASTER:{item['batch_position']}:{item['canonical_name']}")
  valid.sort(key=lambda c:(c['created_at'],c['workspace'].name))
  c=valid[-1];v=c['validation'];bp=load(c['workspace']/'blueprint.json')
  receipt={'schema':'die.h01.generation-complete.v1','task_id':'H01-108','status':'GENERATION_COMPLETE','job_id':c['job_id'],'batch_position':item['batch_position'],'queue_item_id':item['queue_item_id'],'source_candidate_id':item['source_candidate_id'],'semantic_asset_id':bp.get('semantic_asset_id') or f"H01SVG-{item['source_candidate_id']}",'noun':item['canonical_name'],'provider_id':c['provider_id'],'profile_id':c['profile_id'],'udd_id':c['udd_id'],'provider_original_sha256':c['provider_original_sha256'],'canonical_svg_sha256':v['canonical_svg_sha256'],'h01_103_status':'PASS','native_editable':True,'conversion_from_raster':False,'generation_acceptance_boundary':'H01_103_PASS_SEMANTIC_MASTER','postproduction_state':'INDEPENDENT_DOWNSTREAM','sealed_from_historical_h01_103':True,'sealed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'submission_authorized':False,'publication_authorized':False}
  existing=load(c['workspace']/'generation-complete.receipt.json')
  if existing and (existing.get('provider_original_sha256')!=receipt['provider_original_sha256'] or existing.get('canonical_svg_sha256')!=receipt['canonical_svg_sha256']):raise SystemExit(f"E_EXISTING_GENERATION_RECEIPT_CONFLICT:{c['workspace']}")
  if not ns.dry_run and not existing:atomic_json(c['workspace']/'generation-complete.receipt.json',receipt)
  rows.append({'position':item['batch_position'],'noun':item['canonical_name'],'workspace':str(c['workspace']),'provider':c['provider_id'],'candidate_count':len(valid),'provider_original_sha256':receipt['provider_original_sha256'],'canonical_svg_sha256':receipt['canonical_svg_sha256']})
 if len(rows)!=len(items) or len({r['position'] for r in rows})!=len(items):raise SystemExit('E_SEAL_COUNT')
 progress={'schema':'die.h01.h01-108-autonomous-supervisor.v2','task_id':'H01-108','status':'COMPLETE_PASS','generated_count':len(rows),'remaining_count':0,'total_count':len(items),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'current':None,'failures':{},'committed_recovery_pending':{},'terminal_provider_output_mismatches':{},'duplicate_retry_policy':'NO_AUTO_RESUBMIT_AFTER_COMMIT','adaptive_redistribution_policy':'ONE_PROVIDER_SWITCH_AFTER_PROVEN_TERMINAL_MODALITY_MISMATCH','attempt_budget_policy':'COMMITTED_PROVIDER_DISPATCHES_ONLY','generation_acceptance_boundary':'H01_103_PASS_SEMANTIC_MASTER','postproduction_dependency':'NONE','submission_authorized':False,'publication_authorized':False}
 if not ns.dry_run:
  progress_path=Path(ns.progress_file)
  if progress_path.exists():
   backup=progress_path.with_name('autonomous-progress.pre-generation-seal.json')
   if not backup.exists():backup.write_bytes(progress_path.read_bytes())
  atomic_json(progress_path,progress)
 out={'schema':'die.h01.h01-108-generation-seal.v1','status':'PASS','dry_run':ns.dry_run,'sealed_count':len(rows),'rows':rows,'progress':progress}
 print(json.dumps(out,sort_keys=True))
 return 0

if __name__=='__main__':raise SystemExit(main())
