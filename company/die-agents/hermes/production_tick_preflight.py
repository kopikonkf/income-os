#!/usr/bin/env python3
"""Single deterministic scheduler preflight for active-card continuation vs new-seed selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from production_active_card_resolver import resolve_active_card
from production_seed_selector import select_seed

SCHEMA = "die.production-tick-preflight.v1"
DEFAULT_WORKSPACES = Path("/var/lib/die/workspaces")
DEFAULT_DB = Path("/var/lib/die/atlas/object-asset-engine/db/object_asset_engine.db")


def preflight(workspaces: Path, db: Path) -> dict:
    active = resolve_active_card(workspaces)
    common = {"schema": SCHEMA, "authority_effect": "NONE", "existing_authority_unchanged": True}
    if active["status"] == "CONTINUE_ACTIVE_CARD":
        return {**common, "mode": "CONTINUE_ACTIVE_CARD", "active_card_resolution": active, "active_card": active["active_card"]}
    if active["status"] == "DELEGATED_ACTIVE_CARD":
        return {**common, "wakeAgent": False, "mode": "WAITING_COGNITION", "active_card_resolution": active, "active_card": active["active_card"]}
    if active["status"] in {"BLOCKED_ACTIVE_CARD", "BLOCKED"}:
        return {**common, "mode": "BLOCKED_ACTIVE_CARD", "active_card_resolution": active, "active_card": active.get("active_card")}
    try:
        seed = select_seed(db, workspaces)
    except Exception as exc:  # fail closed before LLM reasoning
        return {**common, "mode": "BLOCKED_PREFLIGHT", "error": type(exc).__name__, "message": str(exc), "active_card_resolution": active}
    if seed["status"] == "SELECTED":
        return {**common, "mode": "START_NEW_SEED", "active_card_resolution": active, "seed_selection": seed, "seed": seed["seed"]}
    return {**common, "mode": "NO_ELIGIBLE_WORK", "active_card_resolution": active, "seed_selection": seed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspaces", type=Path, default=DEFAULT_WORKSPACES)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    a = ap.parse_args(argv)
    out = preflight(a.workspaces, a.db)
    print(json.dumps(out, sort_keys=True))
    return 2 if out["mode"] == "BLOCKED_PREFLIGHT" else 0

if __name__ == "__main__":
    raise SystemExit(main())
