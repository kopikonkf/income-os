from pathlib import Path
import copy, importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib'
F=ROOT/'company/factory-asset/fixtures/governed-canary'
REG=ROOT/'company/factory-asset/registries/governed-canary-assets.v1.json'
RESULT=F/'FA-204-metadata-rights-result.json'
GRAPH=ROOT/'company/factory-asset/task-graph-v1.json'


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,LIB/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;assert spec and spec.loader;spec.loader.exec_module(m);return m

sm=load('fa204_sm_test','factory_state_manager.py')


def test_metadata_and_ai_disclosure_are_exact_hash_bound():
    r=json.loads(RESULT.read_text());m=r['metadata']
    assert r['result']=='PASS'
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


def test_complete_visual_rights_pass_and_hard_veto_control():
    r=json.loads(RESULT.read_text());rights=r['rights_signal'];pre=r['source_rights_preflight'];neg=r['hard_veto_negative_control']
    assert rights['result']=='PASS' and rights['signal_gate_pass'] is True
    assert set(rights['detector_states'].values())=={'COMPLETE'}
    assert rights['blocking_signals']==[] and rights['review_signals']==[]
    assert pre['state']=='CLEAR' and pre['hard_veto_expected'] is False and pre['legal_clearance_claimed'] is False and pre['human_rights_clearance'] is False
    assert neg['result']=='BLOCK' and any(x['signal']=='TRADEMARK_CONFIRMED' for x in neg['blocking_signals'])
    assert r['package_readiness']['result']=='PACKAGE_READY' and r['package_readiness']['blockers']==[]
    assert r['authority']['human_rights_clearance'] is False


def test_registry_and_orchestration_advance_to_package_ready_without_submission_authority():
    d=json.loads(REG.read_text());a=d['assets'][0];r=json.loads(RESULT.read_text())
    assert d['revision']==3
    assert a['metadata_sha256']=='3a8d362ae8877a500d550988a72f800d00ee81a2cf76bd186f3b3c449633d27a'
    assert a['rights_state']=='PASS';assert a['state']=='PACKAGE_READY';assert a['package_state']=='PACKAGE_READY'
    assert a['package_plan_sha256']==r['package_readiness']['package_plan']['package_plan_sha256']=='e5912d1892f5faeedf0a931076ac8d34f7854e6ba12635f0c5840554a69a326b'
    assert r['orchestration']['state']=='PACKAGE_READY' and r['orchestration']['rights_disposition']=='PASS'
    assert a['canonical_truth'] is True and a['authority']['submission_authorized'] is False and a['authority']['publication_authorized'] is False


def test_state_manager_review_to_pass_transition_is_bounded_and_idempotent(tmp_path):
    current=json.loads(REG.read_text());base=copy.deepcopy(current)
    base['revision']=2;base['history']=base['history'][:-1];a=base['assets'][0]
    # The canonical registry history preserves the exact prior review enrichment; reconstruct only transition-sensitive fields.
    r=json.loads(RESULT.read_text())
    a['rights_state']='REVIEW_REQUIRED';a['state']='METADATA_READY_RIGHTS_REVIEW_REQUIRED';a['package_state']='PACKAGE_BLOCKED_RIGHTS_REVIEW';a.pop('package_plan_sha256',None)
    # Restore the pre-resolution enrichment hash from history revision 2.
    review_event=base['history'][-1]
    a['metadata_rights_enrichment_sha256']=review_event['enrichment_sha256']
    a['rights_signal_sha256']=review_event.get('rights_signal_sha256',a.get('rights_signal_sha256'))
    a['record_sha256']='0'*64
    rp=tmp_path/'r.json';rp.write_text(json.dumps(base))
    one=sm.advance_asset_metadata_rights(registry_path=rp,semantic_asset_id=r['semantic_asset_id'],metadata=r['metadata'],rights_signal=r['rights_signal'],package_readiness=r['package_readiness'],writer_id='DIE_STATE_MANAGER')
    two=sm.advance_asset_metadata_rights(registry_path=rp,semantic_asset_id=r['semantic_asset_id'],metadata=r['metadata'],rights_signal=r['rights_signal'],package_readiness=r['package_readiness'],writer_id='DIE_STATE_MANAGER')
    assert one['result']=='RIGHTS_RESOLVED_AND_COMMITTED' and two['result']=='IDEMPOTENT_REUSE'
    final=sm.load_registry(rp);assert final['revision']==3 and final['assets'][0]['rights_state']=='PASS' and final['assets'][0]['package_state']=='PACKAGE_READY'


def test_fa204_done_unlocks_fa205_but_does_not_itself_approve_founder_qc():
    g=json.loads(GRAPH.read_text());by={x['id']:x for x in g['tasks']}
    assert by['FA-204']['status']=='DONE'
    assert by['FA-205']['status'] in {'READY','DONE'}
    assert by['FA-205']['authority']=='FOUNDER_REQUIRED'
    if by['FA-205']['status']=='DONE':
        r=json.loads((ROOT/'company/factory-asset/receipts/FA-205-founder-qc.receipt.json').read_text())
        assert r['founder_verdict']['decision'] in {'APPROVE','REJECT','REVISE'}
        assert r['founder_verdict']['silence_is_approval'] is False
