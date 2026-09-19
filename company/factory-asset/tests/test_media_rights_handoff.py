from __future__ import annotations
import hashlib,importlib.util,json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib/media_rights_handoff.py'
spec=importlib.util.spec_from_file_location('media_rights_handoff',LIB);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m)

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def base(tmp_path:Path):
 w=tmp_path/'job';f=w/'final';f.mkdir(parents=True);asset=f/'asset.png';asset.write_bytes(b'png-payload');h=sha(asset)
 pkg={'result':'PACKAGE_READY','package_plan':{'package_plan_sha256':'a'*64}}
 rights={'result':'PASS','master_sha256':'b'*64}
 fm={'task_id':'JOB-1','semantic_asset_id':'FASA-1','blueprint_id':'FABP-1','listing_path':str(asset),'listing_sha256':h,'founder_qc':'PENDING'}
 delivery={'derivative_id':'PNG_DELIVERY','sha256':h,'qa_result':'PASS','receipt_ref':'receipt://qa'}
 return w,asset,h,pkg,rights,fm,delivery

def test_review_required_without_explicit_rights_authorization(tmp_path,monkeypatch):
 w,asset,h,pkg,rights,fm,delivery=base(tmp_path);monkeypatch.delenv('DIE_MEDIA_PUBLIC_BASE_URL',raising=False)
 out=m.build_handoff(workspace=w,package_readiness=pkg,rights_signal=rights,final_manifest=fm,delivery_evidence=delivery)
 assert out['schema']==m.SCHEMA and out['artifact']['sha256']==h
 assert out['artifact']['delivery_state']=='DELIVERY_URL_PENDING' and out['artifact']['source_uri'] is None
 assert out['rights']['state']=='REVIEW_REQUIRED' and out['rights']['publish_allowed'] is False
 assert out['authority']['publication_authorized'] is False
 ob=m.emit_outbox(workspace=w,manifest=out)
 assert ob['state']=='PENDING' and Path(ob['path']).is_file()
 assert m.deliver_outbox(out)['state']=='DEFERRED_NOT_CONFIGURED'

def test_explicit_hash_bound_rights_authorization_attests_and_binds_https(tmp_path,monkeypatch):
 w,asset,h,pkg,rights,fm,delivery=base(tmp_path)
 auth=w/'rights-authorization.json'
 auth.write_text(json.dumps({'schema':m.AUTH_SCHEMA,'artifact_sha256':h,'basis':'owned_original','publish_allowed':True,'commercial_use_allowed':True,'derivatives_allowed':True,'attribution_required':False,'attribution_text':None,'evidence_refs':['receipt:founder-rights'],'authorized_by':'founder','state':'APPROVED'}))
 monkeypatch.setenv('DIE_MEDIA_PUBLIC_BASE_URL','https://artifacts.example/h01')
 out=m.build_handoff(workspace=w,package_readiness=pkg,rights_signal=rights,final_manifest=fm,delivery_evidence=delivery,rights_authorization_path=auth)
 assert out['rights']['state']=='ATTESTED' and out['rights']['commercial_use_allowed'] is True
 assert out['artifact']['source_uri']=='https://artifacts.example/h01/asset.png'
 assert out['artifact']['delivery_state']=='READY'
 assert out['rights']['rights_ref'].startswith('h01-rights:')

def test_handoff_fails_closed_on_hash_mismatch(tmp_path):
 w,asset,h,pkg,rights,fm,delivery=base(tmp_path);delivery['sha256']='0'*64
 with pytest.raises(m.MediaRightsHandoffError) as exc:m.build_handoff(workspace=w,package_readiness=pkg,rights_signal=rights,final_manifest=fm,delivery_evidence=delivery)
 assert exc.value.code=='DELIVERY_HASH_MISMATCH'

def test_production_orchestration_wires_durable_handoff():
 src=(ROOT/'company/die-agents/hermes/production-runtime/factory_orchestration_v2.py').read_text()
 for needle in ('media_rights_handoff.py','build_handoff(','emit_outbox(','deliver_outbox(','media-rights-handoff-result.json'):assert needle in src
