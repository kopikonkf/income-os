import importlib.util,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'company/factory-asset/lib/dual_atlas_context_bridge.py');m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m)

def obj(seed,noun,cls='utility',cat='Utility'):
    return {'seed_id':seed,'noun':noun,'object_class':cls,'category_path':cat,'evidence_refs':[f'object-atlas://{seed}']}

def test_foundation_contexts_validate_and_do_not_inherit_demand():
    rows=m.load_catalog(); assert len(rows)==3
    for c in rows:
        m.validate_context(c); assert c['evidence']['label']=='CANON_EXAMPLE_ONLY'; assert c['evidence']['inherited_demand_allowed'] is False

def test_supply_first_maps_cable_organizer_to_remote_work_context_without_cartesian_expansion():
    r=m.supply_first(obj('SEED-CABLE','cable organizer','office utility','Office/Organization'),m.load_catalog(),limit=3)
    assert r['direction']=='SUPPLY_FIRST' and r['considered_count']==3 and r['result_count']>=1
    assert r['candidates'][0]['context_id']=='HDC-REMOTE_DESK_CABLES'
    assert 'EXACT_OBJECT_HINT' in r['candidates'][0]['coherence_reasons']
    assert r['candidates'][0]['hypothesis_only'] is True
    assert r['policy']['cartesian_enumeration'] is False and r['policy']['production_authorized'] is False

def test_demand_first_maps_senior_medication_context_to_pill_organizer_first():
    ctx=next(x for x in m.load_catalog() if x['context_id']=='HDC-SENIOR_MED_ROUTINE')
    objects=[obj('SEED-CABLE','cable organizer'),obj('SEED-PILL','pill organizer','health utility','Health/Medication'),obj('SEED-METER','soil moisture meter')]
    r=m.demand_first(ctx,objects,limit=3)
    assert r['direction']=='DEMAND_FIRST' and r['candidates'][0]['seed_id']=='SEED-PILL'
    assert r['candidates'][0]['context_evidence_label']=='CANON_EXAMPLE_ONLY'
    assert r['policy']['inherited_demand_allowed'] is False and r['policy']['provider_dispatch_authorized'] is False

def test_noncoherent_object_is_not_forced_into_context():
    ctx=next(x for x in m.load_catalog() if x['context_id']=='HDC-SENIOR_MED_ROUTINE')
    r=m.demand_first(ctx,[obj('SEED-SAIL','sailboat','vehicle','Transport/Marine')])
    assert r['result_count']==0 and r['candidates']==[]

def test_bounded_retrieval_fails_closed_above_256_candidates_and_limit_12():
    ctx=m.load_catalog()[0]
    with pytest.raises(m.DualAtlasBridgeError,match='BOUNDED_SCAN_EXCEEDED'):
        m.demand_first(ctx,[obj(f'SEED-{i}','pill organizer') for i in range(257)])
    with pytest.raises(m.DualAtlasBridgeError,match='LIMIT_INVALID'):
        m.supply_first(obj('SEED-PILL','pill organizer'),m.load_catalog(),limit=13)

def test_bridge_is_deterministic():
    o=obj('SEED-PILL','pill organizer','health utility','Health/Medication')
    assert m.supply_first(o,m.load_catalog())==m.supply_first(o,m.load_catalog())
