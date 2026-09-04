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