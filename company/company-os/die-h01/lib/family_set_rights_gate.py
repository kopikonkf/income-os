from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

HERE = Path(__file__).resolve().parents[1]
SCHEMA_PATH = HERE / 'contracts' / 'h01-family-set-rights-candidate.v1.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
FAMILY_SCHEMA_PATH = HERE / 'contracts' / 'h01-semantic-family.v1.schema.json'

RIGHTS_RANK = {
    'GENERIC_UNRESTRICTED': 0,
    'REVIEW_REQUIRED': 1,
    'UNKNOWN': 2,
    'BRAND_RESTRICTED': 3,
}


class FamilySetRightsGateError(ValueError):
    pass


def _aggregate_rights(classes: list[str]) -> str:
    if not classes:
        raise FamilySetRightsGateError('E_CONSTITUENTS_REQUIRED')
    return max(classes, key=lambda value: RIGHTS_RANK[value])


def validate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        jsonschema.Draft202012Validator(SCHEMA).validate(candidate)
    except jsonschema.ValidationError as exc:
        raise FamilySetRightsGateError(f'E_SCHEMA:{exc.message}') from exc

    refs = [row['ref_id'] for row in candidate['constituents']]
    if len(refs) != len(set(refs)):
        raise FamilySetRightsGateError('E_DUPLICATE_CONSTITUENT')

    evidence_ids = [row['evidence_id'] for row in candidate['evidence']]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise FamilySetRightsGateError('E_DUPLICATE_EVIDENCE')
    evidence_set = set(evidence_ids)
    missing = sorted({ref for row in candidate['constituents'] for ref in row['evidence_refs']} - evidence_set)
    if missing:
        raise FamilySetRightsGateError('E_EVIDENCE_REF_UNKNOWN:' + ','.join(missing))

    aggregate = _aggregate_rights([row['rights_class'] for row in candidate['constituents']])
    if aggregate == 'BRAND_RESTRICTED' and not any(row['kind'] == 'RIGHTS_EVIDENCE' for row in candidate['evidence']):
        raise FamilySetRightsGateError('E_BRAND_RESTRICTION_EVIDENCE_REQUIRED')
    if candidate['declared_rights_class'] != aggregate:
        raise FamilySetRightsGateError(
            f"E_RIGHTS_CLASS_DRIFT:declared={candidate['declared_rights_class']}:aggregate={aggregate}"
        )
    return candidate


def candidate_from_semantic_family(family: dict[str, Any]) -> dict[str, Any]:
    # Import by path so H01 remains self-contained without package-install assumptions.
    import importlib.util
    spec = importlib.util.spec_from_file_location('h01_semantic_family_v1', HERE / 'lib' / 'semantic_family_v1.py')
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.validate_semantic_family(family)

    evidence = [dict(row) for row in family['source']['evidence']]
    evidence_ids = [row['evidence_id'] for row in evidence]
    rights_class = family['rights_class']
    candidate = {
        'schema': 'die.h01.family-set-rights-candidate.v1',
        'schema_version': '1.0.0',
        'candidate_kind': 'SEMANTIC_FAMILY',
        'candidate_id': family['family_id'],
        'declared_rights_class': rights_class,
        'constituents': [
            {
                'ref_id': member['canonical_subject_ref']['subject_id'],
                'ref_kind': 'CANONICAL_SEMANTIC_MEMBER',
                'rights_class': rights_class,
                'evidence_refs': evidence_ids,
            }
            for member in family['members']
        ],
        'evidence': evidence,
        'requested_route': 'NORMAL_STOCK_PRODUCTION',
    }
    return validate_candidate(candidate)


def evaluate_family_set_rights(candidate: dict[str, Any]) -> dict[str, Any]:
    validate_candidate(candidate)
    rights_class = candidate['declared_rights_class']
    if rights_class == 'BRAND_RESTRICTED':
        decision = 'BLOCK_NORMAL_STOCK'
        next_route = 'RESTRICTED_RIGHTS_REVIEW'
        reason = 'BRAND_RESTRICTED candidates remain discoverable but are barred from normal stock production routing.'
    elif rights_class in {'REVIEW_REQUIRED', 'UNKNOWN'}:
        decision = 'REVIEW_REQUIRED'
        next_route = 'RIGHTS_REVIEW_HOLD'
        reason = 'Rights evidence is not clear enough for normal stock candidate routing.'
    else:
        decision = 'PASS_TO_NEXT_GATE'
        next_route = 'NORMAL_STOCK_CANDIDATE'
        reason = 'All declared constituent rights are GENERIC_UNRESTRICTED with auditable evidence.'

    return {
        'schema': 'die.h01.family-set-rights-gate-decision.v1',
        'candidate_kind': candidate['candidate_kind'],
        'candidate_id': candidate['candidate_id'],
        'rights_class': rights_class,
        'decision': decision,
        'next_route': next_route,
        'reason': reason,
        'discovery_preserved': True,
        'normal_stock_route_allowed': decision == 'PASS_TO_NEXT_GATE',
        'legal_clearance_claimed': False,
        'authority': {
            'production_authorized': False,
            'submission_authorized': False,
            'publication_authorized': False,
            'rights_gate_bypass_allowed': False,
        },
        'evidence_ids': [row['evidence_id'] for row in candidate['evidence']],
    }
