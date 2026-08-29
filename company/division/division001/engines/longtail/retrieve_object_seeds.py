#!/usr/bin/env python3
"""Bounded read-only Object Atlas cleaned-seed retrieval adapter v1."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

MAX_RESULTS = 50
ALLOWED_QUERY_KEYS = {"seed_ids", "canonical_names", "object_class", "category_prefix", "limit"}


class RetrievalError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    db_path = db_path.expanduser().resolve()
    if not db_path.is_file():
        raise RetrievalError("E_OBJECT_DB_MISSING")
    uri = db_path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    if conn.execute("PRAGMA query_only").fetchone()[0] != 1:
        conn.close()
        raise RetrievalError("E_OBJECT_DB_NOT_QUERY_ONLY")
    return conn


def _validate_query(query: dict[str, Any]) -> None:
    extra = set(query) - ALLOWED_QUERY_KEYS
    if extra:
        raise RetrievalError("E_OBJECT_QUERY_KEY:" + ",".join(sorted(extra)))
    limit = query.get("limit", 25)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > MAX_RESULTS:
        raise RetrievalError("E_OBJECT_LIMIT")
    if not any(query.get(k) for k in ("seed_ids", "canonical_names", "object_class", "category_prefix")):
        raise RetrievalError("E_OBJECT_QUERY_UNBOUNDED")
    for key in ("seed_ids", "canonical_names"):
        value = query.get(key)
        if value is not None:
            if not isinstance(value, list) or not value or len(value) > MAX_RESULTS or not all(isinstance(x, str) and x.strip() for x in value):
                raise RetrievalError("E_OBJECT_QUERY_LIST:" + key)


def retrieve(db_path: Path, query: dict[str, Any], *, source_db_sha256: str | None = None, verify_hash: bool = False) -> dict[str, Any]:
    _validate_query(query)
    db_path = db_path.expanduser().resolve()
    if source_db_sha256 is None:
        source_db_sha256 = _sha256_file(db_path)
    if len(source_db_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_db_sha256):
        raise RetrievalError("E_OBJECT_DB_SHA256")
    if verify_hash and _sha256_file(db_path) != source_db_sha256:
        raise RetrievalError("E_OBJECT_DB_HASH_MISMATCH")

    where = ["status = 'approved'"]
    params: list[Any] = []
    seed_ids = query.get("seed_ids")
    if seed_ids:
        where.append("id IN (" + ",".join("?" for _ in seed_ids) + ")")
        params.extend(seed_ids)
    names = query.get("canonical_names")
    if names:
        where.append("LOWER(canonical_name) IN (" + ",".join("LOWER(?)" for _ in names) + ")")
        params.extend(names)
    if query.get("object_class"):
        where.append("LOWER(COALESCE(object_class,'')) = LOWER(?)")
        params.append(query["object_class"])
    if query.get("category_prefix"):
        where.append("LOWER(COALESCE(category_path,'')) LIKE LOWER(?)")
        params.append(str(query["category_prefix"]).rstrip("/") + "%")
    limit = query.get("limit", 25)
    sql = "SELECT id, canonical_name, aliases, object_class, existence_type, category_path, visuality_score, risk_score, status, updated_at FROM seeds WHERE " + " AND ".join(where) + " ORDER BY canonical_name COLLATE NOCASE, id LIMIT ?"
    params.append(limit)

    conn = connect_readonly(db_path)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(seeds)")}
        required = {"id","canonical_name","aliases","object_class","existence_type","category_path","visuality_score","risk_score","status","updated_at"}
        if not required.issubset(cols):
            raise RetrievalError("E_OBJECT_SCHEMA_MISMATCH")
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        aliases = []
        raw_aliases = row["aliases"]
        if raw_aliases:
            try:
                parsed = json.loads(raw_aliases)
                aliases = parsed if isinstance(parsed, list) else [str(parsed)]
            except json.JSONDecodeError:
                aliases = [x.strip() for x in str(raw_aliases).split(",") if x.strip()]
        results.append({
            "seed_id": row["id"],
            "canonical_name": row["canonical_name"],
            "aliases": aliases,
            "object_class": row["object_class"],
            "existence_type": row["existence_type"],
            "category_path": row["category_path"],
            "visuality_score": row["visuality_score"],
            "risk_score": row["risk_score"],
            "status": row["status"],
            "updated_at": row["updated_at"],
        })
    receipt_id = "OBJRET-" + hashlib.sha256(json.dumps({"db":source_db_sha256,"query":query,"results":[r["seed_id"] for r in results]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24].upper()
    return {
        "schema":"die.object-atlas.seed-retrieval.v1",
        "receipt_id":receipt_id,
        "source_db":{"path_ref":str(db_path),"sha256":source_db_sha256,"mode":"READ_ONLY_POINT_IN_TIME_OR_AUTHORITATIVE_SNAPSHOT"},
        "query":query,
        "policy":{"approved_only":True,"max_results":MAX_RESULTS,"arbitrary_sql":False,"dataset_finality_required":False},
        "result_count":len(results),
        "results":results,
    }


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--db",required=True); ap.add_argument("--query",required=True); ap.add_argument("--db-sha256"); ap.add_argument("--verify-hash",action="store_true")
    args=ap.parse_args()
    try:
        query=json.loads(Path(args.query).read_text(encoding="utf-8"))
        print(json.dumps(retrieve(Path(args.db),query,source_db_sha256=args.db_sha256,verify_hash=args.verify_hash),indent=2,ensure_ascii=False))
        return 0
    except (OSError,json.JSONDecodeError,sqlite3.Error,RetrievalError) as exc:
        print(json.dumps({"schema":"die.object-atlas.seed-retrieval-run.v1","status":"FAIL","error":str(exc)},indent=2)); return 2

if __name__=="__main__": raise SystemExit(main())
