import hashlib, importlib.util, json, sys
from pathlib import Path
import jsonschema, pytest
from PIL import Image
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('rd',R/'company/factory-asset/lib/raster_derivative.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load(); RECEIPT_SCHEMA=json.loads((R/'company/factory-asset/schemas/derivative-receipt.schema.json').read_text())
def make_master(tmp,alpha=True):
 p=tmp/'master.png'; img=Image.new('RGBA' if alpha else 'RGB',(64,48),(255,0,0,128) if alpha else (255,0,0)); img.save(p); return p
def recipe(master,fmt,alpha):
 return {'schema':'die.factory-asset.derivative-recipe.v1','recipe_id':f'raster-{fmt.lower()}-test-v1','recipe_version':'1.0.0','input':{'master_sha256':m.sha256_file(master),'semantic_asset_id':'FASA-TEST_ASSET_001','format':'PNG'},'output':{'format':fmt,'purpose':'MARKETPLACE_DELIVERY','width_px':32,'height_px':24,'color_space':'SRGB','alpha_policy':alpha,'quality':90,'semantic_identity_effect':'NONE'},'marketplace_profile':{'platform_id':'ADOBE_STOCK','profile_revision':'1.0'},'idempotency':{'key_material':['master_sha256','recipe_id','recipe_version','marketplace_profile.platform_id','marketplace_profile.profile_revision','output'],'output_collision_action':'VERIFY_HASH_AND_REUSE_OR_FAIL'},'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256':True,'dimensions_if_raster':True},'compatibility':{'unknown_action':'BLOCK_PACKAGE','require_profile_match':True}}
@pytest.mark.parametrize('fmt,alpha',[('JPEG','FLATTEN_WHITE'),('WEBP','PRESERVE'),('TIFF','PRESERVE')])
def test_pinned_raster_outputs_decode_and_validate(tmp_path,fmt,alpha):
 master=make_master(tmp_path); out=tmp_path/f'out.{fmt.lower()}'; rec=m.render_raster_derivative(master,out,recipe(master,fmt,alpha)); jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(rec); assert rec['result']=='PASS'; assert rec['output']['width_px']==32 and rec['output']['height_px']==24
 with Image.open(out) as im: im.load(); assert im.format==fmt

def test_jpeg_alpha_requires_explicit_flatten(tmp_path):
 master=make_master(tmp_path)
 with pytest.raises(m.RasterDerivativeError) as e:m.render_raster_derivative(master,tmp_path/'x.jpg',recipe(master,'JPEG','PRESERVE'))
 assert e.value.code=='ALPHA_POLICY_REQUIRED'
def test_never_overwrites_master(tmp_path):
 master=make_master(tmp_path)
 with pytest.raises(m.RasterDerivativeError) as e:m.render_raster_derivative(master,master,recipe(master,'JPEG','FLATTEN_WHITE'))
 assert e.value.code=='MASTER_OVERWRITE_FORBIDDEN'
def test_master_hash_must_match(tmp_path):
 master=make_master(tmp_path); r=recipe(master,'WEBP','PRESERVE');r['input']['master_sha256']='a'*64
 with pytest.raises(m.RasterDerivativeError) as e:m.render_raster_derivative(master,tmp_path/'x.webp',r)
 assert e.value.code=='MASTER_HASH_MISMATCH'
def test_same_recipe_same_bytes(tmp_path):
 master=make_master(tmp_path);r=recipe(master,'JPEG','FLATTEN_WHITE');a=tmp_path/'a.jpg';b=tmp_path/'b.jpg';m.render_raster_derivative(master,a,r);m.render_raster_derivative(master,b,r);assert a.read_bytes()==b.read_bytes()