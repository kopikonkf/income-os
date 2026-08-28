"""OPCODE-009 TASK-011 — Kaikki.org English JSONL -> raw_nouns (STREAMING).

Rules (per Qwen spec):
- Stream line-by-line (never load whole file into RAM)
- Keep entries with pos == 'noun'
- Extract word, senses count, categories, wikidata_id
- BATCH INSERT every 10,000 rows inside one transaction
- INSERT OR IGNORE for duplicate safety
- Progress print every 50,000 lines

Usage:
  python kaikki_noun_ingest.py            # full file
  python kaikki_noun_ingest.py --limit N  # dry-run first N lines
"""
import json
import sqlite3
import sys
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
SRC = pathlib.Path(r"D:\object-asset-engine\data\raw\enwiktionary_dump.jsonl")
BATCH = 10_000
PROGRESS_EVERY = 50_000


def main() -> None:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    conn = sqlite3.connect(DB)
    try:
        total = seen = kept = dup_skipped = 0
        batch = []
        t0 = datetime.now(timezone.utc)

        def flush():
            nonlocal kept
            if not batch:
                return
            conn.executemany(
                """INSERT OR IGNORE INTO raw_nouns
                   (word, pos_tag, language, senses_count, categories, wikidata_id, status)
                   VALUES (?, 'noun', 'en', ?, ?, ?, 'unprocessed')""",
                batch,
            )
            kept += conn.total_changes and len(batch)  # approximate; verified by COUNT
            conn.commit()
            batch.clear()

        with open(SRC, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total += 1
                if limit and total > limit:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("pos") != "noun":
                    continue
                word = obj.get("word")
                if not word or ":" in word or " " not in word and len(word) < 2:
                    if not word:
                        continue
                senses = obj.get("senses") or []
                # categories live inside senses[].categories (Kaikki structure)
                cats = []
                wikidata = obj.get("wikidata")
                for s in senses:
                    for c in s.get("categories") or []:
                        name = c.get("name") if isinstance(c, dict) else c
                        if name and name not in cats:
                            cats.append(name)
                    if not wikidata and s.get("wikidata"):
                        wd = s["wikidata"]
                        wikidata = wd if isinstance(wd, str) else json.dumps(wd)[:200]
                batch.append((
                    word,
                    len(senses),
                    json.dumps(cats)[:4000],
                    wikidata,
                ))
                seen += 1
                if len(batch) >= BATCH:
                    flush()
                if total % PROGRESS_EVERY == 0:
                    in_db = conn.execute("SELECT COUNT(*) FROM raw_nouns").fetchone()[0]
                    print(f"progress lines={total} noun_seen={seen} in_db={in_db} "
                          f"elapsed={(datetime.now(timezone.utc)-t0).seconds}s", flush=True)
        flush()

        in_db = conn.execute("SELECT COUNT(*) FROM raw_nouns").fetchone()[0]
        print(f"DONE lines={total} noun_entries_seen={seen} raw_nouns_in_db={in_db} "
              f"elapsed={(datetime.now(timezone.utc)-t0).seconds}s")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
