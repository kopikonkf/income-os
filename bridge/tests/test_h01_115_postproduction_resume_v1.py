import hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company/company-os/die-h01/engineering/h01_108_finalize.py'
S=importlib.util.spec_from_file_location('h01115finalize',MOD);M=importlib.util.module_from_spec(S);assert S and S.loader;sys.modules[S.name]=M;S.loader.exec_module(M)

def h(b):return hashlib.sha256(b).hexdigest()
def setup_workspace(root:Path):
 w=root/'w';p=w/'postproduction';p.mkdir(parents=True)
 original=b'<svg>provider</svg>';canonical=b'<svg>canonical</svg>';preview=b'jpg-bytes'
 (p/'provider-original.svg').write_bytes(original);(p/'canonical-master.svg').write_bytes(canonical);(p/'preview.jpg').write_bytes(preview)
 generation={'provider_original_sha256':h(original)};validation={'canonical_svg_sha256':h(canonical)};bp={'semantic_asset_id':'H01SVG-CAND-1'}
 receipt={'result':'PASS','semantic_asset_id':bp['semantic_asset_id'],'lineage':{'provider_original_sha256':h(original),'canonical_svg_sha256':h(canonical)},'artifacts':[{'path':'provider-original.svg','sha256':h(original),'source_role':'PROVIDER_ORIGINAL','format':'SVG'},{'path':'canonical-master.svg','sha256':h(canonical),'source_role':'CANONICAL_MASTER','format':'SVG'},{'path':'preview.jpg','sha256':h(preview),'source_role':'CANONICAL_MASTER','format':'JPG'}]}
 (p/'postproduction.receipt.json').write_text(json.dumps(receipt));return w,generation,validation,bp,receipt

def test_verified_existing_package_is_reused_without_rewrite():
 with tempfile.TemporaryDirectory() as td:
  w,g,v,bp,receipt=setup_workspace(Path(td));before={x.name:x.read_bytes() for x in (w/'postproduction').iterdir()}
  out=M.verified_existing_postproduction(w,g,v,bp);assert out==receipt
  after={x.name:x.read_bytes() for x in (w/'postproduction').iterdir()};assert after==before
  r=json.loads((w/'postproduction-resume.receipt.json').read_text());assert r['status']=='REUSED_VERIFIED_IMMUTABLE_PACKAGE';assert r['provider_generation_dispatched'] is False;assert r['generation_validity_effect']=='NONE'

def test_existing_package_tamper_fails_closed():
 with tempfile.TemporaryDirectory() as td:
  w,g,v,bp,_=setup_workspace(Path(td));(w/'postproduction/preview.jpg').write_bytes(b'tampered')
  with pytest.raises(SystemExit,match='E_EXISTING_POSTPRODUCTION_ARTIFACT_HASH'):M.verified_existing_postproduction(w,g,v,bp)

def test_existing_package_lineage_mismatch_fails_closed():
 with tempfile.TemporaryDirectory() as td:
  w,g,v,bp,_=setup_workspace(Path(td));bad=dict(v);bad['canonical_svg_sha256']='0'*64
  with pytest.raises(SystemExit,match='E_EXISTING_POSTPRODUCTION_CANONICAL_LINEAGE'):M.verified_existing_postproduction(w,g,bad,bp)

def test_missing_receipt_allows_fresh_generation_path():
 with tempfile.TemporaryDirectory() as td:
  w=Path(td)/'w';w.mkdir();assert M.verified_existing_postproduction(w,{}, {}, {}) is None
