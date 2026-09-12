#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE=Path(__file__).resolve(); H01=HERE.parents[1]
sys.path.insert(0,str(H01/'engineering'))
from svg_prompt_composer_v2 import compile_master_instruction, compile_provider_prompt, sha256_value, sha256_text

PROFILE={'claude':'CLAUDE_WEB','chatgpt':'CHATGPT_WEB','qwen':'QWEN_WEB','gemini':'GEMINI_WEB','manus':'MANUS_WEB','copilot':'GENERIC_WEB_AI'}

def safe_id(s:str)->str:return re.sub(r'[^A-Z0-9]+','_',s.upper()).strip('_')[:48]

def noun_class(item):
 s=str(item.get('suitability',''))
 for c in ('animal','plant','food','body','artifact','object'):
  if f'noun.{c}' in s:return c
 return 'object'

def build_blueprint(item):
 noun=item['canonical_name']; cls=noun_class(item)
 view={'animal':'clear side or three-quarter iconic view','plant':'clear front-biased botanical view','food':'clear three-quarter product view','artifact':'clear three-quarter product view','body':'clear front-biased educational icon view','object':'clear iconic view'}[cls]
 anchors=[f'immediately recognizable generic {noun} silhouette',f'distinctive major features typical of a real {noun}',f'plausible proportions for a generic {noun}']
 components=[f'primary body or dominant form of the {noun}',f'major characteristic parts required to recognize a {noun}']
 materials={'animal':['natural surface cues appropriate to the animal without photoreal fur detail'],'plant':['natural botanical surface cues without photoreal texture'],'food':['clean simplified food/material cues without photoreal texture'],'artifact':['generic unbranded material cues appropriate to the object'],'body':['clean anatomical form cues suitable for stock illustration'],'object':['generic material cues appropriate to the object']}[cls]
 use=f'editable isolated {noun} vector for stock design, ecommerce, education, presentations, interfaces and compositing'
 bp={
 'schema':'die.h01.svg-blueprint.v2','blueprint_id':f"H01BP-{safe_id(noun)}-{item['source_candidate_id'].replace('CAND-','')}",'queue_id':item['queue_item_id'],'source_candidate_id':item['source_candidate_id'],'semantic_asset_id':f"H01SVG-{item['source_candidate_id']}",
 'production_contract':{'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1'},
 'subject':{'canonical_name':noun,'recognition_anchors':anchors,'essential_components':components,'proportion_notes':[f'credible generic {noun} proportions','avoid exaggerated or novelty proportions unless inherent to recognition'],'material_notes':materials,'color_notes':['limited harmonious stock-friendly palette','clear shape separation at thumbnail size'],'texture_notes':['minimal texture','clean flat vector surfaces without noisy grain']},
 'commercial':{'primary_use_case':use,'buyer_value':f'clean reusable {noun} object that can be recolored, resized and composed into many layouts','stock_suitability':'generic unbranded universally recognizable standalone object with broad design utility and no contextual dependency','reuse_contexts':['ecommerce compositions','editorial layouts','education graphics','presentation diagrams','interface and web design']},
 'visual':{'viewpoint':view,'composition':['single object only','centered with generous transparent margin','complete silhouette fully visible with no crop','no scene or unrelated props'],'visual_hierarchy':[f'{noun} silhouette reads first','major recognition features remain distinct at thumbnail size'],'style_system':['clean contemporary stock vector','simple editable shapes','crisp geometry','subtle dimensional separation without photorealism']},
 'vector':{'editability':'NATIVE_EDITABLE_VECTOR','shape_language':['few purposeful paths and primitive shapes','closed clean contours','avoid microscopic decorative geometry'],'stroke_policy':'use no stroke unless a small structural edge requires one; keep any stroke simple and consistent','fill_policy':'use solid fills only with a compact palette and no bitmap textures','depth_policy':'express depth through overlapping shapes and restrained flat color separation, not filters or raster effects'},
 'complexity':{'max_svg_bytes':524288,'max_geometry_elements':256,'max_total_points':4096,'max_path_chars':16384,'max_group_depth':32},
 'rights':{'trademark_free':True,'copyright_safe':True,'no_readable_text':True,'no_watermark':True,'forbidden_content':['logos','brand marks','copyrighted character imagery','trade dress','readable text','watermarks']},
 'output_contract':{'format':'SVG','native_vector_required':True,'transparent_background':True,'allowed_elements':['g','path','rect','circle','ellipse','line','polyline','polygon'],'allowed_path_commands':['M','L','H','V','C','S','Q','T','A','Z'],'forbidden_svg_features':['script','external references','embedded raster image','foreignObject','text','style','defs','symbol','use']}
 }
 return bp

def compact_manus(bp,master):
 s=bp['subject']; c=bp['commercial']; v=bp['visual']; x=bp['complexity']; r=bp['rights']; out=bp['output_contract']
 text=(f"Return exactly one complete raw <svg>...</svg> and nothing else. Preserve every requirement. "
 f"SUBJECT: one standalone {s['canonical_name']}; recognition: {'; '.join(s['recognition_anchors'])}; components: {'; '.join(s['essential_components'])}; proportions: {'; '.join(s['proportion_notes'])}; materials: {'; '.join(s['material_notes'])}; colors: {'; '.join(s['color_notes'])}. "
 f"COMMERCIAL: {c['primary_use_case']}; {c['stock_suitability']}. COMPOSITION: {v['viewpoint']}; single centered object, transparent generous margin, full silhouette, no crop/scene/props, thumbnail-readable. "
 f"STYLE: clean contemporary native editable vector, crisp simple purposeful geometry, solid fills, compact palette, no bitmap texture, filters, raster effects or photorealism; overlap/flat color only for depth. "
 f"LIMITS: SVG<={x['max_svg_bytes']} bytes, geometry<={x['max_geometry_elements']}, points<={x['max_total_points']}, path d<={x['max_path_chars']} chars, group depth<={x['max_group_depth']}. "
 f"RIGHTS: no logos/trademarks/brand marks/trade dress/copyrighted characters/readable text/watermark. SVG: genuine native source, transparent, no background rect; elements only {','.join(out['allowed_elements'])}; path commands only {','.join(out['allowed_path_commands'])}; forbid {','.join(out['forbidden_svg_features'])}. Root finite viewBox + visible editable geometry. No submission/publication authority.")
 if len(text)>2950: raise ValueError(f'MANUS_COMPACT_TOO_LONG:{len(text)}')
 return {'schema':'die.h01.svg-provider-prompt.v2','composer_revision':'H01-108-COMPACT-1','provider_profile':'MANUS_WEB','blueprint_id':bp['blueprint_id'],'blueprint_sha256':sha256_value(bp),'master_instruction_sha256':master['master_instruction_sha256'],'prompt':text,'prompt_chars':len(text),'prompt_budget_chars':3000,'prompt_sha256':sha256_text(text),'semantic_omission_count':0,'authority':{'provider_call_authorized':False,'submission_authorized':False,'publication_authorized':False},'prompt_variant':'COMPACT_SEMANTIC_EQUIVALENT_UI_3000_CHAR_LIMIT'}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--position',type=int,required=True); ap.add_argument('--provider',required=True); ap.add_argument('--out-dir',required=True); ns=ap.parse_args()
 m=json.loads(Path(ns.manifest).read_text()); item=next((x for x in m['items'] if x['batch_position']==ns.position),None)
 if not item: raise SystemExit('E_POSITION')
 bp=build_blueprint(item); master=compile_master_instruction(bp); profile=PROFILE[ns.provider]
 prompt=compact_manus(bp,master) if ns.provider=='manus' else compile_provider_prompt(blueprint=bp,master=master,provider_profile=profile)
 out=Path(ns.out_dir); out.mkdir(parents=True,exist_ok=True)
 for name,val in [('blueprint.json',bp),('master-instruction.json',master),('provider-prompt.json',prompt),('batch-item.json',item)]: (out/name).write_text(json.dumps(val,indent=2,sort_keys=True)+'\n')
 (out/'prompt.txt').write_text(prompt['prompt']+'\n')
 print(json.dumps({'status':'PASS','position':ns.position,'noun':item['canonical_name'],'provider':ns.provider,'blueprint_sha256':sha256_value(bp),'master_sha256':master['master_instruction_sha256'],'prompt_sha256':prompt['prompt_sha256'],'prompt_chars':prompt['prompt_chars']}))
if __name__=='__main__':main()
