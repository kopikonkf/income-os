"""OPCODE-009 TASK-010 — raw_nouns table (Layer 1: Raw data lake)."""
import sqlite3
import pathlib

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")

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
