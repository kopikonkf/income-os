from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

class MasterIngestionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_name(dst.name+f'.tmp-{os.getpid()}')
    try:
        shutil.copyfile(src,tmp)
        os.replace(tmp,dst)
    finally:
        if tmp.exists(): tmp.unlink()


def stage_master(*,source_path:str|Path, staging_root:str|Path, attempt_id:str, semantic_asset_id:str, blueprint_id:str, expected_sha256:str|None=None) -> dict[str,Any]:
    src=Path(source_path).resolve(); root=Path(staging_root).resolve()
    if not src.is_file(): raise MasterIngestionError('SOURCE_NOT_FOUND',str(src))
    if not attempt_id or not semantic_asset_id or not blueprint_id: raise MasterIngestionError('INGESTION_IDENTITY_INCOMPLETE','attempt/semantic/blueprint required')
    actual=sha256_file(src)
    if expected_sha256 is not None and actual!=expected_sha256: raise MasterIngestionError('SOURCE_HASH_MISMATCH',actual)
    ext=src.suffix.lower() or '.bin'; blob=root/'blobs'/'sha256'/actual[:2]/f'{actual}{ext}'
    reused=blob.exists()
    if reused:
        if sha256_file(blob)!=actual: raise MasterIngestionError('CONTENT_ADDRESS_COLLISION',str(blob))
    else:
        _atomic_copy(src,blob)
        if sha256_file(blob)!=actual: raise MasterIngestionError('STAGED_BLOB_HASH_MISMATCH',str(blob))
    receipts=root/'attempt-receipts'; receipts.mkdir(parents=True,exist_ok=True); receipt_path=receipts/f'{attempt_id}.json'
    receipt={
      'schema':'die.factory-asset.master-ingestion-attempt.v1','attempt_id':attempt_id,'semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,
      'source_path':str(src),'source_sha256':actual,'source_bytes':src.stat().st_size,'staged_blob_path':str(blob),'blob_reused':reused,
      'ingestion_state':'STAGED_NOT_CANONICAL','canonical_truth':False,'state_manager_commit_required':True,
      'state_manager_proposal':{'schema':'die.factory-asset.master-ingestion-proposal.v1','action':'FACTORY_MASTER_INGEST','semantic_asset_id':semantic_asset_id,'blueprint_id':blueprint_id,'master_sha256':actual,'staged_blob_path':str(blob),'attempt_receipt_path':str(receipt_path),'physical_writer_required':'DIE_STATE_MANAGER'}
    }
    payload=json.dumps(receipt,sort_keys=True,indent=2)+'\n'
    if receipt_path.exists():
        existing=json.loads(receipt_path.read_text(encoding='utf-8'))
        if existing!=receipt: raise MasterIngestionError('ATTEMPT_ID_CONFLICT',attempt_id)
    else: receipt_path.write_text(payload,encoding='utf-8',newline='\n')
    return receipt


def staged_index(staging_root:str|Path) -> dict[str,Any]:
    root=Path(staging_root).resolve(); receipts=[]
    for p in sorted((root/'attempt-receipts').glob('*.json')) if (root/'attempt-receipts').is_dir() else []:
        receipts.append(json.loads(p.read_text(encoding='utf-8')))
    blobs=sorted(str(p) for p in (root/'blobs').rglob('*') if p.is_file()) if (root/'blobs').is_dir() else []
    return {'schema':'die.factory-asset.master-ingestion-staging-index.v1','ingestion_state':'STAGED_NOT_CANONICAL','canonical_truth':False,'attempt_receipts':receipts,'unique_blob_paths':blobs,'attempt_count':len(receipts),'unique_blob_count':len(blobs)}

def _publish_immutable_bytes(path: Path, payload: bytes, *, conflict_code: str) -> bool:
    """Publish once without replacing a concurrent writer; return whether reused.

    Read-only mode is an application guard, not a privileged-user WORM guarantee.
    Every reuse compares the complete pinned payload and fails closed on tampering.
    """
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.intake-', dir=path.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        tmp.chmod(0o444)
        try:
            os.link(tmp, path)
            reused = False
        except FileExistsError:
            reused = True
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise MasterIngestionError(conflict_code, str(path))
        return reused
    finally:
        if tmp.exists():
            # Windows requires writable mode before removing a read-only temp link.
            if os.name == 'nt':
                tmp.chmod(0o600)
            tmp.unlink()


def stage_master_snapshot(*, source_bytes: bytes, source_path: str | Path,
                          staging_root: str | Path, attempt_id: str,
                          semantic_asset_id: str, blueprint_id: str,
                          expected_sha256: str,
                          provider_original: dict[str, Any]) -> dict[str, Any]:
    """Stage already validated original bytes, without a second source-file read.

    Provider intake uses this path; generic stage_master remains backward compatible.
    Extensionless CAS keys deduplicate .jpg/.jpeg and .tif/.tiff aliases without
    renaming the source or claiming a different encoding. No canonical state writes.
    """
    import re

    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', attempt_id or ''):
        raise MasterIngestionError('INGESTION_IDENTITY_INCOMPLETE', 'unsafe attempt_id')
    if not semantic_asset_id or not blueprint_id:
        raise MasterIngestionError('INGESTION_IDENTITY_INCOMPLETE', 'semantic/blueprint required')
    actual = hashlib.sha256(source_bytes).hexdigest()
    if actual != expected_sha256:
        raise MasterIngestionError('SOURCE_HASH_MISMATCH', actual)
    root = Path(staging_root).resolve()
    blob = root / 'blobs' / 'sha256' / actual[:2] / actual
    receipt_path = root / 'attempt-receipts' / f'{attempt_id}.json'
    for path in (blob.parent, receipt_path.parent):
        for parent in (path, *path.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise MasterIngestionError('STAGING_PATH_UNSAFE', str(parent))
    receipt = {
        'schema': 'die.factory-asset.master-ingestion-attempt.v1',
        'attempt_id': attempt_id, 'semantic_asset_id': semantic_asset_id,
        'blueprint_id': blueprint_id, 'source_path': str(Path(source_path).resolve()),
        'source_sha256': actual, 'source_bytes': len(source_bytes),
        'staged_blob_path': str(blob), 'blob_reused': False,
        'provider_original': provider_original,
        'ingestion_state': 'STAGED_NOT_CANONICAL', 'canonical_truth': False,
        'state_manager_commit_required': True,
        'state_manager_proposal': {
            'schema': 'die.factory-asset.master-ingestion-proposal.v1',
            'action': 'FACTORY_MASTER_INGEST', 'semantic_asset_id': semantic_asset_id,
            'blueprint_id': blueprint_id, 'master_sha256': actual,
            'staged_blob_path': str(blob), 'attempt_receipt_path': str(receipt_path),
            'physical_writer_required': 'DIE_STATE_MANAGER',
        },
    }
    if receipt_path.exists() or receipt_path.is_symlink():
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise MasterIngestionError('ATTEMPT_ID_CONFLICT', attempt_id) from exc
        if not isinstance(existing, dict) or not isinstance(existing.get('blob_reused'), bool):
            raise MasterIngestionError('ATTEMPT_ID_CONFLICT', attempt_id)
        candidate = dict(receipt, blob_reused=existing.get('blob_reused'))
        if receipt_path.is_symlink() or candidate != existing:
            raise MasterIngestionError('ATTEMPT_ID_CONFLICT', attempt_id)
        # A missing/corrupt pinned blob is evidence corruption, never silently repaired.
        if blob.is_symlink() or not blob.is_file() or blob.read_bytes() != source_bytes:
            raise MasterIngestionError('CONTENT_ADDRESS_COLLISION', str(blob))
        return existing
    receipt['blob_reused'] = _publish_immutable_bytes(
        blob, source_bytes, conflict_code='CONTENT_ADDRESS_COLLISION')
    payload = (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('utf-8')
    try:
        _publish_immutable_bytes(receipt_path, payload, conflict_code='ATTEMPT_ID_CONFLICT')
    except MasterIngestionError:
        # A concurrent identical attempt can observe a different reuse flag.
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise MasterIngestionError('ATTEMPT_ID_CONFLICT', attempt_id) from exc
        if not isinstance(existing, dict) or not isinstance(existing.get('blob_reused'), bool):
            raise MasterIngestionError('ATTEMPT_ID_CONFLICT', attempt_id)
        if receipt_path.is_symlink() or dict(receipt, blob_reused=existing.get('blob_reused')) != existing:
            raise
        return existing
    return receipt
