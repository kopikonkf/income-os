from __future__ import annotations
import hashlib,json,os,shutil,statistics,subprocess
from pathlib import Path
from typing import Any
from PIL import Image,ImageChops

class Fa124CartoonEvaluationError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def _dhash_image(im:Image.Image)->int:
    g=im.convert('L').resize((9,8),Image.Resampling.LANCZOS);px=list(g.getdata());v=0
    for y in range(8):
        for x in range(8):v=(v<<1)|int(px[y*9+x]>px[y*9+x+1])
    return v

def dhash(path:Path)->int:
    with Image.open(path) as im:return _dhash_image(im)

def object_dhash(path:Path)->int:
    with Image.open(path) as im:
        rgb=im.convert('RGB');diff=ImageChops.difference(rgb,Image.new('RGB',rgb.size,(255,255,255))).convert('L');mask=diff.point(lambda x:255 if x>=18 else 0);bbox=mask.getbbox()
        if not bbox:return _dhash_image(rgb)
        x0,y0,x1,y1=bbox;pad=max(4,int(max(x1-x0,y1-y0)*.05));crop=rgb.crop((max(0,x0-pad),max(0,y0-pad),min(rgb.width,x1+pad),min(rgb.height,y1+pad)))
        return _dhash_image(crop)

def hamming(a:int,b:int)->int:return (a^b).bit_count()
def atomic_json(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}');tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n');os.replace(tmp,path)
def load_canonical_json(repo_root:Path,ref:str)->dict[str,Any]:
    p=repo_root/ref
    if p.is_file():return json.loads(p.read_text())
    cp=subprocess.run(['git','-C',str(repo_root),'show',f'origin/main:{ref}'],capture_output=True,text=True,check=False,timeout=30)
    if cp.returncode!=0:raise Fa124CartoonEvaluationError('E_CANONICAL_REF',ref)
    return json.loads(cp.stdout)
def percentile(values:list[float],q:float)->float|None:
    if not values:return None
    xs=sorted(values);idx=min(len(xs)-1,max(0,int(round((len(xs)-1)*q))));return round(xs[idx],3)

def evaluate_fa124_cartoon(*,repo_root:str|Path,state_root:str|Path,cohort_path:str|Path,manifestation_path:str|Path,output_path:str|Path|None=None)->dict[str,Any]:
    repo=Path(repo_root).resolve();state=Path(state_root).resolve();cohort=json.loads(Path(cohort_path).read_text());manifest=json.loads(Path(manifestation_path).read_text())
    if cohort.get('schema')!='die.factory-asset.fa124-fixed-manifestation-cohort.v1':raise Fa124CartoonEvaluationError('E_COHORT_SCHEMA',str(cohort.get('schema')))
    if manifest.get('preset_id')!='ISOLATED_CARTOON_WATERCOLOR_L0':raise Fa124CartoonEvaluationError('E_MANIFESTATION',str(manifest.get('preset_id')))
    plan={j['job_id']:j for j in cohort['jobs']};rows=[];dispatch_commits=0;provider_failures=0;latencies:dict[str,list[float]]={};accepted=[]
    for jid,j in plan.items():
        d=state/'jobs'/jid;summary_file=d/'summary.json';attempt_file=d/'attempt.json';src=summary_file if summary_file.is_file() else attempt_file
        if not src.is_file():continue
        s=json.loads(src.read_text());committed=s.get('dispatch_committed') is True;dispatch_commits+=int(committed);provider_failures+=int(s.get('status')=='FAILED' and committed)
        if isinstance(s.get('latency_ms'),(int,float)):latencies.setdefault(f"{j['provider_id']}@{j['cluster_id']}",[]).append(float(s['latency_ms']))
        row={'job_id':jid,'seed_id':j['seed_id'],'seed_noun':j['seed_noun'],'provider_id':j['provider_id'],'cluster_id':j['cluster_id'],'route_seq':j['route_seq'],'status':s.get('status'),'dispatch_committed':committed,'failure_code':s.get('failure_code'),'technical_qa':None}
        if s.get('status')=='SUCCEEDED':
            a=s.get('artifact') or {};p=Path(str(a.get('path') or ''));checks={'file_exists':p.is_file(),'sha256_matches':False,'bytes_nontrivial':False,'decode_reopen':False,'format_allowed':False,'dimensions_nontrivial':False};fmt=None;w=h=0;actual=None
            if p.is_file():
                actual=sha256_file(p);checks['sha256_matches']=actual==a.get('sha256') and len(actual)==64;checks['bytes_nontrivial']=p.stat().st_size>=10000
                try:
                    with Image.open(p) as im:im.load();fmt=im.format;w,h=im.size
                    checks['decode_reopen']=True;checks['format_allowed']=fmt in {'PNG','JPEG','WEBP'};checks['dimensions_nontrivial']=min(w,h)>=256
                except Exception:pass
            ratio=(min(w,h)/max(w,h)) if w and h else 0;qa=all(checks.values())
            row['technical_qa']={'result':'PASS' if qa else 'FAIL','checks':checks,'path':str(p),'sha256':actual,'bytes':p.stat().st_size if p.is_file() else 0,'format':fmt,'width_px':w,'height_px':h,'orientation_request':'SQUARE_1_TO_1_BEST_EFFORT','orientation_result':'PASS' if ratio>=.95 else 'ADVISORY_MISMATCH','orientation_hard_gate':False,'square_ratio':round(ratio,4)}
            if qa:accepted.append((row,p,actual,dhash(p),object_dhash(p)))
        rows.append(row)
    hashes=[x[2] for x in accepted];hash_counts={h:hashes.count(h) for h in set(hashes)};exact=sorted(h for h,n in hash_counts.items() if n>1)
    threshold=4;near=[];full_canvas_candidates=[]
    for i in range(len(accepted)):
        for k in range(i+1,len(accepted)):
            full_dist=hamming(accepted[i][3],accepted[k][3])
            if full_dist<=threshold:
                crop_dist=hamming(accepted[i][4],accepted[k][4]);ev={'job_a':accepted[i][0]['job_id'],'job_b':accepted[k][0]['job_id'],'seed_a':accepted[i][0]['seed_noun'],'seed_b':accepted[k][0]['seed_noun'],'full_canvas_dhash_hamming':full_dist,'object_crop_dhash_hamming':crop_dist}
                full_canvas_candidates.append(ev)
                if crop_dist<=threshold:near.append(ev)
    route_counts={f'{p}@{c}':0 for c in ('cluster-a','cluster-b') for p in ('chatgpt','qwen','gemini','manus','duckai')}
    for row,_,_,_,_ in accepted:route_counts[f"{row['provider_id']}@{row['cluster_id']}"]+=1
    accepted_seed_ids={x[0]['seed_id'] for x in accepted};orientation_mismatches=sum(x[0]['technical_qa']['orientation_result']=='ADVISORY_MISMATCH' for x in accepted)
    fa123=load_canonical_json(repo,'company/factory-asset/receipts/FA-123-downstream-capacity.receipt.json');pc=fa123.get('package_capacity') or {}
    secret_clean=all((json.loads((state/'jobs'/j/'summary.json').read_text()).get('credential_values_read') is False and json.loads((state/'jobs'/j/'summary.json').read_text()).get('cookies_or_tokens_read') is False) for j in plan if (state/'jobs'/j/'summary.json').is_file())
    spend=sum(float(json.loads((state/'jobs'/j/'summary.json').read_text()).get('spend_usd') or 0) for j in plan if (state/'jobs'/j/'summary.json').is_file())
    disk=shutil.disk_usage(state);artifact_bytes=sum(x[0]['technical_qa']['bytes'] for x in accepted)
    assertions={
      'exactly_100_accepted_masters':len(accepted)==100,
      'exactly_100_unique_master_sha256':len(set(hashes))==100,
      'exactly_100_unique_seed_ids':len(accepted_seed_ids)==100,
      'all_10_provider_cluster_routes_certified':len(route_counts)==10 and all(v>=1 for v in route_counts.values()),
      'provider_commit_budget_lte_120':dispatch_commits<=120,
      'zero_exact_duplicate_hashes':not exact,
      'zero_object_confirmed_near_duplicate_pairs_at_dhash4':not near,
      'zero_secret_cookie_token_reads':secret_clean,
      'zero_observed_spend':spend==0,
      'fa123_downstream_capacity_pass':fa123.get('task_id')=='FA-123' and fa123.get('status')=='DONE' and fa123.get('result')=='PASS' and pc.get('readiness_passed')==100 and pc.get('composition_passed')==100,
    }
    result='PASS' if all(assertions.values()) else ('REVIEW_REQUIRED' if all(v for k,v in assertions.items() if k!='zero_object_confirmed_near_duplicate_pairs_at_dhash4') and near else 'FAIL')
    out={'schema':'die.factory-asset.fa124-cartoon-watercolor-evaluation.v1','task_id':'FA-124','result':result,'manifestation':{'asset_family':manifest['asset_family'],'asset_function':manifest['asset_function'],'style_preset':manifest['style_preset'],'scene_level':manifest['scene_level'],'orientation_policy':manifest.get('orientation_policy')},'counts':{'planned_jobs':len(plan),'dispatch_commits':dispatch_commits,'provider_failures_after_commit':provider_failures,'successful_provider_artifacts':sum(r['status']=='SUCCEEDED' for r in rows),'accepted_masters':len(accepted),'unique_sha256':len(set(hashes)),'unique_seed_ids':len(accepted_seed_ids),'exact_duplicate_hashes':len(exact),'near_duplicate_pairs':len(near),'full_canvas_near_candidates':len(full_canvas_candidates),'orientation_advisory_mismatches':orientation_mismatches},'route_counts':route_counts,'exact_duplicate_hashes':exact,'near_duplicate_pairs':near,'full_canvas_near_candidates':full_canvas_candidates,'technical_qa':rows,'provider_latency_ms':{k:{'n':len(v),'p50':percentile(v,.5),'p90':percentile(v,.9),'max':round(max(v),3)} for k,v in sorted(latencies.items())},'storage_economics':{'accepted_provider_artifact_bytes':artifact_bytes,'accepted_provider_artifact_gib':round(artifact_bytes/(1024**3),4),'free_disk_bytes_after':disk.free,'free_disk_gib_after':round(disk.free/(1024**3),3),'observed_spend_usd':spend,'monetary_provider_cost_claimed':False},'fa123_package_capacity_reference':{'task_id':fa123.get('task_id'),'status':fa123.get('status'),'result':fa123.get('result'),'readiness_passed':pc.get('readiness_passed'),'composition_passed':pc.get('composition_passed'),'fa124_full_postprocessed_packages_created':False,'founder_qc_policy_changed':False},'truth_boundaries':{'orientation_mismatch_is_advisory':True,'style_semantic_output_compliance_not_proven_by_dimension_checks':True,'founder_qc_remains_100_percent_per_fa123':True,'credential_values_read':False,'cookies_or_tokens_read':False,'marketplace_submission_authorized':False,'publication_authorized':False},'assertions':assertions}
    if output_path:atomic_json(Path(output_path),out)
    return out
