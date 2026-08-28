#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='/var/lib/die/atlas/object-asset-engine')
    ap.add_argument('--manifest',default=str(Path(__file__).with_name('POINT_IN_TIME_SNAPSHOT_V1.json')))
    args=ap.parse_args()
    root=Path(args.root).resolve(); manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    observed={'schema':'die.object-engine.runtime-verification.v1','root':str(root),'db':{},'data':{},'status':'PASS'}
    for name,expected in manifest['sqlite_snapshots'].items():
        path=root/'db'/name
        assert path.is_file(), f'DB_MISSING:{name}'
        assert path.stat().st_size==expected['bytes'], f'DB_SIZE:{name}'
        assert sha256(path)==expected['sha256'], f'DB_HASH:{name}'
        with sqlite3.connect(f'file:{path.as_posix()}?mode=ro',uri=True) as c:
            quick=c.execute('PRAGMA quick_check').fetchone()[0]
            tables=c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            assert quick=='ok',f'DB_QUICK:{name}:{quick}'
            assert tables==expected['tables'],f'DB_TABLES:{name}:{tables}'
            row={'bytes':path.stat().st_size,'sha256':expected['sha256'],'quick_check':quick,'tables':tables}
            if name=='object_asset_engine.db':
                row['candidate_seeds_count']=c.execute('SELECT COUNT(*) FROM candidate_seeds').fetchone()[0]
                row['audit_queue_count']=c.execute('SELECT COUNT(*) FROM audit_queue').fetchone()[0]
                row['audit_pending_count']=c.execute("SELECT COUNT(*) FROM audit_queue WHERE audit_status='pending'").fetchone()[0]
                for key in ('candidate_seeds_count','audit_queue_count','audit_pending_count'):
                    assert row[key]==expected[key],f'DB_COUNT:{name}:{key}:{row[key]}'
            else:
                row['objects_count']=c.execute('SELECT COUNT(*) FROM objects').fetchone()[0]
                assert row['objects_count']==expected['objects_count'],f'DB_COUNT:{name}:objects_count:{row["objects_count"]}'
            observed['db'][name]=row
    total=0
    for row in manifest['data']['files']:
        path=root/'data'/row['path']
        assert path.is_file(),f'DATA_MISSING:{row["path"]}'
        assert path.stat().st_size==row['bytes'],f'DATA_SIZE:{row["path"]}'
        assert sha256(path)==row['sha256'],f'DATA_HASH:{row["path"]}'
        total+=row['bytes']
    assert total==manifest['data']['total_bytes']
    observed['data']={'file_count':manifest['data']['file_count'],'total_bytes':total,'hash_parity':'PASS'}
    print(json.dumps(observed,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
