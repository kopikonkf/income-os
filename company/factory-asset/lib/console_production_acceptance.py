from __future__ import annotations
import datetime as dt,json,urllib.request
from pathlib import Path

BROKERS={'cluster-a':'http://127.0.0.1:39121/v1/status','cluster-b':'http://127.0.0.1:39122/v1/status'}
PROVIDERS=('chatgpt','qwen','gemini','manus','duckai')

def _read(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def _fetch(url:str,timeout:float=2.0):
    with urllib.request.urlopen(url,timeout=timeout) as r:return json.loads(r.read())

def build_production_acceptance(repo_root:Path,*,broker_fetch=_fetch,observed_at:str|None=None)->dict:
    root=Path(repo_root)
    fa124=_read(root/'company/factory-asset/fixtures/scale/FA-124-final-result.json')
    c011=_read(root/'company/factory-asset/receipts/FA-C011-console-batch-acceptance.receipt.json')
    c012=_read(root/'company/factory-asset/receipts/FA-C012-console-recovery.receipt.json')
    fa313=_read(root/'company/factory-asset/contracts/fa313-hermes-multi-cluster-production.v1.json')
    fa314=_read(root/'company/factory-asset/contracts/fa314-storage-retention.v1.json')
    routes=[];clusters=[]
    for cid,url in BROKERS.items():
        try:
            b=broker_fetch(url);leases=b.get('tab_leases') or {};states=leases.get('provider_states') or {};active=int(leases.get('active_leases') or 0);ready=b.get('state')=='READY'
            clusters.append({'cluster_id':cid,'broker_state':b.get('state'),'active_leases':active,'open_pages':leases.get('open_pages'),'max_tabs':leases.get('max_tabs'),'reachable':True})
            for pid in PROVIDERS:
                state=states.get(pid,'UNAVAILABLE');routes.append({'route_id':f'{pid}@{cid}','provider_id':pid,'cluster_id':cid,'health':state,'capacity':'AVAILABLE' if ready and active<1 and state=='HEALTHY' else 'UNAVAILABLE','accepted_in_fa124':int(fa124['route_counts'].get(f'{pid}@{cid}',0))})
        except Exception as e:
            clusters.append({'cluster_id':cid,'broker_state':'UNREACHABLE','active_leases':None,'open_pages':None,'max_tabs':None,'reachable':False,'error_code':type(e).__name__})
            for pid in PROVIDERS:routes.append({'route_id':f'{pid}@{cid}','provider_id':pid,'cluster_id':cid,'health':'UNKNOWN','capacity':'UNAVAILABLE','accepted_in_fa124':int(fa124['route_counts'].get(f'{pid}@{cid}',0))})
    healthy=sum(1 for r in routes if r['health']=='HEALTHY');cluster_ok=all(c['reachable'] and c['broker_state']=='READY' for c in clusters)
    p95=int(fa314['measurement']['workspace_total_bytes']['p95']);gib=1024**3
    technical=(fa124.get('result')=='PASS' and c011.get('result')=='PASS' and c012.get('result')=='PASS' and cluster_ok and healthy>=2)
    return {
      'schema':'die.factory-asset.console-production-acceptance.v1','observed_at':observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
      'technical_result':'PASS' if technical else 'REVIEW_REQUIRED','founder_validation_required':True,'publication_authority':False,'provider_dispatch_authority':False,
      'production_model':{'accepted_masters':fa124['throughput']['accepted_masters'],'unique_sha256':fa124['throughput']['unique_sha256'],'unique_seed_ids':fa124['throughput']['unique_seed_ids'],'dispatch_commits':fa124['throughput']['dispatch_commits'],'dispatch_commit_cap':fa124['throughput']['dispatch_commit_cap'],'distribution_policy':fa124['throughput']['distribution_policy'],'all_10_routes_certified':fa124['route_certification']['all_10_routes_certified']},
      'live_pool':{'clusters':clusters,'routes':routes,'healthy_routes':healthy,'scheduler_contract':fa313['scheduler_contract'],'cluster_b_optional_capacity_not_spof':fa313['routing']['cluster_b_optional_capacity_not_spof']},
      'batch_queue':{'fa_c011_result':c011['result'],'quantity_proven':c011['batch']['quantity'],'worker_slot_limit':c011['concurrency_and_backpressure']['worker_slot_limit'],'backpressure_proven':c011['concurrency_and_backpressure']['backpressure_events']>0,'duplicate_ownership_blocked':c011['ownership_and_dedupe']['duplicate_ownership_blocked']>0},
      'recovery':{'fa_c012_result':c012['result'],'false_success_created':c012['recovery_truth']['false_success_created'],'duplicate_dispatch_blocked':c012['recovery_truth']['duplicate_dispatch_blocked'],'committed_dispatch_fenced':c012['recovery_truth']['committed_dispatch']=='PAUSED_DISPATCH_RECONCILIATION_REQUIRED'},
      'output_truth':{'exact_duplicate_hashes':fa124['distinctness']['exact_duplicate_hashes'],'object_confirmed_near_duplicate_pairs':fa124['distinctness']['object_confirmed_near_duplicate_pairs'],'orientation_advisory_mismatches':fa124['orientation']['advisory_mismatches'],'fa123_downstream_capacity_pass':fa124['truth_boundaries']['fa123_downstream_capacity_pass']},
      'storage':{'workspace_p95_bytes':p95,'estimated_100_per_day_gib':round(p95*100/gib,3),'estimated_30_day_gib':round(p95*100*30/gib,3),'archive_spend_authorized':False},
      'truth_boundaries':{'marketplace_submission_authorized':False,'publication_authorized':False,'credential_values_read':False,'cookies_or_tokens_read':False,'console_live_dispatch_enabled':False}
    }
