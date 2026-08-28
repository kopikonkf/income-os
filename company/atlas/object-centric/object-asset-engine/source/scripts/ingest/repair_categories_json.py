
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""Repair truncated categories JSON ([:4000] cut mid-element)."""
import json
import sqlite3

conn = sqlite3.connect(str(engine_paths.CANON_DB))
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
