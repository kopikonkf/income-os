"""OPCODE-005 — Ingest Concept Batch 01 with longtail_id resolution.

- Reads outputs/concepts/batch_01_concepts.json
- Resolves longtail_id via JOIN:
    longtails.canonical_phrase = longtail_phrase
    AND longtails.seed_id = seeds.id WHERE seeds.canonical_name = seed_canonical
- Unresolved phrases -> reports/concept_reconcile_gaps.log, NOT inserted
- UPSERT into concepts (idempotent by concept_id), status ready_for_production
"""
import json
import sqlite3
import sys
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
SRC = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1
    else r"D:\object-asset-engine\outputs\concepts\batch_01_concepts.json"
)
GAPLOG = pathlib.Path(r"D:\object-asset-engine\reports\concept_reconcile_gaps.log")


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = json.loads(pathlib.Path(SRC).read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        inserted = gaps = 0
        gap_lines = []
        for c in data:
            lt_id = c.get("longtail_id")
            if not lt_id:  # resolve via JOIN when not hard-coded
                row = conn.execute(
                    """SELECT l.id FROM longtails l
                       JOIN seeds s ON s.id = l.seed_id
                       WHERE s.canonical_name = ? AND l.canonical_phrase = ?""",
                    (c["seed_canonical"], c["longtail_phrase"]),
                ).fetchone()
                if not row:
                    gaps += 1
                    gap_lines.append(
                        f"{now} | GAP | {c['concept_id']} | seed='{c['seed_canonical']}' "
                        f"phrase='{c['longtail_phrase']}' — no exact match in longtails"
                    )
                    continue
                lt_id = row["id"]
            else:  # hard-coded id: verify it exists (fail-closed)
                chk = conn.execute(
                    "SELECT 1 FROM longtails WHERE id=?", (lt_id,)
                ).fetchone()
                if not chk:
                    gaps += 1
                    gap_lines.append(
                        f"{now} | GAP | {c['concept_id']} | hard-coded '{lt_id}' "
                        f"NOT FOUND in longtails — skipped fail-closed"
                    )
                    continue
            conn.execute(
                """INSERT INTO concepts
                   (id, longtail_id, object_name, visual_style, composition,
                    background, color_palette, material, mood, target_use_case,
                    target_platform, format_output, variations,
                    negative_constraints, metadata_keywords, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     longtail_id=excluded.longtail_id,
                     object_name=excluded.object_name,
                     visual_style=excluded.visual_style,
                     composition=excluded.composition,
                     background=excluded.background,
                     color_palette=excluded.color_palette,
                     material=excluded.material,
                     mood=excluded.mood,
                     target_use_case=excluded.target_use_case,
                     format_output=excluded.format_output,
                     variations=excluded.variations,
                     negative_constraints=excluded.negative_constraints,
                     metadata_keywords=excluded.metadata_keywords,
                     status=excluded.status,
                     updated_at=excluded.updated_at""",
                (
                    c["concept_id"],
                    lt_id,
                    c["longtail_phrase"],
                    c.get("visual_style"),
                    c.get("composition"),
                    c.get("background"),
                    json.dumps(c.get("color_palette", [])),
                    c.get("material"),
                    c.get("mood"),
                    json.dumps(c.get("target_use_case", [])),
                    "tier1_marketplaces",
                    json.dumps(c.get("format_output", [])),
                    json.dumps(c.get("variations", [])),
                    json.dumps(c.get("negative_constraints", [])),
                    json.dumps({
                        "matrix_trace": c.get("matrix_trace"),
                        "image_gen_prompt_v0": c.get("image_gen_prompt_v0"),
                        "production_note": c.get("production_note"),
                        "keyword_stack": c.get("keyword_stack", []),
                    }),
                    "ready_for_production",
                    now,
                    now,
                ),
            )
            inserted += 1
        conn.commit()

        GAPLOG.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if GAPLOG.exists() else "w"
        with open(GAPLOG, mode, encoding="utf-8") as f:
            f.write("\n".join(gap_lines) + ("\n" if gap_lines else ""))

        total_rfp = conn.execute(
            "SELECT COUNT(*) FROM concepts WHERE status='ready_for_production'"
        ).fetchone()[0]
        print(f"in_file={len(data)} inserted={inserted} gaps={gaps} ready_for_production_in_db={total_rfp}")
        for r in conn.execute(
            """SELECT c.id, c.object_name, c.status, l.id AS lt
               FROM concepts c JOIN longtails l ON l.id = c.longtail_id
               WHERE c.status='ready_for_production' LIMIT 2"""
        ):
            print("sample:", r["id"], "|", r["object_name"], "|", r["status"], "|", r["lt"])
        if gap_lines:
            print("--- GAPS ---")
            print("\n".join(gap_lines))
        print(f"gaplog: {GAPLOG}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
