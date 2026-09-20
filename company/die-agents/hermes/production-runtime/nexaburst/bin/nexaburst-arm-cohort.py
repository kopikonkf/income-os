#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,time
from pathlib import Path

STATE=Path('/var/lib/die/h01/nexaburst/state')
ARM=STATE/'FULL_ROLLOUT_ARMED.json'

def sha(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def rows(p:Path):
 return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def validate(p:Path,lane:str,cohort_id:str|None):
 rs=rows(p)
 if not rs: raise SystemExit('E_EMPTY_COHORT')
 if len(rs)>500: raise SystemExit('E_COHORT_GT_500')
 cids=[str(x.get('candidate_id') or '') for x in rs]
 sk=[str(x.get('semantic_key') or '') for x in rs]
 if any(not x for x in cids):raise SystemExit('E_CANDIDATE_ID_MISSING')
 if any(not x for x in sk):raise SystemExit('E_SEMANTIC_KEY_MISSING')
 if len(cids)!=len(set(cids)):raise SystemExit('E_DUPLICATE_CANDIDATE')
 if len(sk)!=len(set(sk)):raise SystemExit('E_DUPLICATE_SEMANTIC_KEY')
 if any(str(x.get('lane_id'))!=lane for x in rs):raise SystemExit('E_LANE_MISMATCH')
 ids={str(x.get('cohort_id') or '') for x in rs}
 if cohort_id and ids!={cohort_id}:raise SystemExit('E_COHORT_ID_MISMATCH')
 return rs

def atomic(path:Path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 t=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 t.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 os.replace(t,path)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--cohort-file',required=True,type=Path)
 ap.add_argument('--lane',required=True)
 ap.add_argument('--cohort-id')
 ap.add_argument('--authorized-by',default='Founder Dee')
 ap.add_argument('--validate-only',action='store_true')
 ap.add_argument('--arm',action='store_true')
 ap.add_argument('--founder-go',default='')
 a=ap.parse_args()
 p=a.cohort_file.resolve()
 rs=validate(p,a.lane,a.cohort_id)
 out={'status':'VALID','lane_id':a.lane,'cohort_id':a.cohort_id or rs[0].get('cohort_id'),
      'rows':len(rs),'candidate_unique':len({x['candidate_id'] for x in rs}),
      'semantic_unique':len({x['semantic_key'] for x in rs}),'plan_path':str(p),'plan_sha256':sha(p)}
 if a.arm:
  if a.founder_go!='I_AUTHORIZE_THIS_COHORT': raise SystemExit('E_FOUNDER_GO_REQUIRED')
  arm={'schema':'die.h01.nexaburst.full-rollout-arm.v2','authorized':True,'lane_id':a.lane,
       'authorized_plan_items':len(rs),'authorized_cohort_id':out['cohort_id'],
       'plan_path':str(p),'plan_sha256':out['plan_sha256'],'authorized_by':a.authorized_by,
       'authorization_scope':'EXACT_COHORT_FILE_ONLY','next_cohort_requires_new_founder_authorization':True,
       'authorized_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
  atomic(ARM,arm);out['status']='ARMED';out['arm_path']=str(ARM)
 print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
