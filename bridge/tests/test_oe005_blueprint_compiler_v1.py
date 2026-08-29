from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'division'/'division001'/'engines'/'blueprint'

def load(name,path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
F=load('oe005f_fixture_test',ENGINE/'fixtures'/'build_blueprint_fixture.py')
C=load('oe005f_compiler_test',ENGINE/'compile_blueprint.py')
L=load('oe005f_lock_test',ENGINE/'lock_compiled_blueprint.py')
CANARY=load('oe005f_canary_test',ENGINE/'run_compiler_canary.py')
BA=load('oe005f_author_test',ENGINE/'validate_blueprint_authoring.py')
BC=load('oe005f_boundary_test',ENGINE/'prepare_compile_input.py')
BR=load('oe005f_review_test',ENGINE/'validate_executive_blueprint_review.py')

AS_OF='2026-08-29T13:00:00Z'
LOCKED_AT='2026-08-29T13:01:00Z'

def refresh_review(review,bp,boundary,governed):
    r=copy.deepcopy(review)
    r['blueprint_artifact']['blueprint_id']=bp['blueprint_id']
    r['blueprint_artifact']['sha256']=BR.sha(bp)
    r['blueprint_artifact']['author_principal_id']=bp['principal']['principal_id']
    r['compile_boundary']['sha256']=BR.sha(boundary)
    r['compile_boundary']['semantic_content_mutated']=boundary['semantic_content_mutated']
    r['governed_worth_making']['bundle_id']=governed['bundle_id']
    r['governed_worth_making']['sha256']=BR.sha(governed)
    r['governed_worth_making']['decision']=governed['decision']
    for row in r['challenges']:
        row['evidence_refs']=[{'ref':'fixture://blueprint/'+bp['blueprint_id'],'sha256':BR.sha(bp)}]
    return r

def compile_fixture():
    review,bp,boundary,governed,wm,wreview,candidate=F.build_review()
    compiled=C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)
    return compiled,review,bp,boundary,governed,wm,wreview,candidate

def lock_fixture(tmp_path:Path):
    compiled,review,bp,boundary,governed,wm,wreview,candidate=compile_fixture()
    path=tmp_path/'compiled-blueprint.json'; digest=C.write_compiled(path,compiled)
    receipt=L.lock_compiled(path,blueprint=bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF,locked_at=LOCKED_AT)
    return path,digest,receipt,compiled,review,bp,boundary,governed,wm,wreview,candidate

def test_oe005d_same_inputs_compile_byte_identically_and_hash_identically():
    a,*rest=compile_fixture(); b,*_=compile_fixture()
    assert a==b
    assert C.canonical_bytes(a)==C.canonical_bytes(b)
    assert C.sha(a)==C.sha(b)
    assert a['compiler']['role']=='SERIALIZE_VALIDATE_HASH_ONLY'
    assert a['production_authority_granted'] is False

def test_oe005d_exact_authored_prompt_variation_and_semantic_hashes_survive_compile():
    compiled,_,bp,boundary,*_=compile_fixture()
    assert compiled['production_contract']['master_prompt']==bp['production']['master_prompt']
    assert compiled['production_contract']['negative_constraints']==bp['production']['negative_constraints']
    assert compiled['production_contract']['semantic_variation_plan']==bp['production']['semantic_variation_plan']
    assert compiled['semantic_hashes']==boundary['semantic_field_hashes']
    assert compiled['compile_boundary']['semantic_content_mutated'] is False

def test_oe005d_capability_plan_is_contract_compatible_but_not_runtime_ready_claim():
    compiled,*_=compile_fixture()
    cap=compiled['capability_plan']
    assert cap['engine_id']=='MUXIA_CHATGPT_IMAGE'
    assert cap['provider_id']=='chatgpt'
    assert cap['required_capability']=='image.generate'
    assert cap['contract_compatible'] is True
    assert cap['runtime_availability_claimed'] is False

def test_oe005d_ambiguous_engine_selection_fails_after_valid_fresh_review():
    review,bp,_,governed,wm,wreview,candidate=F.build_review(); bp=copy.deepcopy(bp); bp['production']['engines_eligible']=['MUXIA_CHATGPT_IMAGE','MUXIA_CHATGPT_IMAGE_ALT']
    boundary=BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    review=refresh_review(review,bp,boundary,governed)
    with pytest.raises(C.CompilerError,match='E_ENGINE_SELECTION_AMBIGUOUS'):
        C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005d_capability_mismatch_fails_after_valid_fresh_review():
    review,bp,_,governed,wm,wreview,candidate=F.build_review(); bp=copy.deepcopy(bp); bp['production']['asset_type']='VECTOR_IMAGE'
    boundary=BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    review=refresh_review(review,bp,boundary,governed)
    with pytest.raises(C.CompilerError,match='E_CAPABILITY_MISMATCH'):
        C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005d_unsupported_single_engine_fails():
    review,bp,_,governed,wm,wreview,candidate=F.build_review(); bp=copy.deepcopy(bp); bp['production']['engines_eligible']=['UNKNOWN_ENGINE']
    boundary=BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    review=refresh_review(review,bp,boundary,governed)
    with pytest.raises(C.CompilerError,match='E_ENGINE_UNSUPPORTED'):
        C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005d_revise_review_never_compiles():
    review,bp,boundary,governed,wm,wreview,candidate=F.build_review(outcome='REVISE')
    with pytest.raises(C.CompilerError,match='E_EXECUTIVE_REVIEW_NOT_NO_VETO'):
        C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005d_stale_executive_review_never_compiles():
    review,bp,boundary,governed,wm,wreview,candidate=F.build_review(); review=copy.deepcopy(review); review['expires_at']='2026-08-29T12:59:00Z'
    with pytest.raises(C.CompilerError,match='E_EXECUTIVE_REVIEW_STALE'):
        C.compile_blueprint(bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005d_semantic_gap_or_post_review_tamper_fails_before_compile():
    review,bp,_,governed,wm,wreview,candidate=F.build_review(); bad=copy.deepcopy(bp); bad['production']['master_prompt']='TODO '+bad['production']['master_prompt']
    with pytest.raises(C.CompilerError,match='E_AUTHOR_ARTIFACT_INVALID'):
        C.compile_blueprint(bad,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)
    bad2=copy.deepcopy(bp); bad2['production']['master_prompt'] += ' mutation after review'
    with pytest.raises(C.CompilerError,match='E_EXECUTIVE_REVIEW_INVALID'):
        C.compile_blueprint(bad2,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF)

def test_oe005e_lock_pins_exact_canonical_bytes_and_founder_hash_without_authorizing(tmp_path:Path):
    path,digest,receipt,*_=lock_fixture(tmp_path)
    assert receipt['compiled_artifact']['sha256']==digest
    assert receipt['compiled_artifact']['bytes']==path.stat().st_size
    assert receipt['founder_gate']['eligible_for_exact_hash_authorization'] is True
    assert receipt['founder_gate']['exact_compiled_blueprint_sha256']==digest
    assert receipt['founder_gate']['authorization_granted'] is False
    assert receipt['production_authority_granted'] is False
    assert L.verify_lock(path,receipt)==[]

def test_oe005e_lock_is_reproducible_for_same_compiled_bytes_and_locked_at(tmp_path:Path):
    path,digest,receipt,compiled,review,bp,boundary,governed,wm,wreview,candidate=lock_fixture(tmp_path)
    receipt2=L.lock_compiled(path,blueprint=bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF,locked_at=LOCKED_AT)
    assert receipt==receipt2
    assert receipt['lock_id']=='BPLOCK-'+digest[:20].upper()

def test_oe005e_noncanonical_or_forged_compiled_file_cannot_be_locked(tmp_path:Path):
    compiled,review,bp,boundary,governed,wm,wreview,candidate=compile_fixture(); path=tmp_path/'compiled.json'
    path.write_text(json.dumps(compiled,indent=2)+'\n',encoding='utf-8')
    with pytest.raises(L.LockError,match='E_COMPILED_ARTIFACT_NOT_CANONICAL_OR_TAMPERED'):
        L.lock_compiled(path,blueprint=bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF,locked_at=LOCKED_AT)
    forged=copy.deepcopy(compiled); forged['production_contract']['master_prompt']+=' forged'; path.write_bytes(C.canonical_bytes(forged))
    with pytest.raises(L.LockError,match='E_COMPILED_ARTIFACT_NOT_CANONICAL_OR_TAMPERED'):
        L.lock_compiled(path,blueprint=bp,governed_result=governed,worth_making=wm,worth_making_review=wreview,longtail_candidate=candidate,executive_blueprint_review=review,as_of=AS_OF,locked_at=LOCKED_AT)

def test_oe005e_post_lock_artifact_mutation_breaks_verification(tmp_path:Path):
    path,digest,receipt,compiled,*_=lock_fixture(tmp_path); tampered=copy.deepcopy(compiled); tampered['production_contract']['master_prompt']+=' tampered after lock'; path.write_bytes(C.canonical_bytes(tampered))
    errors=L.verify_lock(path,receipt)
    assert 'E_HASH_LOCK:artifact_sha_mismatch' in errors
    assert 'E_HASH_LOCK:founder_hash_mismatch' in errors

def test_oe005e_receipt_hash_tamper_breaks_verification(tmp_path:Path):
    path,digest,receipt,*_=lock_fixture(tmp_path); bad=copy.deepcopy(receipt); bad['compiled_artifact']['sha256']='0'*64
    assert 'E_HASH_LOCK:artifact_sha_mismatch' in L.verify_lock(path,bad)

def test_oe005f_compiled_schema_and_lock_schema_are_parseable_json():
    for p in [ENGINE/'die.division001.compiled-blueprint.v1.schema.json',ENGINE/'die.division001.compiled-blueprint-lock.v1.schema.json',ENGINE/'BLUEPRINT_COMPILER_CAPABILITY_PROFILE_V1.json']:
        assert isinstance(json.loads(p.read_text(encoding='utf-8')),dict)

def test_oe005f_executable_compiler_canary_matches_pinned_expected(tmp_path:Path):
    out=CANARY.run(tmp_path/'compiler-canary')
    expected=json.loads((ENGINE/'fixtures'/'compiler-canary-expected-v1.json').read_text(encoding='utf-8'))
    assert out['status']=='PASS'
    assert out['compiled_blueprint_sha256']==expected['compiled_blueprint_sha256']
    assert out['lock_id']==expected['lock_id']
    assert out['provider_id']==expected['provider_id']=='chatgpt'
    assert out['required_capability']==expected['required_capability']=='image.generate'
    assert out['deterministic_replay'] is True
    assert out['lock_verify'] is True
    assert out['runtime_availability_claimed'] is False
    assert out['production_authority_granted'] is False