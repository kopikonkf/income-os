from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[3]
C=ROOT/'company/factory-asset/contracts/fa307-two-cluster-live.v1.json'
R=ROOT/'company/factory-asset/bin/run_fa307_two_cluster_live.mjs'
G=ROOT/'company/factory-asset/task-graph-v1.json'
REC=ROOT/'company/factory-asset/receipts/FA-307-two-cluster-parallel.receipt.json'
CLOSE=ROOT/'company/factory-asset/fixtures/multi-cluster/FA-307-composite-closure-20260908.json'

def test_composite_closure_consumes_no_attempt9_provider_calls():
 c=json.loads(C.read_text());x=json.loads(CLOSE.read_text())
 assert c['status']=='ACCEPTED' and c['revision']=='1.9.0-composite-closure'
 assert c['authority']['authorized_provider_calls']==0 and c['closure']['attempt_9_provider_calls_performed']==0
 assert x['result']=='PASS_COMPOSITE_EVIDENCE' and x['attempt_9_provider_calls_performed']==0
 assert x['historical_attempts_relabelled'] is False and x['all_acceptance_predicates_satisfied'] is True

def test_composite_evidence_satisfies_parallel_topology_and_original_lineage():
 x=json.loads(CLOSE.read_text());a=x['assertions'];assert all(a.values())
 assert x['parallel_topology_basis']['assertions']['parallel_dispatch_intervals_overlap'] is True
 q=x['current_original_lineage']['qwen_cluster_a'];g=x['current_original_lineage']['gemini_cluster_b']
 assert q['status']=='SUCCEEDED' and g['status']=='SUCCEEDED'
 assert q['provider_id']=='qwen' and q['cluster_id']=='cluster-a'
 assert g['provider_id']=='gemini' and g['cluster_id']=='cluster-b'
 assert q['artifact']['sha256']!=g['artifact']['sha256']
 assert g['artifact']['original_byte_acquisition_method']=='provider_generated_image_response_body_after_dispatch'
 assert q['lease_release']['released'] is True and g['lease_release']['released'] is True

def test_attempts_1_to_8_remain_historical_failures_without_retry():
 names=['FA-307-attempt-1-qwen-gemini-result.json','FA-307-attempt-2-qwen-manus-result.json','FA-307-attempt-3-qwen-manus-result.json','FA-307-attempt-4-duck-manus-result.json','FA-307-attempt-5-gemini-manus-result.json','FA-307-attempt-6-gemini-manus-result.json','FA-307-attempt-7-qwen-gemini-result.json','FA-307-attempt-8-qwen-gemini-result.json']
 ds=[json.loads((ROOT/'company/factory-asset/fixtures/multi-cluster'/n).read_text()) for n in names]
 assert all(d['result']=='FAIL' for d in ds) and all(d['post_dispatch_retry_performed'] is False for d in ds)
 assert ds[3]['human_challenge_bypassed'] is False

def test_runner_selftest_and_gemini_hardening_remain_valid_reference():
 r=subprocess.run(['node',str(R),'selftest'],capture_output=True,text=True,check=True,timeout=30);d=json.loads(r.stdout);assert d['result']=='PASS' and all(d['assertions'].values())
 s=R.read_text();start=s.index('async function generateGemini');listener=s.index("page.on('response'",start);guard=s.index('if(!dispatchCommitted)return',listener);commit=s.index('dispatchCommitted=true',start);network_select=s.index('if(networkImages.length)',commit);control=s.index("if(!control)throw new Error('E_BOUNDED_COMPLETION_TIMEOUT')",commit);assert listener<guard<commit<control<network_select
 assert 'provider_generated_image_response_body_after_dispatch' in s

def test_receipt_and_graph_close_fa307_and_unlock_direct_dependents():
 r=json.loads(REC.read_text());g=json.loads(G.read_text());by={x['id']:x for x in g['tasks']}
 assert r['status']=='DONE' and r['result']=='PASS' and r['closure_mode']=='PASS_COMPOSITE_EVIDENCE'
 assert r['composite_closure']['attempt_9_provider_calls_performed']==0 and r['composite_closure']['historical_attempts_1_to_8_relabelled'] is False
 assert by['FA-307']['status']=='DONE' and 'PASS_COMPOSITE_EVIDENCE' in by['FA-307']['result']
 for tid in ['FA-310','FA-311','FA-312','FA-313','FA-314']: assert by[tid]['status'] in {'READY','IN_PROGRESS','DONE'}
 assert by['FA-C018']['status'] in {'BLOCKED','READY','IN_PROGRESS','DONE'} and by['FA-308']['status']=='DEFERRED'
