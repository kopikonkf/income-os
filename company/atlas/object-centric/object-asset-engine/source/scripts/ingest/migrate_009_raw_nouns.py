
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-009 TASK-010 — raw_nouns table (Layer 1: Raw data lake)."""
import sqlite3
import pathlib

DB = engine_paths.CANON_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_nouns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    pos_tag TEXT DEFAULT 'noun',
    language TEXT DEFAULT 'en',
    senses_count INTEGER DEFAULT 0,
    categories TEXT,
    wikidata_id TEXT,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'unprocessed'
);
CREATE INDEX IF NOT EXISTS idx_raw_nouns_status ON raw_nouns(status);
CREATE INDEX IF NOT EXISTS idx_raw_nouns_word ON raw_nouns(word);
"""

conn = sqlite3.connect(DB)
try:
    conn.executescript(SCHEMA)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM raw_nouns").fetchone()[0]
    print(f"raw_nouns ready, rows={n}")
finally:
    conn.close()
