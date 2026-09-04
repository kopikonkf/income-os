import importlib.util,sys
from pathlib import Path
import pytest
from PIL import Image,PngImagePlugin
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('dp',R/'company/factory-asset/lib/derivative_policy.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def master(tmp,alpha=True,comment=True):
 p=tmp/'m.png';img=Image.new('RGBA' if alpha else 'RGB',(80,60),(20,30,40,128) if alpha else (20,30,40));info=PngImagePlugin.PngInfo();
 if comment:info.add_text('comment','safe-note');info.add_text('unsafe','drop-me')
 img.save(p,pnginfo=info);return p
def pol(**kw):
 x={'color_space':'SRGB','icc_policy':'EMBED_SRGB','alpha_policy':'FLATTEN_WHITE','dpi':300,'metadata_policy':'STRIP_ALL'};x.update(kw);return x
def test_policy_embeds_srgb_flattens_alpha_sets_dpi_and_strips_metadata(tmp_path):
 p=master(tmp_path);r=m.apply_policy(p,tmp_path/'o.jpg',format='JPEG',policy=pol());assert r['result']=='PASS';assert r['icc_state']=='EMBEDDED';assert r['alpha_state']=='ABSENT';assert r['dpi_ok'];assert r['metadata_ok']
def test_preserve_alpha_is_verified(tmp_path):
 p=master(tmp_path);r=m.apply_policy(p,tmp_path/'o.png',format='PNG',policy=pol(alpha_policy='PRESERVE'));assert r['result']=='PASS';assert r['alpha_state']=='PRESENT'
def test_forbid_alpha_rejects_alpha_source(tmp_path):
 p=master(tmp_path)
 with pytest.raises(m.DerivativePolicyError) as e:m.apply_policy(p,tmp_path/'o.png',format='PNG',policy=pol(alpha_policy='FORBID'))
 assert e.value.code=='ALPHA_FORBIDDEN'
def test_preserve_source_icc_never_guesses_when_missing(tmp_path):
 p=master(tmp_path)
 with pytest.raises(m.DerivativePolicyError) as e:m.apply_policy(p,tmp_path/'o.png',format='PNG',policy=pol(icc_policy='PRESERVE_SOURCE'))
 assert e.value.code=='SOURCE_ICC_REQUIRED'
def test_invalid_or_incomplete_policy_fails_closed():
 x=pol();x.pop('dpi')
 with pytest.raises(m.DerivativePolicyError) as e:m.validate_policy(x)
 assert e.value.code=='POLICY_INCOMPLETE'