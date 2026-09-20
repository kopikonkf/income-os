#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/'config'
PSR_REG=CFG/'lane2-object-psr-registry.v1.json'
HC_LANES=CFG/'human-scene-lanes.v1.json'
HC_FAMILIES=CFG/'human-commercial-families.v1.json'
HOLD=CFG/'lane23-activation-hold.v1.json'
AUTHORITY='NEXABURST_TYPED_VISUAL_CONTRACT_V2'

DIMENSIONS=('human','activity','object','place','time','demographic','emotion','problem','industry','commercial_intent')

class ContractError(RuntimeError): pass

def cjson(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def sha(v:Any)->str:
    return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else cjson(v)).hexdigest()

def safe(s:str)->str:
    return re.sub(r'[^A-Z0-9]+','-',str(s).upper()).strip('-')

def load(path:Path)->dict:
    return json.loads(path.read_text(encoding='utf-8'))

def index(items:list[dict],key:str)->dict[str,dict]:
    return {str(x[key]):x for x in items}

def common_system_rules()->list[str]:
    return [
      'Create one commercially useful stock asset that obeys the frozen visual contract.',
      'Preserve subject and scene truth; do not invent brands, logos, readable text, watermarks, or unrelated props.',
      'Do not create collage, border, mockup frame, fake UI text, or duplicated subjects unless explicitly required.',
      'Composition must communicate the commercial job-to-be-done in one glance.',
      'Human anatomy, hand-object interaction, eye-line, scale, perspective, lighting and object placement must be coherent.',
      'The provider may choose rendering details only inside the frozen constraints; it may not change semantic identity.'
    ]

def compile_object_psr(req:dict)->dict:
    reg=load(PSR_REG); lanes=index(reg['lanes'],'lane_id')
    lane_id=str(req.get('lane_id') or 'PSR-L0')
    lane=lanes.get(lane_id)
    if not lane: raise ContractError('E_OBJECT_LANE_UNKNOWN:'+lane_id)
    if lane.get('status') not in {'DESIGN_READY_NOT_LIVE','FUTURE_DESIGN_ONLY'}:
        raise ContractError('E_OBJECT_LANE_STATUS')
    cid=str(req.get('candidate_id') or '').strip(); noun=str(req.get('noun') or '').strip()
    if not cid or not noun: raise ContractError('E_OBJECT_SUBJECT_REQUIRED')
    spec=req.get('subject_spec') or {}
    recognition=[str(x).strip() for x in spec.get('recognition_anchors',[]) if str(x).strip()]
    essential=[str(x).strip() for x in spec.get('essential_components',[]) if str(x).strip()]
    forbidden=[str(x).strip() for x in spec.get('forbidden_mutations',[]) if str(x).strip()]
    semantic_asset_id=f"NBPSR-{safe(cid.replace('CAND-','C'))}-{safe(lane_id)}"
    contract={
      'schema':'die.h01.nexaburst.object-expression-contract.v1',
      'authority':AUTHORITY,'engine_id':reg['engine_id'],'semantic_asset_id':semantic_asset_id,
      'candidate_id':cid,'noun':noun,'lane_id':lane_id,
      'commercial_expression':{
        'buyer_utility':lane['buyer_utility'],
        'distinctness_requirements':lane.get('distinctness_from_wc') or lane.get('distinctness_from_l0') or []
      },
      'subject_spec':{
        'noun':noun,'recognition_anchors':recognition,'essential_components':essential,
        'forbidden_mutations':forbidden
      },
      'visual_requirement':{
        'composition':lane['composition'],'style':lane.get('style',{}),
        'forbidden':sorted(set(lane.get('forbidden',[])+forbidden))
      },
      'activation':'PREPARED_NOT_AUTHORIZED'
    }
    prompt=[
      f"SUBJECT: {noun}.",
      "COMMERCIAL PURPOSE: "+'; '.join(lane['buyer_utility'])+'.',
      f"VISUAL EXPRESSION: {lane['name']}.",
      "COMPOSITION: "+', '.join(f"{k}={v}" for k,v in lane['composition'].items())+'.',
    ]
    if lane.get('style'):
        prompt.append("STYLE/FIDELITY: "+', '.join(f"{k}={v}" for k,v in lane['style'].items())+'.')
    if recognition: prompt.append("RECOGNITION ANCHORS: "+'; '.join(recognition)+'.')
    if essential: prompt.append("ESSENTIAL COMPONENTS: "+'; '.join(essential)+'.')
    prompt.append("DISTINCTNESS: "+'; '.join(contract['commercial_expression']['distinctness_requirements'])+'.')
    prompt.append("FORBIDDEN: "+'; '.join(contract['visual_requirement']['forbidden'])+'.')
    contract_sha=sha(contract)
    system_prompt=' '.join(common_system_rules())
    provider_prompt=' '.join(prompt)
    final_provider_prompt=system_prompt+'\n\n'+provider_prompt
    return {
      'schema':'die.h01.nexaburst.compiled-preproduction.v1','kind':'OBJECT_EXPRESSION',
      'semantic_asset_id':semantic_asset_id,'lane_id':lane_id,'contract':contract,
      'contract_sha256':contract_sha,'system_prompt':system_prompt,
      'provider_prompt':provider_prompt,'provider_prompt_sha256':sha(provider_prompt.encode()),
      'final_provider_prompt':final_provider_prompt,'final_provider_prompt_sha256':sha(final_provider_prompt.encode()),
      'dispatch_authorized':False
    }

def validate_scene_dimensions(dim:dict):
    missing=[k for k in DIMENSIONS if not str(dim.get(k) or '').strip()]
    if missing: raise ContractError('E_SCENE_DIMENSIONS_MISSING:'+','.join(missing))

def compile_human_scene(req:dict)->dict:
    lane_reg=load(HC_LANES); family_reg=load(HC_FAMILIES)
    lanes=index(lane_reg['lanes'],'lane_id'); families=index(family_reg['families'],'family_id')
    lane_id=str(req.get('lane_id') or '').strip(); family_id=str(req.get('family_id') or '').strip()
    lane=lanes.get(lane_id); family=families.get(family_id)
    if not lane: raise ContractError('E_HC_LANE_UNKNOWN:'+lane_id)
    if not family: raise ContractError('E_HC_FAMILY_UNKNOWN:'+family_id)
    if lane_id not in family.get('eligible_lanes',[]): raise ContractError('E_FAMILY_LANE_INELIGIBLE')
    dim=req.get('dimensions') or {};validate_scene_dimensions(dim)
    story=req.get('story') or {}
    for k in ('job_to_be_done','commercial_buyer','problem_signal'):
        if not str(story.get(k) or '').strip(): raise ContractError('E_SCENE_STORY_REQUIRED:'+k)
    object_ids=[str(x).strip() for x in req.get('object_candidate_ids',[]) if str(x).strip()]
    scene_key={
      'family_id':family_id,'lane_id':lane_id,'dimensions':{k:str(dim[k]).strip() for k in DIMENSIONS},
      'job_to_be_done':str(story['job_to_be_done']).strip(),'object_candidate_ids':object_ids
    }
    scene_hash=sha(scene_key)[:16].upper()
    semantic_asset_id=f"NBHC-{safe(family_id.replace('HF-',''))}-{safe(lane_id)}-{scene_hash}"
    contract={
      'schema':'die.h01.nexaburst.human-scene-contract.v1','authority':AUTHORITY,
      'engine_id':lane_reg['engine_id'],'semantic_asset_id':semantic_asset_id,
      'family':{'family_id':family_id,'name':family['name'],'anchors':family['anchors']},
      'lane':{'lane_id':lane_id,'name':lane['name'],'job':lane['job'],'composition':lane['composition']},
      'dimensions':{k:str(dim[k]).strip() for k in DIMENSIONS},
      'object_atlas':{'candidate_ids':object_ids,'role':family['object_atlas_role']},
      'story':{
        'job_to_be_done':str(story['job_to_be_done']).strip(),
        'commercial_buyer':str(story['commercial_buyer']).strip(),
        'problem_signal':str(story['problem_signal']).strip(),
        'interaction':str(story.get('interaction') or dim['activity']).strip(),
        'copy_space':str(story.get('copy_space') or 'SUBJECT_APPROPRIATE').strip(),
        'anti_cliche':list(story.get('anti_cliche') or [])
      },
      'visual_requirement':{
        'required_scene_fields':lane['required'],
        'composition':lane['composition'],
        'forbidden':sorted(set(lane_reg.get('global_forbidden',[])+list(story.get('anti_cliche') or [])))
      },
      'activation':'PREPARED_NOT_AUTHORIZED','h03_dependency':False,'web_ai_cognition_dependency':False
    }
    d=contract['dimensions']; st=contract['story']
    prompt=[
      f"COMMERCIAL SCENE FAMILY: {family['name']}.",
      f"SCENE EXPRESSION: {lane['name']} — {lane['job']}.",
      f"HUMAN: {d['human']}; DEMOGRAPHIC: {d['demographic']}.",
      f"ACTION: {d['activity']}. OBJECT EVIDENCE: {d['object']}. PLACE: {d['place']}. TIME: {d['time']}.",
      f"EMOTION: {d['emotion']}. PROBLEM: {d['problem']}. INDUSTRY: {d['industry']}. COMMERCIAL INTENT: {d['commercial_intent']}.",
      f"BUYER: {st['commercial_buyer']}. JOB-TO-BE-DONE: {st['job_to_be_done']}. PROBLEM SIGNAL: {st['problem_signal']}.",
      f"INTERACTION: {st['interaction']}. COMPOSITION: {lane['composition']}. COPY SPACE: {st['copy_space']}.",
      "FORBIDDEN: "+'; '.join(contract['visual_requirement']['forbidden'])+'.'
    ]
    contract_sha=sha(contract);provider_prompt=' '.join(prompt)
    system_prompt=' '.join(common_system_rules()+[
        'Humans are demand/story carriers, not decorative extras.',
        'Every visible object must support the activity, problem, environment or buyer message.',
        'Avoid generic posed stock scenes; prefer believable task evidence and interaction.'
      ])
    final_provider_prompt=system_prompt+'\n\n'+provider_prompt
    return {
      'schema':'die.h01.nexaburst.compiled-preproduction.v1','kind':'HUMAN_SCENE',
      'semantic_asset_id':semantic_asset_id,'lane_id':lane_id,'family_id':family_id,
      'contract':contract,'contract_sha256':contract_sha,
      'system_prompt':system_prompt,
      'provider_prompt':provider_prompt,'provider_prompt_sha256':sha(provider_prompt.encode()),
      'final_provider_prompt':final_provider_prompt,'final_provider_prompt_sha256':sha(final_provider_prompt.encode()),
      'dispatch_authorized':False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('kind',choices=['object-psr','human-scene'])
    ap.add_argument('--request',required=True,type=Path)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    req=json.loads(args.request.read_text(encoding='utf-8'))
    out=compile_object_psr(req) if args.kind=='object-psr' else compile_human_scene(req)
    text=json.dumps(out,indent=2,ensure_ascii=False)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text,encoding='utf-8')
    print(json.dumps({'status':'COMPILED_NOT_AUTHORIZED','kind':out['kind'],'semantic_asset_id':out['semantic_asset_id'],
                      'lane_id':out['lane_id'],'contract_sha256':out['contract_sha256'],
                      'provider_prompt_sha256':out['provider_prompt_sha256'],'dispatch_authorized':False},sort_keys=True))
if __name__=='__main__':
    try: main()
    except ContractError as e:
        raise SystemExit(str(e))