import importlib.util,sys
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('dq',R/'company/factory-asset/lib/derivative_qa.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def png(tmp,alpha=False):p=tmp/'x.png';Image.new('RGBA' if alpha else 'RGB',(40,20),(1,2,3,120) if alpha else (1,2,3)).save(p);return p
def test_valid_png_passes(tmp_path):
 p=png(tmp_path);r=m.inspect_derivative(p,expected_format='PNG',expected_dimensions=(40,20),expected_alpha='ABSENT',allowed_formats={'PNG','JPEG'});assert r['result']=='PASS'
def test_corrupt_fails_magic_and_decode(tmp_path):
 p=tmp_path/'bad.png';p.write_bytes(b'not an image');r=m.inspect_derivative(p,expected_format='PNG');assert r['result']=='FAIL';assert 'MAGIC_FORMAT_MISMATCH' in r['failures'];assert 'DECODE_REOPEN_FAILED' in r['failures']
def test_mislabeled_content_fails_magic(tmp_path):
 p=png(tmp_path);r=m.inspect_derivative(p,expected_format='JPEG');assert r['result']=='FAIL';assert 'MAGIC_FORMAT_MISMATCH' in r['failures']
def test_truncated_png_fails_reopen(tmp_path):
 p=png(tmp_path);data=p.read_bytes();p.write_bytes(data[:30]);r=m.inspect_derivative(p,expected_format='PNG');assert r['result']=='FAIL';assert 'DECODE_REOPEN_FAILED' in r['failures']
def test_wrong_alpha_fails(tmp_path):
 p=png(tmp_path,alpha=True);r=m.inspect_derivative(p,expected_format='PNG',expected_alpha='ABSENT');assert r['result']=='FAIL';assert 'ALPHA_MISMATCH' in r['failures']
def test_incompatible_format_fails_even_if_decodable(tmp_path):
 p=png(tmp_path);r=m.inspect_derivative(p,expected_format='PNG',allowed_formats={'JPEG'});assert r['result']=='FAIL';assert 'COMPATIBILITY_FORMAT_FORBIDDEN' in r['failures'];assert r['compatibility']=='INCOMPATIBLE'
def test_hash_mismatch_fails(tmp_path):
 p=png(tmp_path);r=m.inspect_derivative(p,expected_format='PNG',expected_sha256='a'*64);assert r['result']=='FAIL';assert 'SHA256_MISMATCH' in r['failures']