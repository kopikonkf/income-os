from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from marketplace_delivery_adapter import build_all_marketplace_packages
from submission_ready_projection import project_submission_ready
from marketplace_transport_contract import (
    DuplicateSubmissionError,
    LocalTransportContract,
    ReceiptStore,
)

HERE = Path(__file__).resolve()
H01_ROOT = HERE.parents[1]
TRANSPORT_FIXTURE = H01_ROOT / 'fixtures' / 'h01-136' / 'submission-ready-entry.synthetic.json'
LIVE_SUBMISSION_READY = Path('/var/lib/die/h01/submission-ready')


class PreflightError(RuntimeError):
    pass


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return fallback


def _workspace_hashes(workspace: Path) -> dict[str, str]:
    rels = [
        'metadata.json',
        'rights-signal.json',
        'postproduction/optimized-master.svg',
        'postproduction/canonical-master.svg',
        'postproduction/master.eps',
        'postproduction/preview.jpg',
    ]
    out: dict[str, str] = {}
    for rel in rels:
        path = workspace / rel
        if path.is_file():
            out[rel] = _sha_file(path)
    return out


def _clean_managed(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def _live_submission_ready_state(root: Path) -> dict[str, Any]:
    index = _read_json(root / 'submission-ready-index.json', {}) if root.is_dir() else {}
    return {
        'root': str(root),
        'root_exists': root.is_dir(),
        'eligible_count': int(index.get('eligible_count') or 0),
        'entry_count': len(index.get('entries') or []),
        'external_action': index.get('external_action', 'NONE'),
        'index_sha256': _sha_file(root / 'submission-ready-index.json') if (root / 'submission-ready-index.json').is_file() else None,
    }


def _transport_idempotency_proof(root: Path, prepared_at: str) -> dict[str, Any]:
    source = _read_json(TRANSPORT_FIXTURE)
    if not isinstance(source, dict):
        raise PreflightError('H01-136 synthetic submission-ready fixture unavailable')
    store_root = root / 'transport-receipts'
    contract = LocalTransportContract(ReceiptStore(store_root))
    first = contract.prepare(source, prepared_at=prepared_at)
    replay = contract.prepare(source, prepared_at=prepared_at)
    receipt_files = sorted(store_root.glob('H01-136-*.json'))

    changed = json.loads(json.dumps(source))
    changed['files'][0]['sha256'] = 'd' * 64
    duplicate_conflict_blocked = False
    try:
        contract.prepare(changed, prepared_at=prepared_at)
    except DuplicateSubmissionError:
        duplicate_conflict_blocked = True

    authority = first.get('authority') or {}
    actions = first.get('actions') or {}
    return {
        'fixture': 'company/company-os/die-h01/fixtures/h01-136/submission-ready-entry.synthetic.json',
        'receipt_id': first.get('receipt_id'),
        'idempotency_key': first.get('idempotency_key'),
        'duplicate_scope_key': first.get('duplicate_scope_key'),
        'exact_replay_same_receipt': first == replay,
        'durable_receipt_count': len(receipt_files),
        'duplicate_scope_conflict_blocked': duplicate_conflict_blocked,
        'authority_gate': authority.get('gate'),
        'founder_authorized': authority.get('founder_authorized'),
        'external_action_performed': authority.get('external_action_performed'),
        'credential_accessed': authority.get('credential_accessed'),
        'actions': actions,
    }


def run_preflight(
    workspace: Path,
    output_root: Path,
    *,
    founder_qc: str = 'NOT_RECORDED',
    observed_at: str,
    live_submission_ready_root: Path = LIVE_SUBMISSION_READY,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    if not (workspace / 'metadata.json').is_file() or not (workspace / 'postproduction').is_dir():
        raise PreflightError(f'workspace is not an H01 postproduction workspace: {workspace}')

    output_root = output_root.resolve()
    _clean_managed(output_root)
    package_root = output_root / 'delivery'
    projection_root = output_root / 'submission-ready-projection'
    source_before = _workspace_hashes(workspace)

    packages = build_all_marketplace_packages(
        workspace,
        package_root,
        founder_qc=founder_qc,
    )
    source_after_packaging = _workspace_hashes(workspace)
    projection = project_submission_ready(package_root, projection_root)
    source_after_projection = _workspace_hashes(workspace)

    diagnostics: dict[str, Any] = {}
    for marketplace, manifest in sorted(packages.items()):
        compatibility = manifest.get('compatibility') or {}
        rights = manifest.get('rights_signal') or {}
        diagnostics[marketplace] = {
            'compatibility': compatibility.get('status'),
            'compatibility_blockers': compatibility.get('blockers') or [],
            'rights': rights.get('result'),
            'founder_qc': manifest.get('founder_qc'),
            'submission_eligible': bool(manifest.get('submission_eligible')),
            'manifest_path': manifest.get('manifest_path'),
            'manifest_sha256': manifest.get('manifest_file_sha256') or manifest.get('manifest_sha256'),
            'actions': {
                'login': manifest.get('login_action'),
                'upload': manifest.get('upload_action'),
                'submission': manifest.get('submission_action'),
                'publication': manifest.get('publication_action'),
                'spend': manifest.get('spend_action'),
            },
        }

    transport = _transport_idempotency_proof(output_root, observed_at)
    live_state = _live_submission_ready_state(live_submission_ready_root)
    isolated_eligible = int(projection.get('eligible_count') or 0)
    handoff_state = 'READY_FOR_FOUNDER' if isolated_eligible > 0 else 'WAITING_ELIGIBILITY'

    actions_none = all(
        value in (None, 'NONE')
        for row in diagnostics.values()
        for value in row['actions'].values()
    )
    source_immutable = source_before == source_after_packaging == source_after_projection
    transport_pass = (
        transport['exact_replay_same_receipt']
        and transport['durable_receipt_count'] == 1
        and transport['duplicate_scope_conflict_blocked']
        and transport['external_action_performed'] is False
        and transport['credential_accessed'] is False
        and all(v == 'NONE' for v in transport['actions'].values())
    )

    status = 'PASS' if source_immutable and actions_none and transport_pass else 'FAIL'
    receipt = {
        'schema': 'die.h01.h01-109a.marketplace-real-upload-preflight.v1',
        'task_id': 'H01-109A',
        'status': status,
        'observed_at': observed_at,
        'workspace': str(workspace),
        'source_immutable': source_immutable,
        'source_hashes_before': source_before,
        'source_hashes_after': source_after_projection,
        'marketplace_package_count': len(diagnostics),
        'marketplaces': diagnostics,
        'isolated_submission_ready': {
            'eligible_count': isolated_eligible,
            'skipped_count': int(projection.get('skipped_count') or 0),
            'skipped': projection.get('skipped') or [],
            'external_action': projection.get('external_action'),
            'index_file_sha256': projection.get('index_file_sha256'),
        },
        'live_submission_ready': live_state,
        'transport_idempotency': transport,
        'founder_handoff': {
            'state': handoff_state,
            'real_upload_task': 'H01-109B',
            'real_upload_authority': 'FOUNDER_REQUIRED',
            'login_performed': False,
            'upload_performed': False,
            'submission_performed': False,
            'publication_performed': False,
            'spend_performed': False,
        },
        'acceptance_note': (
            'Zero eligible submission-ready assets is an honest technical-preflight result and does not fail H01-109A.'
            if isolated_eligible == 0 else
            'At least one isolated eligible package exists; Founder may proceed only through H01-109B.'
        ),
    }
    _write_json(output_root / 'H01-109A.preflight.receipt.json', receipt)
    if status != 'PASS':
        raise PreflightError('preflight invariant failed')
    return receipt


def main() -> None:
    ap = argparse.ArgumentParser(description='H01-109A local-only marketplace real-upload technical preflight')
    ap.add_argument('--workspace', required=True)
    ap.add_argument('--output-root', required=True)
    ap.add_argument('--observed-at', required=True)
    ap.add_argument('--founder-qc', default='NOT_RECORDED')
    ap.add_argument('--live-submission-ready-root', default=str(LIVE_SUBMISSION_READY))
    args = ap.parse_args()
    receipt = run_preflight(
        Path(args.workspace),
        Path(args.output_root),
        founder_qc=args.founder_qc,
        observed_at=args.observed_at,
        live_submission_ready_root=Path(args.live_submission_ready_root),
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
