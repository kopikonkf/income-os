
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""OPCODE-004 — Concept Generation Pipeline Shell.

Maps every approved longtail to the concepts table + emits
outputs/concepts/batch_01_concepts_shell.json for AI Web Chat (Qwen)
to fill as Concept Producer.

Shell fields left null/empty per QWEN CONCEPT PROTOCOL; background,
format_output and negative_constraints pre-filled per U1 raster-only rules.
Idempotent via UNIQUE(id) upsert.
"""
import json
import sqlite3
import pathlib
from datetime import datetime, timezone

DB = engine_paths.CANON_DB
OUT = engine_paths.OUTPUTS_DIR / "concepts" / "batch_01_concepts_shell.json"

FORMAT_OUTPUT = ["PNG transparent (master)", "JPG white (derivative)"]
NEGATIVE_CONSTRAINTS = [
    "no text",
    "no watermark",
    "no brand logo",
    "no human hands",
]


def lt_to_concept_id(lt_id: str) -> str:
    """LT-SEED-000021-0007 -> CON-SEED-000021-0007-0001"""
    return f"{lt_id.replace('LT-', 'CON-', 1)}-0001"


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        longtails = conn.execute(
            """SELECT l.id AS lt_id, l.seed_id, l.canonical_phrase
               FROM longtails l WHERE l.status='approved' ORDER BY l.id"""
        ).fetchall()

        shells = []
        for lt in longtails:
            cid = lt_to_concept_id(lt["lt_id"])
            shell = {
                "concept_id": cid,
                "longtail_id": lt["lt_id"],
                "seed_id": lt["seed_id"],
                "keyword": lt["canonical_phrase"],
                "visual_style": None,
                "composition": None,
                "background": "isolated / white / transparent",
                "color_palette": [],
                "material": None,
                "mood": None,
                "target_use_case": [],
                "format_output": FORMAT_OUTPUT,
                "variations": [],
                "negative_constraints": list(NEGATIVE_CONSTRAINTS),
                "image_gen_prompt_v0": None,
                "status": "draft",
            }
            shells.append(shell)
            conn.execute(
                """INSERT INTO concepts
                   (id, longtail_id, object_name, visual_style, composition,
                    background, color_palette, material, mood, target_use_case,
                    target_platform, format_output, variations,
                    negative_constraints, metadata_keywords, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, NULL, NULL, ?, NULL, NULL, NULL, NULL,
                           NULL, ?, NULL, ?, NULL, 'draft', ?, ?)
                   ON CONFLICT(id) DO NOTHING""",
                (
                    cid,
                    lt["lt_id"],
                    lt["canonical_phrase"],
                    shell["background"],
                    json.dumps(FORMAT_OUTPUT),
                    json.dumps(NEGATIVE_CONSTRAINTS),
                    now,
                    now,
                ),
            )
        conn.commit()

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(shells, indent=2), encoding="utf-8")

        n_db = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
        print(f"longtails_approved={len(longtails)}")
        print(f"concepts_in_db={n_db}")
        print(f"shell_file={OUT} ({OUT.stat().st_size} bytes)")
        print("sample:")
        print(json.dumps(shells[0], indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
