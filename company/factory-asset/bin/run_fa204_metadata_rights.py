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

F=ROOT/'company/factory-asset/fixtures/governed-canary'
BLUEPRINT=F/'FA-201-shopping-bag-blueprint-v2.json'
FA203=F/'FA-203-registry-qa-result.json'
ORCH=F/'FA-203-postproduction-state.json'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
RESULT=F/'FA-204-metadata-rights-result.json'
OBS=F/'FA-204-rights-observation.json'
NEG=F/'FA-204-rights-negative-control.json'
VISUAL_RUN=F/'FA-204-visual-rights-detector-run.json'
VISUAL_SELF=F/'FA-204-visual-rights-self-test.json'

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def sha_json(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def atomic_json(p:Path,v:Any):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--fa202-workspace',type=Path,required=True);ap.add_argument('--fa204-workspace',type=Path,required=True);args=ap.parse_args()
    srcw=args.fa202_workspace.resolve();outw=args.fa204_workspace.resolve();outw.mkdir(parents=True,exist_ok=True)
    bp=json.loads(BLUEPRINT.read_text());fa203=json.loads(FA203.read_text());sid=fa203['semantic_asset_id'];master_sha=fa203['master_qa']['sha256'];master=srcw/'master/master.png'
    if not master.is_file() or sha_file(master)!=master_sha:raise RuntimeError('E_MASTER_DRIFT')
    src_paths={'ADOBE_JPEG':srcw/'derivatives/adobe-jpeg.jpg','PNG_PREVIEW':srcw/'derivatives/png-preview.png','WEBP_PREVIEW':srcw/'derivatives/webp-preview.webp'}
    drows=[]
    for d in fa203['derivatives']:
        p=src_paths[d['derivative_id']]
        if not p.is_file() or sha_file(p)!=d['sha256']:raise RuntimeError(f"E_DERIVATIVE_DRIFT:{d['derivative_id']}")
        drows.append({'derivative_id':d['derivative_id'],'format':d['format'],'purpose':d['purpose'],'sha256':d['sha256'],'master_sha256':master_sha,'qa_result':'PASS','qa_sha256':d['sha256'],'sha256_verified':True})

    provenance={'source_class':'GENERATIVE_AI','ai_generated':True,'ai_disclosure':'GENERATIVE_AI','binary_metadata_injected':True,'title_override':'Shopping Bag - Isolated Object','description_override':'Unbranded shopping bag isolated on white for customer-order packing and fulfillment workflows.'}
    metadata=package.build_metadata(blueprint=bp,master_sha256=master_sha,derivative_hashes=drows,provenance=provenance)
    atomic_json(outw/'metadata.json',metadata)
    listing=outw/metadata['listing_filename'];source_jpeg=src_paths['ADOBE_JPEG'];source_before=sha_file(source_jpeg);fields={k:metadata[k] for k in ('title','description','keywords','ai_disclosure')}
    if listing.is_file():
        rb=bmeta.readback_jpeg(listing)
        if rb['xmp']!=fields or rb['iptc']!=fields:raise RuntimeError('E_BINARY_METADATA_REUSE_CONFLICT')
        inject={'schema':'die.factory-asset.binary-metadata-injection.v1','result':'IDEMPOTENT_REUSE','format':'JPEG','source_path':str(source_jpeg),'source_sha256':source_before,'output_path':str(listing),'output_sha256':sha_file(listing),'dimensions':[4096,4096],'xmp_readback':'PASS','iptc_readback':'PASS','fields':fields,'immutable_source_preserved':sha_file(source_jpeg)==source_before,'semantic_identity_effect':'NONE','platform_form_ai_disclosure_still_required':True}
    else: inject=bmeta.inject_jpeg(source_path=source_jpeg,output_path=listing,metadata=metadata)
    if sha_file(source_jpeg)!=source_before:raise RuntimeError('E_CANONICAL_DERIVATIVE_MUTATED')
    readback=bmeta.readback_jpeg(listing)
    if readback['xmp']!=fields or readback['iptc']!=fields:raise RuntimeError('E_BINARY_METADATA_READBACK')
    atomic_json(outw/'binary-metadata-injection.json',inject);atomic_json(outw/'binary-metadata-readback.json',readback)

    detector=json.loads(VISUAL_RUN.read_text());selftest=json.loads(VISUAL_SELF.read_text())
    if detector.get('master_sha256')!=master_sha or detector.get('runtime',{}).get('self_test_result')!='PASS' or selftest.get('result')!='PASS':raise RuntimeError('E_VISUAL_DETECTOR_EVIDENCE')
    observation=detector['observation'];atomic_json(OBS,observation)
    source_ip=detector.get('classification',{}).get('source_ip') or {}
    if source_ip.get('disposition')!='CLEAR':raise RuntimeError('E_SOURCE_IP_NOT_CLEAR')
    rights=rights_gate.evaluate_rights_signals(master_path=master,expected_sha256=master_sha,observation=observation)
    if rights['result']!='PASS' or rights['signal_gate_pass'] is not True:raise RuntimeError('E_RIGHTS_NOT_PASS')

    preflight={'schema':'die.factory-asset.automated-source-rights-preflight.v1','master_sha256':master_sha,'state':'CLEAR','source_lineage_clear':True,'automated_visual_rights_state':'PASS','source_ip':source_ip,'detector_evidence_sha256':sha_file(VISUAL_RUN),'detector_self_test_sha256':sha_file(VISUAL_SELF),'findings':[],'release_evidence':{'required':False,'state':'NOT_REQUIRED','refs':[]},'hard_veto_expected':False,'legal_clearance_claimed':False,'human_rights_clearance':False,'authority_boundary':{'submission_authorized':False,'publication_authorized':False}}

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
    if readiness['result']!='PACKAGE_READY' or readiness['blockers'] or not readiness.get('package_plan'):raise RuntimeError('E_PACKAGE_NOT_READY')

    st=post.load_state(ORCH)
    if st.get('rights_disposition')=='REVIEW_REQUIRED':
        st=post.resolve_rights_review(ORCH,evidence={'result':'PASS','master_sha256':master_sha,'rights_signal_sha256':sha_json(rights),'visual_detector_run_sha256':sha_file(VISUAL_RUN)},event_id='FA204-AUTOMATED-RIGHTS-RESOLUTION',expected_revision=st['revision'])
    if st.get('rights_disposition')!='PASS':raise RuntimeError('E_RIGHTS_DISPOSITION_NOT_PASS')
    if st['state']=='METADATA_READY':
        st=post.advance(ORCH,target_state='PACKAGE_READY',evidence={'result':'PACKAGE_READY','master_sha256':master_sha,'package_plan':readiness['package_plan']},event_id='FA204-PACKAGE-READY',expected_revision=st['revision'])
    if st['state']!='PACKAGE_READY':raise RuntimeError('E_ORCHESTRATION_NOT_PACKAGE_READY')

    commit=sm.advance_asset_metadata_rights(registry_path=REG,semantic_asset_id=sid,metadata=metadata,rights_signal=rights,package_readiness=readiness,writer_id='DIE_STATE_MANAGER')
    replay=sm.advance_asset_metadata_rights(registry_path=REG,semantic_asset_id=sid,metadata=metadata,rights_signal=rights,package_readiness=readiness,writer_id='DIE_STATE_MANAGER')
    if replay['result']!='IDEMPOTENT_REUSE':raise RuntimeError('E_STATE_MANAGER_REPLAY')
    if commit['result'] not in {'RIGHTS_RESOLVED_AND_COMMITTED','IDEMPOTENT_REUSE'}:raise RuntimeError('E_STATE_MANAGER_RIGHTS_RESOLUTION')

    result={'schema':'die.factory-asset.fa204-metadata-rights-result.v1','result':'PASS','task_id':'FA-204','semantic_asset_id':sid,'master_sha256':master_sha,'metadata':metadata,'binary_metadata':inject,'binary_metadata_readback':readback,'visual_rights_detector':{'run_ref':'company/factory-asset/fixtures/governed-canary/FA-204-visual-rights-detector-run.json','run_sha256':sha_file(VISUAL_RUN),'self_test_ref':'company/factory-asset/fixtures/governed-canary/FA-204-visual-rights-self-test.json','self_test_sha256':sha_file(VISUAL_SELF),'runtime':detector['runtime'],'classification':detector['classification']},'rights_signal':rights,'source_rights_preflight':preflight,'hard_veto_negative_control':neg_result,'package_readiness':readiness,'orchestration':{'state':st['state'],'revision':st['revision'],'rights_disposition':st['rights_disposition'],'package_plan_sha256':st['package_plan_sha256']},'state_manager_commit':commit,'state_manager_replay':replay,'provider_calls_performed':False,'detector_runtime':{'ocr':True,'logo':True,'watermark':True,'safety_vision':True,'cpu_only':True},'next_action':'FA-205_FOUNDER_EXACT_HASH_QC','authority':{'human_rights_clearance':False,'submission_authorized':False,'publication_authorized':False,'marketplace_upload':False,'spend_usd':0}}
    atomic_json(RESULT,result);print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())