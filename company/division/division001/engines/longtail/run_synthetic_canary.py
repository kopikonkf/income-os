#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import generate_longtail as generator
import guard_longtail as guardrails
import longtail_registry as registry
import phrase_signal_score as phrase_score
import retrieve_human_contexts as human_contexts


def run(fixture: dict, work_dir: Path) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    contexts = human_contexts.retrieve(fixture["human_context_query"])
    generation = generator.generate(
        fixture["object_receipt"],
        contexts,
        budget=fixture["budget"],
        expression_level=fixture["expression_level"],
        created_at=fixture["created_at"],
    )
    guard = guardrails.apply(generation)
    conn = registry.connect(work_dir / "longtail.db")
    attach = []
    try:
        ingest = registry.ingest_guard(conn, guard)
        for idx, plan in enumerate(fixture["signal_plans"]):
            outcome = guard["outcomes"][idx]
            candidate = generation["candidates"][idx]
            if outcome["status"] != "ACCEPTED":
                attach.append({"candidate_id": candidate["candidate_id"], "status": "DEFERRED_GUARD"})
                continue
            scored = phrase_score.synthetic_canary(
                candidate,
                outcome,
                plan,
                fixture["hard_veto"],
                registry_db=work_dir / "signals.db",
                evaluated_at=fixture["evaluated_at"],
            )
            attach.append({
                "candidate_id": candidate["candidate_id"],
                "status": registry.attach_score(conn, scored),
                "score_status": scored["demand_score"]["score_status"],
                "final_score": scored["demand_score"]["final_score"],
            })
        ranking = registry.ranking(conn)
    finally:
        conn.close()
    return {
        "schema": "die.division001.longtail-synthetic-canary-run.v1",
        "fixture_schema": fixture["schema"],
        "generated_count": generation["generated_count"],
        "guard_counts": guard["counts"],
        "registry_ingest": ingest,
        "score_attach": attach,
        "ranking": ranking,
        "network_collection_performed": False,
        "object_atlas_written": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture")
    ap.add_argument("--work-dir", required=True)
    args = ap.parse_args()
    try:
        fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        print(json.dumps(run(fixture, Path(args.work_dir)), indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "die.division001.longtail-synthetic-canary-run.v1", "status": "FAIL", "error": str(exc)}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())