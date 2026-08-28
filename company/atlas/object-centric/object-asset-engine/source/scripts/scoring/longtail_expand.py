
# DIE-203 OS-neutral runtime paths.
import pathlib as _die_pathlib
import sys as _die_sys
_DIE_ENGINE_SOURCE = _die_pathlib.Path(__file__).resolve().parents[2]
if str(_DIE_ENGINE_SOURCE) not in _die_sys.path:
    _die_sys.path.insert(0, str(_DIE_ENGINE_SOURCE))
import object_engine_paths as engine_paths
"""PHASE 3 — Longtail Expansion Engine v0 (Qwen framework §4 Phase 3 + §5).

Expands top-priority seeds (validated_high) into commercially useful children
with mandatory modifier classification, then applies Dedup Guardrail:
L1 canonical normalization, L2 exact-dup, L3 parent-child redundancy,
L4 modifier classification, L5 near-dup (Jaccard >=0.90 reject,
0.75-0.90 review), L6 quota (max 50/seed), L8 IP blocklist re-check.

Idempotent via UNIQUE(seed_id, canonical_phrase).
"""
import json
import sqlite3
import pathlib
import re
from datetime import datetime, timezone

DB = engine_paths.CANON_DB
REPORT = engine_paths.DATA_DIR / "processed" / "longtail_report_PHASE3.json"

MAX_PER_SEED = 50          # L6
NEAR_DUP_REJECT = 0.90     # L5
NEAR_DUP_REVIEW = 0.75

IP_TERMS = {"nike", "apple", "sony", "disney", "pokemon", "lego", "starbucks"}

# Curated expansion dictionaries: canonical_name -> [(phrase, [modifier_types])]
EXPANSIONS = {
    "bottle": [
        ("wine bottle", ["use_case"]),
        ("perfume bottle", ["use_case", "industry"]),
        ("glass bottle", ["material"]),
        ("plastic bottle", ["material"]),
        ("amber bottle", ["color", "material"]),
        ("apothecary bottle", ["style", "time_period"]),
        ("vintage bottle", ["style", "time_period"]),
        ("potion bottle", ["fictional_genre"]),
        ("baby bottle", ["audience", "use_case"]),
        ("sports water bottle", ["use_case", "audience"]),
        ("olive oil bottle", ["use_case", "industry"]),
        ("laboratory bottle", ["industry", "place"]),
        ("dropper bottle", ["function"]),
        ("spray bottle", ["function"]),
        ("sauce bottle", ["use_case"]),
    ],
    "trophy": [
        ("gold trophy", ["color", "material"]),
        ("silver trophy", ["color", "material"]),
        ("bronze trophy", ["color", "material"]),
        ("star trophy", ["shape"]),
        ("champion cup trophy", ["use_case", "emotion_or_mood"]),
        ("sports trophy", ["use_case"]),
        ("victory trophy", ["emotion_or_mood"]),
        ("kids trophy", ["audience"]),
        ("academic trophy", ["use_case"]),
    ],
    "candle": [
        ("scented candle", ["function"]),
        ("pillar candle", ["shape"]),
        ("birthday candle", ["use_case"]),
        ("tea light candle", ["shape", "use_case"]),
        ("jar candle", ["material"]),
        ("taper candle", ["shape"]),
        ("votive candle", ["style", "use_case"]),
        ("advent candle", ["time_period", "use_case"]),
        ("citronella candle", ["function"]),
        ("memorial candle", ["use_case", "emotion_or_mood"]),
    ],
    "shopping bag": [
        ("paper shopping bag", ["material"]),
        ("canvas tote bag", ["material", "use_case"]),
        ("gift shopping bag", ["use_case"]),
        ("grocery shopping bag", ["use_case"]),
        ("eco shopping bag", ["emotion_or_mood", "material"]),
        ("kraft shopping bag", ["material", "color"]),
        ("luxury shopping bag", ["style", "emotion_or_mood"]),
        ("mini shopping bag", ["shape"]),
    ],
    "question mark": [
        ("3d question mark", ["commercial_format"]),
        ("red question mark", ["color"]),
        ("golden question mark", ["color", "material"]),
        ("wooden question mark", ["material"]),
        ("question mark icon", ["commercial_format"]),
        ("grunge question mark", ["style"]),
        ("neon question mark", ["style", "material"]),
    ],
}


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
        report = []
        inserted_total = 0
        for seed_name, children in EXPANSIONS.items():
            srow = conn.execute(
                "SELECT id FROM seeds WHERE LOWER(canonical_name)=LOWER(?) AND status='approved'",
                (seed_name,),
            ).fetchone()
            if not srow:
                print(f"SKIP (seed not found/approved): {seed_name}")
                continue
            seed_id = srow["id"]
            seq = conn.execute(
                "SELECT COUNT(*) FROM longtails WHERE seed_id=?", (seed_id,)
            ).fetchone()[0]

            kept_phrases = []  # normalized survivors for L5
            actions = []
            for phrase, mods in children:
                if seq >= MAX_PER_SEED:  # L6 quota
                    break
                norm = re.sub(r"\s+", " ", phrase.lower().strip())  # L1
                if norm == seed_name.lower():  # L3
                    actions.append({"phrase": norm, "action": "rejected", "reason": "L3 equals parent"})
                    continue
                if set(norm.split()) & IP_TERMS:  # L8
                    actions.append({"phrase": norm, "action": "rejected", "reason": "L8 ip"})
                    continue
                if not mods:  # L4
                    actions.append({"phrase": norm, "action": "rejected", "reason": "L4 no modifier"})
                    continue

                dup = next((k for k in kept_phrases if jaccard(norm, k) >= NEAR_DUP_REJECT), None)
                status = None
                reason = None
                if dup:
                    status, reason = "merged", f"L5 >= {NEAR_DUP_REJECT} of '{dup}'"
                elif any(0.75 <= jaccard(norm, k) < NEAR_DUP_REJECT for k in kept_phrases):
                    status, reason = "review", f"L5 {NEAR_DUP_REVIEW}-{NEAR_DUP_REJECT} near-dup"
                else:
                    status, reason = "approved", "pass"

                if status != "merged":
                    kept_phrases.append(norm)
                    seq += 1
                    lt_id = f"LT-{seed_id}-{seq:04d}"
                    conn.execute(
                        """INSERT INTO longtails
                           (id, seed_id, phrase, canonical_phrase, modifier_types,
                             demand_score, similarity_max, status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
                           ON CONFLICT(seed_id, canonical_phrase) DO NOTHING""",
                        (lt_id, seed_id, phrase, norm, json.dumps(mods), status, now, now),
                    )
                    actions.append({"lt_id": lt_id, "phrase": norm, "action": status, "reason": reason})
                else:
                    actions.append({"phrase": norm, "action": status, "reason": reason})

            n_ok = sum(1 for a in actions if a["action"] in ("approved", "review"))
            inserted_total += n_ok
            report.append({"seed_id": seed_id, "seed": seed_name, "children": actions})
            print(f"{seed_name} ({seed_id}): {n_ok}/{len(children)} kept")

        conn.commit()
        totals = conn.execute(
            "SELECT seed_id, COUNT(*) c, SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) a "
            "FROM longtails GROUP BY seed_id"
        ).fetchall()
        REPORT.write_text(
            json.dumps({"run_at": now, "batches": report}, indent=2), encoding="utf-8"
        )
        print(f"inserted_kept={inserted_total}")
        for t in totals:
            print(f"  {t['seed_id']}: total={t['c']} approved={t['a']}")
        print(f"report: {REPORT}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
