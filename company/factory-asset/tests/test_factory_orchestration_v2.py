import importlib.util,json,sys
from PIL import Image
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def load():
 p=R/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py';s=importlib.util.spec_from_file_location('fv2test',p);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load()
def legacy():return {'blueprint_id':'BP-PROD-TEST001','seed':{'id':'SEED-999001','canonical_name':'shopping bag','object_class':'container','category_path':'commerce/retail'},'family':{'buyer_persona':['E-commerce designer'],'use_cases':['Compose clean retail product layouts']},'production':{'master_prompt':'Create an isolated shopping bag on a clean white background with no logos.'},'metadata_direction':{'title_direction':'Isolated shopping bag for ecommerce composition'}}
def test_legacy_bridge_produces_valid_isolated_expression_and_v2_blueprint(tmp_path):
 bp=legacy();plan,v2=m.project_legacy_raster_blueprint(legacy_blueprint=bp,blueprint_sha256=m.csha(bp),workspace=tmp_path);assert plan['evidence'][0]['kind']=='OBJECT_ATLAS_SEED';assert plan['expressions'][0]['semantic_mode']=='ISOLATED_OBJECT';assert v2['asset_type']=='ISOLATED_OBJECT' and v2['producer_class']=='RASTER_GENERATIVE';assert v2['semantic_identity']['subject']=='shopping bag'
def test_telegram_event_is_idempotent(tmp_path):
 w=tmp_path/'PRODTEST';w.mkdir();sent=[];a=m.telegram_event(w,'ARTIFACT_CREATED',{'seed':'shopping bag'},sent.append);b=m.telegram_event(w,'ARTIFACT_CREATED',{'seed':'shopping bag'},sent.append);assert a['event_id']==b['event_id'];assert len(sent)==1;assert b['delivery']=='IDEMPOTENT_REUSE';assert len((w/'factory-v2/telegram-events.jsonl').read_text().splitlines())==1
def test_listing_slug_is_human_readable_and_collision_bounded():
 assert m.slug('Shopping Bag / Retail')=='shopping-bag-retail'

def test_founder_facing_alias_is_group_readable_but_not_world_readable(tmp_path):
 p=tmp_path/'listing.jpg';p.write_bytes(b'jpeg');p.chmod(0o600);m.make_founder_readable(p);assert (p.stat().st_mode & 0o777)==0o640


def test_bounded_master_normalization_preserves_aspect_and_caps_oversized_x4(tmp_path):
 x4=tmp_path/'x4.png';active=tmp_path/'active.png';Image.new('RGB',(112,64),(10,20,30)).save(x4)
 before=m.sha(x4);rec=m.normalize_upscaled_master(x4_path=x4,active_path=active,min_width=20,min_height=20,min_megapixels=0.0004,preferred_max_edge=40,max_pixels=1600)
 assert rec['method']=='REALESRGAN_X4_THEN_LANCZOS_DOWNSAMPLE'
 assert rec['input_dimensions']==[112,64] and rec['output_dimensions']==[40,23]
 assert rec['aspect_ratio_preserved'] is True and m.sha(x4)==before and active.is_file()
 with Image.open(active) as im:assert im.size==(40,23) and im.format=='PNG'

def test_bounded_master_dimension_policy_keeps_sane_x4_and_fails_closed_on_impossible_extreme():
 assert m.bounded_master_dimensions(4096,4096)==(4096,4096)
 assert m.bounded_master_dimensions(11264,6144)==(4096,2235)
 try:m.bounded_master_dimensions(80000,4000)
 except m.FactoryOrchestrationError as exc:assert exc.code=='BOUNDED_MASTER_PIXEL_LIMIT'
 else:raise AssertionError('extreme aspect must fail closed')
