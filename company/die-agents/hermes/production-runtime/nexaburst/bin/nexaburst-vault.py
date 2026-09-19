#!/usr/bin/env python3
from __future__ import annotations
import argparse, fcntl, hashlib, json, mimetypes, os, time, urllib.parse, urllib.request, uuid, zipfile
from pathlib import Path

ENV=Path('/home/kopiko/.config/die/nexaburst.env')
ROOT=Path('/var/lib/die/h01/nexaburst')
WORKSPACES=ROOT/'workspaces'
VAULT=ROOT/'vault'
ARCHIVES=VAULT/'archives'
RESTORES=VAULT/'restores'
RECEIPTS=VAULT/'receipts'
DONE=ROOT/'state'/'vault-done.jsonl'
ERRORS=ROOT/'state'/'vault-errors.jsonl'
LOCK=ROOT/'state'/'vault-worker.lock'

def load_env():
    if ENV.is_file():
        for raw in ENV.read_text(encoding='utf-8').splitlines():
            line=raw.strip()
            if line and not line.startswith('#') and '=' in line:
                k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip())

def truthy(v): return str(v or '').strip().lower() in {'1','true','yes','on'}

def sha256_path(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def atomic(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def append(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(value,sort_keys=True,ensure_ascii=False)+'\n')

def inside_root(path):
    try: Path(path).resolve().relative_to(ROOT.resolve()); return True
    except Exception: return False

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def completed_ids():
    out=set()
    if DONE.is_file():
        for line in DONE.read_text(encoding='utf-8').splitlines():
            try:
                row=json.loads(line)
                if row.get('status')=='BACKUP_VERIFIED': out.add(row.get('archive_identity'))
            except Exception: pass
    return out

def workspace_info(ws):
    result_path=ws/'nexaburst-v2-result.json'
    if not result_path.is_file(): return None
    result=read_json(result_path)
    if result.get('status')!='WAITING_FOUNDER_QC': return None
    state_path=ws/'factory-v2'/'postproduction-state.json'
    state=read_json(state_path) if state_path.is_file() else {}
    master_sha=state.get('active_master_sha256') or state.get('source_master_sha256')
    semantic_id=state.get('semantic_asset_id') or result.get('asset_id')
    if not master_sha: raise RuntimeError('E_VAULT_MASTER_SHA_MISSING')
    identity=hashlib.sha256(f'{semantic_id}:{master_sha}'.encode()).hexdigest()
    package_path=ws/'factory-v2'/'package-readiness.json'
    package=read_json(package_path) if package_path.is_file() else {}
    rights_path=ws/'factory-v2'/'rights-signal.json'
    rights=read_json(rights_path) if rights_path.is_file() else {}
    return {'result':result,'state':state,'package':package,'rights':rights,
            'master_sha256':master_sha,'semantic_asset_id':semantic_id,'archive_identity':identity}

def collect_files(ws):
    files=[]
    for p in sorted(ws.rglob('*')):
        if p.is_file():
            low='/'.join(p.relative_to(ws).parts).lower()
            if any(x in low for x in ('cookie','credential','secret','token','/udd/')):
                continue
            files.append((p,'workspace/'+p.relative_to(ws).as_posix()))
    src_path=ws/'nexaburst-source.json'
    if src_path.is_file():
        src=read_json(src_path)
        for key,prefix in [('source_path','source/provider-original'),('generation_receipt','source/generation-receipt')]:
            val=src.get(key)
            if val:
                p=Path(val)
                if p.is_file() and inside_root(p):
                    suffix=p.suffix or '.bin'
                    files.append((p,prefix+suffix))
    seen=set(); out=[]
    for p,arc in files:
        if arc not in seen: seen.add(arc); out.append((p,arc))
    return out

def build_archive(ws,info):
    ARCHIVES.mkdir(parents=True,exist_ok=True)
    asset=info['result']['asset_id']
    name=f'{asset}__{info["master_sha256"][:12]}.zip'
    dest=ARCHIVES/name
    entries=[]
    files=collect_files(ws)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,arc in files:
            h=sha256_path(p); size=p.stat().st_size
            z.write(p,arc); entries.append({'path':arc,'sha256':h,'bytes':size})
        manifest={
          'schema':'die.h01.nexaburst.telegram-vault-manifest.v1',
          'engine_id':'H01-NEXABURST','asset_id':asset,
          'semantic_asset_id':info['semantic_asset_id'],
          'archive_identity':info['archive_identity'],
          'master_sha256':info['master_sha256'],
          'source_state':'WAITING_FOUNDER_QC',
          'package_result':info['package'].get('result'),
          'rights_result':info['rights'].get('result'),
          'files':entries,
          'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        }
        mbytes=(json.dumps(manifest,indent=2,sort_keys=True,ensure_ascii=False)+'\n').encode()
        z.writestr('ARCHIVE_MANIFEST.json',mbytes)
        checks=''.join(f'{e["sha256"]}  {e["path"]}\n' for e in entries)
        z.writestr('CHECKSUMS.sha256',checks.encode())
    return dest,manifest

def multipart_post(url,fields,file_field,file_path,timeout=120):
    boundary='----NexaBurst'+uuid.uuid4().hex
    parts=[]
    for k,v in fields.items():
        if v is None or str(v)=='': continue
        parts += [f'--{boundary}\r\n'.encode(),
                  f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(),
                  str(v).encode(),b'\r\n']
    p=Path(file_path); mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    parts += [f'--{boundary}\r\n'.encode(),
              f'Content-Disposition: form-data; name="{file_field}"; filename="{p.name}"\r\n'.encode(),
              f'Content-Type: {mime}\r\n\r\n'.encode(),p.read_bytes(),b'\r\n',
              f'--{boundary}--\r\n'.encode()]
    req=urllib.request.Request(url,data=b''.join(parts),method='POST',
        headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def api_post(token,method,data,timeout=30):
    req=urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}',
        data=urllib.parse.urlencode(data).encode(),method='POST',
        headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def upload_and_verify(archive,info):
    token=os.getenv('NEXABURST_TELEGRAM_BOT_TOKEN','').strip()
    chat=os.getenv('NEXABURST_VAULT_CHAT_ID','').strip()
    thread=os.getenv('NEXABURST_VAULT_THREAD_ID','').strip()
    if not token or not chat or not thread: raise RuntimeError('E_VAULT_CONFIG')
    max_upload=int(os.getenv('NEXABURST_VAULT_MAX_UPLOAD_BYTES','49000000'))
    max_restore=int(os.getenv('NEXABURST_VAULT_MAX_RESTORE_BYTES','19500000'))
    size=archive.stat().st_size
    if size>max_upload: raise RuntimeError(f'E_VAULT_UPLOAD_LIMIT:{size}')
    if size>max_restore: raise RuntimeError(f'E_VAULT_RESTORE_LIMIT:{size}')
    archive_sha=sha256_path(archive)
    cap=(f'NEXABURST_BACKUP\nasset={info["result"]["asset_id"]}\n'
         f'state=WAITING_FOUNDER_QC\nmaster_sha256={info["master_sha256"]}\n'
         f'archive_sha256={archive_sha}\nbytes={size}')
    payload=multipart_post(f'https://api.telegram.org/bot{token}/sendDocument',
        {'chat_id':chat,'message_thread_id':thread,'caption':cap,'disable_notification':'true'},
        'document',archive)
    if not payload.get('ok'): raise RuntimeError('E_VAULT_UPLOAD_API:'+str(payload.get('description')))
    msg=payload.get('result') or {}; doc=msg.get('document') or {}
    file_id=doc.get('file_id')
    if not file_id: raise RuntimeError('E_VAULT_FILE_ID')
    gf=api_post(token,'getFile',{'file_id':file_id})
    if not gf.get('ok'): raise RuntimeError('E_VAULT_GETFILE:'+str(gf.get('description')))
    remote=(gf.get('result') or {}).get('file_path')
    if not remote: raise RuntimeError('E_VAULT_REMOTE_PATH')
    h=hashlib.sha256()
    downloaded=0
    with urllib.request.urlopen(f'https://api.telegram.org/file/bot{token}/{remote}',timeout=120) as r:
        while True:
            chunk=r.read(1024*1024)
            if not chunk: break
            h.update(chunk)
            downloaded += len(chunk)
    restored_sha=h.hexdigest()
    if downloaded!=size: raise RuntimeError(f'E_VAULT_RESTORE_SIZE:{downloaded}:{size}')
    if restored_sha!=archive_sha: raise RuntimeError(f'E_VAULT_RESTORE_HASH:{restored_sha}')
    return {
      'schema':'die.h01.nexaburst.telegram-vault-receipt.v1',
      'status':'BACKUP_VERIFIED','asset_id':info['result']['asset_id'],
      'semantic_asset_id':info['semantic_asset_id'],'archive_identity':info['archive_identity'],
      'master_sha256':info['master_sha256'],'archive_path':str(archive),
      'archive_sha256':archive_sha,'archive_bytes':size,
      'telegram_chat_id':chat,'telegram_thread_id':thread,
      'telegram_message_id':msg.get('message_id'),'telegram_file_id':file_id,
      'telegram_file_unique_id':doc.get('file_unique_id'),
      'restore_sha256':restored_sha,'restore_bytes':downloaded,
      'verification_mode':'STREAM_SHA256_NO_TEMP_FILE',
      'local_archive_policy':'DELETE_AFTER_VERIFIED_LEDGER',
      'verified_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    }

def process(ws,dry_run=False):
    info=workspace_info(ws)
    if not info: return None
    if info['archive_identity'] in completed_ids():
        return {'status':'SKIP_ALREADY_VERIFIED','asset_id':info['result']['asset_id']}
    archive,manifest=build_archive(ws,info)
    if dry_run:
        return {'status':'DRY_RUN','asset_id':info['result']['asset_id'],
                'archive':str(archive),'sha256':sha256_path(archive),'bytes':archive.stat().st_size,
                'files':len(manifest['files'])}
    receipt=upload_and_verify(archive,info)
    RECEIPTS.mkdir(parents=True,exist_ok=True)
    atomic(RECEIPTS/f'{receipt["asset_id"]}__{receipt["archive_sha256"][:12]}.json',receipt)
    append(DONE,receipt)
    archive.unlink(missing_ok=True)
    return receipt


def cleanup_verified_archives():
    if not DONE.is_file(): return 0
    removed=0
    for line in DONE.read_text(encoding='utf-8').splitlines():
        try: row=json.loads(line)
        except Exception: continue
        if row.get('status')!='BACKUP_VERIFIED': continue
        raw=row.get('archive_path')
        if not raw: continue
        p=Path(raw)
        try:
            p.resolve().relative_to(ARCHIVES.resolve())
        except Exception:
            continue
        if p.is_file():
            p.unlink()
            removed += 1
    return removed

def candidates(asset_id=None):
    if asset_id:
        ws=WORKSPACES/asset_id
        return [ws] if ws.is_dir() else []
    out=[]
    done=completed_ids()
    for ws in sorted(WORKSPACES.iterdir() if WORKSPACES.is_dir() else []):
        try:
            info=workspace_info(ws)
            if not info or info['archive_identity'] in done: continue
            src_path=ws/'nexaburst-source.json'
            src=read_json(src_path) if src_path.is_file() else {}
            receipt_path=Path(src.get('generation_receipt',''))
            receipt=read_json(receipt_path) if receipt_path.is_file() and inside_root(receipt_path) else {}
            if receipt.get('transport')!='WEB_SESSION_INTERNAL_JOB_API': continue
            out.append(ws)
        except Exception: pass
    return out

def main():
    load_env()
    ap=argparse.ArgumentParser()
    ap.add_argument('--once',action='store_true')
    ap.add_argument('--asset-id')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    if not truthy(os.getenv('NEXABURST_VAULT_ENABLED','false')) and not args.dry_run:
        print(json.dumps({'status':'SKIP','reason':'vault_disabled'})); return 0
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open('w') as lf:
        try: fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status':'SKIP','reason':'vault_lock_busy'})); return 0
        cleanup_verified_archives()
        rows=candidates(args.asset_id)
        if not rows:
            print(json.dumps({'status':'IDLE'})); return 0
        for ws in rows[:1] if args.once or args.asset_id else rows:
            try:
                result=process(ws,args.dry_run); print(json.dumps(result,sort_keys=True))
            except Exception as exc:
                row={'schema':'die.h01.nexaburst.telegram-vault-error.v1','asset_id':ws.name,
                     'error':str(exc),'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
                append(ERRORS,row); print(json.dumps({'status':'ERROR','asset_id':ws.name,'error':str(exc)}))
                return 2
    return 0

if __name__=='__main__': raise SystemExit(main())
