from __future__ import annotations

from typing import Any

EFFECT_KEYS = {
    "queue_identity_effect",
    "object_atlas_validity_effect",
    "rights_effect",
    "feasibility_effect",
    "standalone_production_blocking_effect",
}
AUTHORITY_KEYS = {
    "production_authorized",
    "submission_authorized",
    "publication_authorized",
    "spend_authorized",
}
FRESHNESS = {"FRESH", "STALE", "UNKNOWN"}
SIGNAL_STATES = {"NO_EVIDENCE", "PARTIAL", "COMPLETE", "STALE"}
RANK_STATES = {"RANKED", "UNRANKED"}


def validate_record(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != "die.h01.demand-signal-ranking.v1":
        errors.append("E_SCHEMA")
    queue_item_id = payload.get("queue_item_id")
    if not isinstance(queue_item_id, str) or not queue_item_id.startswith("H01-SVGQ-"):
        errors.append("E_QUEUE_ITEM_ID")

    signal_state = payload.get("signal_state")
    rank_state = payload.get("rank_state")
    score = payload.get("rank_score")
    if signal_state not in SIGNAL_STATES:
        errors.append("E_SIGNAL_STATE")
    if rank_state not in RANK_STATES:
        errors.append("E_RANK_STATE")
    if score is not None and (not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= float(score) <= 1):
        errors.append("E_RANK_SCORE_RANGE")

    effects = payload.get("effects") or {}
    if set(effects) != EFFECT_KEYS or any(effects.get(key) != "NONE" for key in EFFECT_KEYS):
        errors.append("E_NON_BLOCKING_EFFECTS")
    authority = payload.get("authority") or {}
    if set(authority) != AUTHORITY_KEYS or any(authority.get(key) is not False for key in AUTHORITY_KEYS):
        errors.append("E_AUTHORITY_EXPANSION")

    evidence = payload.get("evidence_refs")
    if not isinstance(evidence, list):
        errors.append("E_EVIDENCE_REFS")
        evidence = []
    ids: set[str] = set()
    fresh = 0
    for row in evidence:
        if not isinstance(row, dict):
            errors.append("E_EVIDENCE_ROW")
            continue
        evidence_id = row.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append("E_EVIDENCE_ID")
        elif evidence_id in ids:
            errors.append("E_EVIDENCE_DUPLICATE")
        else:
            ids.add(evidence_id)
        if row.get("freshness") not in FRESHNESS:
            errors.append("E_EVIDENCE_FRESHNESS")
        elif row.get("freshness") == "FRESH":
            fresh += 1

    if signal_state == "NO_EVIDENCE":
        if evidence:
            errors.append("E_NO_EVIDENCE_HAS_REFS")
        if rank_state != "UNRANKED" or score is not None:
            errors.append("E_NO_EVIDENCE_MUST_BE_UNRANKED")
    if signal_state == "STALE" and fresh:
        errors.append("E_STALE_HAS_FRESH_EVIDENCE")
    if rank_state == "RANKED":
        if score is None:
            errors.append("E_RANKED_SCORE_REQUIRED")
        if fresh == 0:
            errors.append("E_RANKED_FRESH_EVIDENCE_REQUIRED")
    if rank_state == "UNRANKED" and score is not None:
        errors.append("E_UNRANKED_SCORE_MUST_BE_NULL")

    discoveries = payload.get("discoveries") or {}
    for bucket, expected_kind in (("buyers", "BUYER"), ("use_cases", "USE_CASE"), ("family_hypotheses", "FAMILY")):
        rows = discoveries.get(bucket, []) if isinstance(discoveries, dict) else []
        if not isinstance(rows, list):
            errors.append(f"E_DISCOVERY_BUCKET:{bucket}")
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("kind") != expected_kind or row.get("status") != "HYPOTHESIS":
                errors.append(f"E_DISCOVERY_CONTRACT:{bucket}")
                continue
            refs = row.get("evidence_ids")
            if not isinstance(refs, list) or any(ref not in ids for ref in refs):
                errors.append(f"E_DISCOVERY_EVIDENCE:{bucket}")

    return errors
