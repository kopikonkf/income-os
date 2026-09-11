import importlib.util,json,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
def load():
 s=importlib.util.spec_from_file_location('pps',R/'company/factory-asset/lib/postproduction_state.py');m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
m=load();SHA='a'*64
def test_cannot_skip_state(tmp_path):
 p=tmp_path/'s.json';d=m.create_state(p,job_id='JOB-FA138-001',semantic_asset_id='FASA-TEST_ASSET_001',blueprint_id='FABP-TEST_ASSET_001',source_master_sha256=SHA)
 with pytest.raises(m.PostproductionStateError) as e:m.advance(p,target_state='WAITING_FOUNDER_QC',evidence={'founder_qc_required':True,'human_rights_clearance':False,'package_plan_sha256':'b'*64},event_id='EVENT-001',expected_revision=0)
 assert e.value.code=='STATE_TRANSITION_INVALID'
def test_replay_is_idempotent_and_stale_write_rejected(tmp_path):
 p=tmp_path/'s.json';d=m.create_state(p,job_id='JOB-FA138-002',semantic_asset_id='FASA-TEST_ASSET_001',blueprint_id='FABP-TEST_ASSET_001',source_master_sha256=SHA);ev={'result':'PASS','master_sha256':SHA};d=m.advance(p,target_state='MASTER_VALIDATED',evidence=ev,event_id='EVENT-001',expected_revision=0);r=m.advance(p,target_state='MASTER_VALIDATED',evidence=ev,event_id='EVENT-001',expected_revision=0);assert r['revision']==1
 with pytest.raises(m.PostproductionStateError) as e:m.advance(p,target_state='UPSCALE_DECIDED',evidence={'result':'NOOP','source_sha256':SHA,'source_unchanged':True,'final_sha256':SHA},event_id='EVENT-002',expected_revision=0)
 assert e.value.code=='STALE_REVISION'
def test_failure_resume_preserves_source_lineage(tmp_path):
 p=tmp_path/'s.json';d=m.create_state(p,job_id='JOB-FA138-003',semantic_asset_id='FASA-TEST_ASSET_001',blueprint_id='FABP-TEST_ASSET_001',source_master_sha256=SHA);d=m.record_failure(p,code='TEMP_FAIL',retryable=True,stage='ARTIFACT_CREATED',evidence={'attempt':1},event_id='FAIL-001',expected_revision=0);assert d['status']=='BLOCKED' and d['source_master_sha256']==SHA;d=m.resume_retry(p,event_id='RESUME-001',expected_revision=1);assert d['status']=='ACTIVE' and d['source_master_sha256']==SHA and [x['kind'] for x in d['history']][-2:]==['FAILURE','RESUME']
def test_nonretryable_failure_stays_blocked(tmp_path):
 p=tmp_path/'s.json';d=m.create_state(p,job_id='JOB-FA138-004',semantic_asset_id='FASA-TEST_ASSET_001',blueprint_id='FABP-TEST_ASSET_001',source_master_sha256=SHA);d=m.record_failure(p,code='RIGHTS_FAILED',retryable=False,stage='ARTIFACT_CREATED',evidence={},event_id='FAIL-001',expected_revision=0)
 with pytest.raises(m.PostproductionStateError) as e:m.resume_retry(p,event_id='RESUME-001',expected_revision=1)
 assert e.value.code=='FAILURE_NOT_RETRYABLE'

def test_active_master_repair_is_append_only_and_only_allowed_before_derivatives(tmp_path):
 p=tmp_path/'s.json';src='a'*64;old='b'*64;new='c'*64
 d=m.create_state(p,job_id='J',semantic_asset_id='S',blueprint_id='B',source_master_sha256=src)
 d=m.advance(p,target_state='MASTER_VALIDATED',evidence={'result':'PASS','master_sha256':src},event_id='M',expected_revision=d['revision'])
 d=m.advance(p,target_state='UPSCALE_DECIDED',evidence={'result':'PASS','source_sha256':src,'source_unchanged':True,'final_sha256':old},event_id='U',expected_revision=d['revision'])
 e={'repair_kind':'BOUNDED_MASTER_NORMALIZATION','prior_active_master_sha256':old,'new_active_master_sha256':new}
 d2=m.repair_active_master(p,expected_prior_sha256=old,new_active_master_sha256=new,evidence=e,event_id='R',expected_revision=d['revision'])
 assert d2['state']=='UPSCALE_DECIDED' and d2['active_master_sha256']==new and d2['revision']==3
 assert d2['history'][-1]['kind']=='ACTIVE_MASTER_REPAIR' and d2['history'][-1]['from']==d2['history'][-1]['to']=='UPSCALE_DECIDED'
 assert m.repair_active_master(p,expected_prior_sha256=old,new_active_master_sha256=new,evidence=e,event_id='R',expected_revision=d2['revision'])==d2

def test_active_master_repair_rejects_wrong_prior_hash(tmp_path):
 p=tmp_path/'s.json';src='a'*64;old='b'*64;new='c'*64
 d=m.create_state(p,job_id='J',semantic_asset_id='S',blueprint_id='B',source_master_sha256=src)
 d=m.advance(p,target_state='MASTER_VALIDATED',evidence={'result':'PASS','master_sha256':src},event_id='M',expected_revision=d['revision'])
 d=m.advance(p,target_state='UPSCALE_DECIDED',evidence={'result':'PASS','source_sha256':src,'source_unchanged':True,'final_sha256':old},event_id='U',expected_revision=d['revision'])
 e={'repair_kind':'BOUNDED_MASTER_NORMALIZATION','prior_active_master_sha256':'d'*64,'new_active_master_sha256':new}
 with pytest.raises(m.PostproductionStateError,match='ACTIVE_MASTER_REPAIR_PRIOR_HASH_MISMATCH'):m.repair_active_master(p,expected_prior_sha256='d'*64,new_active_master_sha256=new,evidence=e,event_id='R',expected_revision=d['revision'])
