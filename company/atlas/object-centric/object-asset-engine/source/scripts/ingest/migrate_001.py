
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-001 — Schema migration + path/config alignment.

Adds columns per Qwen framework lock-in:
  canonical_lang, asset_tier, source_batch, master_source_id, demand_signal
Backfills existing MASTER-13 rows. Idempotent.
"""
import json
import sqlite3
import pathlib

DB = engine_paths.CANON_DB
CONFIG = engine_paths.CONFIG_FILE

NEW_COLS = {
    "canonical_lang": "TEXT DEFAULT 'en-US'",
    "asset_tier": "TEXT DEFAULT 'U1-raster'",
    "source_batch": "TEXT",
    "master_source_id": "TEXT",
    "demand_signal": "TEXT",
}

CONFIG_DATA = {
    "db_path": str(engine_paths.CANON_DB),
    "asset_tier_current": "U1-raster",
    "canonical_lang": "en-US",
    "validation_batch_target": 100,
    "batches": {
        "MASTER-13": {"count": 20, "id_range": "SEED-000001..SEED-000020"},
        "QWEN-DEMAND-20": {"count": 20, "id_range": "SEED-000021..SEED-000040"},
        "WIKTIONARY-60": {"count": 60, "id_range": "SEED-000041..SEED-000100"},
    },
}


def main() -> None:
    conn = sqlite3.connect(DB)
    try:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(seeds)")}
        for col, decl in NEW_COLS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE seeds ADD COLUMN {col} {decl}")
                print(f"added column: {col}")
        conn.execute(
            """UPDATE seeds SET source_batch='MASTER-13', asset_tier='U1-raster',
               canonical_lang='en-US'
               WHERE source_batch IS NULL AND id LIKE 'SEED-%'"""
        )
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) FROM seeds WHERE source_batch='MASTER-13'"
        ).fetchone()[0]
        print(f"backfilled MASTER-13 rows: {n}")
    finally:
        conn.close()
    CONFIG.write_text(json.dumps(CONFIG_DATA, indent=2), encoding="utf-8")
    print(f"config written: {CONFIG}")


if __name__ == "__main__":
    main()
