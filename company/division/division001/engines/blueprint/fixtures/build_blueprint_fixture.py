from __future__ import annotations

import importlib.util, json, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DIVISION=ROOT.parent
WORTH=DIVISION/'worth-making'
for p in (ROOT,WORTH,WORTH/'fixtures'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError('load:'+str(path))
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
WB=load('oe005_wm_builder',WORTH/'fixtures'/'build_governed_fixture.py')
WV=load('oe005_wm_governed_validator',WORTH/'validate_governed_bundle.py')
BA=load('oe005_bp_author_validator',ROOT/'validate_blueprint_authoring.py')
BC=load('oe005_bp_compile_boundary',ROOT/'prepare_compile_input.py')
BR=load('oe005_bp_review_validator',ROOT/'validate_executive_blueprint_review.py')

def build_author() -> tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    bundle=WB.build(outcome='NO_VETO',recommendation='VALIDATE',artifact_suffix='BP')
    governed=WV.validate_bundle(bundle)
    assert governed['status']=='PASS' and governed['decision']=='PROMOTABLE_TO_BLUEPRINT'
    wm=bundle['division_artifact']; wreview=bundle['executive_review']; candidate=bundle['precheck_input']['candidate']
    bp={
      'schema_version':'die.division001.blueprint-authoring.v1','blueprint_id':'BP-DIV001-SYNTHETIC-CABLE-0001','decision_class':'BLUEPRINT_AUTHORING',
      'principal':{'principal_id':'division-head-division01','role':'AUTHOR','division_id':'division001'},
      'snapshot':{'repository_sha':bundle['repository_sha'],'snapshot_id':'fixture://division01/blueprint/snapshot-1','as_of':'2026-08-29T12:45:00Z','expires_at':'2026-08-30T12:45:00Z'},
      'upstream':{
        'governed_worth_making_result':{'id':governed['bundle_id'],'sha256':BA.sha(governed)},
        'worth_making_artifact':{'id':wm['artifact_id'],'sha256':BA.sha(wm)},
        'executive_review':{'id':wreview['review_id'],'sha256':BA.sha(wreview)},
        'longtail_candidate':{'id':candidate['candidate_id'],'sha256':BA.sha(candidate)}},
      'family':{'family_id':wm['candidate']['family_id'],'family_thesis':'A bounded family of commercially useful remote-work cable-organization images that emphasizes practical desk utility rather than generic isolated objects.','candidate_id':wm['candidate']['candidate_id'],'candidate_phrase':wm['candidate']['phrase'],'commercial_use_hypothesis':wm['commercial_use_hypothesis'],'differentiation_thesis':wm['differentiation_thesis']},
      'buyer':{'persona':['office-supply marketer','remote-work content publisher'],'use_cases':['remote-work desk organization marketing','educational cable-management illustration'],'job_to_be_done':wm['buyer']['job_to_be_done'],'buyer_utility':wm['buyer']['buyer_utility']},
      'product_expression':wm['product_expression_recommendation'],
      'visual_spec':{'visual_language':'Clean photorealistic utility-focused product imagery with legible cable-management function and restrained commercial styling.','subject_constraints':['Show one recognizable cable organizer as the primary subject.','Keep cable routing physically plausible and easy to understand.'],'composition_constraints':['Maintain clear negative space for downstream design use.','Keep the primary utility action visible at thumbnail scale.'],'background_constraints':['Use a clean neutral workspace or isolated light background appropriate to the variation.'],'lighting_color_constraints':['Use coherent soft commercial lighting without crushed shadows or clipped highlights.'],'forbidden_visual_elements':['logos','trademarks','watermarks','unreadable text','duplicated cable ends','impossible geometry']},
      'production':{'asset_type':'RASTER_IMAGE','batch_size':20,'engines_eligible':['MUXIA_CHATGPT_IMAGE'],'master_prompt':'Create a clean commercially useful raster image of a practical cable organizer for remote-work desk setup, emphasizing clear physical utility, plausible cable routing, uncluttered composition, and buyer-ready design flexibility. Preserve the accepted family thesis and do not introduce brands or text.','negative_constraints':['no logos or trademarks','no watermark or signature','no illegible text','no impossible cable geometry','no duplicate organizer artifacts'],'semantic_variation_plan':[
        {'variation_id':'VAR-USECASE-001','semantic_dimension':'buyer_use_case','instruction':'Show the organizer solving a compact home-office desk cable-management use case.','commercial_rationale':'Tests utility for remote-work organization content.','distinctness_test':'Use case and cable-routing problem must differ materially from the base composition.'},
        {'variation_id':'VAR-PLACE-002','semantic_dimension':'place','instruction':'Place the organizer in a clean shared-workspace desk context while keeping the utility action obvious.','commercial_rationale':'Tests broader office communication utility without changing the accepted family thesis.','distinctness_test':'Workspace context and surrounding functional cues must be meaningfully different from the home-office variation.'},
        {'variation_id':'VAR-COMPOSE-003','semantic_dimension':'composition','instruction':'Create an isolated product-forward composition with generous copy space and visibly organized cables.','commercial_rationale':'Tests flexible stock-design usage for marketers and publishers.','distinctness_test':'Composition must change framing and copy-space utility, not just camera micro-perturbation.'}]},
      'platform_strategy':{'eligible_marketplaces':['Adobe Stock','Dreamstime'],'required_profiles':['AI-generated raster disclosure profile'],'technical_transforms':['export high-resolution RGB raster without watermark'],'ai_disclosures':['declare generative-AI origin where current platform contract requires it']},
      'metadata_direction':{'title_direction':'Describe practical cable organization and remote-work desk utility without keyword stuffing.','primary_keywords':['cable organizer','desk organization','remote work'],'secondary_keywords':['cable management','home office','workspace utility','organized desk'],'category_direction':['business','technology','objects']},
      'qa_falsification':{'universal_checks':['artifact integrity and exact blueprint lineage','no unresolved rights/safety/watermark hard veto'],'platform_checks':['current platform raster dimensions and AI disclosure profile pass'],'duplicate_distance_rule':'Reject or review outputs that are materially near-duplicate in subject, composition and buyer-use semantics.','blueprint_adherence_checks':['accepted cable-organizer utility remains visually obvious','variation follows its authored semantic dimension','forbidden visual elements remain absent'],'falsification_test':'Produce the bounded validation batch and test whether assets retain strong QA pass rate plus usable platform acceptance signals for the buyer/use-case thesis.','success_criterion':'The predefined QA and platform-acceptance evidence supports continuing the family hypothesis.','failure_criterion':'The bounded batch fails QA, differentiation, or platform acceptance enough to invalidate or revise the family thesis.'},
      'evidence':[
        {'kind':'GOVERNED_WORTH_MAKING','ref':'fixture://governed/'+governed['bundle_id'],'sha256':BA.sha(governed),'label':'VERIFIED'},
        {'kind':'WORTH_MAKING','ref':'fixture://worth-making/'+wm['artifact_id'],'sha256':BA.sha(wm),'label':'VERIFIED'},
        {'kind':'EXECUTIVE_REVIEW','ref':'fixture://executive/'+wreview['review_id'],'sha256':BA.sha(wreview),'label':'VERIFIED'},
        {'kind':'LONGTAIL_CANDIDATE','ref':'fixture://longtail/'+candidate['candidate_id'],'sha256':BA.sha(candidate),'label':'VERIFIED'}],
      'economics':{'expected_cost_usd':0,'expected_asset_days_to_signal':30,'revenue_claim_status':'HYPOTHESIS'},
      'production_authority_granted':False}
    errors=BA.validate(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    assert errors==[], errors
    compile_boundary=BC.prepare(bp,governed_result=governed,worth_making=wm,executive_review=wreview,longtail_candidate=candidate,as_of='2026-08-29T12:50:00Z')
    return bp,compile_boundary,governed,wm,wreview,candidate

def build_review(*, outcome:str='NO_VETO', assessment:str='PASS') -> tuple[dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any],dict[str,Any]]:
    bp,compile_boundary,governed,wm,wreview,candidate=build_author(); bph=BR.sha(bp); cph=BR.sha(compile_boundary); gh=BR.sha(governed)
    ids=['worth_making_thesis_fidelity','family_strategy_coherence','constraint_contradiction_integrity','portfolio_overlap_differentiation','product_expression_fit','production_tests_worth_making_thesis']
    actions=[]; escalation=None
    if outcome=='REVISE': assessment='CONCERN'; actions=['Return to Division01 for a new immutable Blueprint artifact addressing the challenged semantics.']
    elif outcome=='VETO_PENDING_EVIDENCE': assessment='UNKNOWN'; actions=['Acquire missing evidence and return through Division01 before Blueprint promotion.']
    elif outcome=='ESCALATE_FOUNDER': escalation='Material strategy or sovereignty decision requires Founder judgment.'
    review={'schema_version':'die.executive.blueprint-review.v1','review_id':'BP-EXEC-SYNTHETIC-CABLE-0001','principal':{'principal_id':'chatgpt-plus-executive','role':'REVIEWER'},'snapshot':{'repository_sha':bp['snapshot']['repository_sha'],'snapshot_id':'fixture://executive/blueprint-review/snapshot-1','as_of':'2026-08-29T12:55:00Z'},'blueprint_artifact':{'blueprint_id':bp['blueprint_id'],'sha256':bph,'author_principal_id':'division-head-division01'},'compile_boundary':{'sha256':cph,'semantic_content_mutated':False},'governed_worth_making':{'bundle_id':governed['bundle_id'],'sha256':gh,'decision':'PROMOTABLE_TO_BLUEPRINT'},'challenges':[{'challenge_id':i,'assessment':assessment,'rationale':'Synthetic Executive Blueprint challenge grounded in exact authored and governed hashes.','evidence_refs':[{'ref':'fixture://blueprint/'+bp['blueprint_id'],'sha256':bph}]} for i in ids],'outcome':outcome,'required_actions':actions,'escalation_reason':escalation,'review_mode':'READ_ONLY_CHALLENGE','blueprint_artifact_edited':False,'semantic_content_authored':False,'production_authority_granted':False,'reviewed_at':'2026-08-29T12:55:00Z','expires_at':'2026-08-30T12:55:00Z'}
    return review,bp,compile_boundary,governed,wm,wreview,candidate