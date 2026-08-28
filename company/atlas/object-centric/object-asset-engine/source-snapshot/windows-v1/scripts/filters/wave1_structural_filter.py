"""OPCODE-011 — Wave 1 Structural Filter (H1-H8 + soft scoring S1-S3).

Spec: Qwen Nouns_Generator2.md answer A (unchanged per verdict Nouns_Generator3).
- first-match-reject, filter_log audit per rule
- passes -> candidate_seeds (wave1_status='pass', wave1_soft_score)
- raw_nouns.status -> 'wave1_processed'
- INSERT OR IGNORE idempotent, commit per 50k, progress per 100k
"""
import json
import re
import sqlite3
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
BATCH = 50_000

H7_BLACKLIST = {
    "the", "a", "an", "it", "this", "that", "one", "none",
    "thing", "stuff", "item", "object", "entity", "something",
    "anything", "nothing", "everything", "what", "which", "who",
}
S3_SUFFIXES = (
    "er", "or", "ware", "piece", "let", "ette", "ling", "stone",
    "box", "bag", "cup", "pot", "pan", "tin", "jar", "rack", "stand",
    "board", "blade", "wheel", "handle", "grip", "hook", "ring",
)
ALLOWED_CHARS = re.compile(r"[^a-z0-9\s\-'/]")


def classify(word: str, senses: int):
    """Return (reject_rule|None, soft_score)."""
    if len(word) < 3:
        return "H1_MIN_LENGTH", 0
    if len(word) > 50:
        return "H2_MAX_LENGTH", 0
    wc = len(word.split(" "))
    if wc > 4:
        return "H3_MAX_WORD_COUNT", 0
    if ALLOWED_CHARS.search(word):
        return "H4_ASCII_ONLY", 0
    if not word or not ("a" <= word[0] <= "z"):
        return "H5_START_CHAR", 0
    if re.fullmatch(r"[0-9a-z]*[0-9][0-9a-z]*", word) and " " not in word:
        return "H6_PURE_NUMERIC", 0
    if word in H7_BLACKLIST:
        return "H7_BLACKLIST_EXACT", 0
    if senses == 1 and len(word) > 25:
        return "H8_OBSCURE_SINGLE_SENSE", 0
    # soft scoring S1-S3
    s1 = 2 if wc == 1 else (1 if wc == 2 else 0)
    s2 = 2 if senses >= 3 else (1 if senses == 2 else 0)
    s3 = 1 if any(word.endswith(sfx) for sfx in S3_SUFFIXES) else 0
    return None, s1 + s2 + s3


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_seeds)")}
        if "wave1_soft_score" not in cols:
            conn.execute("ALTER TABLE candidate_seeds ADD COLUMN wave1_soft_score REAL")
        if "wave1_checked_at" not in cols:
            conn.execute("ALTER TABLE candidate_seeds ADD COLUMN wave1_checked_at TEXT")

        t0 = datetime.now(timezone.utc)
        reject_counts = {}
        passed = 0
        processed = 0
        while True:
            rows = conn.execute(
                "SELECT id, word, senses_count, categories FROM raw_nouns "
                "WHERE status='unprocessed' LIMIT ?",
                (BATCH,),
            ).fetchall()
            if not rows:
                break
            cand_batch, log_batch = [], []
            for rid, word, senses, cats in rows:
                processed += 1
                rule, soft = classify(word, senses)
                if rule:
                    reject_counts[rule] = reject_counts.get(rule, 0) + 1
                    log_batch.append((rid, "wave1", rule, "reject", word))
                else:
                    cand_batch.append((
                        f"CAND-{rid:07d}", rid, word, len(word.split(" ")),
                        senses, cats, "pass", None, soft, now,
                    ))
                    log_batch.append((rid, "wave1", "ALL_PASS", "pass", word))
                    passed += 1
            conn.executemany(
                """INSERT OR IGNORE INTO candidate_seeds
                   (id, raw_noun_id, canonical_name, word_count, senses_count,
                    wiktionary_categories, wave1_status, wave1_reject_reason,
                    wave1_soft_score, wave1_checked_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                cand_batch,
            )
            conn.executemany(
                """INSERT INTO filter_log (raw_noun_id, filter_wave, filter_rule, result, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                log_batch,
            )
            conn.execute(
                "UPDATE raw_nouns SET status='wave1_processed' "
                "WHERE status='unprocessed' AND id IN (%s)"
                % ",".join(str(r[0]) for r in rows)
            )
            conn.commit()
            if processed // 100_000 != (processed - len(rows)) // 100_000:
                print(f"progress processed={processed} passed={passed} "
                      f"elapsed={(datetime.now(timezone.utc)-t0).seconds}s", flush=True)

        elapsed = (datetime.now(timezone.utc) - t0).seconds
        print(f"DONE processed={processed} passed={passed} elapsed={elapsed}s")
        print("reject breakdown:")
        for k, v in sorted(reject_counts.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

        print("\n-- candidate_seeds status --")
        for r in conn.execute(
            "SELECT wave1_status, COUNT(*) FROM candidate_seeds GROUP BY wave1_status"
        ):
            print(f"  {r[0]}: {r[1]}")
        print("\n-- filter_log rejects --")
        for r in conn.execute(
            """SELECT filter_rule, COUNT(*) FROM filter_log
               WHERE result='reject' GROUP BY filter_rule ORDER BY 2 DESC"""
        ):
            print(f"  {r[0]}: {r[1]}")
        print("\n-- sample 20 rejected --")
        for r in conn.execute(
            """SELECT f.detail, f.filter_rule FROM filter_log f
               WHERE f.result='reject' ORDER BY RANDOM() LIMIT 20"""
        ):
            print(f"  {r[0]} ({r[1]})")
        print("\n-- sample 20 passed --")
        for r in conn.execute(
            "SELECT canonical_name, wave1_soft_score FROM candidate_seeds "
            "ORDER BY RANDOM() LIMIT 20"
        ):
            print(f"  {r[0]} (soft={r[1]})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
