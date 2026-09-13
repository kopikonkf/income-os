from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT_MARKER = '.die-h01-submission-ready-root.json'
INDEX_NAME = 'submission-ready-index.json'

class ProjectionError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f'{code}: {detail}')
        self.code = code
        self.detail = detail

def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())

def _json(path: Path) -> dict[str, Any]:
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as exc:
        raise ProjectionError('JSON_READ_FAILED',str(path)) from exc
    if not isinstance(value,dict): raise ProjectionError('JSON_OBJECT_REQUIRED',str(path))
    return value

def _write_exact(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()==data: return
    path.write_bytes(data)

def _eligible(manifest: dict[str,Any]) -> tuple[bool,list[str]]:
    reasons=[]
    if manifest.get('submission_eligible') is not True: reasons.append('MANIFEST_NOT_ELIGIBLE')
    comp=manifest.get('compatibility') or {}
    if comp.get('status')!='COMPATIBLE' and comp.get('result')!='PASS': reasons.append('COMPATIBILITY_NOT_PASS')
    rights=manifest.get('rights_signal') or {}
    if rights.get('result')!='PASS': reasons.append('RIGHTS_NOT_PASS')
    if manifest.get('founder_qc')!='PASS': reasons.append('FOUNDER_QC_NOT_PASS')
    return not reasons,reasons

def _safe_root(root: Path) -> None:
    root.mkdir(parents=True,exist_ok=True)
    marker=root/ROOT_MARKER
    if marker.exists():
        data=_json(marker)
        if data.get('schema')!='die.h01.submission-ready-root.v1': raise ProjectionError('ROOT_MARKER_INVALID',str(marker))
        return
    existing=[p for p in root.iterdir()]
    if existing: raise ProjectionError('OUTPUT_ROOT_NOT_MANAGED',str(root))
    _write_exact(marker,(json.dumps({'schema':'die.h01.submission-ready-root.v1','managed_by':'H01-135'},sort_keys=True,indent=2)+'\n').encode())

def _manifest_files(manifest_path: Path, manifest: dict[str,Any]) -> list[tuple[Path,str,str]]:
    files_dir=manifest_path.parent/'files'; rows=[]
    for a in manifest.get('artifacts') or []:
        target=str(a.get('target') or a.get('path') or '')
        if not target: continue
        src=files_dir/target
        if not src.is_file(): raise ProjectionError('PACKAGE_FILE_MISSING',str(src))
        expected=str(a.get('sha256') or '')
        actual=_sha_file(src)
        if expected and actual!=expected: raise ProjectionError('PACKAGE_HASH_MISMATCH',str(src))
        rows.append((src,target,actual))
    side=manifest.get('sidecar_metadata') or {}
    side_rel=side.get('path')
    if side_rel:
        src=manifest_path.parent/str(side_rel)
        if not src.is_file(): raise ProjectionError('SIDECAR_MISSING',str(src))
        actual=_sha_file(src); expected=str(side.get('sha256') or '')
        if expected and actual!=expected: raise ProjectionError('SIDECAR_HASH_MISMATCH',str(src))
        rows.append((src,'metadata.json',actual))
    return rows

def project_submission_ready(source_root: Path, output_root: Path) -> dict[str,Any]:
    source_root=Path(source_root); output_root=Path(output_root)
    _safe_root(output_root)
    manifests=sorted(source_root.rglob('manifest.json')) if source_root.exists() else []
    desired: dict[str,dict[str,Any]]={}; skipped=[]
    for mp in manifests:
        m=_json(mp)
        if m.get('schema')!='die.h01.marketplace-delivery-package.v1': continue
        ok,reasons=_eligible(m)
        marketplace=str(m.get('marketplace') or '').lower(); sid=str(m.get('semantic_asset_id') or '')
        if not marketplace or not sid: raise ProjectionError('PACKAGE_IDENTITY_MISSING',str(mp))
        key=f'{marketplace}/{sid}'
        if not ok:
            skipped.append({'key':key,'manifest':str(mp),'reasons':reasons}); continue
        if key in desired: raise ProjectionError('DUPLICATE_ELIGIBLE_PACKAGE',key)
        desired[key]={'manifest_path':mp,'manifest':m}
    desired_top={k.split('/',1)[0] for k in desired}
    for marketplace_dir in [p for p in output_root.iterdir() if p.is_dir()]:
        if marketplace_dir.name.startswith('.'): continue
        for asset_dir in [p for p in marketplace_dir.iterdir() if p.is_dir()]:
            key=f'{marketplace_dir.name}/{asset_dir.name}'
            if key not in desired: shutil.rmtree(asset_dir)
        if not any(marketplace_dir.iterdir()) and marketplace_dir.name not in desired_top: marketplace_dir.rmdir()
    entries=[]
    for key,row in sorted(desired.items()):
        marketplace,sid=key.split('/',1); dest=output_root/marketplace/sid; dest.mkdir(parents=True,exist_ok=True)
        files=[]
        for src,name,sha in _manifest_files(row['manifest_path'],row['manifest']):
            data=src.read_bytes(); target=dest/name; _write_exact(target,data)
            files.append({'path':name,'sha256':sha,'bytes':len(data)})
        source_manifest_sha=_sha_file(row['manifest_path'])
        projection={'schema':'die.h01.submission-ready-entry.v1','marketplace':marketplace.upper(),'semantic_asset_id':sid,'source_manifest':str(row['manifest_path']),'source_manifest_sha256':source_manifest_sha,'files':sorted(files,key=lambda x:x['path']),'eligibility':{'compatibility':'PASS','rights':'PASS','founder_qc':'PASS','submission_eligible':True},'action':'NONE'}
        pdata=(json.dumps(projection,sort_keys=True,indent=2)+'\n').encode(); _write_exact(dest/'projection.json',pdata)
        entries.append({'marketplace':marketplace.upper(),'semantic_asset_id':sid,'relative_path':key,'source_manifest_sha256':source_manifest_sha,'projection_sha256':_sha_bytes(pdata),'files':projection['files']})
    index={'schema':'die.h01.submission-ready-index.v1','entries':entries,'eligible_count':len(entries),'skipped_count':len(skipped),'skipped':skipped,'external_action':'NONE'}
    raw=(json.dumps(index,sort_keys=True,indent=2)+'\n').encode(); _write_exact(output_root/INDEX_NAME,raw)
    index['index_file_sha256']=_sha_bytes(raw)
    return index

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument('--source-root',default='/var/lib/die/h01/delivery'); ap.add_argument('--output-root',default='/var/lib/die/h01/submission-ready'); args=ap.parse_args()
    print(json.dumps(project_submission_ready(Path(args.source_root),Path(args.output_root)),indent=2,sort_keys=True))
if __name__=='__main__': main()
