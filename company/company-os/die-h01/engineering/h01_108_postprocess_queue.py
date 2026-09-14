#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,time,tempfile,os
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
PYTHON='/opt/die/factory-asset/venv/bin/python'
TERMINAL={'PARKED_FOUNDER_QC','PARKED_RIGHTS_BLOCK'}

def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
 fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as h:h.write(data);h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def generation_proven(w:Path)->bool:
 g=load(w/'generation-complete.receipt.json');v=load(w/'final/h01-103-validation.json')
 return g.get('status')=='GENERATION_COMPLETE' and v.get('status')=='PASS' and g.get('canonical_svg_sha256')==v.get('canonical_svg_sha256')

def candidates(root:Path):
 out=[]
 for w in sorted((p for p in root.iterdir() if p.is_dir()),key=lambda p:p.name):
  if not generation_proven(w):continue
  s=load(w/'postproduction-state.json');status=s.get('status')
  if status in TERMINAL:continue
  a=load(w/'asset-receipt.json')
  if a.get('postproduction_classification') in {'PASS','REVIEW_REQUIRED','BLOCKED_RIGHTS'}:continue
  if status=='PARKED_POSTPRODUCTION_RETRY':
   retry=load(w/'postproduction-retry.json')
   if retry.get('attempts',0)>=2 or time.time()<retry.get('next_retry_epoch',0):continue
  out.append(w)
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--continuous',action='store_true');ap.add_argument('--poll-seconds',type=int,default=30);ns=ap.parse_args();root=Path(ns.runs_root)
 while True:
  rows=candidates(root)
  if not rows:
   if not ns.continuous:return 0
   time.sleep(ns.poll_seconds);continue
  for w in rows:
   if load(w/'postproduction-state.json').get('status')=='PARKED_POSTPRODUCTION_RETRY':
    r=load(w/'postproduction-retry.json');n=r.get('attempts',0)+1
    atomic_json(w/'postproduction-retry.json',{'schema':'die.h01.h01-115-local-retry.v1','attempts':n,'next_retry_epoch':time.time()+(120 if n==1 else 480),'policy':'MAX_TWO_LOCAL_RETRIES_NO_GENERATION','provider_generation_dispatched':False})
   cp=subprocess.run([PYTHON,str(H01/'engineering/h01_108_postprocess_one.py'),'--workspace',str(w)],text=True,capture_output=True)
   print(json.dumps({'workspace':str(w),'returncode':cp.returncode,'stdout':cp.stdout[-1200:],'stderr':cp.stderr[-1200:],'provider_generation_dispatched':False}),flush=True)
  if not ns.continuous:return 0
  time.sleep(ns.poll_seconds)

if __name__=='__main__':raise SystemExit(main())
