from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import cognition_work_card
import profile_pool
import web_ai_capability

BATCH_SCHEMA = "die.h03.content-block-batch.v1"
_ALLOWED_KINDS = {"PARAGRAPH","STEP","BULLET","CHECKLIST_ITEM","CALLOUT","INPUT_PROMPT"}


def _claim_index(kp: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(kp, dict) or kp.get("schema_version") != "die.h03.knowledge-package.v1" or kp.get("holding_id") != "H03":
        raise ValueError("SEMANTIC_PRODUCER_ACCEPTED_KNOWLEDGE_REQUIRED")
    claims = kp.get("claims") or []
    if not claims:
        raise ValueError("SEMANTIC_PRODUCER_CLAIMS_REQUIRED")
    out: dict[str, dict[str, Any]] = {}
    for claim in claims:
        cid = claim.get("claim_id")
        refs = claim.get("evidence_refs")
        if not cid or cid in out or not claim.get("text") or not isinstance(refs, list) or not refs:
            raise ValueError("SEMANTIC_PRODUCER_CLAIM_INVALID")
        out[cid] = claim
    return out


def build_producer_work_cards(*, blueprint: dict[str, Any], knowledge_package: dict[str, Any]) -> list[dict[str, Any]]:
    claims = _claim_index(knowledge_package)
    if blueprint.get("schema_version") != "die.h03.product-blueprint.v1" or blueprint.get("knowledge_package_id") != knowledge_package.get("knowledge_package_id"):
        raise ValueError("SEMANTIC_PRODUCER_BLUEPRINT_INVALID")
    sections = blueprint.get("sections") or []
    if not sections:
        raise ValueError("SEMANTIC_PRODUCER_SECTIONS_REQUIRED")
    cards: list[dict[str, Any]] = []
    for idx, section in enumerate(sections, start=1):
        heading = section.get("heading")
        claim_ids = section.get("claim_ids") or []
        if not heading or not claim_ids:
            raise ValueError("SEMANTIC_PRODUCER_SECTION_INVALID")
        missing = [cid for cid in claim_ids if cid not in claims]
        if missing:
            raise ValueError("SEMANTIC_PRODUCER_UNKNOWN_CLAIM:" + ",".join(missing))
        sid = f"SEC-{idx:03d}"
        card = {
            "schema_version": cognition_work_card.CARD_SCHEMA,
            "work_card_id": f"H03-WC-PROD-{blueprint['product_id']}-{sid}",
            "holding_id": "H03",
            "task_id": "H03-PROD-002",
            "role": "PRODUCER",
            "queue": "production",
            "idempotency_key": f"h03-prod:{blueprint['product_id']}:{sid}",
            "input_artifacts": [
                {"artifact_id": blueprint["product_id"], "kind": "product_blueprint", "ref": f"artifact://product-blueprint/{blueprint['product_id']}", "sha256": None},
                {"artifact_id": knowledge_package["knowledge_package_id"], "kind": "knowledge_package", "ref": f"artifact://knowledge-package/{knowledge_package['knowledge_package_id']}", "sha256": None},
            ],
            "output_contract": {"artifact_kind": "content_block_batch", "schema_version": BATCH_SCHEMA},
            "capability_requirements": cognition_work_card.standard_web_ai_capabilities(),
            "terminal_policy": {"max_attempts":3,"retryable_failures":["RATE_LIMITED","PROVIDER_UNAVAILABLE","PROFILE_UNAVAILABLE","INVALID_OUTPUT"]},
        }
        cards.append(cognition_work_card.validate_work_card(card))
    return cards


def allocate_producer_dispatches(*, blueprint: dict[str, Any], knowledge_package: dict[str, Any], registry: dict[str, Any], pool: dict[str, Any]) -> list[dict[str, Any]]:
    claims = _claim_index(knowledge_package)
    cards = build_producer_work_cards(blueprint=blueprint, knowledge_package=knowledge_package)
    working_pool = copy.deepcopy(pool)
    dispatches: list[dict[str, Any]] = []
    for idx, card in enumerate(cards, start=1):
        section = blueprint["sections"][idx - 1]
        sid = f"SEC-{idx:03d}"
        claim_ids = list(section["claim_ids"])
        route = profile_pool.route_worker_from_pool(role="PRODUCER", registry=registry, pool=working_pool, required_capabilities=["text_generation"])
        consumed = False
        for shard in working_pool["shards"]:
            if shard["shard_id"] != route.get("profile_shard_id"):
                continue
            for provider in shard["providers"]:
                if provider["provider_id"] == route["provider_id"] and provider["available_slots"] > 0:
                    provider["available_slots"] -= 1
                    consumed = True
                    break
            if consumed:
                break
        if not consumed:
            raise RuntimeError("SEMANTIC_PRODUCER_ROUTE_SLOT_NOT_FOUND")
        claim_context = [{"claim_id":cid,"text":claims[cid]["text"]} for cid in claim_ids]
        req = {
            "schema_version": web_ai_capability.REQUEST_SCHEMA,
            "request_id": f"REQ-{card['work_card_id']}",
            "holding_id": "H03",
            "role": "PRODUCER",
            "task_id": "H03-PROD-002",
            "model_route": route["model_route"],
            "prompt": "Write this product section as concise useful content. Return JSON with key blocks, each block containing block_id, kind, text, and claim_ids. Use only supplied claim_ids. Do not invent provenance, citations, rights, prices, sales, or unsupported factual claims.",
            "context": {
                "product_id": blueprint["product_id"],
                "product_form": blueprint["form"],
                "title": blueprint["title"],
                "section_id": sid,
                "section_heading": section["heading"],
                "claims": claim_context,
                "desired_outcome": (blueprint.get("metadata") or {}).get("desired_outcome"),
            },
            "output_mode": "JSON",
        }
        web_ai_capability.validate_capability_request(req)
        dispatches.append({
            "work_card":card,
            "route":route,
            "request":req,
            "section_id":sid,
            "section_heading":section["heading"],
            "claim_ids":claim_ids,
        })
    return dispatches


def _parse_model_json(model_content: Any) -> dict[str, Any]:
    if isinstance(model_content, dict):
        return model_content
    if not isinstance(model_content, str) or not model_content.strip():
        raise ValueError("SEMANTIC_PRODUCER_MODEL_OUTPUT_INVALID")
    text = model_content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("SEMANTIC_PRODUCER_MODEL_JSON_INVALID") from exc
    if not isinstance(parsed, dict):
        raise ValueError("SEMANTIC_PRODUCER_MODEL_JSON_OBJECT_REQUIRED")
    return parsed


def normalize_producer_output(*, dispatch: dict[str, Any], knowledge_package: dict[str, Any], model_output: Any) -> dict[str, Any]:
    claims = _claim_index(knowledge_package)
    card = dispatch["work_card"]
    route = dispatch["route"]
    allowed_claim_ids = set(dispatch["claim_ids"])
    parsed = _parse_model_json(model_output)
    raw_blocks = parsed.get("blocks")
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise ValueError("SEMANTIC_PRODUCER_BLOCKS_REQUIRED")
    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_blocks:
        if not isinstance(raw, dict):
            raise ValueError("SEMANTIC_PRODUCER_BLOCK_INVALID")
        bid = raw.get("block_id")
        kind = raw.get("kind")
        text = raw.get("text")
        claim_ids = raw.get("claim_ids")
        if not isinstance(bid, str) or not bid.strip() or bid in seen or kind not in _ALLOWED_KINDS or not isinstance(text, str) or not text.strip():
            raise ValueError("SEMANTIC_PRODUCER_BLOCK_INVALID")
        seen.add(bid)
        if not isinstance(claim_ids, list) or not claim_ids or len(claim_ids) != len(set(claim_ids)):
            raise ValueError("SEMANTIC_PRODUCER_BLOCK_CLAIMS_INVALID")
        if not set(claim_ids).issubset(allowed_claim_ids):
            raise ValueError("SEMANTIC_PRODUCER_BLOCK_CLAIM_OUT_OF_SECTION")
        evidence_refs: list[str] = []
        for cid in claim_ids:
            for ref in claims[cid]["evidence_refs"]:
                if ref not in evidence_refs:
                    evidence_refs.append(ref)
        blocks.append({"block_id":bid,"kind":kind,"text":text.strip(),"claim_ids":list(claim_ids),"evidence_refs":evidence_refs})
    return {
        "schema_version": BATCH_SCHEMA,
        "content_batch_id": f"H03-CB-{card['work_card_id']}",
        "holding_id": "H03",
        "product_id": dispatch["request"]["context"]["product_id"],
        "knowledge_package_id": knowledge_package["knowledge_package_id"],
        "section_id": dispatch["section_id"],
        "section_heading": dispatch["section_heading"],
        "producer_observation": {
            "provider_id": route["provider_id"],
            "model_route": route["model_route"],
            "profile_shard_id": route.get("profile_shard_id"),
            "transport_family": route.get("transport_family"),
        },
        "blocks": blocks,
        "truth_status": "DERIVED_SEMANTIC_CONTENT",
    }
