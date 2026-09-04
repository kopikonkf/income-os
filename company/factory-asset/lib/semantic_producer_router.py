from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / 'company/factory-asset/registries/producer-dispatch.v1.json'


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

asset_expression = _load_module('fa133_asset_expression', ROOT / 'company/factory-asset/lib/asset_expression_plan.py')
blueprint_compiler = _load_module('fa133_blueprint_compiler', ROOT / 'company/factory-asset/lib/blueprint_compiler.py')


class ProducerDispatchError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))


def _find_expression(plan: dict[str, Any], semantic_asset_id: str) -> dict[str, Any]:
    matches = [x for x in plan.get('expressions', []) if x.get('semantic_asset_id') == semantic_asset_id]
    if len(matches) != 1:
        raise ProducerDispatchError('EXPRESSION_NOT_UNIQUE', semantic_asset_id)
    return matches[0]


def _expected_representation(mode: str) -> str:
    if mode in {'PHOTO', 'ISOLATED_OBJECT'}:
        return 'RASTER_PIXELS'
    if mode in {'ICON', 'OUTLINE', 'PATTERN'}:
        return 'VECTOR_PATHS'
    if mode == 'ANIMATION':
        return 'TIMED_FRAMES'
    raise ProducerDispatchError('SEMANTIC_MODE_UNKNOWN', mode)


def _route_entry(registry: dict[str, Any], producer_class: str, semantic_mode: str) -> dict[str, Any]:
    matches = [r for r in registry.get('routes', []) if r.get('producer_class') == producer_class and semantic_mode in r.get('semantic_modes', [])]
    if len(matches) != 1:
        raise ProducerDispatchError('ROUTE_NOT_UNIQUE', f'{producer_class}:{semantic_mode}')
    return matches[0]


def route_frozen_expression(*, plan: dict[str, Any], semantic_asset_id: str, blueprint: dict[str, Any], frozen_blueprint_sha256: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        asset_expression.validate_asset_expression_plan(plan)
    except Exception as exc:
        code = getattr(exc, 'code', 'UNKNOWN')
        raise ProducerDispatchError('EXPRESSION_PLAN_INVALID', f'{code}:{exc}') from exc
    if plan.get('decision') != 'SELECT':
        raise ProducerDispatchError('PLAN_NOT_SELECTABLE', str(plan.get('decision')))
    expression = _find_expression(plan, semantic_asset_id)

    actual_blueprint_sha = canonical_sha256(blueprint)
    if actual_blueprint_sha != frozen_blueprint_sha256:
        raise ProducerDispatchError('FROZEN_BLUEPRINT_HASH_MISMATCH', actual_blueprint_sha)

    if blueprint.get('semantic_identity', {}).get('semantic_asset_id') != semantic_asset_id:
        raise ProducerDispatchError('BLUEPRINT_SEMANTIC_ASSET_MISMATCH', blueprint['semantic_identity']['semantic_asset_id'])
    if blueprint['asset_type'] != expression['semantic_mode']:
        raise ProducerDispatchError('BLUEPRINT_MODE_MISMATCH', f"{blueprint['asset_type']}!={expression['semantic_mode']}")
    if blueprint.get('producer_class') != expression['producer_class']:
        raise ProducerDispatchError('BLUEPRINT_PRODUCER_MISMATCH', f"{blueprint.get('producer_class')}!={expression['producer_class']}")
    try:
        blueprint_compiler.validate_blueprint(blueprint)
    except Exception as exc:
        code = getattr(exc, 'code', 'UNKNOWN')
        raise ProducerDispatchError('BLUEPRINT_INVALID', f'{code}:{exc}') from exc
    expected_representation = _expected_representation(expression['semantic_mode'])
    if blueprint['native_representation'] != expected_representation:
        raise ProducerDispatchError('BLUEPRINT_REPRESENTATION_MISMATCH', blueprint['native_representation'])

    route = _route_entry(registry or load_registry(), expression['producer_class'], expression['semantic_mode'])
    if route.get('post_hoc_conversion_allowed') is not False or route.get('master_generation_mode') != 'DIRECT_FROM_BLUEPRINT':
        raise ProducerDispatchError('UNSAFE_ROUTE_POLICY', f"{expression['producer_class']}:{expression['semantic_mode']}")
    if route.get('engine_state') != 'ACCEPTED':
        raise ProducerDispatchError('PRODUCER_ENGINE_UNAVAILABLE', f"{route.get('dispatch_adapter')}:{route.get('engine_state')}")

    marketplace = expression['candidate_marketplace_route']['platform_id']
    if marketplace not in set(blueprint['policy']['marketplace_profiles']):
        raise ProducerDispatchError('MARKETPLACE_ROUTE_MISMATCH', marketplace)

    return {
        'schema': 'die.factory-asset.semantic-producer-dispatch.v1',
        'result': 'DISPATCH_READY',
        'plan_id': plan['plan_id'],
        'seed_id': plan['seed']['seed_id'],
        'seed_noun': plan['seed']['noun'],
        'semantic_asset_id': semantic_asset_id,
        'semantic_mode': expression['semantic_mode'],
        'producer_class': expression['producer_class'],
        'blueprint_id': blueprint['blueprint_id'],
        'frozen_blueprint_sha256': actual_blueprint_sha,
        'native_representation': blueprint['native_representation'],
        'master_spec': dict(blueprint['master_spec']),
        'marketplace_route': marketplace,
        'route_kind': route['route_kind'],
        'dispatch_adapter': route['dispatch_adapter'],
        'engine_state': route['engine_state'],
        'evidence_refs': list(route['evidence_refs']),
        'master_generation_mode': 'DIRECT_FROM_BLUEPRINT',
        'post_hoc_conversion_allowed': False,
        'derivative_planning_stage': 'AFTER_VALIDATED_MASTER',
        'provider_selection_delegated': route['route_kind'] == 'PROVIDER_ROUTER',
        'submission_authority': 'FOUNDER_CONTROLLED',
        'dispatch_key': canonical_sha256({
            'plan_id': plan['plan_id'],
            'semantic_asset_id': semantic_asset_id,
            'blueprint_sha256': actual_blueprint_sha,
            'dispatch_adapter': route['dispatch_adapter'],
            'marketplace_route': marketplace,
        }),
    }