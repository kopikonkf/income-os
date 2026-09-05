import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REG=json.loads((ROOT/'company/factory-asset/registries/provider-feasibility.v1.json').read_text())
P={x['provider_id']:x for x in REG['providers']}

def test_all_six_providers_and_scores_are_deterministic():
    assert set(P)=={'qwen','chatgpt','gemini','grok','manus','duckai'}
    dims=('transport','policy','auth','linux_feasibility','image_capability','capacity','technical_quality','maintenance')
    for row in P.values():
        assert row['total_score']==sum(row[d]['score'] for d in dims)
        assert 0 <= row['total_score'] <= 100

def test_unknown_capacity_never_becomes_throughput_claim():
    for pid in ('qwen','chatgpt','gemini','manus','duckai'):
        assert P[pid]['capacity']['state']=='UNKNOWN'
        assert P[pid]['capacity']['sustained_throughput_proven'] is False
    assert P['grok']['capacity']['sustained_throughput_proven'] is False
    doc=(ROOT/'docs/architecture/FACTORY_ASSET_PROVIDER_FEASIBILITY_V1.md').read_text()
    assert 'sustained capacity remains **`UNKNOWN`**' in doc
    assert 'No jobs/day or quota extrapolation from latency' in doc

def test_policy_and_linux_truth_boundaries_fail_closed():
    assert P['chatgpt']['linux_feasibility']['state']=='PROVEN_LIVE'
    for pid in ('qwen','gemini','manus','duckai'):
        assert P[pid]['linux_feasibility']['state']=='CANDIDATE_NOT_PROVEN'
    assert P['grok']['policy']['state']=='DEFERRED_PLATFORM_GATE'
    assert P['grok']['eligibility']=='DEFERRED_NOT_IN_ACTIVE_POOL'
    assert REG['deferred']==['grok']

def test_machine_and_document_rank_agree():
    assert REG['recommended_sequence']==['chatgpt','qwen','gemini','manus','duckai']
    scores=[P[x]['total_score'] for x in REG['recommended_sequence']]
    assert scores==sorted(scores,reverse=True)
    assert P['chatgpt']['total_score']==85
    assert P['qwen']['total_score']==79
