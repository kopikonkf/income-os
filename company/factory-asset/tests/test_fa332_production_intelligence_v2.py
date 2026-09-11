import importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('pi2',ROOT/'company/factory-asset/lib/production_intelligence_v2.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m)

def seed():return {'id':'SEED-000028','canonical_name':'gift box','object_class':'commerce','category_path':'Commerce/Gifting','demand_status':'validated_medium','demand_score':0.628,'status':'approved'}
def contexts():return [
 {'schema':'die.factory-asset.human-demand-context.v1','context_id':'HDC-GIFT-DESIGN','human':'gift and retail content creator','activity':'building reusable gifting layouts','place':'digital design workspace','time':'seasonal campaign production','demographic':'working adult','emotion':'clarity','problem':'need a reusable gift component','industry':'retail and packaging','commercial_intent':'reusable stock design utility','use_case':'reusable gift presentation and packaging composition','object_hints':['gift box'],'evidence':{'label':'RESEARCH_HYPOTHESIS','refs':['fixture://gift-design'],'inherited_demand_allowed':False}},
 {'schema':'die.factory-asset.human-demand-context.v1','context_id':'HDC-GIFT-UI','human':'ecommerce interface designer','activity':'designing checkout interface','place':'digital product workspace','time':'checkout flow design','demographic':'working adult','emotion':'clarity','problem':'need a gift action symbol','industry':'ecommerce','commercial_intent':'interface navigation icon utility','use_case':'gift action icon in ecommerce checkout interface','object_hints':['gift box'],'evidence':{'label':'RESEARCH_HYPOTHESIS','refs':['fixture://gift-ui'],'inherited_demand_allowed':False}},
 {'schema':'die.factory-asset.human-demand-context.v1','context_id':'HDC-GIFT-WRAP','human':'packaging designer','activity':'designing wrapping paper','place':'design studio','time':'seasonal packaging production','demographic':'working adult','emotion':'delight','problem':'need repeatable gift motif','industry':'packaging','commercial_intent':'wrapping pattern design utility','use_case':'repeat gift motifs on wrapping paper pattern','object_hints':['gift box'],'evidence':{'label':'RESEARCH_HYPOTHESIS','refs':['fixture://gift-wrap'],'inherited_demand_allowed':False}},
]

def test_end_to_end_trace_keeps_champion_exploitation_and_bounded_exploration():
 r=m.build_trace(seed=seed(),contexts=contexts())
 assert r['schema']=='die.factory-asset.production-intelligence-v2-trace.v1'
 assert r['dual_atlas_bridge']['direction']=='SUPPLY_FIRST' and r['dual_atlas_bridge']['result_count']>=1
 assert r['opportunity_plan']['force_all_modes'] is False and r['opportunity_plan']['cartesian_enumeration'] is False
 assert r['selected_champion']['semantic_mode']=='ISOLATED_OBJECT'
 assert r['selected_champion']['preset_id']=='ISOLATED_CARTOON_WATERCOLOR_L0'
 assert r['selected_champion']['candidate_lane']=='EXPLOITATION'
 assert r['expression_plan']['decision']=='SELECT' and len(r['expression_plan']['expressions'])==1
 assert r['asset_blueprint_v2']['asset_type']=='ISOLATED_OBJECT'
 assert r['producer_route']['result']=='DISPATCH_READY' and r['producer_route']['dispatch_adapter']=='FA104_PROVIDER_ROUTER'
 assert r['production_plan']['producer']['class']=='RASTER_GENERATIVE'
 assert all(x['semantic_identity_effect']=='NONE' for x in r['production_plan']['derivatives'])
 assert r['postproduction_acceptance']=={'receipt':'company/factory-asset/receipts/FA-319-baseline-package-acceptance.receipt.json','result':'PASS','package_result':'PACKAGE_READY','final_state':'WAITING_FOUNDER_QC'}
 assert r['authority']=={'effect':'NONE','throughput_scale_authorized':False,'provider_call_authorized':False,'submission_authorized':False,'publication_authorized':False}

def test_alternate_modes_and_premium_preset_remain_research_exploration_not_commands():
 r=m.build_trace(seed=seed(),contexts=contexts())
 modes={x['semantic_mode'] for x in r['exploration_candidates']}
 assert 'ICON' in modes and 'PATTERN' in modes
 premium=[x for x in r['exploration_candidates'] if x['preset_id']=='ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0']
 assert premium and all(x['state']=='RESEARCH_ONLY' for x in premium)
 assert all(x['candidate_lane']=='EXPLORATION' for x in r['exploration_candidates'] if x['semantic_mode']!='ISOLATED_OBJECT')

def test_expression_identity_is_semantic_not_file_derivative_identity():
 r=m.build_trace(seed=seed(),contexts=contexts());i=r['expression_identity']
 assert i['seed_id']=='SEED-000028' and i['semantic_mode']=='ISOLATED_OBJECT'
 assert i['preset_id']=='ISOLATED_CARTOON_WATERCOLOR_L0' and i['preset_revision']=='1.0.0'
 assert 'format' not in i and 'derivative' not in i
 premium=m.ledger.expression_identity(seed_id='SEED-000028',noun='gift box',semantic_mode='ISOLATED_OBJECT',commercial_expression=r['expression_plan']['expressions'][0]['product_expression'],preset_id='ISOLATED_PREMIUM_SEMI_REALISTIC_ILLUSTRATION_L0',preset_revision='1.0.0')
 assert premium['expression_fingerprint']!=i['expression_fingerprint']

def test_trace_is_deterministic():
 assert m.build_trace(seed=seed(),contexts=contexts())==m.build_trace(seed=seed(),contexts=contexts())
