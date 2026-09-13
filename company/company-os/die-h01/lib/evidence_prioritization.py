from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable

SCHEMA = "die.h01.evidence-prioritization.v1"
POLICY_VERSION = "H01-133-V1"
CONFIDENCE_SCORE = {"NONE": 0.0, "LOW": 0.25, "MEDIUM": 0.6, "HIGH": 1.0}
FRESHNESS_FACTOR = {"FRESH": 1.0, "UNKNOWN": 0.5, "STALE": 0.25}
WEIGHTS = {"demand": 0.60, "competition_opportunity": 0.25, "confidence": 0.15}


class PrioritizationError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _competition_opportunity(evidence_rows: Iterable[dict[str, Any]]) -> tuple[float | None, list[str]]:
    weighted: list[tuple[float, float]] = []
    evidence_ids: list[str] = []
    for row in evidence_rows:
        metrics = row.get("normalized_metrics") or {}
        index = metrics.get("competition_index")
        if index is None:
            continue
        try:
            index_float = float(index)
        except (TypeError, ValueError):
            continue
        if not 0 <= index_float <= 100:
            continue
        factor = FRESHNESS_FACTOR.get(str(row.get("freshness") or "UNKNOWN"), 0.5)
        weighted.append((1.0 - (index_float / 100.0), factor))
        if row.get("evidence_id"):
            evidence_ids.append(str(row["evidence_id"]))
    if not weighted:
        return None, []
    numerator = sum(score * factor for score, factor in weighted)
    denominator = sum(factor for _, factor in weighted)
    return _clamp01(numerator / denominator), sorted(set(evidence_ids))


def _demand_component(demand_record: dict[str, Any] | None) -> tuple[float | None, float, list[str]]:
    if not demand_record or demand_record.get("rank_state") != "RANKED":
        return None, 0.0, []
    score = demand_record.get("rank_score")
    if score is None:
        return None, 0.0, []
    confidence = CONFIDENCE_SCORE.get(str(demand_record.get("confidence") or "NONE"), 0.0)
    evidence_ids = sorted(
        str(row.get("evidence_id"))
        for row in demand_record.get("evidence_refs") or []
        if isinstance(row, dict) and row.get("evidence_id")
    )
    return _clamp01(float(score)), confidence, evidence_ids


def _score_components(
    demand_record: dict[str, Any] | None,
    connector_evidence: list[dict[str, Any]],
) -> tuple[float | None, dict[str, Any]]:
    demand_score, confidence_score, demand_evidence_ids = _demand_component(demand_record)
    competition_score, competition_evidence_ids = _competition_opportunity(connector_evidence)

    components: dict[str, Any] = {
        "demand": demand_score,
        "competition_opportunity": competition_score,
        "confidence": confidence_score if demand_score is not None else None,
        "weights": WEIGHTS,
        "evidence_ids": sorted(set(demand_evidence_ids + competition_evidence_ids)),
    }
    market_signal_present = demand_score is not None or competition_score is not None
    if not market_signal_present:
        return None, components

    available: list[tuple[float, float]] = []
    if demand_score is not None:
        available.append((demand_score, WEIGHTS["demand"]))
        available.append((confidence_score, WEIGHTS["confidence"]))
    if competition_score is not None:
        available.append((competition_score, WEIGHTS["competition_opportunity"]))
    numerator = sum(value * weight for value, weight in available)
    denominator = sum(weight for _, weight in available)
    return round(_clamp01(numerator / denominator), 6), components


def _family_hypotheses(demand_record: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not demand_record:
        return []
    rows = (demand_record.get("discoveries") or {}).get("family_hypotheses") or []
    output = []
    for row in rows:
        if not isinstance(row, dict) or row.get("kind") != "FAMILY" or row.get("status") != "HYPOTHESIS":
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        output.append(
            {
                "label": label,
                "status": "HYPOTHESIS",
                "evidence_ids": sorted(set(str(x) for x in row.get("evidence_ids") or [])),
            }
        )
    return sorted(output, key=lambda item: (item["label"].casefold(), item["label"]))


def prioritize(
    queue_items: list[dict[str, Any]],
    *,
    demand_records: dict[str, dict[str, Any]] | None = None,
    connector_evidence: dict[str, list[dict[str, Any]]] | None = None,
    produced_queue_item_ids: Iterable[str] = (),
) -> dict[str, Any]:
    demand_records = demand_records or {}
    connector_evidence = connector_evidence or {}
    produced = set(str(x) for x in produced_queue_item_ids)

    seen: set[str] = set()
    remaining: list[dict[str, Any]] = []
    preserved: list[dict[str, Any]] = []
    family_accumulator: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for source_position, queue_row in enumerate(queue_items):
        queue_item_id = str(queue_row.get("queue_item_id") or "")
        if not queue_item_id.startswith("H01-SVGQ-"):
            raise PrioritizationError(f"E_QUEUE_ITEM_ID:{queue_item_id}")
        if queue_item_id in seen:
            raise PrioritizationError(f"E_DUPLICATE_QUEUE_ITEM:{queue_item_id}")
        seen.add(queue_item_id)
        canonical_name = str(queue_row.get("canonical_name") or queue_row.get("name") or "").strip()
        if not canonical_name:
            raise PrioritizationError(f"E_CANONICAL_NAME:{queue_item_id}")

        base = {
            "queue_item_id": queue_item_id,
            "canonical_name": canonical_name,
            "source_position": source_position,
            "dispatch_eligible": bool(queue_row.get("dispatch_eligible", True)),
            "effects": {
                "queue_identity_effect": "NONE",
                "object_atlas_validity_effect": "NONE",
                "rights_effect": "NONE",
                "feasibility_effect": "NONE",
                "produced_master_validity_effect": "NONE",
            },
        }

        if queue_item_id in produced:
            preserved.append(
                {
                    **base,
                    "projection_state": "PRESERVED_PRODUCED",
                    "priority_score": None,
                    "rank_state": "NOT_RERANKED",
                }
            )
            continue

        demand_record = demand_records.get(queue_item_id)
        score, components = _score_components(
            demand_record,
            list(connector_evidence.get(queue_item_id) or []),
        )
        families = _family_hypotheses(demand_record)
        rank_state = "RANKED" if score is not None else "UNRANKED"
        row = {
            **base,
            "projection_state": "REMAINING",
            "priority_score": score,
            "rank_state": rank_state,
            "components": components,
            "family_hypotheses": families,
        }
        remaining.append(row)
        for family in families:
            family_accumulator[family["label"]].append(row)

    remaining.sort(
        key=lambda row: (
            row["priority_score"] is None,
            -(row["priority_score"] or 0.0),
            row["source_position"],
            row["queue_item_id"],
        )
    )
    ranked_position = 0
    for row in remaining:
        if row["priority_score"] is None:
            row["priority_rank"] = None
        else:
            ranked_position += 1
            row["priority_rank"] = ranked_position

    family_rankings: list[dict[str, Any]] = []
    for label, rows in family_accumulator.items():
        ranked_rows = [row for row in rows if row["priority_score"] is not None]
        if not ranked_rows:
            score = None
            rank_state = "UNRANKED"
        else:
            score = round(sum(row["priority_score"] for row in ranked_rows) / len(ranked_rows), 6)
            rank_state = "RANKED"
        family_rankings.append(
            {
                "label": label,
                "status": "HYPOTHESIS",
                "rank_state": rank_state,
                "priority_score": score,
                "member_queue_item_ids": sorted(row["queue_item_id"] for row in rows),
                "evidence_ids": sorted(
                    {
                        evidence_id
                        for row in rows
                        for hypothesis in row["family_hypotheses"]
                        if hypothesis["label"] == label
                        for evidence_id in hypothesis["evidence_ids"]
                    }
                ),
                "canonical_family_promotion_authorized": False,
            }
        )
    family_rankings.sort(
        key=lambda row: (
            row["priority_score"] is None,
            -(row["priority_score"] or 0.0),
            row["label"].casefold(),
        )
    )
    family_rank_position = 0
    for row in family_rankings:
        if row["priority_score"] is None:
            row["priority_rank"] = None
        else:
            family_rank_position += 1
            row["priority_rank"] = family_rank_position

    identity_material = {
        "policy_version": POLICY_VERSION,
        "queue_item_ids": [row["queue_item_id"] for row in queue_items],
        "demand_records": demand_records,
        "connector_evidence": connector_evidence,
        "produced_queue_item_ids": sorted(produced),
    }
    return {
        "schema": SCHEMA,
        "policy_version": POLICY_VERSION,
        "projection_id": "H01-PRIO-" + _sha256(identity_material)[:24].upper(),
        "source_queue_item_count": len(queue_items),
        "remaining_count": len(remaining),
        "produced_preserved_count": len(preserved),
        "remaining_ranked": remaining,
        "produced_preserved": preserved,
        "family_rankings": family_rankings,
        "policy": {
            "source_queue_mutated": False,
            "already_produced_masters_invalidated": False,
            "unranked_items_remain_production_valid": True,
            "family_hypotheses_are_canonical_families": False,
            "supply_first_independent": True,
        },
        "authority": {
            "production_authorized": False,
            "submission_authorized": False,
            "publication_authorized": False,
            "spend_authorized": False,
        },
    }
