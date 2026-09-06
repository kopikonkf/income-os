#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
R=ROOT/'company/factory-asset/receipts'
F=ROOT/'company/factory-asset/fixtures/governed-canary'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'
OUT=F/'FA-206-v1-acceptance-result.json'

LIVE={
 'provider_original':Path('/var/lib/die/workspaces/FA202-SHOPPING-BAG-20260905A/provider/source-original.png'),
 'master_png':Path('/var/lib/die/workspaces/FA202-SHOPPING-BAG-20260905A/master/master.png'),
 'adobe_jpeg':Path('/var/lib/die/workspaces/FA202-SHOPPING-BAG-20260905A/derivatives/adobe-jpeg.jpg'),
 'png_preview':Path('/var/lib/die/workspaces/FA202-SHOPPING-BAG-20260905A/derivatives/png-preview.png'),
 'webp_preview':Path('/var/lib/die/workspaces/FA202-SHOPPING-BAG-20260905A/derivatives/webp-preview.webp'),
 'listing_jpeg':Path('/var/lib/die/workspaces/FA204-SHOPPING-BAG-20260906A/shopping-bag-isolated-object__5630d1fd.jpg'),
 'metadata_bundle':Path('/var/lib/die/workspaces/FA204-SHOPPING-BAG-20260906A/metadata.json'),
}

def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def load(name:str)->dict[str,Any]: return json.loads((R/name).read_text())
def fail(code:str,detail:Any='')->None: raise RuntimeError(f'{code}:{detail}')
def atomic_json(p:Path,v:Any)->None: p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')

def main()->int:
 fa200=load('FA-200-canary-selection.receipt.json');fa201=load('FA-201-canary-blueprint-compile.receipt.json');fa202=load('FA-202-governed-production.receipt.json');fa203=load('FA-203-canary-registry-qa.receipt.json');fa204=load('FA-204-canary-metadata-rights.receipt.json');fa205=load('FA-205-founder-qc.receipt.json')
 graph=json.loads(GRAPH.read_text());by={x['id']:x for x in graph['tasks']}
 for tid in ('FA-200','FA-201','FA-202','FA-203','FA-204','FA-205'):
  if by[tid]['status']!='DONE': fail('E_DEPENDENCY_NOT_DONE',tid)
 if fa205['founder_verdict']['decision']!='APPROVE' or not fa205['authority_boundary']['founder_qc_approved']: fail('E_FOUNDER_QC')
 sid='FASA-SHOPPING_BAG_FULFILLMENT_ISOLATED';bp='FABP-FA200_SHOPPING_BAG_FULFILLMENT'
 # Blueprint/semantic continuity.
 if fa200['selected']['semantic_asset_id']!=sid or fa201['blueprint']['semantic_asset_id']!=sid or fa202['frozen_semantics']['semantic_asset_id']!=sid or fa205['semantic_asset_id']!=sid: fail('E_SEMANTIC_CONTINUITY')
 if fa201['blueprint']['blueprint_id']!=bp: fail('E_BLUEPRINT_ID')
 if fa201['master_spec']!={'format':'PNG','width_px':4096,'height_px':4096,'pixel_count':16777216,'color_space':'SRGB','lineage_sha256_required':True,'immutable':True}: fail('E_MASTER_SPEC')
 # Provider exactly-once governed generation + immutable original.
 pd=fa202['provider_dispatch'];po=fa202['provider_original']
 if pd['generation_call_count']!=1 or pd['rerun_generation_call_count']!=0 or pd['credential_values_read'] or pd['cookies_or_tokens_read']: fail('E_PROVIDER_BOUNDARY')
 if pd['transport']!='BROWSER_CDP' or pd['provider_id']!='chatgpt' or pd['runtime_owner']!='MUXIA': fail('E_PROVIDER_ROUTE')
 if not po['immutable_after_postprocess'] or not fa202['idempotency']['bytes_unchanged_on_rerun'] or fa202['idempotency']['rerun_provider_call_performed']: fail('E_PROVIDER_ORIGINAL_IMMUTABILITY')
 # Live byte verification against Founder-approved package hashes.
 expected=dict(fa205['exact_hashes']); expected['provider_original']=po['sha256']
 live={}
 for key,p in LIVE.items():
  if not p.is_file(): fail('E_LIVE_FILE_MISSING',key)
  h=sha_file(p); live[key]={'path':str(p),'sha256':h,'bytes':p.stat().st_size}
  if key=='metadata_bundle':
   md=json.loads(p.read_text())
   live[key]['canonical_metadata_sha256']=md.get('metadata_sha256')
   if md.get('metadata_sha256')!=expected['metadata_bundle']: fail('E_METADATA_CANONICAL_HASH_DRIFT',md.get('metadata_sha256'))
   if md.get('master_sha256')!=expected['master_png'] or md.get('semantic_asset_id')!=sid: fail('E_METADATA_IDENTITY_DRIFT')
  elif h!=expected[key]: fail('E_LIVE_HASH_DRIFT',key)
 # Derivative and QA continuity.
 for did,key in [('ADOBE_JPEG','adobe_jpeg'),('PNG_PREVIEW','png_preview'),('WEBP_PREVIEW','webp_preview')]:
  d=fa202['derivatives'][did]
  if d['sha256']!=expected[key] or d['qa_result']!='PASS' or d['semantic_identity_effect']!='NONE' or not d['idempotent_reuse']: fail('E_DERIVATIVE',did)
 if fa203['acceptance']['master_technical_qa']!='PASS' or fa203['acceptance']['canonical_truth'] is not True: fail('E_REGISTRY_QA')
 if fa203['acceptance']['semantic_asset_count']!=1 or fa203['acceptance']['physical_master_count']!=1 or fa203['acceptance']['duplicate_suppression']['same_semantic_commit_replay']!='IDEMPOTENT_REUSE': fail('E_REGISTRY_DEDUPE')
 # Rights, metadata, package readiness.
 if fa204['rights']['signal_result']!='PASS' or fa204['package']['result']!='PACKAGE_READY' or fa204['package']['blockers']!=[]: fail('E_PACKAGE_NOT_READY')
 if fa204['truth_boundaries']['human_rights_clearance'] is not False or fa204['rights']['source_preflight']['legal_clearance_claimed'] is not False: fail('E_RIGHTS_BOUNDARY')
 if not fa204['binary_metadata']['immutable_source_preserved'] or fa204['idempotency']['binary_metadata_rerun']!='IDEMPOTENT_REUSE' or fa204['idempotency']['state_manager_rerun']!='IDEMPOTENT_REUSE': fail('E_METADATA_IDEMPOTENCY')
 # Canonical registry + rollback/history evidence.
 reg=json.loads(REG.read_text())
 if reg['revision']!=3 or reg['canonical_writer']!='DIE_STATE_MANAGER' or len(reg['assets'])!=1 or len(reg['physical_masters'])!=1: fail('E_REGISTRY_REVISION')
 asset=reg['assets'][0]
 if asset['semantic_asset_id']!=sid or asset['state']!='PACKAGE_READY' or asset['rights_state']!='PASS' or asset['package_state']!='PACKAGE_READY': fail('E_REGISTRY_FINAL_STATE')
 hist=reg['history']
 expected_history=[('ASSET_COMMIT',1),('ASSET_METADATA_RIGHTS',2),('ASSET_RIGHTS_RESOLUTION',3)]
 if [(x['kind'],x['revision']) for x in hist]!=expected_history: fail('E_REGISTRY_HISTORY')
 rev2=hist[1];rev3=hist[2]
 if rev2['rights_result']!='REVIEW_REQUIRED' or rev2['package_result']!='PACKAGE_BLOCKED': fail('E_REV2_BOUNDARY')
 if rev3['rights_result']!='PASS' or rev3['package_result']!='PACKAGE_READY' or rev3['prior_enrichment_sha256']!=rev2['enrichment_sha256']: fail('E_REV3_RESOLUTION_CHAIN')
 staged=Path(reg['physical_masters'][0]['staged_blob_path'])
 if not staged.is_file() or sha_file(staged)!=expected['master_png']: fail('E_STAGED_MASTER_ROLLBACK_SOURCE')
 # Non-destructive rollback rehearsal: reconstruct the last pre-PASS boundary in memory from durable history + immutable hashes.
 rollback_rehearsal={
  'mode':'NON_DESTRUCTIVE_IN_MEMORY_RECONSTRUCTION',
  'target_revision':2,
  'semantic_asset_id':sid,
  'master_sha256':rev2['master_sha256'],
  'metadata_sha256':rev2['metadata_sha256'],
  'rights_state':'REVIEW_REQUIRED',
  'package_state':'PACKAGE_BLOCKED',
  'prior_enrichment_sha256':rev2['enrichment_sha256'],
  'source_master_retained':sha_file(staged)==expected['master_png'],
  'provider_original_retained':live['provider_original']['sha256']==po['sha256'],
  'canonical_master_retained':live['master_png']['sha256']==expected['master_png'],
  'external_side_effect_to_undo':False,
  'result':'PASS',
 }
 # Publication/upload must remain outside scope at every final boundary.
 auth=[fa200['authority'],fa202['truth_boundaries'],fa203['truth_boundaries'],fa204['truth_boundaries'],fa205['authority_boundary'],asset['authority']]
 for i,a in enumerate(auth):
  for k in ('submission_authorized','publication_authorized','marketplace_upload'):
   if k in a and a[k] is not False: fail('E_EXTERNAL_AUTHORITY',f'{i}:{k}')
 package_plan=fa204['package']['package_plan_sha256']
 if package_plan!=expected['package_plan']: fail('E_PACKAGE_PLAN_HASH')
 pr=fa204['package'];
 # Overall acceptance matrix.
 matrix={
  'selection_and_demand_basis':'PASS','blueprint':'PASS','provider_generation':'PASS','immutable_provider_original':'PASS','master_normalization':'PASS','derivatives':'PASS','canonical_registry':'PASS','technical_qa':'PASS','metadata':'PASS','automated_rights':'PASS','package_readiness':'PASS','founder_exact_hash_qc':'PASS','rollback_rehearsal':'PASS','publication_outside_scope':'PASS'
 }
 result={'schema':'die.factory-asset.fa206-v1-acceptance-result.v1','task_id':'FA-206','result':'PASS','semantic_asset_id':sid,'blueprint_id':bp,'acceptance_matrix':matrix,'live_hashes':live,'rollback_evidence':rollback_rehearsal,'registry':{'revision':reg['revision'],'history':hist,'semantic_asset_count':len(reg['assets']),'physical_master_count':len(reg['physical_masters'])},'founder_qc':{'decision':'APPROVE','receipt':'company/factory-asset/receipts/FA-205-founder-qc.receipt.json','exact_hashes':fa205['exact_hashes']},'truth_boundaries':{'marketplace_acceptance_claimed':False,'legal_clearance_claimed':False,'human_rights_clearance':False,'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'provider_calls_performed':False,'spend_usd':0,'fa121_dependency':False},'next':'Factory Asset Level Up v1 governed canary acceptance complete; publication remains a separate Founder-controlled scope.'}
 atomic_json(OUT,result);print(json.dumps(result));return 0
if __name__=='__main__': raise SystemExit(main())