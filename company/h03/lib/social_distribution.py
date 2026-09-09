from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

_LIB=Path(__file__).resolve().parent
if str(_LIB) not in sys.path: sys.path.insert(0,str(_LIB))
import profile_pool

ADAPTER_SCHEMA='die.h03.social-distribution-adapter-registry.v1'


def load_adapter_registry()->dict[str,Any]:
    p=Path(__file__).resolve().parents[1]/'runtime'/'social-distribution-adapter-registry.v1.json'
    return json.loads(p.read_text(encoding='utf-8'))


def load_growth_pool()->dict[str,Any]:
    p=Path(__file__).resolve().parents[1]/'runtime'/'growth-browser-profile-pool.v1.json'
    return json.loads(p.read_text(encoding='utf-8'))


def validate_adapter_registry(registry:dict[str,Any])->dict[str,Any]:
    if registry.get('schema_version')!=ADAPTER_SCHEMA or registry.get('holding_id')!='H03': raise ValueError('SOCIAL_ADAPTER_REGISTRY_INVALID')
    policy=registry.get('policy') or {}
    if policy.get('initial_transport')!='BROWSER_CDP' or policy.get('credentials_session_material')!='HOST_LOCAL_ONLY' or policy.get('publication_requires_founder') is not True: raise ValueError('SOCIAL_ADAPTER_POLICY_INVALID')
    adapters=registry.get('adapters') or []
    ids=[a.get('channel_id') for a in adapters]
    if not adapters or len(ids)!=len(set(ids)) or any(not x for x in ids): raise ValueError('SOCIAL_ADAPTER_CHANNEL_INVALID')
    for a in adapters:
        if a.get('initial_transport')!='BROWSER_CDP' or not isinstance(a.get('future_adapter_families'),list): raise ValueError('SOCIAL_ADAPTER_TRANSPORT_INVALID')
    return registry


def validate_growth_pool(pool:dict[str,Any])->dict[str,Any]:
    profile_pool.validate_profile_pool(pool)
    if pool.get('purpose')!='GROWTH_WORKFORCE': raise ValueError('SOCIAL_GROWTH_POOL_PURPOSE_REQUIRED')
    if str(pool.get('pool_id','')).startswith('knowledge'): raise ValueError('SOCIAL_KNOWLEDGE_POOL_REUSE_FORBIDDEN')
    return pool


def build_distribution_intents(*, atoms:list[dict[str,Any]], pool:dict[str,Any]|None=None, registry:dict[str,Any]|None=None)->list[dict[str,Any]]:
    if not atoms: raise ValueError('SOCIAL_ATOMS_REQUIRED')
    pool=validate_growth_pool(copy.deepcopy(pool or load_growth_pool()))
    registry=validate_adapter_registry(registry or load_adapter_registry())
    adapters={a['channel_id']:a for a in registry['adapters']}
    status=profile_pool.aggregate_runtime_status(pool)
    intents=[]
    for atom in atoms:
        cid=atom.get('channel_id')
        if cid not in adapters: raise ValueError(f'SOCIAL_ADAPTER_MISSING:{cid}')
        if atom.get('publication_authorized') is not False or atom.get('paid_ads') is not False: raise ValueError('SOCIAL_ATOM_AUTHORITY_INVALID')
        observed=status.get(cid,{'state':'UNKNOWN','available_slots':0,'profile_shard_id':None,'transport_family':'BROWSER_CDP'})
        ready=observed.get('state')=='READY' and observed.get('available_slots',0)>0
        intents.append({
            'schema_version':'die.h03.social-distribution-intent.v1',
            'holding_id':'H03',
            'atom_id':atom['atom_id'],
            'channel_id':cid,
            'surface':atom['surface'],
            'campaign_id':atom['campaign_id'],
            'creative_id':atom['creative_id'],
            'transport_family':'BROWSER_CDP',
            'future_adapter_families':list(adapters[cid]['future_adapter_families']),
            'profile_shard_id':observed.get('profile_shard_id'),
            'runtime_state':observed.get('state','UNKNOWN'),
            'available_slots':observed.get('available_slots',0),
            'distribution_state':'READY_FOR_FOUNDER_GATE' if ready else 'WAITING_ACCOUNT_PREFLIGHT',
            'founder_gate_required':True,
            'publication_authorized':False,
            'credential_values_read':False,
            'session_material_persisted':False,
        })
    return intents
