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
from production_seed_ledger import DEFAULT_LEDGER, consumed, normalize_noun, expression_identity, expression_available

SCHEMA = "die.production-seed-selection.v1"
DEFAULT_DB = Path("/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db")
DEFAULT_WORKSPACES = Path("/var/lib/die/workspaces")
ELIGIBLE_DEMAND = ("validated_high", "validated_medium")
SEED_RE = re.compile(r"^SEED-\d{6}$")
SEED_ANY_RE = re.compile(r"\bSEED-\d{6}\b")
SELECTION_POLICY = "APPROVED_U1_DEMAND_RANKED_SEMANTIC_EXPRESSION_V3"
BASELINE_MODE="ISOLATED_OBJECT"
BASELINE_PRESET_ID="ISOLATED_CARTOON_WATERCOLOR_L0"
BASELINE_PRESET_REVISION="1.0.0"


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

    A newly-started production card writes seed-selection.json before cognition,
    so seed ownership is durable before a Blueprint/job exists. Invalid JSON is
    ignored instead of inventing state.
    """
    used: set[str] = set()
    if not workspaces_root.exists():
        return used

    relpaths = (
        "seed-selection.json",
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
            if rel == "seed-selection.json" and isinstance(payload, dict):
                seed = payload.get("seed")
                if isinstance(seed, dict) and isinstance(seed.get("id"), str) and SEED_RE.fullmatch(seed["id"]):
                    used.add(seed["id"])
            if rel == "job.json":
                used.update(SEED_ANY_RE.findall(raw))
    return used



def produced_seed_names(workspaces_root: Path) -> set[str]:
    names:set[str]=set()
    if not workspaces_root.exists(): return names
    for workspace in sorted(p for p in workspaces_root.iterdir() if p.is_dir()):
        path=workspace/'seed-selection.json'
        if not path.is_file(): continue
        try: payload=json.loads(path.read_text(encoding='utf-8')); seed=payload.get('seed') if isinstance(payload,dict) else None
        except Exception: continue
        if isinstance(seed,dict) and isinstance(seed.get('canonical_name'),str):
            n=normalize_noun(seed['canonical_name'])
            if n:names.add(n)
    return names

def _expressions(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='production_seed_expressions'"
    ).fetchone()
    if not exists:
        return {}
    rows = connection.execute(
        """
        SELECT expression_id, seed_id, candidate_id, commercial_expression,
               evidence_level, evidence_ref, opportunity_score, policy_revision
          FROM production_seed_expressions
        """
    ).fetchall()
    return {
        str(r["seed_id"]): {
            "expression_id": r["expression_id"],
            "candidate_id": r["candidate_id"],
            "commercial_expression": r["commercial_expression"],
            "evidence_level": r["evidence_level"],
            "evidence_ref": r["evidence_ref"],
            "opportunity_score": r["opportunity_score"],
            "policy_revision": r["policy_revision"],
        }
        for r in rows
    }


def select_seed(db_path: Path, workspaces_root: Path, *, ledger_path: Path | None = None, semantic_mode: str = BASELINE_MODE, preset_id: str = BASELINE_PRESET_ID, preset_revision: str = BASELINE_PRESET_REVISION, commercial_expression_override: str | None = None) -> dict[str, Any]:
    if not db_path.is_file():
        raise FileNotFoundError(f"object atlas database unavailable: {db_path}")

    used = produced_seed_ids(workspaces_root)
    used_names = produced_seed_names(workspaces_root)
    ledger_ids,ledger_names = consumed(ledger_path)
    used |= ledger_ids; used_names |= ledger_names
    uri = f"file:{db_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT id, canonical_name, object_class, existence_type,
                   category_path, demand_score, demand_status, asset_tier,
                   risk_score, status, source_batch, master_source_id, demand_signal
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
        expressions = _expressions(connection)
    finally:
        connection.close()

    for row in rows:
        seed_id = str(row["id"])
        expression = expressions.get(seed_id)
        commercial_expression = commercial_expression_override or (expression or {}).get('commercial_expression') or f"isolated {row['canonical_name']} stock design component"
        identity = expression_identity(seed_id=seed_id,noun=str(row['canonical_name']),semantic_mode=semantic_mode,commercial_expression=commercial_expression,preset_id=preset_id,preset_revision=preset_revision)
        baseline_compat = semantic_mode == BASELINE_MODE and preset_id == BASELINE_PRESET_ID and preset_revision == BASELINE_PRESET_REVISION
        # Legacy noun/seed history blocks only the historical baseline expression. It must not globally consume other modes/presets.
        if not expression_available(ledger_path,identity,legacy_baseline_compatibility=baseline_compat):
            continue
        return {
            "schema": SCHEMA,
            "status": "SELECTED",
            "selection_policy": SELECTION_POLICY,
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
                "source_batch": row["source_batch"],
                "master_source_id": row["master_source_id"],
                "demand_signal": row["demand_signal"],
            },
            "commercial_expression": expression,
            "expression_identity": identity,
            "semantic_mode": semantic_mode,
            "preset_id": preset_id,
            "preset_revision": preset_revision,
            "excluded_used_seed_count": len(used),
            "excluded_used_noun_count": len(used_names),
            "used_seed_ids": sorted(used),
            "authority_effect": "NONE",
            "existing_authority_unchanged": True,
        }

    return {
        "schema": SCHEMA,
        "status": "NO_ELIGIBLE_SEED",
        "selection_policy": SELECTION_POLICY,
        "excluded_used_seed_count": len(used),
        "excluded_used_noun_count": len(used_names),
        "used_seed_ids": sorted(used),
        "authority_effect": "NONE",
        "existing_authority_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("DIE_OBJECT_ATLAS_DB", DEFAULT_DB)))
    parser.add_argument("--workspaces", type=Path, default=Path(os.environ.get("DIE_WORKSPACES_ROOT", DEFAULT_WORKSPACES)))
    parser.add_argument("--ledger", type=Path, default=Path(os.environ.get("DIE_PRODUCTION_SEED_LEDGER", DEFAULT_LEDGER)))
    args = parser.parse_args(argv)
    try:
        result = select_seed(args.db, args.workspaces, ledger_path=args.ledger)
    except (FileNotFoundError, sqlite3.Error) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "BLOCKED", "error": type(exc).__name__, "message": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())