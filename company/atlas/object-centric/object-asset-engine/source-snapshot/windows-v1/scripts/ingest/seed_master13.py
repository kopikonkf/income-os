"""TASK-006 (partial) — Seed registry with 20 MASTER-13 pre-approved nouns.

Source of truth: C:\DIE\workspaces\M001-U1-001\ASSET_BLUEPRINT.json
These enter as status='approved' per D-006 (founder-ratified blueprint).
IDs follow SEED-NNNNNN format.
"""
import json
import sqlite3
import datetime
import pathlib

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
BP = pathlib.Path(r"C:\DIE\workspaces\M001-U1-001\ASSET_BLUEPRINT.json")

CATEGORY_MAP = {
    "Food & drink": "kitchen_utensils.food_drink",
    "Botanical & floral": "nature.botanical_floral",
    "Household & decor": "household.decor",
    "Education & simple symbols": "education.symbols",
    "Travel & nature objects": "travel.nature_objects",
    "Everyday tools & accessories": "tools.everyday_accessories",
}


def main() -> None:
    bp = json.loads(BP.read_text(encoding="utf-8"))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    try:
        n = 0
        for i, v in enumerate(bp["production"]["semantic_variation_plan"], start=1):
            seed_id = f"SEED-{i:06d}"
            obj = v["object"]
            cat = CATEGORY_MAP.get(v["territory"], "misc.unsorted")
            conn.execute(
                """INSERT INTO seeds
                   (id, canonical_name, aliases, object_class, existence_type,
                    category_path, visuality_score, demand_score, risk_score,
                    status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO NOTHING""",
                (
                    seed_id,
                    obj,
                    "",
                    "concrete_visual",
                    "real_world",
                    cat,
                    0.8,
                    None,
                    0.0,
                    "approved",
                    now,
                    now,
                ),
            )
            n += 1
        conn.commit()
        rows = conn.execute(
            "SELECT id, canonical_name, category_path, status FROM seeds ORDER BY id"
        ).fetchall()
        print(f"seeded={n} total_in_db={len(rows)}")
        for r in rows:
            print(" | ".join(str(x) for x in r))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
