#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve();H01=HERE.parents[1]
PYTHON='/opt/die/factory-asset/venv/bin/python'
def load(p):
 try:return json.loads(Path(p).read_text())
 except Exception:return {}
def slug(s):return s.replace(' ','-')
def generated(root:Path,item:dict)->bool:
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{item['planned_provider']}"
 for w in root.glob(prefix+'*'):
  if load(w/'artifact-created.receipt.json').get('status')=='ARTIFACT_CREATED':return True
  b=load(w/'browser-job-result.json')
  if b.get('terminal_state')=='SUCCEEDED' and (w/'final/provider-original.svg').is_file():return True
 return False
def next_attempt(root:Path,item:dict)->int:
 prefix=f"{item['batch_position']:03d}-{slug(item['canonical_name'])}-{item['planned_provider']}-a"
 vals=[]
 for w in root.glob(prefix+'*'):
  m=re.search(r'-a(\d+)$',w.name)
  if m:vals.append(int(m.group(1)))
 return max(vals,default=0)+1
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--runs-root',default='/var/lib/die/h01/runs/H01-108');ap.add_argument('--positions',default='');ap.add_argument('--max-new-attempts',type=int,default=1);ns=ap.parse_args();m=json.loads(Path(ns.manifest).read_text());root=Path(ns.runs_root);wanted={int(x) for x in ns.positions.split(',') if x.strip()} if ns.positions else None
 summary=[]
 for item in m['items']:
  if wanted is not None and item['batch_position'] not in wanted:continue
  if generated(root,item):summary.append({'position':item['batch_position'],'status':'ALREADY_ARTIFACT_CREATED'});continue
  success=False
  for _ in range(ns.max_new_attempts):
   a=next_attempt(root,item);cp=subprocess.run([PYTHON,str(H01/'engineering/h01_108_run_one.py'),'--manifest',ns.manifest,'--position',str(item['batch_position']),'--attempt',str(a)],text=True,capture_output=True)
   row={'position':item['batch_position'],'noun':item['canonical_name'],'provider':item['planned_provider'],'attempt':a,'returncode':cp.returncode,'stdout':cp.stdout[-800:],'stderr':cp.stderr[-800:]};summary.append(row);print(json.dumps(row),flush=True)
   if cp.returncode==0:success=True;break
   time.sleep(1)
 print(json.dumps({'schema':'die.h01.h01-108-generation-cycle.v1','status':'COMPLETE_PASS' if all(generated(root,i) for i in m['items'] if wanted is None or i['batch_position'] in wanted) else 'COMPLETE_WITH_GAPS','rows':summary},sort_keys=True))
 return 0
if __name__=='__main__':raise SystemExit(main())
