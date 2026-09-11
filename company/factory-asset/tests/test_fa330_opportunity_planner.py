import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s and s.loader;sys.modules[s.name]=m;s.loader.exec_module(m);return m
bridge=load('dab',ROOT/'company/factory-asset/lib/dual_atlas_context_bridge.py')
planner=load('opp',ROOT/'company/factory-asset/lib/opportunity_planner.py')

def seed(noun='gift box'):
 return {'id':'SEED-000028','canonical_name':noun,'object_class':'commerce','category_path':'Commerce/Gifting','demand_status':'validated_medium','demand_score':0.628,'status':'approved'}

def object_row(noun='gift box'):
 return {'seed_id':'SEED-000028','noun':noun,'object_class':'commerce','category_path':'Commerce/Gifting','evidence_refs':['object-atlas://SEED-000028']}

def ctx(cid,use,intent,hints=('gift box',),industry='retail design'):
 return {'schema':'die.factory-asset.human-demand-context.v1','context_id':cid,'human':'commercial designer','activity':'creating design assets','place':'digital workspace','time':'campaign production','demographic':'working adult','emotion':'clarity','problem':'need reusable design material','industry':industry,'commercial_intent':intent,'use_case':use,'object_hints':list(hints),'evidence':{'label':'RESEARCH_HYPOTHESIS','refs':['fixture://context'],'inherited_demand_allowed':False}}

def test_baseline_champion_survives_without_human_context_and_does_not_authorize_production():
 b={'schema':'die.factory-asset.dual-atlas-context-bridge.v1','direction':'SUPPLY_FIRST','anchor':{},'considered_count':0,'result_count':0,'max_scan':256,'max_results':12,'policy':{'cartesian_enumeration':False,'bounded_retrieval_required':True,'inherited_demand_allowed':False,'authority_effect':'NONE','production_authorized':False,'provider_dispatch_authorized':False,'submission_authorized':False,'publication_authorized':False},'candidates':[]}
 r=planner.plan_seed_opportunities(seed=seed(),bridge_result=b)
 assert r['candidate_count']==1
 c=r['candidates'][0]; assert c['semantic_mode']=='ISOLATED_OBJECT' and c['preset_id']=='ISOLATED_CARTOON_WATERCOLOR_L0'
 assert c['candidate_lane']=='EXPLOITATION' and c['state']=='ELIGIBLE_BASELINE'
 assert c['production_authorized'] is False and r['force_all_modes'] is False and r['cartesian_enumeration'] is False

def test_context_terms_create_sparse_mode_candidates_not_force_all_modes():
 contexts=[ctx('HDC-GIFT-WRAP','repeat gift motifs on wrapping paper','wrapping pattern design utility'),ctx('HDC-GIFT-UI','show gift action in ecommerce checkout interface','interface navigation icon for checkout')]
 b=bridge.supply_first(object_row(),contexts,limit=8)
 r=planner.plan_seed_opportunities(seed=seed(),bridge_result=b)
 modes={x['semantic_mode'] for x in r['candidates']}
 assert 'ISOLATED_OBJECT' in modes and 'PATTERN' in modes and 'ICON' in modes
 assert 'ANIMATION' not in modes and 'PHOTO' not in modes
 assert r['candidate_count']<=12 and r['force_all_modes'] is False
 icon=next(x for x in r['candidates'] if x['semantic_mode']=='ICON')
 assert icon['preset_id'] is None and icon['state']=='RESEARCH_NO_GOVERNED_PRESET'
 assert icon['engine_state']=='UNAVAILABLE_NOT_ACCEPTED'
 assert icon['evidence'][0]['kind']=='HUMAN_CONTEXT_INFERENCE' and icon['production_authorized'] is False

def test_founder_candidate_preset_is_ranked_as_research_not_live_authority():
 b=bridge.supply_first(object_row(),[ctx('HDC-GIFT-COMP','reusable gifting composition asset','reusable stock design utility')])
 r=planner.plan_seed_opportunities(seed=seed(),bridge_result=b)
 premium=[x for x in r['candidates'] if x['preset_id']=='ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0']
 assert premium and all(x['state']=='RESEARCH_ONLY' for x in premium)
 assert all(x['production_authorized'] is False for x in premium)

def test_nonapproved_seed_fails_closed():
 s=seed();s['status']='rejected'
 b=bridge.supply_first(object_row(),[ctx('HDC-GIFT-COMP','reusable gifting composition asset','reusable stock design utility')])
 try:planner.plan_seed_opportunities(seed=s,bridge_result=b);assert False
 except planner.OpportunityPlannerError as e:assert e.code=='SEED_NOT_APPROVED'

def test_plan_is_deterministic():
 contexts=[ctx('HDC-GIFT-WRAP','repeat gift motifs on wrapping paper','wrapping pattern design utility')]
 b=bridge.supply_first(object_row(),contexts)
 assert planner.plan_seed_opportunities(seed=seed(),bridge_result=b)==planner.plan_seed_opportunities(seed=seed(),bridge_result=b)
