from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path: sys.path.insert(0,str(_LIB))
import cognition_work_card
import orchestrator_queue
import product_packager
import product_planner
import resilience_policy

SCHEMA='die.h03.scale-soak-report.v1'
EXECUTION_MODE='NONLIVE_ROLE_FIXTURE'


def _profile(*, pid:str, kp_id:str, seed_id:str, shape:str, sections:list[dict[str,Any]], **overrides:Any) -> dict[str,Any]:
    value={'schema_version':product_planner.PROFILE_SCHEMA,'planning_profile_id':pid,'holding_id':'H03','problem_seed_id':seed_id,'knowledge_package_id':kp_id,'desired_outcome':'reduce people-search exposure with a practical reusable reference','delivery_shape':shape,'recurrence':'ONE_TIME','decision_complexity':'LOW','explanation_depth':'MEDIUM','input_capture':'NONE','lookup_frequency':'LOW','evidence_density':'MEDIUM','reusable_structure':False,'section_plan':sections}
    value.update(overrides); return value


def _content_batches(blueprint:dict[str,Any], kp:dict[str,Any]) -> list[dict[str,Any]]:
    claims={c['claim_id']:c for c in kp['claims']}; batches=[]
    for idx,section in enumerate(blueprint['sections'],start=1):
        blocks=[]
        for j,cid in enumerate(section['claim_ids'],start=1):
            c=claims[cid]
            kind='CHECKLIST_ITEM' if blueprint['form']=='checklist' else ('BULLET' if blueprint['form']=='reference_sheet' else 'STEP')
            blocks.append({'block_id':f'{blueprint["product_id"]}-B{idx:02d}{j:02d}','kind':kind,'text':c['text'],'claim_ids':[cid],'evidence_refs':list(c['evidence_refs'])})
        batches.append({'schema_version':'die.h03.content-block-batch.v1','content_batch_id':f'H03-CB-{blueprint["product_id"]}-{idx:03d}','holding_id':'H03','product_id':blueprint['product_id'],'knowledge_package_id':kp['knowledge_package_id'],'section_id':f'SEC-{idx:03d}','section_heading':section['heading'],'producer_observation':{'provider_id':'SCALE_FIXTURE','execution_mode':EXECUTION_MODE},'blocks':blocks,'truth_status':'DERIVED_SEMANTIC_CONTENT'})
    return batches


def _cards(blueprints:list[dict[str,Any]]) -> list[dict[str,Any]]:
    cards=[]
    for bp in blueprints:
        for idx,_section in enumerate(bp['sections'],start=1):
            cards.append(cognition_work_card.validate_work_card({'schema_version':cognition_work_card.CARD_SCHEMA,'work_card_id':f'H03-WC-SCALE-{bp["product_id"]}-SEC-{idx:03d}','holding_id':'H03','task_id':'H03-SCALE-001','role':'PRODUCER','queue':'production','idempotency_key':f'h03-scale:{bp["product_id"]}:{idx}','input_artifacts':[{'artifact_id':bp['product_id'],'kind':'product_blueprint','ref':f'artifact://product-blueprint/{bp["product_id"]}','sha256':None}],'output_contract':{'artifact_kind':'content_block_batch','schema_version':'die.h03.content-block-batch.v1'},'capability_requirements':cognition_work_card.standard_web_ai_capabilities(),'terminal_policy':{'max_attempts':3,'retryable_failures':['RATE_LIMITED','PROVIDER_UNAVAILABLE','INVALID_OUTPUT']}}))
    return cards


def run_scale_soak(*, output_root:Path, knowledge_package:dict[str,Any], problem_seed_id:str) -> dict[str,Any]:
    # Capacity is explicit runtime observation for this non-live soak, not a production claim.
    provider_slots={'fixture-producer-a':4,'fixture-producer-b':2}
    total_slots=sum(provider_slots.values())
    sections_per_product=2
    safe_product_capacity=max(1,total_slots//sections_per_product)

    section_sets=[
        [{'heading':'Find and opt out','claim_ids':['C1','C2','C3']},{'heading':'Recheck and understand limits','claim_ids':['C4','C5','C6']}],
        [{'heading':'Removal checklist','claim_ids':['C1','C2','C3']},{'heading':'Follow-up checklist','claim_ids':['C4','C5','C6']}],
        [{'heading':'Quick action reference','claim_ids':['C1','C2','C3']},{'heading':'Limits and follow-up','claim_ids':['C4','C5','C6']}],
    ][:safe_product_capacity]
    specs=[
        ('H03-SCALE-PROD-GUIDE','Scale Soak DIY Opt-Out Guide','EXECUTE_SEQUENCE',{}),
        ('H03-SCALE-PROD-CHECK','Scale Soak Opt-Out Checklist','QUICK_VERIFY',{}),
        ('H03-SCALE-PROD-REF','Scale Soak Opt-Out Reference','LOOKUP_REFERENCE',{'lookup_frequency':'HIGH','explanation_depth':'LOW'}),
    ][:safe_product_capacity]
    blueprints=[]
    for sections,(pid,title,shape,extra) in zip(section_sets,specs):
        profile=_profile(pid=f'PLAN-{pid}',kp_id=knowledge_package['knowledge_package_id'],seed_id=problem_seed_id,shape=shape,sections=sections,**extra)
        blueprints.append(product_planner.build_product_blueprint(product_id=pid,title=title,profile=profile,knowledge_package=knowledge_package))

    cards=_cards(blueprints); state=orchestrator_queue.create_state('H03-SCALE-SOAK-001')
    enqueued_at={}; started_at={}; completed_at={}
    start=time.perf_counter(); cpu_start=time.process_time(); tracemalloc.start()
    for card in cards:
        enqueued_at[card['work_card_id']]=time.perf_counter(); orchestrator_queue.enqueue(state,card)

    policy=resilience_policy.default_policy(queue_limit=total_slots)
    bp_action=resilience_policy.backpressure_action(queue_depth=len(cards),policy=policy)
    if not bp_action['backpressure']:
        raise AssertionError('SCALE_BACKPRESSURE_NOT_EXERCISED')

    retry_count=0; fallback_success=0; terminal_failures=0; provider_events=[]
    provider_schedule=['fixture-producer-a']*4+['fixture-producer-b']*2
    for idx,(card,provider) in enumerate(zip(cards,provider_schedule)):
        wid=card['work_card_id']; orchestrator_queue.transition(state,wid,'DISPATCHED'); started_at[wid]=time.perf_counter(); orchestrator_queue.transition(state,wid,'RUNNING')
        if idx==0:
            action=resilience_policy.decide_failure(failure_code='RATE_LIMITED',attempt=1,max_attempts=3,alternative_slots=1,policy=policy)
            provider_events.append({'work_card_id':wid,'provider_id':provider,'failure_code':'RATE_LIMITED','action':action['action']})
            if action['action']!='FALLBACK_ALTERNATE_WORKER': raise AssertionError('SCALE_FALLBACK_NOT_SELECTED')
            retry_count+=1; fallback_success+=1; provider='fixture-producer-b'
        result={'schema_version':cognition_work_card.RESULT_SCHEMA,'work_card_id':wid,'attempt':1,'status':'SUCCEEDED','output_artifacts':[{'artifact_id':f'CB-{wid}','kind':'content_block_batch','ref':f'artifact://content/{wid}'}]}
        orchestrator_queue.apply_result(state,card,result); completed_at[wid]=time.perf_counter()
        provider_events.append({'work_card_id':wid,'provider_id':provider,'status':'SUCCEEDED'})

    package_receipts=[]
    for bp in blueprints:
        package_receipts.append(product_packager.build_local_product_package(output_root=output_root,blueprint=bp,knowledge_package=knowledge_package,content_batches=_content_batches(bp,knowledge_package)))

    current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); end=time.perf_counter(); cpu_end=time.process_time()
    wall=max(end-start,1e-9)
    latencies=[(started_at[k]-enqueued_at[k])*1000 for k in enqueued_at]
    terminal_failures=sum(1 for j in state['jobs'].values() if j['state']=='FAILED_TERMINAL')
    report={'schema_version':SCHEMA,'holding_id':'H03','soak_id':'H03-SCALE-SOAK-001','execution_mode':EXECUTION_MODE,'capacity_basis':{'provider_slots':provider_slots,'total_slots':total_slots,'sections_per_product':sections_per_product,'safe_product_capacity':safe_product_capacity,'sizing_rule':'floor(total_slots/sections_per_product)'},'product_count':len(blueprints),'worker_job_count':len(cards),'throughput_products_per_second':round(len(blueprints)/wall,6),'queue_latency_ms':{'min':round(min(latencies),6),'mean':round(sum(latencies)/len(latencies),6),'max':round(max(latencies),6)},'terminal_failure_rate':terminal_failures/max(1,len(cards)),'retry_count':retry_count,'fallback_success_count':fallback_success,'provider_bottlenecks':[{'provider_id':'fixture-producer-a','kind':'RATE_LIMITED','recovered_by':'fixture-producer-b'}],'profile_bottlenecks':[{'profile_shard_id':'fixture-scale-shard','kind':'CAPACITY_LIMIT','observed_slots':total_slots,'backpressure_action':bp_action['action']}],'resource_usage':{'wall_seconds':round(wall,6),'cpu_seconds':round(cpu_end-cpu_start,6),'peak_tracemalloc_bytes':peak,'current_tracemalloc_bytes':current},'package_receipts':package_receipts,'external_publication':False,'status':'PASS' if terminal_failures==0 and fallback_success==1 else 'FAIL'}
    return report
