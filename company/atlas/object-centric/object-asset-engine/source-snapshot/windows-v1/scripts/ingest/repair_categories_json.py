"""Repair truncated categories JSON ([:4000] cut mid-element)."""
import json
import sqlite3

conn = sqlite3.connect(r"D:\object-asset-engine\db\object_asset_engine.db")
rows = conn.execute("SELECT id, categories FROM raw_nouns WHERE categories != '[]'").fetchall()
fixed = 0
for rid, cats in rows:
    try:
        json.loads(cats)
        continue
    except json.JSONDecodeError:
        pass
    # trim to last complete element boundary
    repaired = None
    for cut in (3990, 3980, 3950, 3900, 3800, 3600, 3400, 3000, 2000, 1000):
        s = cats[:cut]
        if s.endswith("]") and s.startswith("["):
            try:
                json.loads(s)
                repaired = s
                break
            except json.JSONDecodeError:
                pass
        if "}," in s:
            s2 = s[: s.rfind("}") + 1] + "]"
            try:
                json.loads(s2)
                repaired = s2
                break
            except json.JSONDecodeError:
                continue
    if repaired is None:
        repaired = "[]"
    conn.execute("UPDATE raw_nouns SET categories=? WHERE id=?", (repaired, rid))
    fixed += 1
conn.commit()
print(f"repaired={fixed}")
