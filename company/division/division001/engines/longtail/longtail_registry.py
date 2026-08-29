#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

class RegistryError(RuntimeError):
    pass


def _canonical_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidates(
          candidate_id TEXT PRIMARY KEY,
          seed_id TEXT NOT NULL,
          canonical_phrase TEXT NOT NULL,
          candidate_sha256 TEXT NOT NULL,
          candidate_json TEXT NOT NULL,
          guard_status TEXT NOT NULL,
          guard_reasons_json TEXT NOT NULL,
          guard_receipt_id TEXT NOT NULL,
          score_status TEXT,
          final_score REAL,
          score_sha256 TEXT,
          score_json TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(seed_id, canonical_phrase)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lt_rank ON candidates(guard_status,score_status,final_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lt_seed ON candidates(seed_id)")
    conn.commit()
    return conn


def ingest_guard(conn: sqlite3.Connection, guard: dict[str, Any]) -> dict[str, int]:
    if guard.get("schema") != "die.division001.longtail-guard.v1":
        raise RegistryError("E_GUARD_SCHEMA")
    stats = {"INSERTED": 0, "DUPLICATE": 0, "CONFLICT": 0}
    for outcome in guard["outcomes"]:
        cand = outcome["candidate"]
        cid = cand["candidate_id"]
        seed = cand["parent_seed"]["seed_id"]
        phrase = outcome["canonical_phrase"]
        digest = _canonical_sha(cand)
        existing = conn.execute(
            "SELECT candidate_sha256,seed_id,canonical_phrase,guard_status,guard_reasons_json,guard_receipt_id FROM candidates WHERE candidate_id=?",
            (cid,),
        ).fetchone()
        if existing is not None:
            same = (
                existing["candidate_sha256"] == digest
                and existing["seed_id"] == seed
                and existing["canonical_phrase"] == phrase
                and existing["guard_status"] == outcome["status"]
                and json.loads(existing["guard_reasons_json"]) == outcome["reasons"]
                and existing["guard_receipt_id"] == guard["guard_receipt_id"]
            )
            stats["DUPLICATE" if same else "CONFLICT"] += 1
            continue
        collision = conn.execute(
            "SELECT candidate_id FROM candidates WHERE seed_id=? AND canonical_phrase=?",
            (seed, phrase),
        ).fetchone()
        if collision is not None:
            stats["CONFLICT"] += 1
            continue
        conn.execute(
            """INSERT INTO candidates(
                candidate_id,seed_id,canonical_phrase,candidate_sha256,candidate_json,
                guard_status,guard_reasons_json,guard_receipt_id,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                cid,
                seed,
                phrase,
                digest,
                json.dumps(cand, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                outcome["status"],
                json.dumps(outcome["reasons"], sort_keys=True, separators=(",", ":")),
                guard["guard_receipt_id"],
                cand["created_at"],
                cand["created_at"],
            ),
        )
        stats["INSERTED"] += 1
    conn.commit()
    return stats


def attach_score(conn: sqlite3.Connection, phrase_score: dict[str, Any]) -> str:
    if phrase_score.get("schema") != "die.division001.longtail-phrase-score.v1":
        raise RegistryError("E_PHRASE_SCORE_SCHEMA")
    cid = phrase_score["candidate_id"]
    row = conn.execute("SELECT guard_status,score_sha256 FROM candidates WHERE candidate_id=?", (cid,)).fetchone()
    if row is None:
        raise RegistryError("E_CANDIDATE_NOT_FOUND")
    if row["guard_status"] != "ACCEPTED":
        raise RegistryError("E_CANDIDATE_NOT_ACCEPTED")
    digest = _canonical_sha(phrase_score)
    if row["score_sha256"] is not None:
        return "DUPLICATE" if row["score_sha256"] == digest else "CONFLICT"
    score = phrase_score["demand_score"]
    conn.execute(
        "UPDATE candidates SET score_status=?,final_score=?,score_sha256=?,score_json=?,updated_at=? WHERE candidate_id=?",
        (
            score["score_status"],
            score["final_score"],
            digest,
            json.dumps(phrase_score, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            score["evaluated_at"],
            cid,
        ),
    )
    conn.commit()
    return "ATTACHED"


def ranking(conn: sqlite3.Connection, *, limit: int = 100) -> dict[str, Any]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 1000:
        raise RegistryError("E_RANK_LIMIT")
    rows = conn.execute(
        """SELECT candidate_id,seed_id,canonical_phrase,final_score,score_json,candidate_sha256,score_sha256
        FROM candidates
        WHERE guard_status='ACCEPTED' AND score_status='COMPLETE' AND final_score IS NOT NULL
        ORDER BY final_score DESC, canonical_phrase COLLATE NOCASE, candidate_id LIMIT ?""",
        (limit,),
    ).fetchall()
    ranked = []
    for i, row in enumerate(rows, 1):
        score = json.loads(row["score_json"])["demand_score"]
        ranked.append({
            "rank": i,
            "candidate_id": row["candidate_id"],
            "seed_id": row["seed_id"],
            "phrase": row["canonical_phrase"],
            "final_score": row["final_score"],
            "confidence": score["confidence"],
            "candidate_sha256": row["candidate_sha256"],
            "score_sha256": row["score_sha256"],
        })
    deferred_rows = conn.execute(
        """SELECT guard_status,COALESCE(score_status,'UNSCORED') AS s,COUNT(*) AS c
        FROM candidates
        WHERE NOT (guard_status='ACCEPTED' AND score_status='COMPLETE' AND final_score IS NOT NULL)
        GROUP BY guard_status,s ORDER BY guard_status,s"""
    ).fetchall()
    deferred = [{"guard_status": x["guard_status"], "score_status": x["s"], "count": x["c"]} for x in deferred_rows]
    digest = hashlib.sha256(json.dumps([(x["candidate_id"], x["final_score"]) for x in ranked], separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": "die.division001.longtail-ranking.v1",
        "ranking_receipt_id": "LTRANK-" + digest[:24].upper(),
        "ranked_count": len(ranked),
        "deferred": deferred,
        "ranked": ranked,
        "policy": "Only guard ACCEPTED + OE-002 COMPLETE numeric scores are ranked.",
    }


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ingest-guard"); a.add_argument("guard")
    b = sub.add_parser("attach-score"); b.add_argument("score")
    r = sub.add_parser("rank"); r.add_argument("--limit", type=int, default=100)
    sub.add_parser("count")
    args = ap.parse_args()
    conn = connect(Path(args.db))
    try:
        if args.cmd == "ingest-guard":
            print(json.dumps(ingest_guard(conn, json.loads(Path(args.guard).read_text())), indent=2)); return 0
        if args.cmd == "attach-score":
            print(json.dumps({"status": attach_score(conn, json.loads(Path(args.score).read_text()))}, indent=2)); return 0
        if args.cmd == "rank":
            print(json.dumps(ranking(conn, limit=args.limit), indent=2, ensure_ascii=False)); return 0
        print(json.dumps({"count": count(conn)}, indent=2)); return 0
    except Exception as exc:
        print(json.dumps({"schema": "die.division001.longtail-registry-run.v1", "status": "FAIL", "error": str(exc)}, indent=2)); return 2
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())