from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

HERE = Path(__file__).resolve().parents[1]
SCHEMA_PATH = HERE / 'contracts' / 'h01-semantic-family.v1.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


class SemanticFamilyError(ValueError):
    pass


def canonical_family_id(document: dict[str, Any]) -> str:
    subject_ids = sorted(m['canonical_subject_ref']['subject_id'] for m in document['members'])
    payload = {
        'family_version': document['family_version'],
        'family_class': document['family_class'],
        'semantic_key': document['semantic_identity']['semantic_key'],
        'canonical_subject_ids': subject_ids,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()[:24].upper()
    return f"FAM-V1-{document['family_class']}-{digest}"


def validate_semantic_family(document: dict[str, Any]) -> dict[str, Any]:
    try:
        jsonschema.Draft202012Validator(SCHEMA).validate(document)
    except jsonschema.ValidationError as exc:
        raise SemanticFamilyError(f'E_SCHEMA:{exc.message}') from exc

    subject_ids = [m['canonical_subject_ref']['subject_id'] for m in document['members']]
    if subject_ids != sorted(subject_ids):
        raise SemanticFamilyError('E_MEMBER_ORDER:canonical subject IDs must be ascending')
    if len(subject_ids) != len(set(subject_ids)):
        raise SemanticFamilyError('E_DUPLICATE_CANONICAL_SUBJECT')
    for member in document['members']:
        if member['member_id'] != member['canonical_subject_ref']['subject_id']:
            raise SemanticFamilyError('E_MEMBER_ID_DRIFT:member_id must equal canonical Object Atlas subject_id')

    evidence_ids = [x['evidence_id'] for x in document['source']['evidence']]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise SemanticFamilyError('E_DUPLICATE_SOURCE_EVIDENCE')

    expected = canonical_family_id(document)
    if document['family_id'] != expected:
        raise SemanticFamilyError(f'E_FAMILY_ID_MISMATCH:expected={expected}')
    return document
