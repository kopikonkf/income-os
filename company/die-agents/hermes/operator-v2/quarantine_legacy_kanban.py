#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RULE_PATH = ROOT / "LEGACY_KANBAN_QUARANTINE_RULE_V1.json"


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def classify(snapshot: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    rule = json.loads(RULE_PATH.read_text(encoding="utf-8"))
    legacy_ids = set(rule["legacy_card_ids"])
    cards = snapshot.get("kanban_metadata", {}).get("legacy_cards", [])
    if not isinstance(cards, list):
        cards = []
    active = set(projection.get("active_receipt_types", []))
    rows = []
    for raw in cards:
        if not isinstance(raw, dict):
            continue
        card_id = str(raw.get("id") or raw.get("task_id") or "UNKNOWN")
        status = str(raw.get("status") or "unknown")
        declared_backing = raw.get("backing_receipt_types", [])
        if not isinstance(declared_backing, list):
            declared_backing = []
        declared_backing = sorted({str(x) for x in declared_backing if str(x)})
        corroborated = sorted(set(declared_backing) & active)
        invalid_backing = sorted(set(declared_backing) - active)
        rows.append({
            "card_id": card_id,
            "status": status,
            "classification": "QUARANTINED_LEGACY_METADATA" if card_id in legacy_ids else "WORKFLOW_METADATA_ONLY",
            "cognition_effect": "NONE",
            "grandfathered": False,
            "declared_backing_receipt_types": declared_backing,
            "corroborated_by_active_receipts": corroborated,
            "invalid_or_missing_backing_receipt_types": invalid_backing,
            "historically_corroborated": bool(declared_backing) and not invalid_backing,
        })
    return {
        "schema": "die.operator-v2.legacy-kanban-quarantine.v1",
        "mission_id": snapshot.get("mission_id", "M-001"),
        "subject_id": snapshot.get("subject_id", "UNKNOWN"),
        "snapshot_sha256": _sha(snapshot),
        "projection_stage": projection.get("intelligence_stage"),
        "kanban_is_cognition_proof": False,
        "grandfathering_policy": "FORBIDDEN",
        "legacy_card_ids": sorted(legacy_ids),
        "cards": rows,
        "quarantined_count": sum(1 for r in rows if r["classification"] == "QUARANTINED_LEGACY_METADATA"),
        "cognitive_progress_source": "TYPED_PRINCIPAL_RECEIPTS_ONLY",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--projection", required=True)
    args = ap.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    projection = json.loads(Path(args.projection).read_text(encoding="utf-8"))
    print(json.dumps(classify(snapshot, projection), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())