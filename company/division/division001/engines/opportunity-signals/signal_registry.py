#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "die.division001.opportunity-signals.v1.schema.json"
VALIDATOR_PATH = ROOT / "validate_signal_receipt.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("oe001_signal_validator_runtime", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("VALIDATOR_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_receipt_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            signal_id TEXT PRIMARY KEY,
            dedupe_key TEXT NOT NULL UNIQUE,
            receipt_sha256 TEXT NOT NULL,
            subject_kind TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            parent_seed_id TEXT,
            parent_candidate_id TEXT,
            source_id TEXT NOT NULL,
            signal_class TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            evidence_label TEXT NOT NULL,
            receipt_json TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_subject ON signals(subject_kind, subject_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_parent_candidate ON signals(parent_candidate_id)")
    conn.commit()
    return conn


def ingest(conn: sqlite3.Connection, payload: dict[str, Any], *, as_of: dt.datetime | None = None) -> dict[str, Any]:
    validator = _load_validator()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = validator.validate(payload, schema, as_of=as_of)
    if errors:
        return {"status":"REJECTED","signal_id":payload.get("signal_id"),"errors":errors}
    digest = _canonical_receipt_sha(payload)
    existing = conn.execute("SELECT signal_id, receipt_sha256 FROM signals WHERE dedupe_key=?", (payload["dedupe_key"],)).fetchone()
    if existing is not None:
        if existing["receipt_sha256"] == digest and existing["signal_id"] == payload["signal_id"]:
            return {"status":"DUPLICATE","signal_id":existing["signal_id"],"receipt_sha256":digest,"errors":[]}
        return {"status":"CONFLICT","signal_id":payload["signal_id"],"existing_signal_id":existing["signal_id"],"errors":["E_DEDUPE_CONFLICT"]}
    same_id = conn.execute("SELECT receipt_sha256, dedupe_key FROM signals WHERE signal_id=?", (payload["signal_id"],)).fetchone()
    if same_id is not None:
        return {"status":"CONFLICT","signal_id":payload["signal_id"],"errors":["E_SIGNAL_ID_CONFLICT"]}
    subject=payload["subject"]
    conn.execute(
        """INSERT INTO signals(signal_id,dedupe_key,receipt_sha256,subject_kind,subject_id,parent_seed_id,parent_candidate_id,source_id,signal_class,signal_type,observed_at,recorded_at,expires_at,evidence_label,receipt_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (payload["signal_id"],payload["dedupe_key"],digest,subject["kind"],subject["id"],subject.get("parent_seed_id"),subject.get("parent_candidate_id"),payload["source"]["source_id"],payload["signal_class"],payload["signal_type"],payload["observed_at"],payload["recorded_at"],payload["expires_at"],payload["evidence_label"],json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False))
    )
    conn.commit()
    return {"status":"INSERTED","signal_id":payload["signal_id"],"receipt_sha256":digest,"errors":[]}


def query(conn: sqlite3.Connection, *, subject_id: str | None = None, source_id: str | None = None, signal_type: str | None = None, parent_candidate_id: str | None = None, as_of: dt.datetime | None = None, include_stale: bool = False) -> list[dict[str, Any]]:
    clauses=[]; values=[]
    if subject_id is not None: clauses.append("subject_id=?"); values.append(subject_id)
    if source_id is not None: clauses.append("source_id=?"); values.append(source_id)
    if signal_type is not None: clauses.append("signal_type=?"); values.append(signal_type)
    if parent_candidate_id is not None: clauses.append("parent_candidate_id=?"); values.append(parent_candidate_id)
    sql="SELECT receipt_json, expires_at FROM signals"
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY observed_at, source_id, signal_type, signal_id"
    rows=conn.execute(sql,values).fetchall()
    now=(as_of or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    out=[]
    for row in rows:
        stale=now >= _parse_time(row["expires_at"])
        if stale and not include_stale: continue
        payload=json.loads(row["receipt_json"])
        payload["registry_freshness"]="STALE" if stale else "FRESH"
        out.append(payload)
    return out


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0])


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    sub=ap.add_subparsers(dest="command",required=True)
    ing=sub.add_parser("ingest"); ing.add_argument("receipt"); ing.add_argument("--as-of")
    qry=sub.add_parser("query"); qry.add_argument("--subject-id"); qry.add_argument("--source-id"); qry.add_argument("--signal-type"); qry.add_argument("--parent-candidate-id"); qry.add_argument("--as-of"); qry.add_argument("--include-stale",action="store_true")
    sub.add_parser("count")
    args=ap.parse_args(); conn=connect(Path(args.db))
    try:
        if args.command=="ingest":
            payload=json.loads(Path(args.receipt).read_text(encoding="utf-8")); validator=_load_validator(); as_of=validator.parse_time(args.as_of) if args.as_of else None; result=ingest(conn,payload,as_of=as_of); print(json.dumps(result,indent=2)); return 0 if result["status"] in {"INSERTED","DUPLICATE"} else 2
        if args.command=="query":
            as_of=_parse_time(args.as_of) if args.as_of else None; print(json.dumps(query(conn,subject_id=args.subject_id,source_id=args.source_id,signal_type=args.signal_type,parent_candidate_id=args.parent_candidate_id,as_of=as_of,include_stale=args.include_stale),indent=2)); return 0
        print(json.dumps({"count":count(conn)},indent=2)); return 0
    finally:
        conn.close()

if __name__=="__main__": raise SystemExit(main())
