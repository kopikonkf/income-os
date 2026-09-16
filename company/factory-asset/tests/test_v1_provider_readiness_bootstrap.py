from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DISPATCH=ROOT/'company/factory-asset/bin/production_multi_cluster_dispatch.mjs'
LEASES=ROOT/'company/browser/linux/cluster_tab_leases.mjs'
WORKER=ROOT/'company/factory-asset/lib/console_broker_provider_worker.mjs'

def test_dispatcher_matches_broker_default_provider_state_after_restart():
    d=DISPATCH.read_text(encoding='utf-8')
    l=LEASES.read_text(encoding='utf-8')
    assert "providerState(providerId) { return this.providerStates.get(providerId) || 'HEALTHY'; }" in l
    assert "snap.provider_states?.[provider]||'HEALTHY'" in d
    assert "snap.provider_states?.[provider]||'UNAVAILABLE'" not in d

def test_live_worker_reclassifies_provider_before_prompt_dispatch():
    w=WORKER.read_text(encoding='utf-8')
    classify=w.index('const readiness = await classifyProviderAfterSettle')
    persist=w.index('await setClusterProviderState', classify)
    gate=w.index("if (readiness.state !== 'HEALTHY')", persist)
    dispatch=w.index('await markClusterTab', gate)
    assert classify < persist < gate < dispatch
