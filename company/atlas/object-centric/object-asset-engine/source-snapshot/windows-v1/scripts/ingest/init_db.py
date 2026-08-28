"""OPCODE-000/TASK-001 — Initialize Object Asset Engine SQLite schema.

Schema source: Qwen Object-Centric Design Framework §17
Location: D:\object-asset-engine\db\object_asset_engine.db
"""
import sqlite3
import pathlib

DB_PATH = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS seeds (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    aliases TEXT,
    object_class TEXT,
    existence_type TEXT,
    category_path TEXT,
    visuality_score REAL,
    demand_score REAL,
    risk_score REAL,
    status TEXT NOT NULL DEFAULT 'review',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS longtails (
    id TEXT PRIMARY KEY,
    seed_id TEXT NOT NULL REFERENCES seeds(id),
    phrase TEXT NOT NULL,
    canonical_phrase TEXT NOT NULL,
    modifier_types TEXT,
    demand_score REAL,
    similarity_max REAL,
    status TEXT NOT NULL DEFAULT 'review',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(seed_id, canonical_phrase)
);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    longtail_id TEXT NOT NULL REFERENCES longtails(id),
    object_name TEXT NOT NULL,
    visual_style TEXT,
    composition TEXT,
    background TEXT,
    color_palette TEXT,
    material TEXT,
    mood TEXT,
    target_use_case TEXT,
    target_platform TEXT,
    format_output TEXT,
    variations TEXT,
    negative_constraints TEXT,
    metadata_keywords TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES concepts(id),
    file_path TEXT NOT NULL,
    format TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    megapixels REAL,
    color_mode TEXT,
    sha256 TEXT,
    qc_status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    keywords TEXT,
    category TEXT,
    license_type TEXT,
    publish_date TEXT,
    status TEXT NOT NULL DEFAULT 'ready_to_publish',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(asset_id, platform)
);

CREATE TABLE IF NOT EXISTS revenue_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_id TEXT NOT NULL REFERENCES publications(id),
    event_date TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,
    downloads INTEGER DEFAULT 0,
    sales INTEGER DEFAULT 0,
    revenue_usd REAL DEFAULT 0.0,
    conversion_rate REAL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT UNIQUE,
    phase TEXT,
    summary TEXT NOT NULL,
    rationale TEXT,
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_longtails_seed ON longtails(seed_id);
CREATE INDEX IF NOT EXISTS idx_concepts_longtail ON concepts(longtail_id);
CREATE INDEX IF NOT EXISTS idx_assets_concept ON assets(concept_id);
CREATE INDEX IF NOT EXISTS idx_pubs_asset ON publications(asset_id);
CREATE INDEX IF NOT EXISTS idx_revenue_pub ON revenue_events(publication_id);
"""


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        print(f"DB_OK {DB_PATH}")
        print("tables:", ",".join(tables))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
