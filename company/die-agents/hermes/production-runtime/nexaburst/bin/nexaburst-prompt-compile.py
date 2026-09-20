#!/opt/die/factory-asset/venv/bin/python
from __future__ import annotations
import argparse, importlib.util, json, re, sys
from pathlib import Path

BASE=Path('/home/kopiko/die-sessions/NEXABURST-H01-P001')
PC=Path('/srv/die/company/factory-asset/lib/production_prompt_compiler.py')
REG=BASE/'config/nexaburst-presets.v1.json'
ANCHORS=BASE/'config/challenge-anchors-10.json'

def loadmod():
    spec=importlib.util.spec_from_file_location('nexaburst_pc',PC)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
    sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod
pc=loadmod()

def safe(s,limit=60):
    return re.sub(r'[^A-Z0-9]+','_',str(s).upper()).strip('_')[:limit] or 'OBJECT'

def subject_class(suit):
    return {
      'lexname=noun.plant':'PLANT','lexname=noun.animal':'ANIMAL',
      'lexname=noun.artifact':'SIMPLE_OBJECT','lexname=noun.object':'SIMPLE_OBJECT',
      'lexname=noun.food':'OTHER'
    }.get(suit,'OTHER')

def anchors_by_name():
    if not ANCHORS.is_file(): return {}
    return {x['noun'].casefold():x for x in json.loads(ANCHORS.read_text(encoding='utf-8'))}

def make_subject(noun,seed_id=None,candidate_id=None,suitability='lexname=noun.artifact'):
    anchor=anchors_by_name().get(noun.casefold())
    if anchor:
        cls=anchor['subject_class']
        seed_id=anchor.get('seed_id') or seed_id
        primary=anchor['primary_form']
        comps=anchor['components']
        recogn=anchor['anchors']
        attrs=anchor['natural_attributes']
        spatial=anchor['spatial_relationships']
        forbidden=anchor['forbidden_subject_mutations']
        evidence_ref=seed_id or candidate_id or 'OBJECT_ATLAS_NOUN'
    else:
        cls=subject_class(suitability)
        primary=f'one generic unbranded {noun} in its common immediately recognizable form'
        comps=[]
        recogn=[f'clear canonical silhouette and defining form of a {noun}',f'natural recognizable proportions appropriate to a {noun}']
        attrs=['generic unbranded appearance',f'materials, colors and visible details appropriate to a typical {noun}']
        spatial=[]
        forbidden=['do not merge the subject with unrelated objects','do not distort the subject beyond immediate recognizability']
        evidence_ref=seed_id or candidate_id or 'OBJECT_ATLAS_NOUN'
    sid='FASS-NB_'+safe(seed_id or candidate_id or noun)
    v={
      'schema':'die.factory-asset.subject-spec.v1','subject_spec_id':sid,
      'seed_id':seed_id if seed_id and re.fullmatch(r'SEED-[0-9]{6}',seed_id) else None,
      'canonical_name':noun,'subject_class':cls,'primary_form':primary,
      'essential_components':comps,'recognition_anchors':recogn,'natural_attributes':attrs,
      'spatial_relationships':spatial,'forbidden_subject_mutations':forbidden,
      'evidence':{'basis':'MANUAL_CANON','refs':['NEXABURST_PHASE1_DETERMINISTIC_SUBJECT_RULE_V1',evidence_ref]}
    }
    pc.validate_subject_spec(v); return v

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--noun',required=True); ap.add_argument('--seed-id'); ap.add_argument('--candidate-id')
    ap.add_argument('--suitability',default='lexname=noun.artifact')
    ap.add_argument('--preset',default='ISOLATED_SOFT_WATERCOLOR_CLIPART_WHITE_L0')
    ap.add_argument('--asset-id')
    a=ap.parse_args()
    registry=json.loads(REG.read_text(encoding='utf-8')); pc.validate_preset_registry(registry)
    preset=next((x for x in registry['presets'] if x['preset_id']==a.preset),None)
    if not preset: raise SystemExit(f'E_PRESET_NOT_FOUND:{a.preset}')
    asset_id=a.asset_id or ('NB-'+safe(a.noun))
    semantic_id='FASA-NB_'+safe(asset_id)
    subject=make_subject(a.noun,a.seed_id,a.candidate_id,a.suitability)
    visual=pc.resolve_visual_requirements(subject_spec=subject,semantic_asset_id=semantic_id,preset_id=a.preset,registry=registry)
    compiled=pc.compile_provider_prompt(subject_spec=subject,visual_spec=visual)
    out={
      'asset_id':asset_id,'seed_id':a.seed_id,'candidate_id':a.candidate_id,'noun':a.noun,
      'suitability':a.suitability,'preset_id':a.preset,
      'style':preset['style']['variant'].lower().replace('_','-'),'aspect':1,
      'prompt_authority':'TYPED_VISUAL_CONTRACT_V1','prompt':compiled['provider_prompt'],
      'prompt_sha256':compiled['provider_prompt_sha256'],
      'compiled_contract_sha256':compiled['compiled_contract_sha256'],
      'subject_spec':subject,'visual_spec':visual
    }
    print(json.dumps(out,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__': main()
