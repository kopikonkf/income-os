#!/usr/bin/env python3
"""Create and verify a consistent SQLite snapshot from an active source DB."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, sqlite3
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def scalar(conn: sqlite3.Connection, sql: str):
    return conn.execute(sql).fetchone()[0]

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True)
    ap.add_argument('--dest',required=True)
    ap.add_argument('--receipt',required=True)
    args=ap.parse_args()
    source=Path(args.source).resolve(); dest=Path(args.dest).resolve(); receipt=Path(args.receipt).resolve()
    if not source.is_file(): raise SystemExit('SOURCE_DB_MISSING')
    if dest.exists(): raise SystemExit('DEST_ALREADY_EXISTS')
    dest.parent.mkdir(parents=True,exist_ok=True); receipt.parent.mkdir(parents=True,exist_ok=True)
    started=dt.datetime.now(dt.timezone.utc).isoformat()
    src_uri='file:'+source.as_posix()+'?mode=ro'
    with sqlite3.connect(src_uri,uri=True,timeout=60) as src:
        src.execute('PRAGMA busy_timeout=60000')
        source_page_count=scalar(src,'PRAGMA page_count')
        source_page_size=scalar(src,'PRAGMA page_size')
        source_journal_mode=scalar(src,'PRAGMA journal_mode')
        with sqlite3.connect(dest,timeout=60) as dst:
            src.backup(dst,pages=4096,sleep=0.05)
            dst.commit()
    with sqlite3.connect(f'file:{dest.as_posix()}?mode=ro',uri=True,timeout=60) as check:
        quick=scalar(check,'PRAGMA quick_check')
        dest_page_count=scalar(check,'PRAGMA page_count')
        dest_page_size=scalar(check,'PRAGMA page_size')
        table_count=scalar(check,"SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    if quick!='ok': raise SystemExit('DEST_QUICK_CHECK_FAILED:'+str(quick))
    payload={
      'schema':'die.sqlite-online-backup.v1','started_at':started,
      'completed_at':dt.datetime.now(dt.timezone.utc).isoformat(),
      'source':str(source),'dest':str(dest),'source_open_mode':'read-only',
      'backup_api':'sqlite3.Connection.backup','source_journal_mode':source_journal_mode,
      'source_page_count_at_backup_start':source_page_count,'source_page_size':source_page_size,
      'dest_page_count':dest_page_count,'dest_page_size':dest_page_size,'dest_table_count':table_count,
      'dest_bytes':dest.stat().st_size,'dest_sha256':sha256(dest),'quick_check':quick,
      'raw_wal_shm_copied':False
    }
    receipt.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':'PASS','dest':str(dest),'bytes':payload['dest_bytes'],'sha256':payload['dest_sha256'],'quick_check':quick}))
    return 0
if __name__=='__main__': raise SystemExit(main())
