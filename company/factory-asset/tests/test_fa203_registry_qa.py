from pathlib import Path
import copy, importlib.util, json, sys
ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,LIB/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;assert spec and spec.loader;spec.loader.exec_module(m);return m
sm=load('fa203_sm_test','factory_state_manager.py')
F=ROOT/'company/factory-asset/fixtures/governed-canary'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
RESULT=F/'FA-203-registry-qa-result.json'
FA202=F/'FA-202-live-result.json'

def _proposal(): return json.loads(FA202.read_text())['master']['staging']['state_manager_proposal']
def _evidence():
    r=json.loads(RESULT.read_text());return {'schema':'die.factory-asset.asset-registry-commit-evidence.v1','semantic_asset_id':r['semantic_asset_id'],'blueprint_id':'FABP-FA200_SHOPPING_BAG_FULFILLMENT','master':{'sha256':r['master_qa']['sha256'],'technical_qa':'PASS'},'derivatives':[{k:v for k,v in x.items() if k in {'derivative_id','sha256','technical_qa','semantic_identity_effect'}} for x in r['derivatives']],'package_compatibility':r['package_compatibility'],'capacity':r['capacity'],'orchestration':r['orchestration'],'authority':r['authority']}

def test_fa203_canonical_registry_has_one_asset_one_physical_master():
    d=json.loads(REG.read_text());assert d['canonical_writer']=='DIE_STATE_MANAGER';assert d['revision']==1;assert len(d['assets'])==1;assert len(d['physical_masters'])==1
    a=d['assets'][0];assert a['canonical_truth'] is True;assert a['state']=='TECHNICAL_QA_PASS';assert a['rights_state']=='REVIEW_REQUIRED';assert a['package_state']=='METADATA_RIGHTS_PENDING'

def test_fa203_result_truth_boundaries_and_qa():
    r=json.loads(RESULT.read_text());assert r['result']=='PASS';assert r['provider_calls_performed'] is False;assert r['master_qa']['result']=='PASS';assert all(x['technical_qa']=='PASS' for x in r['derivatives']);assert r['registry']['semantic_asset_count']==1;assert r['registry']['physical_master_count']==1
    assert r['package_compatibility']['package_ready'] is False;assert r['rights_state']=='REVIEW_REQUIRED';assert r['metadata_state']=='PENDING_FA204';assert r['capacity']['routing_eligible_now'] is False;assert r['capacity']['evidence_type']=='OBSERVED_SUCCESS_NOT_QUOTA_GUESS';assert r['orchestration']['state']=='TECHNICAL_QA_PASS'

def test_state_manager_replay_and_conflict_fail_closed(tmp_path):
    p=_proposal();e=_evidence();rp=tmp_path/'r.json'
    one=sm.commit_asset(registry_path=rp,proposal=p,evidence=e,writer_id='DIE_STATE_MANAGER');two=sm.commit_asset(registry_path=rp,proposal=p,evidence=e,writer_id='DIE_STATE_MANAGER')
    assert one['result']=='COMMITTED';assert two['result']=='IDEMPOTENT_REUSE';assert sm.load_registry(rp)['revision']==1
    bad=copy.deepcopy(e);bad['master']['sha256']='a'*64;bp=copy.deepcopy(p);bp['master_sha256']='a'*64
    try:sm.commit_asset(registry_path=rp,proposal=bp,evidence=bad,writer_id='DIE_STATE_MANAGER');assert False
    except sm.FactoryStateManagerError as ex:assert ex.code=='SEMANTIC_ASSET_CONFLICT'

def test_state_manager_writer_identity_required(tmp_path):
    try:sm.commit_asset(registry_path=tmp_path/'r.json',proposal=_proposal(),evidence=_evidence(),writer_id='ARCHITECT');assert False
    except sm.FactoryStateManagerError as ex:assert ex.code=='WRITER_ID_FORBIDDEN'

def test_physical_master_duplicate_suppression_does_not_duplicate_blob(tmp_path):
    p=_proposal();e=_evidence();rp=tmp_path/'r.json';sm.commit_asset(registry_path=rp,proposal=p,evidence=e,writer_id='DIE_STATE_MANAGER')
    p2=copy.deepcopy(p);e2=copy.deepcopy(e);p2['semantic_asset_id']='FASA-SHOPPING_BAG_FULFILLMENT_ALT';e2['semantic_asset_id']=p2['semantic_asset_id']
    c=sm.commit_asset(registry_path=rp,proposal=p2,evidence=e2,writer_id='DIE_STATE_MANAGER');d=sm.load_registry(rp)
    assert c['duplicate_suppressed'] is True;assert len(d['assets'])==2;assert len(d['physical_masters'])==1