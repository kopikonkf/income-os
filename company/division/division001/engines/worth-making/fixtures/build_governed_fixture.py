from __future__ import annotations

import copy, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ROOT.parent
LONGTAIL = ENGINES / "longtail"

for p in (ROOT, LONGTAIL):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("load:" + str(path))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

HCTX=_load("oe004f_hctx",LONGTAIL/"retrieve_human_contexts.py")
GEN=_load("oe004f_gen",LONGTAIL/"generate_longtail.py")
GUARD=_load("oe004f_guard",LONGTAIL/"guard_longtail.py")
PHRASE=_load("oe004f_phrase",LONGTAIL/"phrase_signal_score.py")
PRE=_load("oe004f_pre",ROOT/"precheck_worth_making.py")
WM=_load("oe004f_wm",ROOT/"validate_worth_making.py")
EXEC=_load("oe004f_exec",ROOT/"validate_executive_review.py")
ATT=_load("oe004f_att",ROOT/"validate_attempt_lineage.py")

REPO_SHA="f"*40

def sh(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()

def gate(name:str)->dict[str,Any]:
    return {'status':'CLEAR','evidence_ref':'fixture://worth-making/'+name,'evidence_sha256':sh(name),'observed_at':'2026-08-29T12:00:00Z','expires_at':'2026-08-30T12:00:00Z','notes':'synthetic fixture'}

def _signals(score:dict[str,Any])->list[dict[str,str]]:
    out=[]; seen=set()
    for c in score['components']:
        for r in c['evidence_refs']:
            if r['evidence_kind']=='OPPORTUNITY_SIGNAL' and r['evidence_id'] not in seen:
                out.append({'signal_id':r['evidence_id'],'sha256':r['evidence_sha256']}); seen.add(r['evidence_id'])
    return out

def build(*, outcome:str='NO_VETO', recommendation:str='VALIDATE', attempt_number:int=1, previous_attempt:dict[str,Any]|None=None, artifact_suffix:str='A')->dict[str,Any]:
    fix=json.loads((LONGTAIL/'fixtures'/'synthetic-canary-v1.json').read_text(encoding='utf-8'))
    ctx=HCTX.retrieve(fix['human_context_query']); gen=GEN.generate(fix['object_receipt'],ctx,budget=fix['budget'],expression_level=fix['expression_level'],created_at=fix['created_at']); guard=GUARD.apply(gen); cand=gen['candidates'][0]; gout=guard['outcomes'][0]
    with tempfile.TemporaryDirectory() as td:
        score=PHRASE.synthetic_canary(cand,gout,fix['signal_plans'][0],fix['hard_veto'],registry_db=Path(td)/'signals.db',evaluated_at=fix['evaluated_at'])['demand_score']
    pin={'schema_version':'die.division001.worth-making-precheck-input.v1','precheck_id':'WMPRE-SYNTHETIC-CABLE-0001','evaluated_at':'2026-08-29T12:20:00Z','candidate':cand,'demand_score':score,'longtail_guard':{'status':'ACCEPTED','receipt_id':guard['guard_receipt_id'],'receipt_sha256':PRE.canonical_sha(guard),'candidate_id':cand['candidate_id'],'candidate_sha256':PRE.canonical_sha(cand)},'hard_gates':{'rights_ip':gate('rights-ip'),'safety_deception':gate('safety'),'platform_expression_eligibility':gate('platform'),'production_tool_rights':gate('tool-rights')},'spend':{'estimated_cost_usd':0,'authorization_status':'NOT_REQUIRED','authorization_ref':None,'authorization_sha256':None},'buyer_hypothesis_seed':{'source_kind':'HUMAN_ATLAS_HYPOTHESIS','source_ref':'fixture://human/'+ctx['results'][0]['context']['context_id'],'source_sha256':ctx['registry']['sha256'],'buyer_label':ctx['results'][0]['context']['target_buyers'][0],'use_case':ctx['results'][0]['context']['buyer_jobs'][0],'falsification_test':'Run a bounded utility validation and measure predefined acceptance evidence.'}}
    pre=PRE.evaluate(pin)
    model=json.loads((ROOT/'WORTH_MAKING_FACTOR_MODEL_V1.json').read_text()); weights={x['factor_id']:x['weight'] for x in model['factors']}; vals={'demand_evidence':82,'commercial_intent':80,'buyer_utility':85,'competition_gap':70,'differentiation':78,'production_feasibility':90,'eligible_platform_fit':80,'repurposing_potential':65,'speed_to_cheapest_falsification':85}
    refs=[{'kind':'PRECHECK','ref':'fixture://precheck/'+pre['precheck_id'],'sha256':WM.canonical_sha(pre)}]
    factors=[{'factor_id':k,'weight':weights[k],'score':v,'evidence_label':'VERIFIED','evidence_refs':refs,'rationale':'Synthetic governed canary rationale pinned to fixture evidence.'} for k,v in vals.items()]
    total=sum(vals[k]*weights[k] for k in vals)/100
    if recommendation=='RESEARCH':
        vals2={k:65 for k in vals}; factors=[{'factor_id':k,'weight':weights[k],'score':65,'evidence_label':'VERIFIED','evidence_refs':refs,'rationale':'Synthetic research-level fixture.'} for k in vals2]; total=65
    elif recommendation=='DEFER':
        factors=[{'factor_id':k,'weight':weights[k],'score':50,'evidence_label':'VERIFIED','evidence_refs':refs,'rationale':'Synthetic defer-level fixture.'} for k in vals]; total=50
    art={'schema_version':'die.division001.worth-making.v1','artifact_id':'WM-DIV001-SYNTHETIC-'+artifact_suffix+'-0001','decision_class':'WORTH_MAKING','principal':{'principal_id':'division-head-division01','role':'AUTHOR','division_id':'division001'},'snapshot':{'repository_sha':REPO_SHA,'snapshot_id':'fixture://division/'+artifact_suffix,'as_of':'2026-08-29T12:25:00Z','expires_at':'2026-08-30T12:25:00Z'},'upstream':{'precheck_id':pre['precheck_id'],'precheck_sha256':WM.canonical_sha(pre),'demand_score_id':pre['demand_score_id'],'demand_score_sha256':pre['demand_score_sha256'],'longtail_candidate_sha256':pre['candidate_sha256'],'source_signals':_signals(score)},'candidate':{'candidate_id':cand['candidate_id'],'family_id':'FAM-SYNTHETIC-CABLE','phrase':cand['phrase']},'buyer':{'buyer_or_payer':'office-supply marketer','end_user':'remote worker','job_to_be_done':'Explain practical desk cable organization in remote-work content.','buyer_utility':'Provide a clear commercially usable cable-management concept.'},'commercial_use_hypothesis':'A buyer may license a clean utility asset for remote-work desk organization communication.','competition_interpretation':'Supply exists, but contextual utility framing may narrow competition.','differentiation_thesis':'Differentiate with buyer-relevant context rather than isolated-object sameness.','production_feasibility':'A bounded static utility asset is feasible at zero incremental spend.','product_expression_recommendation':{'level':'L0','name':'primitive_static_asset','rationale':'Use cheapest static falsification first.'},'factors':factors,'total_score':total,'confidence':'MEDIUM','cheapest_falsification':{'test':'Run one bounded validation set.','success_criterion':'Meet one predefined acceptance threshold.','failure_criterion':'Miss all predefined acceptance thresholds.','estimated_cost_usd':0,'timebox':'one bounded cycle'},'assumptions':[{'claim':'Context improves buyer utility.','label':'HYPOTHESIS','falsification_ref':'fixture://falsification/context'}],'recommendation':recommendation,'precheck_status':'PASS','production_authority_granted':False}
    ah=EXEC.canonical_sha(art); ids=['evidence_weakness_contradiction','score_inflation_double_counting','portfolio_overlap_cannibalization','strategic_opportunity_cost','product_expression_fit','hypotheses_remaining']
    assessment='PASS'; actions=[]; escalation=None
    if outcome=='REVISE': assessment='CONCERN'; actions=['Division01 must author a new immutable artifact addressing the stated concerns.']
    elif outcome=='VETO_PENDING_EVIDENCE': assessment='UNKNOWN'; actions=['Acquire the missing evidence and return through Division01 before review.']
    elif outcome=='ESCALATE_FOUNDER': escalation='Material sovereignty or policy judgment requires Founder decision.'
    review={'schema_version':'die.executive.worth-making-review.v1','review_id':'WM-EXEC-SYNTHETIC-'+artifact_suffix+'-0001','principal':{'principal_id':'chatgpt-plus-executive','role':'REVIEWER'},'snapshot':{'repository_sha':REPO_SHA,'snapshot_id':'fixture://executive/'+artifact_suffix,'as_of':'2026-08-29T12:30:00Z'},'division_artifact':{'artifact_id':art['artifact_id'],'sha256':ah,'author_principal_id':'division-head-division01','recommendation':art['recommendation'],'total_score':art['total_score'],'confidence':art['confidence']},'precheck':{'precheck_id':pre['precheck_id'],'sha256':EXEC.canonical_sha(pre),'status':'PASS'},'challenges':[{'challenge_id':i,'assessment':assessment,'rationale':'Synthetic required Executive challenge domain.','evidence_refs':[{'ref':'fixture://division/'+art['artifact_id'],'sha256':ah}]} for i in ids],'outcome':outcome,'required_actions':actions,'escalation_reason':escalation,'review_mode':'READ_ONLY_CHALLENGE','division_artifact_edited':False,'production_authority_granted':False,'reviewed_at':'2026-08-29T12:30:00Z','expires_at':'2026-08-30T12:30:00Z'}
    mapping={'NO_VETO':('CLOSED_NO_VETO','BLUEPRINT'),'REVISE':('RETURNED_TO_DIVISION','DIVISION01'),'VETO_PENDING_EVIDENCE':('WAITING_EVIDENCE','EVIDENCE_COLLECTION'),'ESCALATE_FOUNDER':('ESCALATED_FOUNDER','FOUNDER')}; state,owner=mapping[outcome]
    prevref=None if previous_attempt is None else {'attempt_id':previous_attempt['attempt_id'],'sha256':ATT.sha(previous_attempt),'attempt_number':previous_attempt['attempt_number'],'review_outcome':previous_attempt['review_outcome']}
    attempt={'schema_version':'die.division001.worth-making-attempt.v1','chain_id':'WMCHAIN-SYNTHETIC-CABLE-0001','attempt_id':f'WMATT-SYNTHETIC-CABLE-{attempt_number:04d}','attempt_number':attempt_number,'previous_attempt':prevref,'precheck':{'id':pre['precheck_id'],'sha256':ATT.sha(pre)},'division_artifact':{'id':art['artifact_id'],'sha256':ATT.sha(art)},'executive_review':{'id':review['review_id'],'sha256':ATT.sha(review)},'review_outcome':outcome,'state':state,'next_owner':owner,'required_actions':actions,'created_at':'2026-08-29T12:31:00Z','immutable_refs':True}
    return {'bundle_id':'WMBUNDLE-SYNTHETIC-CABLE-0001','validated_at':'2026-08-29T12:40:00Z','repository_sha':REPO_SHA,'precheck_input':pin,'precheck':pre,'division_artifact':art,'executive_review':review,'attempt':attempt,'previous_attempt':previous_attempt}