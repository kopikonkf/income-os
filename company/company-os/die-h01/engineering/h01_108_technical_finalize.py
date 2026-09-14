#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
H01 = HERE.parents[1]
ROOT = HERE.parents[4]
sys.path[:0] = [str(H01 / 'engineering'), str(ROOT / 'company/factory-asset/lib')]

from native_svg_pipeline import validate_and_normalize
from native_svg_request_contract import build_request, build_success_receipt
from svg_prompt_composer_v2 import sha256_value

now = lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
sha = lambda b: hashlib.sha256(b).hexdigest()


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', required=True)
    ns = ap.parse_args()
    w = Path(ns.workspace)
    f = w / 'final'

    created = load(w / 'artifact-created.receipt.json')
    if created.get('status') != 'ARTIFACT_CREATED':
        raise SystemExit('E_ARTIFACT_CREATED_REQUIRED')
    source = f / 'provider-original.svg'
    if not source.is_file():
        raise SystemExit('E_PROVIDER_ORIGINAL_MISSING')
    original = source.read_bytes()
    if sha(original) != created.get('provider_original_sha256'):
        raise SystemExit('E_PROVIDER_ORIGINAL_HASH_MISMATCH')
    if created.get('provider_original_path') and Path(created['provider_original_path']).resolve() != source.resolve():
        raise SystemExit('E_PROVIDER_ORIGINAL_PATH_MISMATCH')

    existing = load(w / 'generation-complete.receipt.json')
    if existing.get('status') == 'GENERATION_COMPLETE':
        validation = load(f / 'h01-103-validation.json')
        if validation.get('status') != 'PASS' or validation.get('input_sha256') != sha(original):
            raise SystemExit('E_GENERATION_REPLAY_LINEAGE_MISMATCH')
        print(json.dumps({'status': 'REPLAY_GENERATION_COMPLETE', 'workspace': str(w), 'generation': existing}, sort_keys=True))
        return 0

    bp = json.loads((w / 'blueprint.json').read_text())
    mi = json.loads((w / 'master-instruction.json').read_text())
    pp = json.loads((w / 'provider-prompt.json').read_text())
    item = json.loads((w / 'batch-item.json').read_text())
    bph = sha256_value(bp)
    provider = created['provider_id']
    job_id = created['job_id']
    profile_id = created['profile_id']
    udd_id = created['udd_id']
    completed = now()

    request = build_request(
        request_id=f'H01SVGREQ-{job_id}',
        queue_item_id=item['queue_item_id'],
        source_candidate_id=item['source_candidate_id'],
        semantic_asset_id=bp['semantic_asset_id'],
        provider_id=provider,
        provider_profile=f'{provider.upper()}_WEB_P001',
        blueprint_id=bp['blueprint_id'],
        blueprint_sha256=bph,
        master_instruction_sha256=mi['master_instruction_sha256'],
        provider_prompt=pp['prompt'],
        provider_prompt_sha256=pp['prompt_sha256'],
    )
    dump(f / 'native-svg-request.json', request)

    try:
        text = original.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise SystemExit(f'E_PROVIDER_ORIGINAL_NOT_UTF8:{exc}')
    norm = validate_and_normalize(text, repair_transport_geometry=True)
    (f / 'canonical.svg').write_text(norm['canonical_svg'])
    validation = {
        'schema': 'die.h01.h01-103.live-validation.v1',
        'task_id': 'H01-103',
        'status': 'PASS',
        'input_sha256': sha(original),
        'canonical_svg_sha256': norm['canonical_svg_sha256'],
        'geometry_count': norm['geometry_count'],
        'path_count': norm['path_count'],
        'shape_count': norm['shape_count'],
        'total_points': norm['total_points'],
        'render_ink_pixels_512': norm['render_ink_pixels_512'],
        'native_editable': norm['native_editable'],
        'conversion_from_raster': norm['conversion_from_raster'],
        'source_repairs': norm.get('source_repairs', {}),
    }
    if validation['native_editable'] is not True or validation['conversion_from_raster'] is not False:
        raise SystemExit('E_H01_103_NATIVE_EDITABLE_REQUIRED')
    dump(f / 'h01-103-validation.json', validation)

    acq = load(f / 'provider-output-acquisition.receipt.json')
    transport_normalization = acq.get('normalization')
    surface = acq.get('provider_surface') or {}
    raw = text
    if surface.get('path'):
        surface_path = Path(surface['path'])
        if surface_path.is_file():
            raw = surface_path.read_text()
    h104 = build_success_receipt(
        request=request,
        ingress='WEB_AI_ADAPTER',
        dispatch_commit_id=f'{job_id}-CDP',
        provider_status='COMPLETED',
        provider_response_text=raw,
        h01_103_canonical_svg_sha256=norm['canonical_svg_sha256'],
        finish_reason='PROVIDER_UI_TERMINAL',
        candidate_svg_text=text,
        transport_normalization=transport_normalization,
    )
    dump(f / 'h01-104-native-svg-receipt.json', h104)

    generation = {
        'schema': 'die.h01.generation-complete.v1',
        'task_id': 'H01-108',
        'status': 'GENERATION_COMPLETE',
        'job_id': job_id,
        'batch_position': item['batch_position'],
        'queue_item_id': item['queue_item_id'],
        'source_candidate_id': item['source_candidate_id'],
        'semantic_asset_id': bp['semantic_asset_id'],
        'noun': item['canonical_name'],
        'provider_id': provider,
        'profile_id': profile_id,
        'udd_id': udd_id,
        'provider_original_sha256': sha(original),
        'canonical_svg_sha256': norm['canonical_svg_sha256'],
        'h01_103_status': 'PASS',
        'native_editable': True,
        'conversion_from_raster': False,
        'generation_acceptance_boundary': 'H01_103_PASS_SEMANTIC_MASTER',
        'postproduction_state': 'PENDING',
        'completed_at': completed,
        'submission_authorized': False,
        'publication_authorized': False,
    }
    dump(w / 'generation-complete.receipt.json', generation)
    print(json.dumps(generation, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
