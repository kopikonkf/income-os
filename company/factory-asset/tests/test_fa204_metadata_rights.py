from pathlib import Path
import copy, importlib.util, json, sys
ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
F=ROOT/'company/factory-asset/fixtures/governed-canary'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
RESULT=F/'FA-204-metadata-rights-result.json'

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,LIB/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;assert spec and spec.loader;spec.loader.exec_module(m);return m
sm=load('fa204_sm_test','factory_state_manager.py')

def test_metadata_and_ai_disclosure_are_exact_hash_bound():
    r=json.loads(RESULT.read_text());m=r['metadata']
    assert r['result']=='WAITING_FOUNDER_RIGHTS_REVIEW'
    assert m['master_sha256']==r['master_sha256']=='5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06'
    assert m['ai_generated'] is True and m['ai_disclosure']=='GENERATIVE_AI' and m['source_class']=='GENERATIVE_AI'
    assert len(m['keywords'])>=3 and m['binary_metadata_injected'] is True
    assert {x['derivative_id'] for x in m['derivative_hashes']}=={'ADOBE_JPEG','PNG_PREVIEW','WEBP_PREVIEW'}

def test_binary_metadata_readback_and_source_immutability():
    r=json.loads(RESULT.read_text());b=r['binary_metadata'];rb=r['binary_metadata_readback'];m=r['metadata']
    assert b['result'] in {'PASS','IDEMPOTENT_REUSE'} and b['immutable_source_preserved'] is True
    expected={k:m[k] for k in ('title','description','keywords','ai_disclosure')}
    assert rb['xmp']==expected and rb['iptc']==expected
    assert b['source_sha256']=='49d116013c9241ae7c12e7b9cc64abb9709db189416fec7a1828df78cf8f9cfd'
    assert b['output_sha256']!=b['source_sha256'] and b['semantic_identity_effect']=='NONE'

def test_rights_uncertainty_blocks_package_and_negative_control_hard_vetoes():
    r=json.loads(RESULT.read_text());rights=r['rights_signal'];pre=r['source_rights_preflight'];neg=r['hard_veto_negative_control']
    assert rights['result']=='REVIEW_REQUIRED' and rights['signal_gate_pass'] is False
    assert set(rights['detector_states'].values())=={'INCOMPLETE'}
    assert pre['state']=='UNCLEAR' and pre['hard_veto_expected'] is True and pre['legal_clearance_claimed'] is False
    assert neg['result']=='BLOCK' and any(x['signal']=='TRADEMARK_CONFIRMED' for x in neg['blocking_signals'])
    assert r['package_readiness']['result']=='PACKAGE_BLOCKED' and 'RIGHTS_REVIEW_REQUIRED' in r['package_readiness']['blockers']

def test_registry_canonical_enrichment_stops_before_package_ready():
    d=json.loads(REG.read_text());a=d['assets'][0]
    assert d['revision']==2 and a['metadata_sha256']=='3a8d362ae8877a500d550988a72f800d00ee81a2cf76bd186f3b3c449633d27a'
    assert a['rights_state']=='REVIEW_REQUIRED';assert a['state']=='METADATA_READY_RIGHTS_REVIEW_REQUIRED';assert a['package_state']=='PACKAGE_BLOCKED_RIGHTS_REVIEW'
    assert a['canonical_truth'] is True and a['authority']['submission_authorized'] is False and a['authority']['publication_authorized'] is False

def test_state_manager_enrichment_replay_and_conflict_fail_closed(tmp_path):
    base=json.loads(REG.read_text());base['revision']=1;base['history']=base['history'][:1];a=base['assets'][0]
    for k in ['metadata_sha256','rights_signal_sha256','metadata_rights_enrichment_sha256']:
        a.pop(k,None)
    a['state']='TECHNICAL_QA_PASS';a['rights_state']='REVIEW_REQUIRED';a['package_state']='METADATA_RIGHTS_PENDING'
    rp=tmp_path/'r.json';rp.write_text(json.dumps(base))
    r=json.loads(RESULT.read_text());one=sm.advance_asset_metadata_rights(registry_path=rp,semantic_asset_id=r['semantic_asset_id'],metadata=r['metadata'],rights_signal=r['rights_signal'],package_readiness=r['package_readiness'],writer_id='DIE_STATE_MANAGER');two=sm.advance_asset_metadata_rights(registry_path=rp,semantic_asset_id=r['semantic_asset_id'],metadata=r['metadata'],rights_signal=r['rights_signal'],package_readiness=r['package_readiness'],writer_id='DIE_STATE_MANAGER')
    assert one['result']=='COMMITTED' and two['result']=='IDEMPOTENT_REUSE'
    bad=copy.deepcopy(r['metadata']);bad['title']='conflicting title';bad['metadata_sha256']='a'*64
    try:sm.advance_asset_metadata_rights(registry_path=rp,semantic_asset_id=r['semantic_asset_id'],metadata=bad,rights_signal=r['rights_signal'],package_readiness=r['package_readiness'],writer_id='DIE_STATE_MANAGER');assert False
    except sm.FactoryStateManagerError as e:assert e.code in {'METADATA_RIGHTS_CONFLICT','METADATA_DERIVATIVE_HASH_MISMATCH'}