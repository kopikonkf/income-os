from __future__ import annotations
import hashlib,json,random,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'company/factory-asset/lib'))
from fa124_cartoon_evaluator import evaluate_fa124_cartoon
COHORT=ROOT/'company/factory-asset/fixtures/scale/FA-124-cartoon-watercolor-cohort.json';MAN=ROOT/'company/factory-asset/contracts/fa124-manifestation.v1.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(tmp,dup=False):
 c=json.loads(COHORT.read_text());chosen=[]
 for cluster in ('cluster-a','cluster-b'):
  for provider in ('chatgpt','qwen','gemini','manus','duckai'):
   chosen.extend([j for j in c['jobs'] if j['cluster_id']==cluster and j['provider_id']==provider][:10])
 first=None
 for i,j in enumerate(chosen):
  d=tmp/'jobs'/j['job_id'];(d/'provider').mkdir(parents=True)
  p=d/'provider'/'source-original.png'
  if dup and i==99:p.write_bytes(first.read_bytes())
  else:
   r=random.Random(9000+i);Image.frombytes('RGB',(256,256),r.randbytes(256*256*3)).save(p,'PNG')
  if first is None:first=p
  s={'job_id':j['job_id'],'provider_id':j['provider_id'],'cluster_id':j['cluster_id'],'status':'SUCCEEDED','dispatch_committed':True,'completed_at':f'2026-09-08T{i//60:02d}:{i%60:02d}:00Z','latency_ms':10000+i,'artifact':{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'mime':'image/png','original_byte_acquisition_method':'synthetic-test'},'credential_values_read':False,'cookies_or_tokens_read':False,'spend_usd':0}
  (d/'summary.json').write_text(json.dumps(s))
 return tmp
def test_e4_passes_exact_100_unique_when_all_routes_certified(tmp_path):
 state=build(tmp_path);r=evaluate_fa124_cartoon(repo_root=ROOT,state_root=state,cohort_path=COHORT,manifestation_path=MAN)
 assert r['result']=='PASS';assert r['counts']['accepted_masters']==100 and r['counts']['unique_sha256']==100;assert all(v>=1 for v in r['route_counts'].values());assert r['assertions']['all_10_provider_cluster_routes_certified'] is True;assert r['assertions']['fa123_downstream_capacity_pass'] is True
def test_e4_rejects_exact_duplicate_inflation(tmp_path):
 state=build(tmp_path,dup=True);r=evaluate_fa124_cartoon(repo_root=ROOT,state_root=state,cohort_path=COHORT,manifestation_path=MAN)
 assert r['result']!='PASS';assert r['counts']['unique_sha256']==99 and r['counts']['exact_duplicate_hashes']==1
