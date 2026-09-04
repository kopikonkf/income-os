"""FA-129 structural and referential validation; no generation or dispatch."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'schemas/asset-expression-plan.schema.json'


class AssetExpressionPlanError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f'{code}: {message}')


def _normalized(value: str) -> str:
    return ' '.join(value.split()).casefold()


def validate_asset_expression_plan(plan: dict[str, Any]) -> None:
    """Validate a plan without mutation, network access or evidence-truth claims.

    JSON Schema handles shape, mode/producer compatibility and cardinality.
    These additional checks pin evidence to each commercial selection, enforce
    unique identities, and reject repeated semantics disguised as new IDs/routes.
    Source authenticity, freshness and motion eligibility are downstream gates.
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    first = next(jsonschema.Draft202012Validator(schema).iter_errors(plan), None)
    if first is not None:
        path = '.'.join(str(part) for part in first.absolute_path) or '$'
        raise AssetExpressionPlanError('PLAN_SCHEMA_INVALID', f'{path}: {first.message}')

    evidence = {}
    for item in plan['evidence']:
        if item['evidence_id'] in evidence:
            raise AssetExpressionPlanError('DUPLICATE_EVIDENCE_ID', item['evidence_id'])
        evidence[item['evidence_id']] = item

    identities: set[str] = set()
    semantic_keys: set[tuple[str, ...]] = set()
    for expression in plan['expressions']:
        identity = expression['semantic_asset_id']
        if identity in identities:
            raise AssetExpressionPlanError('DUPLICATE_SEMANTIC_ASSET_ID', identity)
        identities.add(identity)
        # A different filename, marketplace route or producer never creates a
        # second commercial expression. Semantic near-duplicate review remains
        # necessary for paraphrases that string normalization cannot detect.
        key = tuple(_normalized(expression[field]) for field in
                    ('buyer', 'commercial_use_case', 'product_expression', 'semantic_mode'))
        if key in semantic_keys:
            raise AssetExpressionPlanError('DUPLICATE_SEMANTIC_EXPRESSION', identity)
        semantic_keys.add(key)
        expected = {
            'seed_noun': plan['seed']['noun'],
            **{field: expression[field] for field in
               ('buyer', 'commercial_use_case', 'product_expression', 'semantic_mode')},
            'platform_id': expression['candidate_marketplace_route']['platform_id'],
        }
        for evidence_ref in expression['evidence_refs']:
            item = evidence.get(evidence_ref)
            if item is None:
                raise AssetExpressionPlanError('EVIDENCE_REFERENCE_UNKNOWN', evidence_ref)
            if item['support'] != expected:
                raise AssetExpressionPlanError('EVIDENCE_SCOPE_MISMATCH', f'{identity}: {evidence_ref}')
