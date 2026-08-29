from __future__ import annotations

import copy, importlib.util, json, sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'company'/'division'/'division001'/'engines'/'blueprint'

def load(name,path):
    if str(path.parent) not in sys.path: sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
F=load('oe005_fixture_test',ENGINE/'fixtures'/'build_blueprint_fixture.py')
BA=load('oe005_author_test',ENGINE/'validate_blueprint_authoring.py')
BC=load('oe005_boundary_test',ENGINE/'prepare_compile_input.py')
BR=load('oe005_review_test',ENGINE/'validate_executive_blueprint_review.py')


def author_errors(bp,governed,wm,wreview,candidate,as_of='2026-08-29T12:50:00Z'):
    return BA.validate(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of=as_of)


def test_oe005a_valid_division_blueprint_author_artifact_passes():
    bp,_,governed,wm,wreview,candidate=F.build_author()
    assert author_errors(bp,governed,wm,wreview,candidate)==[]
    assert bp['principal']=={'principal_id':'division-head-division01','role':'AUTHOR','division_id':'division001'}
    assert bp['production_authority_granted'] is False


def test_oe005a_requires_promotable_governed_worth_making():
    bp,_,governed,wm,wreview,candidate=F.build_author(); bad=copy.deepcopy(governed); bad['decision']='NOT_PROMOTABLE'
    assert 'E_UPSTREAM:governed_result_binding' in author_errors(bp,bad,wm,wreview,candidate)
    # If binding is updated to the non-promotable receipt, the semantic gate still blocks.
    bp2=copy.deepcopy(bp); bp2['upstream']['governed_worth_making_result']['sha256']=BA.sha(bad)
    errors=author_errors(bp2,bad,wm,wreview,candidate)
    assert 'E_UPSTREAM:worth_making_not_promotable' in errors


def test_oe005a_blueprint_cannot_drift_candidate_buyer_thesis_or_expression():
    bp,_,governed,wm,wreview,candidate=F.build_author()
    mutations=[
      ('candidate',lambda x:x['family'].__setitem__('candidate_phrase','different phrase')),
      ('commercial_use_hypothesis',lambda x:x['family'].__setitem__('commercial_use_hypothesis','A materially different commercial thesis that bypasses Worth-Making.')),
      ('job_to_be_done',lambda x:x['buyer'].__setitem__('job_to_be_done','A different job to be done that was never reviewed.')),
      ('buyer_utility',lambda x:x['buyer'].__setitem__('buyer_utility','A different buyer utility claim that was never reviewed.')),
      ('product_expression',lambda x:x.__setitem__('product_expression',{'level':'L3','name':'family_pack_bundle','rationale':'Changed only inside Blueprint.'})),
    ]
    for expected,mut in mutations:
        bad=copy.deepcopy(bp); mut(bad); errors=author_errors(bad,governed,wm,wreview,candidate)
        assert any(('E_DRIFT:'+expected) in e for e in errors), (expected,errors)


def test_oe005a_wrong_principal_or_production_authority_fails_schema():
    bp,_,governed,wm,wreview,candidate=F.build_author(); bad=copy.deepcopy(bp); bad['principal']['principal_id']='hermes'
    assert any(x.startswith('E_SCHEMA:') for x in author_errors(bad,governed,wm,wreview,candidate))
    bad2=copy.deepcopy(bp); bad2['production_authority_granted']=True
    assert any(x.startswith('E_SCHEMA:') for x in author_errors(bad2,governed,wm,wreview,candidate))


def test_oe005b_unresolved_placeholders_duplicate_variations_and_keyword_overlap_fail():
    bp,_,governed,wm,wreview,candidate=F.build_author(); bad=copy.deepcopy(bp); bad['production']['master_prompt']='Create useful image TODO with unresolved semantics long enough to pass only schema length checks.'
    assert 'E_SEMANTICS:unresolved_placeholder' in author_errors(bad,governed,wm,wreview,candidate)
    bad2=copy.deepcopy(bp); bad2['production']['semantic_variation_plan'][1]['instruction']=bad2['production']['semantic_variation_plan'][0]['instruction']
    assert 'E_VARIATION:duplicate_instruction' in author_errors(bad2,governed,wm,wreview,candidate)
    bad3=copy.deepcopy(bp); bad3['metadata_direction']['secondary_keywords'].append('remote work')
    assert 'E_METADATA:primary_secondary_overlap' in author_errors(bad3,governed,wm,wreview,candidate)


def test_oe005b_compile_boundary_is_deterministic_exact_projection_and_self_validating():
    bp,a,governed,wm,wreview,candidate=F.build_author()
    b=BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    assert a==b
    assert a['semantic_content_mutated'] is False
    assert a['compiler_role']=='SERIALIZE_VALIDATE_HASH_ONLY'
    assert a['authored_semantics']['master_prompt']==bp['production']['master_prompt']
    assert a['authored_semantics']['semantic_variation_plan']==bp['production']['semantic_variation_plan']
    assert a['author_artifact_sha256']==BC.sha(bp)
    assert a['production_authority_granted'] is False


def test_oe005b_compile_boundary_rejects_invalid_artifact_even_if_caller_wants_compile():
    bp,_,governed,wm,wreview,candidate=F.build_author(); bp['family']['commercial_use_hypothesis']='A different thesis inserted after Worth-Making.'
    with pytest.raises(BC.CompileBoundaryError,match='E_AUTHOR_ARTIFACT_INVALID'):
        BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')


def test_oe005b_semantic_field_hash_changes_when_authored_prompt_changes():
    bp,a,governed,wm,wreview,candidate=F.build_author(); changed=copy.deepcopy(bp); changed['production']['master_prompt'] += ' Use a slightly wider commercial framing while preserving all authored constraints.'
    b=BC.prepare(changed,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    assert a['semantic_field_hashes']['master_prompt']!=b['semantic_field_hashes']['master_prompt']
    assert a['author_artifact_sha256']!=b['author_artifact_sha256']


def test_oe005c_valid_no_veto_review_passes_and_is_read_only():
    review,bp,compile_boundary,governed,_,_,_=F.build_review()
    before=BR.sha(bp)
    assert BR.validate(review,blueprint=bp,compile_boundary=compile_boundary,governed_result=governed)==[]
    assert BR.sha(bp)==before
    assert review['review_mode']=='READ_ONLY_CHALLENGE'
    assert review['blueprint_artifact_edited'] is False
    assert review['semantic_content_authored'] is False
    assert review['production_authority_granted'] is False


def test_oe005c_exact_six_challenge_domains_required():
    review,bp,compile_boundary,governed,_,_,_=F.build_review(); review['challenges'][1]['challenge_id']=review['challenges'][0]['challenge_id']
    errors=BR.validate(review,blueprint=bp,compile_boundary=compile_boundary,governed_result=governed)
    assert 'E_CHALLENGES:exact_six_required' in errors


def test_oe005c_no_veto_forbids_material_concern_or_unknown():
    review,bp,compile_boundary,governed,_,_,_=F.build_review(); review['challenges'][0]['assessment']='MATERIAL_CONCERN'
    assert 'E_OUTCOME:NO_VETO_with_material_or_unknown' in BR.validate(review,blueprint=bp,compile_boundary=compile_boundary,governed_result=governed)
    review2,bp2,c2,g2,_,_,_=F.build_review(); review2['challenges'][0]['assessment']='UNKNOWN'
    assert 'E_OUTCOME:NO_VETO_with_material_or_unknown' in BR.validate(review2,blueprint=bp2,compile_boundary=c2,governed_result=g2)


def test_oe005c_revise_and_veto_require_semantically_correct_actions():
    review,bp,c,g,_,_,_=F.build_review(outcome='REVISE')
    assert BR.validate(review,blueprint=bp,compile_boundary=c,governed_result=g)==[]
    review['required_actions']=[]
    assert 'E_OUTCOME:REVISE_requires_actions' in BR.validate(review,blueprint=bp,compile_boundary=c,governed_result=g)
    veto,bp2,c2,g2,_,_,_=F.build_review(outcome='VETO_PENDING_EVIDENCE')
    assert BR.validate(veto,blueprint=bp2,compile_boundary=c2,governed_result=g2)==[]


def test_oe005c_forged_blueprint_or_compile_boundary_hash_fails():
    review,bp,c,g,_,_,_=F.build_review(); review['blueprint_artifact']['sha256']='0'*64
    assert 'E_BLUEPRINT:binding' in BR.validate(review,blueprint=bp,compile_boundary=c,governed_result=g)
    review2,bp2,c2,g2,_,_,_=F.build_review(); review2['compile_boundary']['sha256']='1'*64
    assert 'E_COMPILE_BOUNDARY:hash_mismatch' in BR.validate(review2,blueprint=bp2,compile_boundary=c2,governed_result=g2)


def test_oe005c_schema_blocks_executive_editing_semantics_or_granting_authority():
    review,bp,c,g,_,_,_=F.build_review(); review['blueprint_artifact_edited']=True
    assert any(x.startswith('E_SCHEMA:') for x in BR.validate(review,blueprint=bp,compile_boundary=c,governed_result=g))
    review2,bp2,c2,g2,_,_,_=F.build_review(); review2['semantic_content_authored']=True
    assert any(x.startswith('E_SCHEMA:') for x in BR.validate(review2,blueprint=bp2,compile_boundary=c2,governed_result=g2))
    review3,bp3,c3,g3,_,_,_=F.build_review(); review3['production_authority_granted']=True
    assert any(x.startswith('E_SCHEMA:') for x in BR.validate(review3,blueprint=bp3,compile_boundary=c3,governed_result=g3))