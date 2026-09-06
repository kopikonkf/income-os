#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
rights_gate=load('fa204_rights_gate',LIB/'rights_signal_gate.py')
package=load('fa204_package',LIB/'package_readiness.py')
bmeta=load('fa204_bmeta',LIB/'binary_metadata.py')
post=load('fa204_post',LIB/'postproduction_state.py')
sm=load('fa204_sm',LIB/'factory_state_manager.py')
rights_preflight=load('fa204_preflight',ROOT/'bridge/income_os_bridge/rights_preflight.py')

F=ROOT/'company/factory-asset/fixtures/governed-canary'
BLUEPRINT=F/'FA-201-shopping-bag-blueprint-v2.json'
FA203=F/'FA-203-registry-qa-result.json'
ORCH=F/'FA-203-postproduction-state.json'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
RESULT=F/'FA-204-metadata-rights-result.json'
OBS=F/'FA-204-rights-observation.json'
NEG=F/'FA-204-rights-negative-control.json'

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def atomic_json(p:Path,v:Any):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--fa202-workspace',type=Path,required=True);ap.add_argument('--fa204-workspace',type=Path,required=True);args=ap.parse_args()
    srcw=args.fa202_workspace.resolve();outw=args.fa204_workspace.resolve();outw.mkdir(parents=True,exist_ok=True)
    bp=json.loads(BLUEPRINT.read_text());fa203=json.loads(FA203.read_text());sid=fa203['semantic_asset_id'];master_sha=fa203['master_qa']['sha256'];master=srcw/'master/master.png'
    if not master.is_file() or sha_file(master)!=master_sha:raise RuntimeError('E_MASTER_DRIFT')
    # Bind exact canonical derivative hashes from FA-203.
    src_paths={'ADOBE_JPEG':srcw/'derivatives/adobe-jpeg.jpg','PNG_PREVIEW':srcw/'derivatives/png-preview.png','WEBP_PREVIEW':srcw/'derivatives/webp-preview.webp'}
    drows=[]
    for d in fa203['derivatives']:
        p=src_paths[d['derivative_id']]
        if not p.is_file() or sha_file(p)!=d['sha256']:raise RuntimeError(f"E_DERIVATIVE_DRIFT:{d['derivative_id']}")
        drows.append({'derivative_id':d['derivative_id'],'format':d['format'],'purpose':d['purpose'],'sha256':d['sha256'],'master_sha256':master_sha,'qa_result':'PASS','qa_sha256':d['sha256'],'sha256_verified':True})
    # Metadata is deterministic and explicitly labels AI provenance.
    provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI','binary_metadata_injected':True,'title_override':'Shopping Bag - Isolated Object','description_override':'Unbranded shopping bag isolated on white for customer-order packing and fulfillment workflows.'}
    metadata=package.build_metadata(blueprint=bp,master_sha256=master_sha,derivative_hashes=drows,provenance=provenance)
    atomic_json(outw/'metadata.json',metadata)
    # Inject XMP/IPTC only into a new listing JPEG; canonical FA-202 derivative remains immutable.
    listing=outw/metadata['listing_filename'];source_jpeg=src_paths['ADOBE_JPEG'];source_before=sha_file(source_jpeg)
    fields={k:metadata[k] for k in ('title','description','keywords','ai_disclosure')}
    if listing.is_file():
        rb=bmeta.readback_jpeg(listing)
        if rb['xmp']!=fields or rb['iptc']!=fields:raise RuntimeError('E_BINARY_METADATA_REUSE_CONFLICT')
        inject={'schema':'die.factory-asset.binary-metadata-injection.v1','result':'IDEMPOTENT_REUSE','format':'JPEG','source_path':str(source_jpeg),'source_sha256':source_before,'output_path':str(listing),'output_sha256':sha_file(listing),'dimensions':[4096,4096],'xmp_readback':'PASS','iptc_readback':'PASS','fields':fields,'immutable_source_preserved':sha_file(source_jpeg)==source_before,'semantic_identity_effect':'NONE','platform_form_ai_disclosure_still_required':True}
    else: inject=bmeta.inject_jpeg(source_path=source_jpeg,output_path=listing,metadata=metadata)
    if sha_file(source_jpeg)!=source_before:raise RuntimeError('E_CANONICAL_DERIVATIVE_MUTATED')
    readback=bmeta.readback_jpeg(listing)
    if readback['xmp']!=fields or readback['iptc']!=fields:raise RuntimeError('E_BINARY_METADATA_READBACK')
    atomic_json(outw/'binary-metadata-injection.json',inject);atomic_json(outw/'binary-metadata-readback.json',readback)
    # Detector runtime truth: no OCR/logo/safety vision runtime is installed on this lane. Uncertainty must block.
    observation={'schema':'die.factory-asset.rights-observation.v1','master_sha256':master_sha,'detectors':{
      'text':{'state':'INCOMPLETE','reason':'OCR_TEXT_DETECTOR_RUNTIME_UNAVAILABLE','detected_strings':[],'confirmed_trademark_terms':[],'trademark_candidates':[],'unresolved_strings':[]},
      'logo':{'state':'INCOMPLETE','reason':'LOGO_DETECTOR_RUNTIME_UNAVAILABLE','candidates':[]},
      'watermark':{'state':'INCOMPLETE','reason':'WATERMARK_DETECTOR_RUNTIME_UNAVAILABLE','candidates':[]},
      'safety':{'state':'INCOMPLETE','reason':'SAFETY_VISION_DETECTOR_RUNTIME_UNAVAILABLE','flags':[]}}}
    atomic_json(OBS,observation)
    rights=rights_gate.evaluate_rights_signals(master_path=master,expected_sha256=master_sha,observation=observation)
    if rights['result']!='REVIEW_REQUIRED':raise RuntimeError('E_RIGHTS_MUST_REVIEW_WITH_INCOMPLETE_DETECTORS')
    # Separate conservative source-rights preflight: lineage is clear, but visual review is not yet clear.
    preflight=rights_preflight.evaluate({'artifact_path':str(master),'artifact_sha256':master_sha,'extracted_text':[],'protected_terms':rights_gate.load_policy()['stock_watermark_terms'],'allowed_terms':[],'detector_findings':[{'class':'uncertain_missing_evidence','signal':'automated visual rights detector runtime unavailable','decision':'UNKNOWN'}],'human_visual_review':{'state':'NOT_REVIEWED','reviewer':'NONE','evidence_ref':'FA-204_PENDING_FOUNDER_RIGHTS_REVIEW'},'release_evidence':{'required':False,'state':'NOT_REQUIRED','refs':[]},'source_lineage_clear':True})
    if preflight['state']!='UNCLEAR' or preflight['hard_veto_expected'] is not True:raise RuntimeError('E_PREFLIGHT_UNCERTAINTY_NOT_BLOCKING')
    # Negative control proves hard veto wiring on this exact master hash without claiming the asset contains a mark.
    negative=json.loads(json.dumps(observation));negative['detectors']={
      'text':{'state':'COMPLETE','detected_strings':['FA204 Synthetic Test Brand'],'confirmed_trademark_terms':['FA204 Synthetic Test Brand'],'trademark_candidates':[],'unresolved_strings':[]},
      'logo':{'state':'COMPLETE','candidates':[]},'watermark':{'state':'COMPLETE','candidates':[]},'safety':{'state':'COMPLETE','flags':[]}}
    neg_result=rights_gate.evaluate_rights_signals(master_path=master,expected_sha256=master_sha,observation=negative)
    if neg_result['result']!='BLOCK':raise RuntimeError('E_HARD_VETO_NEGATIVE_CONTROL')
    atomic_json(NEG,{'schema':'die.factory-asset.fa204-rights-negative-control.v1','synthetic_control':True,'master_sha256':master_sha,'observation':negative,'result':neg_result})
    plan={'schema':'die.factory-asset.derivative-delivery-plan.v1','result':'PLANNED','blueprint_id':bp['blueprint_id'],'semantic_asset_id':sid,'master_sha256':master_sha,'entries':[],'package_blocked':False}
    for d in fa203['derivatives']:
        plan['entries'].append({'derivative_id':d['derivative_id'],'format':d['format'],'purpose':d['purpose'],'compatibility_state':'COMPATIBLE' if d['purpose']=='MARKETPLACE_DELIVERY' else 'INTERNAL'})
    readiness=package.evaluate_package_readiness(blueprint=bp,derivative_plan=plan,rights_signal=rights,derivative_evidence=drows,provenance=provenance,master_technical_qa={'result':'PASS','master_sha256':master_sha})
    if readiness['result']!='PACKAGE_BLOCKED' or 'RIGHTS_REVIEW_REQUIRED' not in readiness['blockers']:raise RuntimeError('E_PACKAGE_MUST_BLOCK_RIGHTS_REVIEW')
    # Advance orchestration only as far as evidence permits: rights review + metadata ready, never PACKAGE_READY.
    st=post.load_state(ORCH)
    if st['state']=='TECHNICAL_QA_PASS': st=post.advance(ORCH,target_state='RIGHTS_SIGNAL_PASS_OR_REVIEW',evidence={'result':'REVIEW_REQUIRED','master_sha256':master_sha,'rights_signal_sha256':hashlib.sha256(json.dumps(rights,sort_keys=True,separators=(',',':')).encode()).hexdigest()},event_id='FA204-RIGHTS-REVIEW',expected_revision=st['revision'])
    st=post.load_state(ORCH)
    if st['state']=='RIGHTS_SIGNAL_PASS_OR_REVIEW': st=post.advance(ORCH,target_state='METADATA_READY',evidence={'master_sha256':master_sha,'metadata_sha256':metadata['metadata_sha256'],'derivative_hashes':[{'derivative_id':x['derivative_id'],'sha256':x['sha256']} for x in drows]},event_id='FA204-METADATA-READY',expected_revision=st['revision'])
    if st['state']!='METADATA_READY' or st['rights_disposition']!='REVIEW_REQUIRED':raise RuntimeError('E_ORCHESTRATION_BOUNDARY')
    commit=sm.advance_asset_metadata_rights(registry_path=REG,semantic_asset_id=sid,metadata=metadata,rights_signal=rights,package_readiness=readiness,writer_id='DIE_STATE_MANAGER')
    replay=sm.advance_asset_metadata_rights(registry_path=REG,semantic_asset_id=sid,metadata=metadata,rights_signal=rights,package_readiness=readiness,writer_id='DIE_STATE_MANAGER')
    if replay['result']!='IDEMPOTENT_REUSE':raise RuntimeError('E_STATE_MANAGER_REPLAY')
    result={'schema':'die.factory-asset.fa204-metadata-rights-result.v1','result':'WAITING_FOUNDER_RIGHTS_REVIEW','task_id':'FA-204','semantic_asset_id':sid,'master_sha256':master_sha,'metadata':metadata,'binary_metadata':inject,'binary_metadata_readback':readback,'rights_signal':rights,'source_rights_preflight':preflight,'hard_veto_negative_control':neg_result,'package_readiness':readiness,'orchestration':{'state':st['state'],'revision':st['revision'],'rights_disposition':st['rights_disposition']},'state_manager_commit':commit,'state_manager_replay':replay,'provider_calls_performed':False,'detector_runtime':{'ocr':False,'logo':False,'watermark':False,'safety_vision':False},'next_action':'FOUNDER_OR_APPROVED_VISUAL_RIGHTS_DETECTOR_MUST_CLEAR_EXACT_MASTER_HASH_BEFORE_PACKAGE_READY','authority':{'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'spend_usd':0}}
    atomic_json(RESULT,result);print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())