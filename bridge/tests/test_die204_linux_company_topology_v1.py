from __future__ import annotations

import copy, importlib.util, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RECEIPT=ROOT/'company'/'muxia'/'receipts'/'DIE-204-linux-company-topology.receipt.json'
VALIDATOR=ROOT/'company'/'scripts'/'validate_die204_topology_receipt.py'


def load_validator():
    spec=importlib.util.spec_from_file_location('die204_validator_test',VALIDATOR); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m


def test_die204_receipt_passes_fail_closed_validator() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8')); m=load_validator()
    assert m.validate(d)==[]
    assert d['status']=='PASS'
    assert d['dependencies']=={'DIE-200':'DONE','DIE-201':'DONE','DIE-202':'DONE','DIE-203':'DONE','MX-052':'DONE'}


def test_die204_topology_chain_pins_data_principal_worker_muxia_artifact_lineage() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    assert d['atlas']['object']['objects']==475560
    assert d['principals']['executive']['tools']==18
    assert d['principals']['division01']['principal_id']=='division-head-division01'
    assert d['principals']['division01']['tools']==6
    assert d['principals']['division01']['semantic_invocation_performed'] is False
    assert d['principals']['hermes']['gateway_active'] is True
    assert d['principals']['hermes']['telegram_e2e']=='PASS'
    assert d['principals']['worker']['executor']=='opencode'
    assert d['handoff']['final_status']=='SUCCEEDED'
    assert d['handoff']['provider_call_performed'] is False
    assert all(d['artifact_registry']['completion_evidence'].values())


def test_die204_preserves_architect_and_aether_boundaries() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8'))
    topo=d['company_topology']; a=d['aether_boundary']; auth=d['authority']
    assert topo['architect_status']=='DEFERRED_SOURCE_IMPORT'
    assert topo['architect_windows_control_preserved'] is True
    assert topo['division002_to_100_materialization']=='ON_DEMAND_NO_EMPTY_SOURCE_TREES'
    assert a=={'active_lineage_text_hits':0,'protected_symlink_hits':0,'absorbed':False}
    assert auth['production_authority_granted'] is False
    assert auth['submission_performed'] is False
    assert auth['publication_performed'] is False
    assert auth['spend_usd']==0


def test_die204_validator_rejects_false_success_and_aether_absorption() -> None:
    d=json.loads(RECEIPT.read_text(encoding='utf-8')); m=load_validator()
    bad=copy.deepcopy(d); bad['artifact_registry']['completion_evidence']['hashMatches']=False
    assert 'E_COMPLETION:hashMatches' in m.validate(bad)
    bad=copy.deepcopy(d); bad['aether_boundary']['absorbed']=True
    assert 'E_AETHER_ABSORPTION' in m.validate(bad)
    bad=copy.deepcopy(d); bad['authority']['production_authority_granted']=True
    assert 'E_AUTHORITY' in m.validate(bad)


def test_die202_and_die204_graph_and_registry_are_closed() -> None:
    graph=json.loads((ROOT/'company'/'muxia-task-graph-v1.json').read_text(encoding='utf-8')); tasks={x['id']:x for x in graph['tasks']}
    assert tasks['DIE-200']['status']=='DONE'; assert tasks['DIE-201']['status']=='DONE'; assert tasks['DIE-202']['status']=='DONE'; assert tasks['DIE-203']['status']=='DONE'; assert tasks['DIE-204']['status']=='DONE'
    reg=json.loads((ROOT/'company'/'component-registry-v1.json').read_text(encoding='utf-8'))['components']
    assert reg['hermes']['status']=='LINUX_ACTIVE_VERIFIED'
    assert reg['workers']['status']=='LINUX_READY_VERIFIED'
    assert reg['muxia']['status']=='LINUX_TOPOLOGY_PROVEN'
    assert reg['architect']['status']=='DEFERRED_SOURCE_IMPORT'