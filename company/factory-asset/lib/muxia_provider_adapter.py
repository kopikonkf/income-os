"""FA-113: adapt MUXIA's exported ChatGPT image into Factory provider/master contracts.

This module deliberately owns no browser, CDP endpoint, profile, credential, provider
session, or MUXIA private-artifact access. MUXIA remains the sole browser/session owner.
Factory consumes only the verified export inside the assigned DIE workspace.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_provider_original = _load('fa113_provider_original', 'provider_original.py')
_derivative = _load('fa113_derivative_planner', 'derivative_delivery_planner.py')

PROVIDER_ID = 'chatgpt'
MUXIA_PROFILE = 'chatgpt-linux-a'
FACTORY_SCHEMA = 'die.factory-asset.image-provider.v1'
QUEUE_SCHEMA = 'die.muxia-dispatch-result.v1'
RUN_SCHEMA = 'die.muxia.chatgpt-image-run.v1'


class MuxiaProviderAdapterError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def capability() -> dict[str, Any]:
    """Expose the bounded capability evidenced by the current MUXIA Linux route."""
    return {
        'schema': FACTORY_SCHEMA,
        'kind': 'CAPABILITY',
        'provider_id': PROVIDER_ID,
        'contract_version': '1.0.0',
        'transport_classes': ['BROWSER_CDP'],
        'image_generation': True,
        'output_formats': ['PNG'],
        'supports_transparency': 'UNKNOWN',
        'supports_requested_dimensions': 'UNKNOWN',
        'capacity_state': 'UNKNOWN',
    }


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise MuxiaProviderAdapterError(code, message)


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def adapt_muxia_success(*, queue_result: dict[str, Any], workspace_root: str | Path,
                        staging_root: str | Path, attempt_id: str,
                        semantic_asset_id: str, blueprint_id: str) -> dict[str, Any]:
    """Convert one verified MUXIA queue success into Factory provider/master evidence.

    The private MUXIA artifact path may be present in the upstream receipt for lineage,
    but this function never dereferences it. The only readable source is the verified
    export under <workspace>/provider/.
    """
    _require(isinstance(queue_result, dict), 'MUXIA_RESULT_INVALID', 'object required')
    _require(queue_result.get('schema') == QUEUE_SCHEMA,
             'MUXIA_RESULT_SCHEMA_INVALID', str(queue_result.get('schema')))
    _require(queue_result.get('status') == 'SUCCEEDED',
             'MUXIA_RESULT_NOT_SUCCEEDED', str(queue_result.get('status')))
    task_id = str(queue_result.get('task_id', ''))
    _require(len(task_id) >= 3, 'MUXIA_TASK_ID_INVALID', task_id)

    dispatch = queue_result.get('dispatch')
    _require(isinstance(dispatch, dict), 'MUXIA_DISPATCH_MISSING', task_id)
    _require(dispatch.get('schema') == RUN_SCHEMA,
             'MUXIA_DISPATCH_SCHEMA_INVALID', str(dispatch.get('schema')))
    _require(dispatch.get('status') == 'SUCCEEDED',
             'MUXIA_DISPATCH_NOT_SUCCEEDED', str(dispatch.get('status')))
    _require(dispatch.get('profile_id') == MUXIA_PROFILE,
             'MUXIA_PROFILE_UNSUPPORTED', str(dispatch.get('profile_id')))
    _require(dispatch.get('prompt_submitted_by_automation') is True and
             dispatch.get('output_extracted_by_automation') is True,
             'MUXIA_AUTOMATION_INCOMPLETE', task_id)
    _require(dispatch.get('credential_values_read') is False and
             dispatch.get('cookies_or_tokens_read') is False,
             'MUXIA_SECRET_BOUNDARY_VIOLATION', task_id)
    _require(dispatch.get('submission_authorized') is False and
             dispatch.get('publication_authorized') is False,
             'MUXIA_AUTHORITY_BOUNDARY_VIOLATION', task_id)
    _require(dispatch.get('private_artifact_access_by_hermes') is False,
             'MUXIA_PRIVATE_BOUNDARY_VIOLATION', task_id)

    sha256 = str(dispatch.get('sha256', ''))
    export_sha = str(dispatch.get('export_artifact_sha256', ''))
    _require(len(sha256) == 64 and sha256 == export_sha,
             'MUXIA_EXPORT_HASH_UNVERIFIED', f'{sha256}:{export_sha}')

    workspace = Path(workspace_root).resolve()
    _require(workspace.name == task_id, 'MUXIA_WORKSPACE_TASK_MISMATCH', str(workspace))
    provider_dir = (workspace / 'provider').resolve()
    export_path = Path(str(dispatch.get('export_artifact_path', ''))).resolve()
    _require(_inside(provider_dir, export_path) and export_path.parent == provider_dir,
             'MUXIA_EXPORT_PATH_UNSAFE', str(export_path))
    receipt_path = Path(str(dispatch.get('export_receipt_path', ''))).resolve()
    _require(_inside(provider_dir, receipt_path) and receipt_path.parent == provider_dir,
             'MUXIA_RECEIPT_PATH_UNSAFE', str(receipt_path))

    declared_mime = str(dispatch.get('content_type', '')).split(';', 1)[0].strip().lower()
    _require(declared_mime in {'image/png', 'image/jpeg', 'image/webp'},
             'MUXIA_CONTENT_TYPE_UNSUPPORTED', declared_mime)

    intake = _provider_original.intake_provider_original(
        source_path=export_path,
        staging_root=staging_root,
        attempt_id=attempt_id,
        semantic_asset_id=semantic_asset_id,
        blueprint_id=blueprint_id,
        provider_id=PROVIDER_ID,
        expected_sha256=sha256,
        declared_mime_type=declared_mime,
    )
    original = intake['provider_original']
    media = original['media']
    _require(original.get('declared_mime_matches') is True,
             'MUXIA_CONTENT_TYPE_MISMATCH', declared_mime)

    observed = dispatch.get('generated_image_observed') or {}
    _require(observed.get('width') == media['width_px'] and
             observed.get('height') == media['height_px'],
             'MUXIA_DIMENSION_DRIFT', f"{observed.get('width')}x{observed.get('height')} != {media['width_px']}x{media['height_px']}")
    _require(dispatch.get('bytes') == media['bytes'],
             'MUXIA_BYTE_COUNT_DRIFT', f"{dispatch.get('bytes')} != {media['bytes']}")

    provider_result = {
        'schema': FACTORY_SCHEMA,
        'kind': 'GENERATE_RESULT',
        'job_id': task_id,
        'provider_id': PROVIDER_ID,
        'transport_class': 'BROWSER_CDP',
        'result': 'PASS',
        'operator_actions_after_dispatch': 0,
        'artifact': {
            'sha256': original['sha256'],
            'bytes': media['bytes'],
            'mime': media['mime_type'],
            'width_px': media['width_px'],
            'height_px': media['height_px'],
            'decode_reopen': bool(media['decode_verified']),
            'provider_original_bytes': True,
            'durable_local_save': True,
        },
    }
    master_facts = _derivative.provider_master_facts(
        provider_original=original,
        semantic_asset_id=semantic_asset_id,
        blueprint_id=blueprint_id,
    )
    return {
        'schema': 'die.factory-asset.muxia-provider-adaptation.v1',
        'provider_result': provider_result,
        'intake_receipt': intake,
        'master_facts': master_facts,
        'ownership_boundary': {
            'browser_owner': 'MUXIA',
            'profile_owner': 'MUXIA',
            'session_owner': 'MUXIA',
            'factory_reads_private_muxia_artifact': False,
            'factory_reads_exported_workspace_artifact_only': True,
            'provider_id': PROVIDER_ID,
            'muxia_profile_id': MUXIA_PROFILE,
        },
    }
