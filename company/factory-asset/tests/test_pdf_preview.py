import importlib.util,json,sys
from pathlib import Path
import jsonschema,pytest
from PIL import Image
from PyPDF2 import PdfReader
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('pp',R/'company/factory-asset/lib/pdf_preview.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);RS=json.loads((R/'company/factory-asset/schemas/derivative-receipt.schema.json').read_text())
def master(tmp):p=tmp/'m.png';Image.new('RGB',(400,200),(20,30,40)).save(p);return p
def recipe(p):return {'schema':'die.factory-asset.derivative-recipe.v1','recipe_id':'raster-pdf-preview-v1','recipe_version':'1.0.0','input':{'master_sha256':m.sha256_file(p),'semantic_asset_id':'FASA-PDF_TEST_001','format':'PNG'},'output':{'format':'PDF','purpose':'PREVIEW','width_px':400,'height_px':200,'color_space':'SRGB','alpha_policy':'FLATTEN_WHITE','semantic_identity_effect':'NONE'},'marketplace_profile':{'platform_id':'ADOBE_STOCK','profile_revision':'1.0'},'idempotency':{'key_material':['master_sha256','recipe_id','recipe_version','marketplace_profile.platform_id','marketplace_profile.profile_revision','output'],'output_collision_action':'VERIFY_HASH_AND_REUSE_OR_FAIL'},'qa':{'magic_mime_match':True,'decode_reopen':True,'sha256':True,'dimensions_if_raster':True},'compatibility':{'unknown_action':'BLOCK_PACKAGE','require_profile_match':True}}
def test_pdf_is_deterministic_and_reopens_with_embedded_image(tmp_path):
 p=master(tmp_path);a=tmp_path/'a.pdf';b=tmp_path/'b.pdf';ra=m.render_pdf_derivative(p,a,recipe(p));rb=m.render_pdf_derivative(p,b,recipe(p));assert a.read_bytes()==b.read_bytes();jsonschema.Draft202012Validator(RS).validate(ra);assert ra['result']=='PASS';reader=PdfReader(str(a),strict=True);assert len(reader.pages)==1;assert int(float(reader.pages[0].mediabox.width))==400
def test_preview_preserves_aspect_and_never_upscales(tmp_path):
 p=master(tmp_path);out=tmp_path/'preview.png';r=m.render_preview(p,out,max_dimension=100,format='PNG');assert r['preview_dimensions']==[100,50];assert r['aspect_error']==0;assert r['decode_reopen'] and r['magic_match']
def test_preview_same_input_same_bytes(tmp_path):
 p=master(tmp_path);a=tmp_path/'a.jpg';b=tmp_path/'b.jpg';m.render_preview(p,a,max_dimension=120,format='JPEG');m.render_preview(p,b,max_dimension=120,format='JPEG');assert a.read_bytes()==b.read_bytes()
def test_pdf_never_overwrites_master(tmp_path):
 p=master(tmp_path)
 with pytest.raises(m.PackagingError) as e:m.render_pdf_derivative(p,p,recipe(p))
 assert e.value.code=='MASTER_OVERWRITE_FORBIDDEN'

def test_pdf_alpha_requires_explicit_white_flatten(tmp_path):
 p=tmp_path/'alpha.png';Image.new('RGBA',(40,20),(10,20,30,0)).save(p);r=recipe(p);r['output']['alpha_policy']='PRESERVE'
 with pytest.raises(m.PackagingError) as e:m.render_pdf_derivative(p,tmp_path/'alpha.pdf',r)
 assert e.value.code=='PDF_ALPHA_POLICY_REQUIRED'
