import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];s=importlib.util.spec_from_file_location('pc',R/'company/factory-asset/lib/package_composer.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def file(tmp,name,data):p=tmp/name;p.write_bytes(data);return p
def rows(tmp):
 a=file(tmp,'a.jpg',b'jpegbytes');b=file(tmp,'b.webp',b'webpbytes');return [
 {'derivative_id':'ADOBE_JPEG','source_path':str(a),'format':'JPEG','purpose':'MARKETPLACE_DELIVERY','recipe_id':'raster-jpeg-stock-v1','receipt_ref':'receipt://jpeg','compatibility_state':'COMPATIBLE'},
 {'derivative_id':'WEB_PREVIEW','source_path':str(b),'format':'WEBP','purpose':'PREVIEW','recipe_id':'raster-webp-preview-v1','receipt_ref':'receipt://webp','compatibility_state':'COMPATIBLE'}]
def test_dry_run_package_contains_exact_files_and_refs(tmp_path):
 r=m.compose_dry_run_package(package_dir=tmp_path/'pkg',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=rows(tmp_path),metadata_ref='metadata://m1',rights_ref='rights://r1',compatibility_receipt_ref='compat://c1');assert r['result']=='PASS';assert r['semantic_asset_count']==1;assert r['derivative_count']==2;manifest=json.loads((tmp_path/'pkg/manifest.json').read_text());assert manifest['publication_action']=='NONE' and manifest['upload_action']=='NONE';assert len(manifest['deliverables'])==2
 for item in manifest['deliverables']:assert (tmp_path/'pkg'/item['package_path']).read_bytes() in (b'jpegbytes',b'webpbytes')
def test_manifest_is_deterministic(tmp_path):
 ra=rows(tmp_path);m.compose_dry_run_package(package_dir=tmp_path/'a',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=ra,metadata_ref='m://1',rights_ref='r://1',compatibility_receipt_ref='c://1');m.compose_dry_run_package(package_dir=tmp_path/'b',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=list(reversed(ra)),metadata_ref='m://1',rights_ref='r://1',compatibility_receipt_ref='c://1');assert (tmp_path/'a/manifest.json').read_bytes()==(tmp_path/'b/manifest.json').read_bytes()
def test_incompatible_derivative_rejected(tmp_path):
 x=rows(tmp_path);x[0]['compatibility_state']='INCOMPATIBLE'
 with pytest.raises(m.PackageComposerError) as e:m.compose_dry_run_package(package_dir=tmp_path/'pkg',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=x,metadata_ref='m',rights_ref='r',compatibility_receipt_ref='c')
 assert e.value.code=='DELIVERABLE_INCOMPATIBLE'
def test_missing_metadata_rights_or_compat_ref_rejected(tmp_path):
 with pytest.raises(m.PackageComposerError):m.compose_dry_run_package(package_dir=tmp_path/'pkg',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=rows(tmp_path),metadata_ref='',rights_ref='r',compatibility_receipt_ref='c')
def test_duplicate_derivative_id_rejected(tmp_path):
 x=rows(tmp_path);x[1]['derivative_id']=x[0]['derivative_id']
 with pytest.raises(m.PackageComposerError) as e:m.compose_dry_run_package(package_dir=tmp_path/'pkg',semantic_asset_id='FASA-PKG_TEST_001',master_sha256='a'*64,deliverables=x,metadata_ref='m',rights_ref='r',compatibility_receipt_ref='c')
 assert e.value.code=='DUPLICATE_DERIVATIVE_ID'