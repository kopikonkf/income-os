from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "die.h01.svg-blueprint.v3"
POLICY_VERSION = "H01-102A-V1"


class CommercialBlueprintError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")[:40]


def noun_class(intent: dict[str, Any]) -> str:
    suitability = str(intent["queue_identity"].get("suitability") or "")
    for cls in ("animal", "plant", "food", "body", "artifact", "object"):
        if f"noun.{cls}" in suitability:
            return cls
    return "object"


def _commercial(intent: dict[str, Any]) -> dict[str, Any]:
    noun = intent["queue_identity"]["canonical_name"]
    basis = intent["commercial_basis"]
    mode = basis["basis_mode"]
    if mode == "MARKETPLACE_DEMAND_EVIDENCE":
        return {
            "primary_use_case": f"editable isolated {noun} vector for generic stock-marketplace composition, resizing, recoloring and layout reuse",
            "buyer_value": f"generic stock-marketplace buyer receives a clean standalone {noun} asset with editable geometry and no contextual dependency",
            "stock_suitability": f"marketplace demand evidence supports prioritizing a generic unbranded standalone {noun}; no unsupported buyer specialization is added",
            "reuse_contexts": ["stock marketplace compositions", "generic layout reuse", "recoloring and resizing", "downstream compositing"],
        }
    if mode == "MACRO_SEARCH_EVIDENCE":
        return {
            "primary_use_case": f"editable isolated {noun} vector for broad standalone design reuse informed only by macro search interest",
            "buyer_value": f"generic designer receives a reusable standalone {noun} vector without any marketplace purchase-intent claim",
            "stock_suitability": f"macro interest supports visibility for a generic unbranded {noun}, but does not justify buyer-segment or purchase-intent specialization",
            "reuse_contexts": ["generic layout reuse", "recoloring and resizing", "editorial compositing"],
        }
    if mode == "ATTENTION_EVIDENCE":
        return {
            "primary_use_case": f"editable isolated {noun} vector for baseline standalone design reuse while attention evidence remains non-commercial",
            "buyer_value": f"generic designer receives a reusable {noun} vector; attention evidence is not converted into buyer or purchase-intent claims",
            "stock_suitability": f"generic unbranded standalone {noun} with attention evidence only; no demand-specific buyer specialization is permitted",
            "reuse_contexts": ["baseline standalone vector reuse", "generic layout compositing", "recoloring and resizing"],
        }
    if mode == "FALLBACK_NO_DEMAND_EVIDENCE":
        return {
            "primary_use_case": f"editable isolated {noun} vector for baseline standalone reuse without demand-specific specialization",
            "buyer_value": f"generic reusable {noun} vector utility only; no demand-evidence-specific buyer segment is asserted",
            "stock_suitability": f"generic unbranded standalone {noun} retained by source-order fallback; no market-demand claim is made",
            "reuse_contexts": ["baseline standalone vector reuse", "generic layout compositing", "recoloring and resizing"],
        }
    return {
        "primary_use_case": f"editable isolated {noun} vector for standalone design reuse without unsupported commercial specialization",
        "buyer_value": f"generic reusable {noun} vector utility while available ranking evidence remains commercially unclassified",
        "stock_suitability": f"generic unbranded standalone {noun}; no buyer-segment claim is permitted beyond the bound evidence",
        "reuse_contexts": ["standalone vector reuse", "generic layout compositing", "recoloring and resizing"],
    }


def build_blueprint_v3(intent: dict[str, Any]) -> dict[str, Any]:
    if intent.get("schema") != "die.h01.phase0-production-intent.v1":
        raise CommercialBlueprintError("E_INTENT_SCHEMA")
    guard = intent.get("phase0_guard") or {}
    if guard != {
        "standalone_noun_only": True,
        "human_context": None,
        "family_hypotheses": [],
        "longtail": None,
        "object_human_cross_join": False,
    }:
        raise CommercialBlueprintError("E_PHASE0_GUARD")
    if any((intent.get("authority") or {}).values()):
        raise CommercialBlueprintError("E_INTENT_AUTHORITY")
    q = intent["queue_identity"]
    if q.get("dispatch_eligible") is not True or q.get("gates", {}).get("rights") != "PASS" or q.get("gates", {}).get("feasibility") != "PASS":
        raise CommercialBlueprintError("E_QUEUE_GATES")
    noun = q["canonical_name"]
    cls = noun_class(intent)
    view = {
        "animal": "clear side or three-quarter iconic view",
        "plant": "clear front-biased botanical view",
        "food": "clear three-quarter product view",
        "artifact": "clear three-quarter product view",
        "body": "clear front-biased educational icon view",
        "object": "clear iconic view",
    }[cls]
    anchors = [
        f"immediately recognizable generic {noun} silhouette",
        f"distinctive major features typical of a real {noun}",
        f"plausible proportions for a generic {noun}",
    ]
    components = [f"primary body or dominant form of the {noun}", f"major characteristic parts required to recognize a {noun}"]
    materials = {
        "animal": ["natural surface cues appropriate to the animal without photoreal fur detail"],
        "plant": ["natural botanical surface cues without photoreal texture"],
        "food": ["clean simplified food or material cues without photoreal texture"],
        "artifact": ["generic unbranded material cues appropriate to the object"],
        "body": ["clean anatomical form cues suitable for stock illustration"],
        "object": ["generic material cues appropriate to the object"],
    }[cls]
    basis = intent["commercial_basis"]
    evidence = intent["demand"]
    blueprint = {
        "schema": SCHEMA,
        "blueprint_id": f"H01BP-V3-{safe_id(noun)}-{q['source_candidate_id'].replace('CAND-','')}",
        "queue_id": q["queue_item_id"],
        "source_candidate_id": q["source_candidate_id"],
        "semantic_asset_id": f"H01SVG-{q['source_candidate_id']}",
        "production_contract": dict(q["production"]),
        "subject": {
            "canonical_name": noun,
            "recognition_anchors": anchors,
            "essential_components": components,
            "proportion_notes": [f"credible generic {noun} proportions", "avoid exaggerated or novelty proportions unless inherent to recognition"],
            "material_notes": materials,
            "color_notes": ["limited harmonious stock-friendly palette", "clear shape separation at thumbnail size"],
            "texture_notes": ["minimal texture", "clean flat vector surfaces without noisy grain"],
        },
        "commercial": _commercial(intent),
        "commercial_evidence": {
            "intent_id": intent["intent_id"],
            "production_intent_sha256": sha256_value(intent),
            "selection_reason": intent["selection"]["selection_reason"],
            "basis_mode": basis["basis_mode"],
            "source_tiers": list(basis["source_tiers"]),
            "demand_rank_state": evidence["rank_state"],
            "demand_rank_score": evidence.get("rank_score"),
            "demand_confidence": evidence["confidence"],
            "evidence_refs": list(evidence["evidence_refs"]),
            "buyer_scope": basis["buyer_scope"],
            "use_case_scope": basis["use_case_scope"],
            "lineage": dict(intent["lineage"]),
        },
        "visual": {
            "viewpoint": view,
            "composition": ["single object only", "centered with generous transparent margin", "complete silhouette fully visible with no crop", "no scene or unrelated props"],
            "visual_hierarchy": [f"{noun} silhouette reads first", "major recognition features remain distinct at thumbnail size"],
            "style_system": ["clean contemporary stock vector", "simple editable shapes", "crisp geometry", "subtle dimensional separation without photorealism"],
        },
        "vector": {
            "editability": "NATIVE_EDITABLE_VECTOR",
            "shape_language": ["few purposeful paths and primitive shapes", "closed clean contours", "avoid microscopic decorative geometry"],
            "stroke_policy": "use no stroke unless a small structural edge requires one; keep any stroke simple and consistent",
            "fill_policy": "use solid fills only with a compact palette and no bitmap textures",
            "depth_policy": "express depth through overlapping shapes and restrained flat color separation, not filters or raster effects",
        },
        "complexity": {"max_svg_bytes": 524288, "max_geometry_elements": 256, "max_total_points": 4096, "max_path_chars": 16384, "max_group_depth": 32},
        "rights": {
            "trademark_free": True,
            "copyright_safe": True,
            "no_readable_text": True,
            "no_watermark": True,
            "forbidden_content": ["logos", "brand marks", "copyrighted character imagery", "trade dress", "readable text", "watermarks"],
        },
        "output_contract": {
            "format": "SVG",
            "native_vector_required": True,
            "transparent_background": True,
            "allowed_elements": ["g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon"],
            "allowed_path_commands": ["M", "L", "H", "V", "C", "S", "Q", "T", "A", "Z"],
            "forbidden_svg_features": ["script", "external references", "embedded raster image", "foreignObject", "text", "style", "defs", "symbol", "use"],
        },
    }
    return blueprint
