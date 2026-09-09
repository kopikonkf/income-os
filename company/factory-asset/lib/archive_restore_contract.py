from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def build_manifest(*,provider_original:Path,active_master:Path,receipts:list[Path])->dict:
 rows=[]
 for role,p in [('PROVIDER_ORIGINAL',provider_original),('ACTIVE_MASTER',active_master),*[( 'RECEIPT',x) for x in receipts]]:
  if not p.is_file():raise FileNotFoundError(p)
  rows.append({'role':role,'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 return {'schema':'die.factory-asset.archive-manifest.v1','objects':rows,'immutable_roles':['PROVIDER_ORIGINAL','ACTIVE_MASTER'],'content_addressed_sha256':True}

def archive_files(manifest:dict,sources:dict[str,Path],archive:Path)->None:
 archive.mkdir(parents=True,exist_ok=True)
 for row in manifest['objects']:
  src=sources[row['name']];dst=archive/row['sha256']
  if dst.exists() and sha(dst)!=row['sha256']:raise RuntimeError('ARCHIVE_HASH_CONFLICT')
  if not dst.exists():shutil.copy2(src,dst)
  if sha(dst)!=row['sha256']:raise RuntimeError('ARCHIVE_HASH_MISMATCH')
 (archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def restore(manifest:dict,archive:Path,destination:Path)->list[Path]:
 if destination.exists() and any(destination.iterdir()):raise RuntimeError('RESTORE_DESTINATION_NOT_EMPTY')
 destination.mkdir(parents=True,exist_ok=True);out=[]
 for row in manifest['objects']:
  src=archive/row['sha256'];dst=destination/row['name']
  if not src.is_file() or sha(src)!=row['sha256']:raise RuntimeError('RESTORE_SOURCE_HASH_MISMATCH')
  shutil.copy2(src,dst)
  if sha(dst)!=row['sha256']:raise RuntimeError('RESTORE_DESTINATION_HASH_MISMATCH')
  out.append(dst)
 return out
