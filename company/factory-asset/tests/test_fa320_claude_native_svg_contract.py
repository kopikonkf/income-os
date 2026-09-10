import copy
import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT=Path(__file__).resolve().parents[3]
LIB=ROOT/'company/factory-asset/lib/claude_native_svg_adapter.py'
spec=importlib.util.spec_from_file_location('claude_svg',LIB); m=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name]=m; spec.loader.exec_module(m)

def bp(name='icon'):
    return json.loads((ROOT/f'company/factory-asset/fixtures/shopping-bag-blueprint-v2/{name}.json').read_text(encoding='utf-8'))

def test_native_producer_shared_contract_includes_native_vector():
    s=json.loads((ROOT/'company/factory-asset/schemas/native-producer.schema.json').read_text(encoding='utf-8'))
    assert 'NATIVE_VECTOR' in s['$defs']['producer_class']['enum']

def test_claude_contract_is_candidate_only_and_grants_no_live_authority():
    c=m.load_contract()
    assert c['provider_id']=='claude' and c['producer_class']=='NATIVE_VECTOR'
    assert c['engine_state']=='CANDIDATE_UNACCEPTED'
    assert c['eligible_asset_types']==['ICON','OUTLINE']
    assert c['provider_output_contract']['raster_to_vector_trace_allowed'] is False
    assert c['authority']=={'provider_call_authorized':False,'route_promotion_authorized':False,'submission_authorized':False,'publication_authorized':False}

def test_request_is_hash_bound_deterministic_and_svg_native_only():
    b=bp('icon'); h=m.sha256_value(b); prompt='Create a clean editable shopping bag icon as genuine SVG paths. Return SVG source only with no raster image.'
    a=m.build_request(job_id='claude-vector-001',blueprint=b,frozen_blueprint_sha256=h,provider_prompt=prompt)
    z=m.build_request(job_id='claude-vector-001',blueprint=copy.deepcopy(b),frozen_blueprint_sha256=h,provider_prompt=prompt)
    assert a==z
    assert a['asset_type']=='ICON' and a['native_representation']=='VECTOR_PATHS' and a['master_format']=='SVG'
    assert a['output_contract']['conversion_from_raster'] is False and a['output_contract']['embedded_raster_only_allowed'] is False
    assert a['provider_prompt_sha256']==m.sha256_text(prompt)
    assert a['authority']['provider_call_authorized'] is False

def test_only_icon_outline_blueprints_are_eligible():
    with pytest.raises(m.ClaudeNativeVectorError,match='UNSUPPORTED_ASSET_TYPE'):
        b=bp('photo'); m.build_request(job_id='claude-vector-002',blueprint=b,frozen_blueprint_sha256=m.sha256_value(b),provider_prompt='Create a native SVG vector source with editable paths only and no embedded raster image.')

def test_blueprint_and_prompt_hash_drift_fail_closed():
    b=bp('outline'); h=m.sha256_value(b)
    with pytest.raises(m.ClaudeNativeVectorError,match='FROZEN_BLUEPRINT_HASH_MISMATCH'):
        m.build_request(job_id='claude-vector-003',blueprint=b,frozen_blueprint_sha256='0'*64,provider_prompt='Create a native SVG outline with editable paths only and no embedded raster image.')
    with pytest.raises(m.ClaudeNativeVectorError,match='PROMPT_HASH_MISMATCH'):
        m.build_request(job_id='claude-vector-003',blueprint=b,frozen_blueprint_sha256=h,provider_prompt='Create a native SVG outline with editable paths only and no embedded raster image.',provider_prompt_sha256='0'*64)

def test_payload_normalizer_accepts_svg_fence_but_rejects_prose_or_non_svg():
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0 L10 0 L10 10 Z"/></svg>'
    assert m.normalize_svg_payload('```svg\n'+svg+'\n```')==svg
    with pytest.raises(m.ClaudeNativeVectorError,match='PROVIDER_RESPONSE_INVALID'):m.normalize_svg_payload('Here is it: '+svg)
    with pytest.raises(m.ClaudeNativeVectorError,match='OUTPUT_NOT_SVG'):m.normalize_svg_payload('not vector')

def test_dispatch_registry_names_claude_candidate_but_route_stays_unaccepted():
    r=json.loads((ROOT/'company/factory-asset/registries/producer-dispatch.v1.json').read_text(encoding='utf-8'))
    row=next(x for x in r['routes'] if x['producer_class']=='NATIVE_VECTOR' and x['semantic_modes']==['ICON','OUTLINE'])
    assert row['dispatch_adapter']=='CLAUDE_NATIVE_SVG_V1' and row['candidate_provider']=='claude'
    assert row['engine_state']=='UNAVAILABLE_NOT_ACCEPTED' and row['post_hoc_conversion_allowed'] is False
    assert row['evidence_refs']==['receipt://FA-320']
