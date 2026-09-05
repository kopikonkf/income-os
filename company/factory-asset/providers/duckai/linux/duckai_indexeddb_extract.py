#!/usr/bin/env python3
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import shutil
import sqlite3
import struct
import tempfile
from pathlib import Path

CHROMIUM_EPOCH = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)


def decode_name(raw: bytes | None) -> str:
    if not raw:
        return ''
    try:
        return raw.decode('utf-16-le').rstrip('\x00')
    except UnicodeDecodeError:
        return ''


def image_info(raw: bytes, mime: str) -> tuple[str, int, int]:
    if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw) >= 24:
        w, h = struct.unpack('>II', raw[16:24])
        return 'png', w, h
    if raw[:3] == b'\xff\xd8\xff':
        i = 2
        sof = {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}
        while i + 9 < len(raw):
            if raw[i] != 0xff:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in sof:
                h = struct.unpack('>H', raw[i + 5:i + 7])[0]
                w = struct.unpack('>H', raw[i + 7:i + 9])[0]
                return 'jpg', w, h
            if marker in (0xd8, 0xd9):
                i += 2
                continue
            if i + 4 > len(raw):
                break
            n = struct.unpack('>H', raw[i + 2:i + 4])[0]
            if n < 2:
                break
            i += 2 + n
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'webp', 0, 0
    raise RuntimeError(f'E_IMAGE_MAGIC:{mime}')


def find_db(profile: Path) -> Path:
    root = profile / 'Default' / 'IndexedDB' / 'https_duck.ai_0'
    candidates = []
    for p in root.glob('*'):
        if p.is_file() and not p.name.endswith(('-wal', '-shm')):
            try:
                with p.open('rb') as f:
                    if f.read(16) == b'SQLite format 3\x00':
                        candidates.append(p)
            except OSError:
                pass
    if len(candidates) != 1:
        raise RuntimeError(f'E_INDEXEDDB_DATABASE_COUNT:{len(candidates)}')
    return candidates[0]


def snapshot(src: Path, tmp: Path) -> Path:
    dst = tmp / 'duck.sqlite'
    shutil.copy2(src, dst)
    for suffix in ('-wal', '-shm'):
        q = Path(str(src) + suffix)
        if q.exists():
            shutil.copy2(q, Path(str(dst) + suffix))
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile-dir', default='/var/lib/muxia/profiles/chatgpt-linux-a/browser')
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--after-utc', default=None)
    args = ap.parse_args()

    profile = Path(args.profile_dir).resolve()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    after = dt.datetime.fromisoformat(args.after_utc.replace('Z', '+00:00')) if args.after_utc else None
    if after and after.tzinfo is None:
        after = after.replace(tzinfo=dt.timezone.utc)

    src = find_db(profile)
    with tempfile.TemporaryDirectory(prefix='duckai-indexeddb-') as td:
        db = snapshot(src, Path(td))
        con = sqlite3.connect(db)
        stores = {decode_name(name): oid for oid, name in con.execute('select id,name from object_stores')}
        store_id = stores.get('chat-images')
        if not store_id:
            raise RuntimeError('E_CHAT_IMAGES_STORE_MISSING')
        rows = con.execute(
            'select b.row_id,b.mime_type,b.size_bytes,b.last_modified,b.bytes '
            'from blobs b '
            'join blob_references br on br.blob_row_id=b.row_id '
            'join records r on r.row_id=br.record_row_id '
            'where r.object_store_id=? and b.mime_type like "image/%" '
            'order by b.last_modified desc',
            (store_id,),
        ).fetchall()

    selected = None
    for row_id, mime, declared, last_modified, raw in rows:
        observed = CHROMIUM_EPOCH + dt.timedelta(microseconds=int(last_modified))
        if after and observed <= after.astimezone(dt.timezone.utc):
            continue
        if len(raw) != declared:
            continue
        try:
            ext, w, h = image_info(raw, mime or '')
        except RuntimeError:
            continue
        if ext != 'webp' and min(w, h) < 512:
            continue
        selected = (row_id, mime, observed, raw, ext, w, h)
        break

    if not selected:
        raise RuntimeError('E_NO_ELIGIBLE_CHAT_IMAGE_BLOB')

    row_id, mime, observed, raw, ext, w, h = selected
    target = out / f'source-original.{ext}'
    target.write_bytes(raw)
    receipt = {
        'schema': 'die.factory-asset.duckai-indexeddb-extraction.v1',
        'provider_id': 'duckai',
        'profile_id': profile.parent.name if profile.name == 'browser' else profile.name,
        'source_origin': 'https://duck.ai',
        'indexeddb_object_store': 'chat-images',
        'blob_row_id': row_id,
        'browser_blob_last_modified_utc': observed.isoformat(),
        'mime': mime,
        'dimensions': [w, h],
        'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'local_path': str(target),
        'original_byte_acquisition_method': 'duckai_indexeddb_chat_images_blob',
        'credential_values_read': False,
        'cookies_or_tokens_read': False,
    }
    (out / 'duckai-indexeddb-extraction.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())