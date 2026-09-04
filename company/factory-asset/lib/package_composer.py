from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

class PackageComposerError(ValueError):
    def __init__(self,code:str,message:str):super().__init__(f'{code}: {message}');self.code=code

def sha256_file(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def compose_dry_run_package(*,package_dir:str|Path,semantic_asset_id:str,master_sha256:str,deliverables:list[dict[str,Any]],metadata_ref:str,rights_ref:str,compatibility_receipt_ref:str)->dict[str,Any]:
    if not semantic_asset_id or not master_sha256 or len(master_sha256)!=64:raise PackageComposerError('IDENTITY_INCOMPLETE','semantic/master hash')
    for name,val in [('metadata_ref',metadata_ref),('rights_ref',rights_ref),('compatibility_receipt_ref',compatibility_receipt_ref)]:
        if not str(val).strip():raise PackageComposerError('REFERENCE_REQUIRED',name)
    if not deliverables:raise PackageComposerError('DELIVERABLES_REQUIRED','empty')
    root=Path(package_dir)
    if root.exists() and any(root.iterdir()):raise PackageComposerError('PACKAGE_DIR_NOT_EMPTY',str(root))
    files_dir=root/'files';files_dir.mkdir(parents=True,exist_ok=True)
    seen_ids=set();items=[]
    for row in deliverables:
        required={'derivative_id','source_path','format','purpose','recipe_id','receipt_ref','compatibility_state'}
        missing=required-set(row)
        if missing:raise PackageComposerError('DELIVERABLE_INCOMPLETE',','.join(sorted(missing)))
        if row['derivative_id'] in seen_ids:raise PackageComposerError('DUPLICATE_DERIVATIVE_ID',row['derivative_id'])
        seen_ids.add(row['derivative_id'])
        if row['compatibility_state']!='COMPATIBLE':raise PackageComposerError('DELIVERABLE_INCOMPATIBLE',row['derivative_id'])
        src=Path(row['source_path'])
        if not src.is_file():raise PackageComposerError('DELIVERABLE_NOT_FOUND',str(src))
        sha=sha256_file(src);ext=src.suffix.lower() or '.'+str(row['format']).lower();dst_name=f'{sha}{ext}';dst=files_dir/dst_name
        if not dst.exists():shutil.copyfile(src,dst)
        items.append({'derivative_id':row['derivative_id'],'format':row['format'],'purpose':row['purpose'],'recipe_id':row['recipe_id'],'receipt_ref':row['receipt_ref'],'compatibility_state':'COMPATIBLE','sha256':sha,'bytes':src.stat().st_size,'package_path':f'files/{dst_name}'})
    items.sort(key=lambda x:x['derivative_id'])
    manifest={'schema':'die.factory-asset.marketplace-dry-run-package.v1','semantic_asset_id':semantic_asset_id,'master_sha256':master_sha256,'deliverables':items,'metadata_ref':metadata_ref,'rights_ref':rights_ref,'compatibility_receipt_ref':compatibility_receipt_ref,'publication_action':'NONE','upload_action':'NONE'}
    payload=json.dumps(manifest,sort_keys=True,indent=2)+'\n';(root/'manifest.json').write_text(payload,encoding='utf-8',newline='\n')
    manifest_sha=hashlib.sha256(payload.encode()).hexdigest()
    return {'schema':'die.factory-asset.marketplace-dry-run-package-receipt.v1','result':'PASS','manifest_sha256':manifest_sha,'manifest_path':str(root/'manifest.json'),'file_count':len(items),'semantic_asset_count':1,'derivative_count':len(items),'publication_action':'NONE','upload_action':'NONE'}