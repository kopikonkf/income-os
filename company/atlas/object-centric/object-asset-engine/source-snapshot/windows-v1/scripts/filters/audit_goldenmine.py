import json
import random
import re
import sqlite3

conn = sqlite3.connect(r"D:\object-asset-engine\db\object_asset_engine.db")
conn.row_factory = sqlite3.Row
random.seed(7)

# Bucket 1: H4 rejects (capitalized) — cari common-noun gems yang tertolak
print("=== BUCKET 1: H4_ASCII_ONLY rejects (97,557) — sample 40 ===")
rows = conn.execute(
    """SELECT f.detail FROM filter_log f WHERE f.filter_rule='H4_ASCII_ONLY'
       AND f.result='reject' ORDER BY RANDOM() LIMIT 40"""
).fetchall()
print(" | ".join(r["detail"] for r in rows))

# Cek spesifik: breed hewan & kata demand-tinggi yang kapital
print("\n-- cek gem spesifik di H4 --")
for w in ["german shepherd", "persian cat", "siamese cat", "labrador retriever",
          "french bulldog", "christmas tree", "mandarin", "turkish towel",
          "english saddle", "scotch egg"]:
    r = conn.execute(
        """SELECT f.filter_rule, f.result FROM filter_log f
           JOIN candidate_seeds c ON c.raw_noun_id=f.raw_noun_id
           WHERE c.canonical_name=? LIMIT 1""", (w,)
    ).fetchone()
    in_seeds = conn.execute(
        "SELECT wave3_status FROM candidate_seeds WHERE canonical_name=?", (w,)
    ).fetchone()
    print(f"  {w}: log={tuple(r) if r else 'NOT_IN_CANDIDATES'} seed_now={in_seeds}")

# Bucket 2: Wave 2 'not_in_wordnet' rejects — berapa & apa isinya
print("\n=== BUCKET 2: Wave2v3 not_in_wordnet ===")
n = conn.execute(
    """SELECT COUNT(*) FROM filter_log WHERE filter_wave='wave2v3'
       AND detail LIKE '%not_in_wordnet%'"""
).fetchone()[0]
print(f"total not_in_wordnet: {n}")
rows = conn.execute(
    """SELECT detail FROM filter_log WHERE filter_wave='wave2v3'
       AND detail LIKE '%not_in_wordnet%' ORDER BY RANDOM() LIMIT 50"""
).fetchall()
words = [r["detail"].split(":")[0] for r in rows]
print("sample 50:", " | ".join(words))

# Bucket 3: H5 start-char (angka)
print("\n=== BUCKET 3: H5_START_CHAR (digit-leading, 1,339) ===")
rows = conn.execute(
    """SELECT detail FROM filter_log WHERE filter_rule='H5_START_CHAR'
       ORDER BY RANDOM() LIMIT 30"""
).fetchall()
print(" | ".join(r["detail"] for r in rows))
