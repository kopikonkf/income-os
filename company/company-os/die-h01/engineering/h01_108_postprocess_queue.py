#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
PYTHON='/opt/die/factory-asset/venv/bin/python'
TERMINAL={'PARKED_FOUNDER_QC','PARKED_RIGHTS_BLOCK'}
def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def generation_proven(w:Path)->bool:
 a=load(w/'artifact-created.receipt.json')
 if a.get('status')=='ARTIFACT_CREATED':return True
 b=load(w/'browser-job-result.json')
 return b.get('terminal_state')=='SUCCEEDED' and (w/'final/provider-original.svg').is_file()
def candidates(root:Path,retry_parked:bool):
 out=[]
 for w in sorted((p for p in root.iterdir() if p.is_dir()),key=lambda p:p.name):
  if not generation_proven(w):continue
  a=load(w/'asset-receipt.json')
  if a.get('status') in {'ACCEPTED_SEMANTIC_MASTER','BLOCKED_RIGHTS'}:continue
  s=load(w/'postproduction-state.json');status=s.get('status')
  if status in TERMINAL:continue
  if status=='PARKED_POSTPRODUCTION_RETRY' and not retry_parked:continue
  out.append(w)
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--retry-parked',action='store_true');ap.add_argument('--continuous',action='store_true');ap.add_argument('--poll-seconds',type=int,default=30);ns=ap.parse_args();root=Path(ns.runs_root)
 while True:
  rows=candidates(root,ns.retry_parked)
  if not rows:
   if not ns.continuous:return 0
   time.sleep(ns.poll_seconds);continue
  for w in rows:
   cp=subprocess.run([PYTHON,str(H01/'engineering/h01_108_postprocess_one.py'),'--workspace',str(w)],text=True,capture_output=True)
   print(json.dumps({'workspace':str(w),'returncode':cp.returncode,'stdout':cp.stdout[-1200:],'stderr':cp.stderr[-1200:]}),flush=True)
  if not ns.continuous:return 0
  time.sleep(ns.poll_seconds)
if __name__=='__main__':raise SystemExit(main())
