"""TASK-002 — Apply seed filtering rules (FILTER_RULES.md) to review seeds.

Idempotent: only touches status='review' (and 'merged' bookkeeping).
Writes audit report to data/processed/filter_report_TASK002.json.
"""
import json
import re
import sqlite3
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
REPORT = pathlib.Path(r"D:\object-asset-engine\data\processed\filter_report_TASK002.json")

# R3 — explicit non-commercial / obscure lexicon (auditable)
REJECT_LEXICON = {
    "ashet",          # Scottish dialect plate
    "ard",            # archaic plow
    "athanor",        # alchemical furnace
    "chakla",         # regional rolling board
    "banker",         # obscure stationery desk-slope term; collides with finance noun
    "gregg ruled",    # adjective (paper ruling style)
    "letter size",    # adjective (paper size)
    "assistive technology",  # concept category, not an object
    "alligator shear",       # industrial machine, no design-asset use case
    "china",                 # material/mass noun, no object boundary
}

ADJECTIVAL_SUFFIXES = ("size", "ruled", "shaped", "type")

SYNONYM_MERGES = {
    "allen wrench": "allen key",
}


def normalize(name: str) -> str:
    t = name.lower().strip()
    t = re.sub(r"[-_]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def is_adjectival(t: str) -> bool:
    return any(t.endswith(" " + s) or t.endswith("-" + s) for s in ADJECTIVAL_SUFFIXES)


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, canonical_name FROM seeds WHERE status='review' ORDER BY id"
        ).fetchall()
        actions = []
        approved: dict[str, str] = {}  # normalized_name -> seed_id

        for r in rows:
            sid, orig = r["id"], r["canonical_name"]
            norm = normalize(orig)

            if norm != orig:
                conn.execute(
                    "UPDATE seeds SET canonical_name=?, updated_at=? WHERE id=?",
                    (norm, now, sid),
                )

            if norm in REJECT_LEXICON:
                conn.execute(
                    "UPDATE seeds SET status='rejected', updated_at=? WHERE id=?",
                    (now, sid),
                )
                actions.append({"id": sid, "name": norm, "action": "rejected", "reason": "R3 lexicon"})
                continue
            if is_adjectival(norm):
                conn.execute(
                    "UPDATE seeds SET status='rejected', updated_at=? WHERE id=?",
                    (now, sid),
                )
                actions.append({"id": sid, "name": norm, "action": "rejected", "reason": "R2 adjectival"})
                continue
            if norm in SYNONYM_MERGES and SYNONYM_MERGES[norm] in approved:
                survivor = approved[SYNONYM_MERGES[norm]]
                conn.execute(
                    "UPDATE seeds SET status='merged', updated_at=? WHERE id=?",
                    (now, sid),
                )
                actions.append(
                    {"id": sid, "name": norm, "action": "merged", "reason": f"R5 synonym of {survivor}"}
                )
                continue

            # R5 near-duplicate vs already-approved this run
            dup = next((s for n, s in approved.items() if jaccard(norm, n) >= 0.90), None)
            if dup:
                conn.execute(
                    "UPDATE seeds SET status='merged', updated_at=? WHERE id=?",
                    (now, sid),
                )
                actions.append({"id": sid, "name": norm, "action": "merged", "reason": f"R5 jaccard>=0.90 of {dup}"})
                continue

            conn.execute(
                "UPDATE seeds SET status='approved', updated_at=? WHERE id=?",
                (now, sid),
            )
            approved[norm] = sid
            actions.append({"id": sid, "name": norm, "action": "approved", "reason": "pass all filters"})

        conn.commit()
        summary = conn.execute(
            "SELECT status, COUNT(*) FROM seeds GROUP BY status ORDER BY status"
        ).fetchall()

        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            json.dumps(
                {
                    "task": "TASK-002",
                    "run_at": now,
                    "rules": "state/FILTER_RULES.md v0",
                    "reviewed": len(rows),
                    "actions": actions,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"reviewed={len(rows)}")
        for s, n in summary:
            print(f"  {s}: {n}")
        rej = [a for a in actions if a["action"] == "rejected"]
        mer = [a for a in actions if a["action"] == "merged"]
        print(f"rejected={len(rej)} merged={len(mer)}")
        for a in rej + mer:
            print(f"  {a['id']} {a['name']} -> {a['action']} ({a['reason']})")
        print(f"report saved: {REPORT}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
