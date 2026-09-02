#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import jsonschema
HERE=Path(__file__).resolve().parent
BP_SCHEMA=HERE/'die.production.family-blueprint.v1.schema.json'; REVIEW_SCHEMA=HERE/'die.production.family-blueprint-review.v1.schema.json'

def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def _schema_errors(v,p):
 s=json.loads(p.read_text()); return [e.message for e in sorted(jsonschema.Draft202012Validator(s).iter_errors(v),key=lambda e:list(e.absolute_path))]
def validate_blueprint(v, *, request, seed_snapshot):
 e=['E_SCHEMA:'+x for x in _schema_errors(v,BP_SCHEMA)]
 if e:return e
 for k in ('request_id','task_id','repository_sha'):
  if v[k]!=request[k]: e.append('E_BINDING:'+k)
 seed=seed_snapshot['seed']; got=v['seed']
 for k in ('id','canonical_name','object_class','category_path','asset_tier','demand_status','demand_score'):
  if got[k]!=seed[k]: e.append('E_SEED_DRIFT:'+k)
 if v['lineage']['seed_snapshot_sha256']!=canonical_sha(seed_snapshot): e.append('E_SEED_HASH')
 unresolved=re.compile(r'(?i)(\bTODO\b|\bTBD\b|\bFIXME\b|<[^>]+>|\{\{[^}]+\}\})')
 if unresolved.search(v['production']['master_prompt']): e.append('E_PROMPT_PLACEHOLDER')
 ids=[x['variation_id'] for x in v['production']['semantic_variation_plan']]
 if len(ids)!=len(set(ids)): e.append('E_VARIATION_DUPLICATE')
 if len(v['production']['semantic_variation_plan'])>v['production']['batch_size']: e.append('E_VARIATION_BATCH')
 return e
def validate_review(v, *, request, blueprint):
 e=['E_SCHEMA:'+x for x in _schema_errors(v,REVIEW_SCHEMA)]
 if e:return e
 for k in ('request_id','task_id','repository_sha'):
  if v[k]!=request[k]: e.append('E_BINDING:'+k)
 if v['blueprint']['blueprint_id']!=blueprint['blueprint_id'] or v['blueprint']['sha256']!=canonical_sha(blueprint): e.append('E_BLUEPRINT_BINDING')
 if v['outcome']=='NO_VETO' and v['required_actions']: e.append('E_NO_VETO_ACTIONS')
 if v['outcome']=='REVISE' and not v['required_actions']: e.append('E_REVISE_ACTIONS')
 return e

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('kind',choices=['blueprint','review']); ap.add_argument('artifact'); ap.add_argument('--request',required=True); ap.add_argument('--seed-snapshot'); ap.add_argument('--blueprint'); a=ap.parse_args(); v=json.load(open(a.artifact)); req=json.load(open(a.request))
 if a.kind=='blueprint':
  if not a.seed_snapshot:
   raise SystemExit('E_SEED_SNAPSHOT_REQUIRED')
  e=validate_blueprint(v,request=req,seed_snapshot=json.load(open(a.seed_snapshot)))
 else:
  if not a.blueprint:
   raise SystemExit('E_BLUEPRINT_REQUIRED')
  e=validate_review(v,request=req,blueprint=json.load(open(a.blueprint)))
 out={'schema':'die.production.cognition-validation.v1','kind':a.kind,'status':'PASS' if not e else 'FAIL','artifact_sha256':canonical_sha(v),'errors':e}; print(json.dumps(out,indent=2)); return 0 if not e else 2
if __name__=='__main__': raise SystemExit(main())
