from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "die.h01.demand-signal-materialization.v1"
RECORD_SCHEMA = "die.h01.demand-signal-ranking.v1"
POLICY_VERSION = "H01-130A-V1"

TIER_WEIGHT = {
    "DIRECT_MARKETPLACE_QUERY": 0.95,
    "MARKETPLACE_POPULAR_QUERY": 0.75,
    "MARKETPLACE_POPULARITY_PROXY": 0.55,
    "MACRO_SEARCH": 0.45,
    "ATTENTION_PROXY": 0.30,
    "LEGACY_PRIOR": 0.15,
}
TIER_CONFIDENCE = {
    "DIRECT_MARKETPLACE_QUERY": "HIGH",
    "MARKETPLACE_POPULAR_QUERY": "MEDIUM",
    "MARKETPLACE_POPULARITY_PROXY": "MEDIUM",
    "MACRO_SEARCH": "MEDIUM",
    "ATTENTION_PROXY": "LOW",
    "LEGACY_PRIOR": "LOW",
}
CONFIDENCE_FACTOR = {
    "HIGH": 1.0,
    "MEDIUM_HIGH": 0.9,
    "MEDIUM": 0.75,
    "LOW": 0.5,
    "NONE": 0.35,
}
FRESHNESS_FACTOR = {"FRESH": 1.0, "UNKNOWN": 0.5, "STALE": 0.25}
MATCH_STRENGTH = {"QUERY_EXACT": 1.0, "TERM_EXACT": 0.9, "LABEL_EXACT": 0.85}
CONFIDENCE_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

EFFECTS_NONE = {
    "queue_identity_effect": "NONE",
    "object_atlas_validity_effect": "NONE",
    "rights_effect": "NONE",
    "feasibility_effect": "NONE",
    "standalone_production_blocking_effect": "NONE",
}
AUTHORITY_FALSE = {
    "production_authorized": False,
    "submission_authorized": False,
    "publication_authorized": False,
    "spend_authorized": False,
}


class DemandMaterializerError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def normalize_term(value: Any) -> str:
    text = str(value or "").casefold().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def load_capabilities(directory: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        source_id = str(row.get("source_id") or "")
        if not source_id:
            continue
        out[source_id] = row
    return out


def load_evidence(root: Path, *, connector_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(Path(root).rglob("evidence/*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if row.get("schema") != "die.h01.market-signal-evidence.v1":
            continue
        connector_id = str(row.get("connector_id") or "")
        if connector_ids is not None and connector_id not in connector_ids:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        if not evidence_id:
            continue
        existing = rows.get(evidence_id)
        if existing is None or str(row.get("retrieved_at") or "") > str(existing.get("retrieved_at") or ""):
            rows[evidence_id] = row
    return [rows[key] for key in sorted(rows)]


def _explicit_labels(metrics: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for key in ("terms", "popular_queries", "queries", "related_searches"):
        value = metrics.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str):
                label = item
            elif isinstance(item, dict):
                label = item.get("term") or item.get("query") or item.get("label") or item.get("name")
            else:
                label = None
            if label:
                yield str(label), "TERM_EXACT"
    for key in ("trends", "trend_labels", "categories", "labels"):
        value = metrics.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str):
                label = item
            elif isinstance(item, dict):
                label = item.get("label") or item.get("name") or item.get("term") or item.get("title")
            else:
                label = None
            if label:
                yield str(label), "LABEL_EXACT"


def evidence_match_keys(row: dict[str, Any]) -> list[tuple[str, str]]:
    keys: dict[str, str] = {}
    query = normalize_term(row.get("query"))
    if query:
        keys[query] = "QUERY_EXACT"
    metrics = row.get("normalized_metrics") or {}
    if isinstance(metrics, dict):
        for label, match_type in _explicit_labels(metrics):
            key = normalize_term(label)
            if key and (key not in keys or MATCH_STRENGTH[match_type] > MATCH_STRENGTH[keys[key]]):
                keys[key] = match_type
    return sorted(keys.items())


def build_evidence_index(evidence_rows: list[dict[str, Any]]) -> dict[str, list[tuple[dict[str, Any], str]]]:
    index: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for row in evidence_rows:
        for key, match_type in evidence_match_keys(row):
            index[key].append((row, match_type))
    return {key: sorted(rows, key=lambda item: str(item[0].get("evidence_id") or "")) for key, rows in index.items()}


def _metric_factor(row: dict[str, Any]) -> float:
    metrics = row.get("normalized_metrics") or {}
    if not isinstance(metrics, dict):
        return 1.0
    total = metrics.get("pageviews_total")
    if isinstance(total, (int, float)) and not isinstance(total, bool) and total >= 0:
        # Bounded monotonic attention strength. It never converts pageviews into commercial demand.
        return max(0.35, min(1.0, math.log10(float(total) + 1.0) / 6.0))
    interest = metrics.get("interest_index")
    if isinstance(interest, (int, float)) and not isinstance(interest, bool):
        return max(0.1, min(1.0, float(interest) / 100.0))
    return 1.0


def _evidence_confidence(row: dict[str, Any]) -> str:
    metrics = row.get("normalized_metrics") or {}
    raw = str(metrics.get("confidence") or "") if isinstance(metrics, dict) else ""
    return raw.upper() if raw.upper() in CONFIDENCE_FACTOR else "MEDIUM"


def _capability_tier(connector_id: str, capabilities: dict[str, dict[str, Any]]) -> str | None:
    cap = capabilities.get(connector_id) or {}
    if cap.get("adapter_state") == "DISABLED":
        return None
    tier = str(cap.get("commercial_intent_tier") or "")
    return tier if tier in TIER_WEIGHT else None


def contribution(row: dict[str, Any], match_type: str, capabilities: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    connector_id = str(row.get("connector_id") or "")
    tier = _capability_tier(connector_id, capabilities)
    if tier is None:
        return None
    freshness = str(row.get("freshness") or "UNKNOWN")
    if freshness not in FRESHNESS_FACTOR:
        freshness = "UNKNOWN"
    source_conf = _evidence_confidence(row)
    value = (
        TIER_WEIGHT[tier]
        * CONFIDENCE_FACTOR[source_conf]
        * FRESHNESS_FACTOR[freshness]
        * MATCH_STRENGTH[match_type]
        * _metric_factor(row)
    )
    return {
        "connector_id": connector_id,
        "evidence_id": str(row.get("evidence_id") or ""),
        "tier": tier,
        "match_type": match_type,
        "freshness": freshness,
        "source_confidence": source_conf,
        "contribution": round(max(0.0, min(1.0, value)), 6),
    }


def _overall_confidence(contributions: list[dict[str, Any]]) -> str:
    if not contributions:
        return "NONE"
    candidates = [TIER_CONFIDENCE.get(str(row.get("tier")), "LOW") for row in contributions]
    return max(candidates, key=lambda value: CONFIDENCE_ORDER[value])


def _record(queue_item_id: str, matched: list[tuple[dict[str, Any], str]], capabilities: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    contribs: list[dict[str, Any]] = []
    for evidence, match_type in matched:
        item = contribution(evidence, match_type, capabilities)
        if item is None:
            continue
        evidence_id = str(evidence.get("evidence_id") or "")
        evidence_sha = str(evidence.get("evidence_sha256") or "")
        signal_class = str(evidence.get("signal_class") or "TREND")
        freshness = str(evidence.get("freshness") or "UNKNOWN")
        if not evidence_id or len(evidence_sha) != 64:
            continue
        refs[evidence_id] = {
            "evidence_id": evidence_id,
            "evidence_sha256": evidence_sha,
            "signal_class": signal_class,
            "freshness": freshness,
        }
        contribs.append(item)

    ordered_refs = [refs[key] for key in sorted(refs)]
    fresh = [row for row in contribs if row["freshness"] == "FRESH" and row["contribution"] > 0]
    if not ordered_refs:
        signal_state, rank_state, score, confidence = "NO_EVIDENCE", "UNRANKED", None, "NONE"
    elif not fresh:
        if all(row["freshness"] == "STALE" for row in contribs):
            signal_state = "STALE"
        else:
            signal_state = "PARTIAL"
        rank_state, score, confidence = "UNRANKED", None, _overall_confidence(contribs)
    else:
        # Probabilistic union: independent corroborating evidence can increase score without exceeding 1.
        product = 1.0
        for row in fresh:
            product *= 1.0 - float(row["contribution"])
        score = round(max(0.0, min(1.0, 1.0 - product)), 6)
        signal_state, rank_state, confidence = "PARTIAL", "RANKED", _overall_confidence(fresh)

    record = {
        "schema": RECORD_SCHEMA,
        "queue_item_id": queue_item_id,
        "signal_state": signal_state,
        "rank_state": rank_state,
        "rank_score": score,
        "confidence": confidence,
        "evidence_refs": ordered_refs,
        "discoveries": {"buyers": [], "use_cases": [], "family_hypotheses": []},
        "effects": dict(EFFECTS_NONE),
        "authority": dict(AUTHORITY_FALSE),
    }
    explain = {
        "queue_item_id": queue_item_id,
        "rank_state": rank_state,
        "rank_score": score,
        "contributions": sorted(contribs, key=lambda row: (-row["contribution"], row["connector_id"], row["evidence_id"])),
    }
    return record, explain


def materialize(
    queue_items: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    capabilities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    index = build_evidence_index(evidence_rows)
    records: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in queue_items:
        queue_item_id = str(row.get("queue_item_id") or "")
        source = row.get("source") or {}
        canonical_name = str(source.get("canonical_name") or row.get("canonical_name") or "").strip()
        if not queue_item_id.startswith("H01-SVGQ-") or not canonical_name:
            raise DemandMaterializerError(f"E_QUEUE_ROW:{queue_item_id}")
        if queue_item_id in seen:
            raise DemandMaterializerError(f"E_DUPLICATE_QUEUE_ITEM:{queue_item_id}")
        seen.add(queue_item_id)
        key = normalize_term(canonical_name)
        record, explain = _record(queue_item_id, list(index.get(key) or []), capabilities)
        records.append(record)
        explanations.append({**explain, "canonical_name": canonical_name})

    ranked = sum(1 for row in records if row["rank_state"] == "RANKED")
    stale = sum(1 for row in records if row["signal_state"] == "STALE")
    identity = {
        "policy_version": POLICY_VERSION,
        "queue_item_ids": [row["queue_item_id"] for row in records],
        "evidence": sorted((str(row.get("evidence_id") or ""), str(row.get("evidence_sha256") or "")) for row in evidence_rows),
        "capability_tiers": sorted((key, str(value.get("commercial_intent_tier") or "")) for key, value in capabilities.items()),
    }
    return {
        "schema": SCHEMA,
        "policy_version": POLICY_VERSION,
        "materialization_id": "H01-DMAT-" + sha256_value(identity)[:24].upper(),
        "source_queue_item_count": len(records),
        "evidence_record_count": len(evidence_rows),
        "ranked_count": ranked,
        "unranked_count": len(records) - ranked,
        "stale_only_count": stale,
        "records": records,
        "explanations": explanations,
        "policy": {
            "matching": "EXACT_NORMALIZED_TEXT_ONLY",
            "presentation_order_inferred_as_volume_or_rank": False,
            "missing_evidence_blocks_production": False,
            "buyer_use_case_family_discovery_authorized": False,
            "tier_order": [
                "DIRECT_MARKETPLACE_QUERY",
                "MARKETPLACE_POPULAR_QUERY",
                "MARKETPLACE_POPULARITY_PROXY",
                "MACRO_SEARCH",
                "ATTENTION_PROXY",
                "LEGACY_PRIOR",
            ],
            "tier_weights": TIER_WEIGHT,
        },
        "authority": dict(AUTHORITY_FALSE),
    }
