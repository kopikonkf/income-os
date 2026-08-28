"""PHASE 2 — Demand Scoring Engine v0 (Qwen framework §PHASE 2).

demand_score = 0.30*search + 0.25*marketplace + 0.20*intent + 0.10*trend
             + 0.10*feasibility + 0.05*seasonality - risk - saturation

All components 0..1. Penalties subtracted raw.
Signals v0: QWEN-DEMAND-20 research (HIGH/MED evidence) + heuristic priors.
Wiki seeds without external signals score conservatively -> 'speculative'
until real marketplace signal collection runs (TASK next phase).

Adds column seeds.demand_status. Idempotent.
Outputs: data/processed/demand_scores_v0.json + reports/weekly/top_priority.md
"""
import json
import sqlite3
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path(r"D:\object-asset-engine\db\object_asset_engine.db")
OUT_JSON = pathlib.Path(r"D:\object-asset-engine\data\processed\demand_scores_v0.json")
OUT_MD = pathlib.Path(r"D:\object-asset-engine\reports\weekly\top_priority.md")

WEIGHTS = {
    "search": 0.30,
    "marketplace": 0.25,
    "intent": 0.20,
    "trend": 0.10,
    "feasibility": 0.10,
    "seasonality": 0.05,
}

# category-based commercial intent prior
INTENT_PRIOR = {
    "symbol": 0.85, "award": 0.85, "commerce": 0.80, "finance": 0.75,
    "container": 0.80, "home_decor": 0.75, "electronics": 0.70,
    "creature": 0.70, "fauna": 0.70, "nature": 0.70,
    "kitchenware": 0.70, "stationery": 0.65, "tools": 0.60,
    "concept": 0.60, "furniture": 0.60, "security": 0.55,
}

# trend velocity boosts (2026 editorial trends per Qwen research)
TREND_BOOST = {
    "candle": 0.75, "shopping bag": 0.70, "laptop": 0.70, "chair": 0.70,
    "potted plant": 0.70, "bottle": 0.70, "dragon": 0.65, "trophy": 0.65,
}
TREND_DEFAULT = 0.40

# evergreen oversaturated generics -> saturation penalty
SATURATION = {
    "tree": 0.20, "key": 0.15, "clock": 0.15, "arrow": 0.15, "camera": 0.10,
    "cat": 0.20, "coin": 0.10, "ruler": 0.05, "stapler": 0.05,
}

# seasonal spikes
SEASONAL = {"gift box": 0.90, "trophy": 0.60}

SIGNAL_MAP = {
    "HIGH": {"search": 0.90, "marketplace": 0.85},
    "MED": {"search": 0.60, "marketplace": 0.55},
}


def score_row(row) -> dict:
    name = row["canonical_name"]
    cat_path = row["category_path"] or ""
    obj_class = row["object_class"] or ""
    sig = row["demand_signal"]

    mapped = SIGNAL_MAP.get(sig, {})
    search = mapped.get("search", 0.30)
    marketplace = mapped.get("marketplace", 0.30)

    intent = INTENT_PRIOR.get(obj_class, 0.50)
    if obj_class == "concrete_visual":
        # inherit from category path
        for k, v in INTENT_PRIOR.items():
            if k in cat_path:
                intent = max(intent, v)
                break

    trend = TREND_BOOST.get(name, TREND_DEFAULT)
    feasibility = 0.70 if any(w in name for w in ("grinder", "drill", "hammer", "shear", "fryer")) else 0.85
    seasonality = SEASONAL.get(name, 0.40)

    risk = 0.05 if row["existence_type"] != "real" else 0.0
    saturation = SATURATION.get(name, 0.02)

    total = (
        WEIGHTS["search"] * search
        + WEIGHTS["marketplace"] * marketplace
        + WEIGHTS["intent"] * intent
        + WEIGHTS["trend"] * trend
        + WEIGHTS["feasibility"] * feasibility
        + WEIGHTS["seasonality"] * seasonality
        - risk
        - saturation
    )
    total = round(max(0.0, min(1.0, total)), 3)

    if total >= 0.68:
        dstatus = "validated_high"
    elif total >= 0.55:
        dstatus = "validated_medium"
    elif total >= 0.45:
        dstatus = "validated_low"
    else:
        dstatus = "speculative"

    return {
        "seed_id": row["id"],
        "canonical_name": name,
        "source_batch": row["source_batch"],
        "components": {
            "search": search, "marketplace": marketplace, "intent": round(intent, 2),
            "trend": trend, "feasibility": feasibility, "seasonality": seasonality,
            "risk": risk, "saturation": saturation,
        },
        "demand_score": total,
        "demand_status": dstatus,
    }


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(seeds)")}
        if "demand_status" not in cols:
            conn.execute("ALTER TABLE seeds ADD COLUMN demand_status TEXT")
        rows = conn.execute(
            "SELECT * FROM seeds WHERE status='approved' ORDER BY id"
        ).fetchall()
        results = [score_row(r) for r in rows]
        for r in results:
            conn.execute(
                "UPDATE seeds SET demand_score=?, demand_status=?, updated_at=? WHERE id=?",
                (r["demand_score"], r["demand_status"], now, r["seed_id"]),
            )
        conn.commit()

        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(
            json.dumps({"scored_at": now, "weights": WEIGHTS, "results": results}, indent=2),
            encoding="utf-8",
        )

        ranked = sorted(results, key=lambda x: -x["demand_score"])
        dist = {}
        for r in results:
            dist[r["demand_status"]] = dist.get(r["demand_status"], 0) + 1

        OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Top Priority Production List (Demand Score v0)",
            f"*Scored: {now} — {len(results)} approved seeds*",
            "",
            "| Rank | Seed ID | Object | Batch | Score | Status |",
            "|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(ranked[:25], start=1):
            lines.append(
                f"| {i} | {r['seed_id']} | {r['canonical_name']} | "
                f"{r['source_batch']} | {r['demand_score']} | {r['demand_status']} |"
            )
        lines += ["", f"Distribution: `{dist}`"]
        OUT_MD.write_text("\n".join(lines), encoding="utf-8")

        print(f"scored={len(results)}")
        print("distribution:", dist)
        print(f"json: {OUT_JSON}")
        print(f"md:   {OUT_MD}")
        print("--- TOP 15 ---")
        for i, r in enumerate(ranked[:15], start=1):
            print(f"{i:2d}. {r['seed_id']} {r['canonical_name']:<22} "
                  f"{r['demand_score']:.3f} {r['demand_status']} ({r['source_batch']})")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
