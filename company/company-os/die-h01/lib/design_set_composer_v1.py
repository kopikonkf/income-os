from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema

HERE = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((HERE / 'contracts' / 'h01-design-set.v1.schema.json').read_text())
SET_VERSION = '1.0.0'
MAX_MEMBERS = 24

class DesignSetError(ValueError):
    pass

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

FAMILY = _load('h01_semantic_family_for_set', HERE / 'lib' / 'semantic_family_v1.py')
RIGHTS = _load('h01_family_set_rights_for_set', HERE / 'lib' / 'family_set_rights_gate.py')

def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def canonical_set_id(document: dict[str, Any]) -> str:
    payload = {
        'set_version': SET_VERSION,
        'source_family_id': document['source_family']['family_id'],
        'semantic_key': document['source_family']['semantic_key'],
        'member_ids': [m['canonical_subject_ref']['subject_id'] for m in document['members']],
        'visual_profile': document['coherence']['visual_profile'],
    }
    return 'DSET-V1-' + hashlib.sha256(_canon(payload)).hexdigest()[:24].upper()

def rights_candidate_from_design_set(document: dict[str, Any], family: dict[str, Any]) -> dict[str, Any]:
    evidence = [dict(x) for x in family['source']['evidence']]
    evidence_ids = [x['evidence_id'] for x in evidence]
    candidate = {
        'schema': 'die.h01.family-set-rights-candidate.v1',
        'schema_version': '1.0.0',
        'candidate_kind': 'DESIGN_SET',
        'candidate_id': document['set_id'],
        'declared_rights_class': family['rights_class'],
        'constituents': [
            {
                'ref_id': m['member_id'],
                'ref_kind': 'CANONICAL_SEMANTIC_MEMBER',
                'rights_class': family['rights_class'],
                'evidence_refs': evidence_ids,
            }
            for m in document['members']
        ],
        'evidence': evidence,
        'requested_route': 'NORMAL_STOCK_PRODUCTION',
    }
    return RIGHTS.validate_candidate(candidate)

def validate_design_set(document: dict[str, Any], family: dict[str, Any]) -> dict[str, Any]:
    FAMILY.validate_semantic_family(family)
    try:
        jsonschema.Draft202012Validator(SCHEMA).validate(document)
    except jsonschema.ValidationError as exc:
        raise DesignSetError(f'E_SCHEMA:{exc.message}') from exc
    if document['source_family']['family_id'] != family['family_id']:
        raise DesignSetError('E_SOURCE_FAMILY_ID_DRIFT')
    subject_ids = [m['canonical_subject_ref']['subject_id'] for m in document['members']]
    if subject_ids != sorted(subject_ids):
        raise DesignSetError('E_MEMBER_ORDER')
    if len(subject_ids) != len(set(subject_ids)):
        raise DesignSetError('E_DUPLICATE_MEMBER')
    family_ids = {m['canonical_subject_ref']['subject_id'] for m in family['members']}
    if not set(subject_ids).issubset(family_ids):
        raise DesignSetError('E_MEMBER_OUTSIDE_SOURCE_FAMILY')
    for member in document['members']:
        if member['member_id'] != member['canonical_subject_ref']['subject_id']:
            raise DesignSetError('E_MEMBER_ID_DRIFT')
        if member['identity_effect'] != 'NONE':
            raise DesignSetError('E_IDENTITY_EFFECT')
        expected = {'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1','composition':'ISOLATED_SINGLE_OBJECT','background_policy':'TRANSPARENT_OR_WHITE'}
        if member['blueprint'] != expected:
            raise DesignSetError('E_MEMBER_BLUEPRINT_DRIFT')
    expected_boundary = {'is_design_set':True,'is_derivative_bundle':False,'is_listing_package':False,'set_members_are_semantic_members':True,'derivatives_create_set_members':False}
    if document['boundary'] != expected_boundary:
        raise DesignSetError('E_BOUNDARY_DRIFT')
    if any(document['authority'].values()):
        raise DesignSetError('E_AUTHORITY_EXPANSION')
    if document['set_id'] != canonical_set_id(document):
        raise DesignSetError('E_SET_ID_MISMATCH')
    candidate = rights_candidate_from_design_set(document, family)
    decision = RIGHTS.evaluate_family_set_rights(candidate)
    for key in ('decision','next_route','normal_stock_route_allowed','legal_clearance_claimed'):
        if document['rights_gate'][key] != decision[key]:
            raise DesignSetError('E_RIGHTS_GATE_DRIFT')
    if document['rights_class'] != decision['rights_class']:
        raise DesignSetError('E_RIGHTS_CLASS_DRIFT')
    return document

def compose_design_set(family, max_members=12):
    FAMILY.validate_semantic_family(family)
    if not isinstance(max_members, int) or isinstance(max_members, bool) or not 2 <= max_members <= MAX_MEMBERS:
        raise DesignSetError('E_MAX_MEMBERS')
    selected = sorted(family['members'], key=lambda x: x['canonical_subject_ref']['subject_id'])[:max_members]
    if len(selected) < 2: raise DesignSetError('E_SET_TOO_SMALL')
    bp = {'media':'VECTOR','mode':'VECTOR_OBJECT','form':'SINGLE','preset':'CLEAN_STOCK_VECTOR_V1','composition':'ISOLATED_SINGLE_OBJECT','background_policy':'TRANSPARENT_OR_WHITE'}
    members = [{'member_id':x['member_id'],'canonical_subject_ref':dict(x['canonical_subject_ref']),'semantic_label':x['semantic_label'],'identity_effect':'NONE','blueprint':dict(bp)} for x in selected]
    doc = {'schema':'die.h01.design-set.v1','set_id':'','source_family':{'family_id':family['family_id'],'family_class':family['family_class'],'semantic_key':family['semantic_identity']['semantic_key']},'members':members}
    doc['coherence'] = {'basis':'SOURCE_SEMANTIC_FAMILY','visual_profile':'CLEAN_STOCK_VECTOR_V1','layout_policy':'ISOLATED_SINGLE_OBJECT_PER_MEMBER','style_consistency':'REQUIRED_WITHIN_SET','viewpoint_consistency':'REQUIRED_WITHIN_SET','palette_consistency':'REQUIRED_WITHIN_SET'}
    doc['rights_class'] = family['rights_class']; doc['rights_gate'] = {}
    doc['authority'] = {'production_authorized':False,'submission_authorized':False,'publication_authorized':False}
    doc['boundary'] = {'is_design_set':True,'is_derivative_bundle':False,'is_listing_package':False,'set_members_are_semantic_members':True,'derivatives_create_set_members':False}
    doc['set_id'] = canonical_set_id(doc)
    decision = RIGHTS.evaluate_family_set_rights(rights_candidate_from_design_set(doc, family))
    doc['rights_gate'] = {k: decision[k] for k in ('decision','next_route','normal_stock_route_allowed','legal_clearance_claimed')}
    return validate_design_set(doc, family)
