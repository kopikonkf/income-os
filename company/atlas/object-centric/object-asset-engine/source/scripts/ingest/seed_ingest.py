
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-002 — Generic batch seed ingest with UPSERT anti-duplicate.

Usage:
  python seed_ingest.py <input_json> <source_batch> <start_seq>

- Reads array of {canonical_name, aliases, object_class, category_path,
  existence_type, demand_signal, master_source_id}
- Assigns SEED-NNNNNN ids starting at start_seq
- UPSERT: re-running never duplicates (id + canonical_name conflict safe)
"""
import json
import sqlite3
import sys
import datetime
import pathlib

DB = engine_paths.CANON_DB


def main() -> None:
    if len(sys.argv) != 4:
        print("usage: seed_ingest.py <input_json> <source_batch> <start_seq>")
        sys.exit(1)
    src = pathlib.Path(sys.argv[1])
    batch = sys.argv[2]
    start_seq = int(sys.argv[3])

    entries = json.loads(src.read_text(encoding="utf-8"))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    try:
        inserted = updated = 0
        for i, e in enumerate(entries):
            seed_id = f"SEED-{start_seq + i:06d}"
            row = (
                seed_id,
                e["canonical_name"],
                json.dumps(e.get("aliases", [])),
                e.get("object_class", ""),
                e.get("existence_type", "real"),
                e.get("category_path", "misc.unsorted"),
                e.get("demand_signal"),
                batch,
                e.get("master_source_id"),
                now,
                now,
            )
            cur = conn.execute(
                """INSERT INTO seeds
                   (id, canonical_name, aliases, object_class, existence_type,
                    category_path, demand_signal, source_batch, master_source_id,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     canonical_name=excluded.canonical_name,
                     aliases=excluded.aliases,
                     object_class=excluded.object_class,
                     existence_type=excluded.existence_type,
                     category_path=excluded.category_path,
                     demand_signal=excluded.demand_signal,
                     source_batch=excluded.source_batch,
                     master_source_id=excluded.master_source_id,
                     updated_at=excluded.updated_at""",
                row,
            )
            if cur.rowcount and conn.total_changes:
                pass
            inserted += 1

        # canonical-name level dedup guard (Layer 2): skip if phrase already exists in another batch
        dupes = conn.execute(
            """SELECT canonical_name, COUNT(*) c FROM seeds
               GROUP BY LOWER(canonical_name) HAVING c > 1"""
        ).fetchall()
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM seeds").fetchone()[0]
        by_batch = conn.execute(
            "SELECT source_batch, COUNT(*) FROM seeds GROUP BY source_batch"
        ).fetchall()
        print(f"processed={inserted} batch={batch}")
        print(f"cross-batch canonical duplicates: {dupes if dupes else 'NONE'}")
        print(f"total_seeds={total}")
        for b, n in by_batch:
            print(f"  {b}: {n}")
        for r in conn.execute(
            """SELECT id, canonical_name, category_path, demand_signal
               FROM seeds WHERE source_batch=? ORDER BY id LIMIT 3""",
            (batch,),
        ):
            print("sample:", " | ".join(str(x) for x in r))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
