
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-010 — Diagnostic queries (Part A) + candidate_seeds/filter_log schema (Part B)."""
import json
import sqlite3
import pathlib

DB = engine_paths.CANON_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidate_seeds (
    id TEXT PRIMARY KEY,
    raw_noun_id INTEGER NOT NULL,
    canonical_name TEXT NOT NULL,
    aliases TEXT DEFAULT '[]',
    word_count INTEGER DEFAULT 1,
    senses_count INTEGER DEFAULT 0,
    category_path TEXT,
    wiktionary_categories TEXT DEFAULT '[]',

    wave1_status TEXT DEFAULT 'pending',
    wave1_reject_reason TEXT,

    wave2_status TEXT DEFAULT 'pending',
    concreteness_score REAL DEFAULT 0,
    wordnet_synsets TEXT DEFAULT '[]',

    wave3_status TEXT DEFAULT 'pending',
    visual_score REAL DEFAULT 0,
    commercial_score REAL DEFAULT 0,
    ip_risk TEXT DEFAULT 'none',

    object_class TEXT DEFAULT 'unknown',
    existence_type TEXT DEFAULT 'unknown',
    status TEXT DEFAULT 'pending',
    promoted_to_seed_id TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_noun_id) REFERENCES raw_nouns(id)
);
CREATE INDEX IF NOT EXISTS idx_candidate_wave1 ON candidate_seeds(wave1_status);
CREATE INDEX IF NOT EXISTS idx_candidate_wave2 ON candidate_seeds(wave2_status);
CREATE INDEX IF NOT EXISTS idx_candidate_status ON candidate_seeds(status);
CREATE INDEX IF NOT EXISTS idx_candidate_name ON candidate_seeds(canonical_name);

CREATE TABLE IF NOT EXISTS filter_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_noun_id INTEGER NOT NULL,
    filter_wave TEXT NOT NULL,
    filter_rule TEXT NOT NULL,
    result TEXT NOT NULL,
    detail TEXT,
    logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_noun_id) REFERENCES raw_nouns(id)
);
CREATE INDEX IF NOT EXISTS idx_filter_log_noun ON filter_log(raw_noun_id);
CREATE INDEX IF NOT EXISTS idx_filter_log_rule ON filter_log(filter_rule);
"""


def diagnostics(conn) -> dict:
    out = {}
    out["q1_total"] = conn.execute("SELECT COUNT(*) FROM raw_nouns").fetchone()[0]
    out["q2_with_categories"] = conn.execute(
        "SELECT COUNT(*) FROM raw_nouns WHERE categories IS NOT NULL AND categories != '[]'"
    ).fetchone()[0]
    out["q3_top30_categories"] = conn.execute(
        """SELECT categories, COUNT(*) as cnt FROM raw_nouns
           WHERE categories IS NOT NULL AND categories != '[]'
           GROUP BY categories ORDER BY cnt DESC LIMIT 30"""
    ).fetchall()
    out["q4_distribution"] = conn.execute(
        """SELECT COUNT(*) as total,
             SUM(CASE WHEN LENGTH(word) < 3 THEN 1 ELSE 0 END) as len_lt3,
             SUM(CASE WHEN LENGTH(word) > 60 THEN 1 ELSE 0 END) as len_gt60,
             SUM(CASE WHEN LENGTH(word) - LENGTH(REPLACE(word, ' ', '')) >= 5 THEN 1 ELSE 0 END) as words_gt5,
             SUM(CASE WHEN senses_count = 1 THEN 1 ELSE 0 END) as single_sense,
             SUM(CASE WHEN senses_count >= 3 THEN 1 ELSE 0 END) as multi_sense
           FROM raw_nouns"""
    ).fetchone()
    out["q5_random50"] = [
        r[0] for r in conn.execute("SELECT word FROM raw_nouns ORDER BY RANDOM() LIMIT 50")
    ]
    return out


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        print("SCHEMA_OK: candidate_seeds + filter_log created")

        d = diagnostics(conn)
        print(f"\nQ1 total raw_nouns: {d['q1_total']}")
        print(f"Q2 with categories: {d['q2_with_categories']}")
        print("\nQ3 top-30 category clusters (raw JSON strings):")
        for r in d["q3_top30_categories"]:
            print(f"  {r['cnt']:>7} | {str(r['categories'])[:110]}")
        q4 = d["q4_distribution"]
        print(f"\nQ4 distribution: total={q4['total']} len<3={q4['len_lt3']} "
              f"len>60={q4['len_gt60']} words>=5={q4['words_gt5']} "
              f"single_sense={q4['single_sense']} multi_sense={q4['multi_sense']}")
        print(f"\nQ5 random 50:")
        print(json.dumps(d["q5_random50"], ensure_ascii=False))

        # bonus: how many categories contain useful concrete keywords
        for kw in ["tool", "vehicle", "furniture", "container", "clothing", "weapon", "musical"]:
            n = conn.execute(
                "SELECT COUNT(*) FROM raw_nouns WHERE categories LIKE ?",
                (f"%{kw}%",),
            ).findone() if False else conn.execute(
                "SELECT COUNT(*) FROM raw_nouns WHERE categories LIKE ?", (f"%{kw}%",)
            ).fetchone()[0]
            print(f"bonus category-like '{kw}': {n}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
