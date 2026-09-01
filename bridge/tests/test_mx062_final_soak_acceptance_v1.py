from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company'/'muxia-task-graph-v1.json'
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'MX-062-final-soak.acceptance.receipt.json'

def test_mx062_done_releases_mx070() -> None:
    tasks={x['id']:x for x in json.loads(GRAPH.read_text(encoding='utf-8'))['tasks']}
    assert tasks['MX-062']['status']=='DONE'
    assert tasks['MX-070']['status']=='DONE'

def test_real_soak_acceptance_gates_are_proven() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    r=d['runner_receipt']; v=d['independent_ledger_verification']; g=d['acceptance_gates']
    assert d['status']=='DONE' and d['decision']=='PASS_REAL_ELAPSED_24H'
    assert r['elapsedMs'] >= r['minimumElapsedMs'] == 86400000
    assert r['coverage'] >= r['minimumCoverage'] == 0.95
    assert all(x==0 for x in r['failures'].values())
    assert v['rows']==r['samples']==1438 and v['chain_valid'] is True
    assert v['recomputed_receipt_matches_host_receipt'] is True
    assert v['gaps_over_90_seconds']==0 and v['clock_or_elapsed_regressions']==0
    assert all(g.values())
    assert r['authorityBoundary']=={'providerInvoked':False,'credentialsRead':False,'productionProfileRead':False,'submissionAuthorized':False}

def test_successful_run_service_evidence_excludes_preflight_failures() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))['linux_host_evidence']
    assert d['source_sha']=='dfb74d7e09b19f68381e1064899d70c645a61f26'
    assert d['service_result']=='success' and d['exec_main_status']==0
    assert d['successful_run_failed_lines']==0
    assert d['successful_run_start_events']==1 and d['successful_run_complete_pass_events']==1 and d['successful_deactivation_events']==1
