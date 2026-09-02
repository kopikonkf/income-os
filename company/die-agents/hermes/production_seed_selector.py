#!/usr/bin/env python3
"""Deterministic read-only phase-0 selector for DIE production seeds."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = "die.production-seed-selection.v1"
DEFAULT_DB = Path("/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db")
DEFAULT_WORKSPACES = Path("/var/lib/die/workspaces")
ELIGIBLE_DEMAND = ("validated_high", "validated_medium")
SEED_RE = re.compile(r"^SEED-\d{6}$")
SEED_ANY_RE = re.compile(r"\bSEED-\d{6}\b")


def _collect_seed_ids(value: Any, out: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"seed_id", "master_id", "parent_seed_id"} and isinstance(item, str) and SEED_RE.fullmatch(item):
                out.add(item)
            _collect_seed_ids(item, out)
    elif isinstance(value, list):
        for item in value:
            _collect_seed_ids(item, out)


def produced_seed_ids(workspaces_root: Path) -> set[str]:
    """Return seeds already materialized into production workspaces.

    This is intentionally conservative: a seed is considered used when it is
    present in a known production envelope/manifest/blueprint. Invalid JSON is
    ignored instead of inventing state.
    """
    used: set[str] = set()
    if not workspaces_root.exists():
        return used

    relpaths = (
        "job.json",
        "blueprint.json",
        "qa/manifest.json",
        "qa/blueprint.json",
    )
    for workspace in sorted(p for p in workspaces_root.iterdir() if p.is_dir()):
        for rel in relpaths:
            path = workspace / rel
            if not path.is_file():
                continue
            try:
                raw = path.read_text(encoding="utf-8")
                payload = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            _collect_seed_ids(payload, used)
            if rel == "job.json":
                # Legacy/current worker envelopes may keep canonical seed only
                # inside bounded context prose. Restrict fallback to SEED ids.
                used.update(SEED_ANY_RE.findall(raw))
    return used


def select_seed(db_path: Path, workspaces_root: Path) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(f"object atlas database unavailable: {db_path}")

    used = produced_seed_ids(workspaces_root)
    uri = f"file:{db_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, canonical_name, object_class, existence_type,
                   category_path, demand_score, demand_status, asset_tier,
                   risk_score, status
              FROM seeds
             WHERE status = 'approved'
               AND asset_tier = 'U1-raster'
               AND demand_status IN ('validated_high', 'validated_medium')
             ORDER BY
               CASE demand_status
                 WHEN 'validated_high' THEN 0
                 WHEN 'validated_medium' THEN 1
                 ELSE 2
               END,
               COALESCE(demand_score, 0) DESC,
               id ASC
            """
        ).fetchall()
    finally:
        connection.close()

    for row in rows:
        seed_id = str(row["id"])
        if seed_id in used:
            continue
        return {
            "schema": SCHEMA,
            "status": "SELECTED",
            "selection_policy": "APPROVED_U1_DEMAND_RANKED_UNUSED_V1",
            "seed": {
                "id": seed_id,
                "canonical_name": row["canonical_name"],
                "object_class": row["object_class"],
                "existence_type": row["existence_type"],
                "category_path": row["category_path"],
                "demand_score": row["demand_score"],
                "demand_status": row["demand_status"],
                "asset_tier": row["asset_tier"],
                "risk_score": row["risk_score"],
                "atlas_status": row["status"],
            },
            "excluded_used_seed_count": len(used),
            "used_seed_ids": sorted(used),
            "authority_effect": "NONE",
            "existing_authority_unchanged": True,
        }

    return {
        "schema": SCHEMA,
        "status": "NO_ELIGIBLE_SEED",
        "selection_policy": "APPROVED_U1_DEMAND_RANKED_UNUSED_V1",
        "excluded_used_seed_count": len(used),
        "used_seed_ids": sorted(used),
        "authority_effect": "NONE",
        "existing_authority_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("DIE_OBJECT_ATLAS_DB", DEFAULT_DB)))
    parser.add_argument("--workspaces", type=Path, default=Path(os.environ.get("DIE_WORKSPACES_ROOT", DEFAULT_WORKSPACES)))
    args = parser.parse_args(argv)
    try:
        result = select_seed(args.db, args.workspaces)
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "BLOCKED", "error": type(exc).__name__, "message": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
