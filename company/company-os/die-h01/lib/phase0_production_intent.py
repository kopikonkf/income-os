from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "die.h01.phase0-production-intent.v1"
MANIFEST_SCHEMA = "die.h01.phase0-production-intent-manifest.v1"
POLICY_VERSION = "H01-132A-V1"
AUTHORITY_FALSE = {
    "production_dispatch_authorized": False,
    "submission_authorized": False,
    "publication_authorized": False,
    "spend_authorized": False,
}

TIER_ORDER = [
    "DIRECT_MARKETPLACE_QUERY",
    "MARKETPLACE_POPULAR_QUERY",
    "MARKETPLACE_POPULARITY_PROXY",
    "MACRO_SEARCH",
    "ATTENTION_PROXY",
    "LEGACY_PRIOR",
]


class Phase0IntentError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_queue(path: Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _commercial_basis(selection_reason: str, contributions: list[dict[str, Any]]) -> dict[str, Any]:
    tiers = []
    for row in contributions:
        tier = str(row.get("tier") or "")
        if tier in TIER_ORDER and tier not in tiers:
            tiers.append(tier)
    tiers.sort(key=TIER_ORDER.index)
    if selection_reason == "SOURCE_ORDER_FALLBACK":
        return {
            "basis_mode": "FALLBACK_NO_DEMAND_EVIDENCE",
            "source_tiers": [],
            "demand_specific_claim_allowed": False,
            "buyer_scope": "No demand-evidence-specific buyer segment may be asserted for this fallback noun.",
            "use_case_scope": "Use only baseline standalone editable-vector utility; do not claim evidence-specific commercial demand.",
        }
    strongest = tiers[0] if tiers else None
    if strongest in {"DIRECT_MARKETPLACE_QUERY", "MARKETPLACE_POPULAR_QUERY", "MARKETPLACE_POPULARITY_PROXY"}:
        mode = "MARKETPLACE_DEMAND_EVIDENCE"
        buyer = "Generic stock-marketplace asset buyer demand is supported; no industry, demographic, or named buyer segment is asserted."
        use_case = "Prioritize a reusable standalone editable vector of the exact noun for marketplace stock composition and downstream layout reuse."
    elif strongest == "MACRO_SEARCH":
        mode = "MACRO_SEARCH_EVIDENCE"
        buyer = "Broad search interest is supported, but marketplace purchase intent and specific buyer segments are not asserted."
        use_case = "Preserve broad standalone vector utility while treating macro search interest only as weak commercial context."
    elif strongest == "ATTENTION_PROXY":
        mode = "ATTENTION_EVIDENCE"
        buyer = "Attention is supported, but buyer intent, purchase intent, and specific buyer segments are not asserted."
        use_case = "Preserve baseline standalone vector utility; attention evidence must not be converted into a purchase-intent claim."
    else:
        mode = "RANKED_UNCLASSIFIED_EVIDENCE"
        buyer = "Ranking evidence exists, but no specific buyer segment may be asserted from the available evidence."
        use_case = "Preserve standalone editable-vector utility without adding unsupported commercial semantics."
    return {
        "basis_mode": mode,
        "source_tiers": tiers,
        "demand_specific_claim_allowed": mode == "MARKETPLACE_DEMAND_EVIDENCE",
        "buyer_scope": buyer,
        "use_case_scope": use_case,
    }


def build_intents(
    *,
    selector: dict[str, Any],
    materialization: dict[str, Any],
    queue_rows: list[dict[str, Any]],
    cycle_id: str,
    selector_manifest_sha256: str,
    demand_materialization_sha256: str,
) -> list[dict[str, Any]]:
    if selector.get("status") != "FROZEN":
        raise Phase0IntentError("E_SELECTOR_NOT_FROZEN")
    if selector.get("authority", {}).get("production_dispatch_authorized") is not False:
        raise Phase0IntentError("E_SELECTOR_AUTHORITY")
    if not str(cycle_id).startswith("H01-DCYCLE-"):
        raise Phase0IntentError("E_CYCLE_ID")
    if materialization.get("materialization_id") is None:
        raise Phase0IntentError("E_MATERIALIZATION_ID")

    queue_by_id = {str(row.get("queue_item_id")): row for row in queue_rows}
    demand_by_id = {str(row.get("queue_item_id")): row for row in materialization.get("records") or []}
    explanation_by_id = {str(row.get("queue_item_id")): row for row in materialization.get("explanations") or []}
    intents = []

    for selected in selector.get("items") or []:
        qid = str(selected.get("queue_item_id") or "")
        queue = queue_by_id.get(qid)
        demand = demand_by_id.get(qid)
        explain = explanation_by_id.get(qid) or {"contributions": []}
        if queue is None or demand is None:
            raise Phase0IntentError(f"E_LINEAGE_MISSING:{qid}")
        source = queue.get("source") or {}
        checks = {
            "canonical_name": (source.get("canonical_name"), selected.get("canonical_name")),
            "source_candidate_id": (source.get("id"), selected.get("source_candidate_id")),
            "queue_position": (queue.get("queue_position"), selected.get("queue_position")),
            "idempotency_key": (queue.get("idempotency_key"), selected.get("idempotency_key")),
        }
        for label, pair in checks.items():
            if pair[0] != pair[1]:
                raise Phase0IntentError(f"E_IDENTITY_DRIFT:{qid}:{label}")

        evidence_ids = sorted(str(row.get("evidence_id")) for row in demand.get("evidence_refs") or [])
        selector_evidence_ids = sorted(str(x) for x in (selected.get("priority_components") or {}).get("evidence_ids") or [])
        reason = str(selected.get("selection_reason") or "")
        if selected.get("human_context") is not None or (selected.get("family_hypotheses") or []):
            raise Phase0IntentError(f"E_PHASE0_CONTEXT_LEAK:{qid}")
        if reason not in {"EVIDENCE_RANKED", "SOURCE_ORDER_FALLBACK"}:
            raise Phase0IntentError(f"E_SELECTION_REASON:{qid}:{reason}")
        if reason == "EVIDENCE_RANKED" and (demand.get("rank_state") != "RANKED" or evidence_ids != selector_evidence_ids):
            raise Phase0IntentError(f"E_RANKED_BINDING:{qid}")
        if reason == "SOURCE_ORDER_FALLBACK" and selector_evidence_ids:
            raise Phase0IntentError(f"E_FALLBACK_EVIDENCE:{qid}")

        base = {
            "schema": SCHEMA,
            "phase": "PHASE_0_STANDALONE_NOUN",
            "day_key": selector["day_key"],
            "cycle_id": cycle_id,
            "selection_id": selector["selection_id"],
            "lineage": {
                "queue_row_sha256": sha256_value(queue),
                "selector_item_sha256": sha256_value(selected),
                "selector_manifest_sha256": selector_manifest_sha256,
                "demand_record_sha256": sha256_value(demand),
                "demand_materialization_id": materialization["materialization_id"],
                "demand_materialization_sha256": demand_materialization_sha256,
            },
            "queue_identity": {
                "queue_item_id": qid,
                "queue_position": queue["queue_position"],
                "source_candidate_id": source["id"],
                "canonical_name": source["canonical_name"],
                "idempotency_key": queue["idempotency_key"],
                "source_tier": source["source_tier"],
                "suitability": source["suitability"],
                "dispatch_eligible": queue["dispatch_eligible"],
                "gates": queue["gates"],
                "production": queue["production"],
            },
            "selection": {
                "batch_position": selected["batch_position"],
                "selection_reason": reason,
                "priority_rank": selected.get("priority_rank"),
                "priority_score": selected.get("priority_score"),
                "priority_components": selected.get("priority_components") or {},
            },
            "demand": {
                "signal_state": demand["signal_state"],
                "rank_state": demand["rank_state"],
                "rank_score": demand.get("rank_score"),
                "confidence": demand["confidence"],
                "evidence_refs": demand.get("evidence_refs") or [],
                "contributions": explain.get("contributions") or [],
            },
            "commercial_basis": _commercial_basis(reason, explain.get("contributions") or []),
            "phase0_guard": {
                "standalone_noun_only": True,
                "human_context": None,
                "family_hypotheses": [],
                "longtail": None,
                "object_human_cross_join": False,
            },
            "authority": dict(AUTHORITY_FALSE),
        }
        intent = {"intent_id": "H01-P0INT-" + sha256_value(base)[:24].upper(), **base}
        intents.append(intent)
    return intents


def _write_immutable(path: Path, value: Any) -> None:
    body = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != body:
        raise Phase0IntentError(f"E_IMMUTABLE_COLLISION:{path}")
    if not path.exists():
        path.write_text(body, encoding="utf-8")


def persist_intents(*, intents: list[dict[str, Any]], output_root: Path, queue_sha256: str) -> dict[str, Any]:
    if not intents:
        raise Phase0IntentError("E_NO_SELECTED_INTENTS")
    first = intents[0]
    root = Path(output_root) / first["day_key"] / first["cycle_id"]
    refs = []
    for intent in intents:
        path = root / "intents" / f"{intent['intent_id']}.json"
        _write_immutable(path, intent)
        refs.append({
            "intent_id": intent["intent_id"],
            "queue_item_id": intent["queue_identity"]["queue_item_id"],
            "canonical_name": intent["queue_identity"]["canonical_name"],
            "batch_position": intent["selection"]["batch_position"],
            "selection_reason": intent["selection"]["selection_reason"],
            "intent_sha256": sha256_value(intent),
            "path": str(path),
        })
    identity = {
        "policy_version": POLICY_VERSION,
        "cycle_id": first["cycle_id"],
        "selection_id": first["selection_id"],
        "queue_sha256": queue_sha256,
        "intent_refs": [(r["intent_id"], r["intent_sha256"]) for r in refs],
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "FROZEN",
        "policy_version": POLICY_VERSION,
        "manifest_id": "H01-P0MAN-" + sha256_value(identity)[:24].upper(),
        "day_key": first["day_key"],
        "cycle_id": first["cycle_id"],
        "selection_id": first["selection_id"],
        "queue_sha256": queue_sha256,
        "selected_count": len(intents),
        "evidence_ranked_count": sum(1 for x in intents if x["selection"]["selection_reason"] == "EVIDENCE_RANKED"),
        "fallback_count": sum(1 for x in intents if x["selection"]["selection_reason"] == "SOURCE_ORDER_FALLBACK"),
        "intents": refs,
        "phase0_policy": {
            "standalone_noun_only": True,
            "human_atlas_join": False,
            "longtail_generation": False,
            "object_human_cross_join": False,
        },
        "authority": dict(AUTHORITY_FALSE),
    }
    manifest_path = root / "manifest.json"
    _write_immutable(manifest_path, manifest)
    latest = Path(output_root) / first["day_key"] / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps({"schema":"die.h01.phase0-production-intent-latest.v1","manifest_id":manifest["manifest_id"],"manifest_path":str(manifest_path),"cycle_id":first["cycle_id"]},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"manifest": manifest, "manifest_path": str(manifest_path)}
