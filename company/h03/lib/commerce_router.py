from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA = "die.h03.commerce-channel-registry.v1"
PACKAGE_SCHEMA = "die.h03.commerce-package.v1"
DRAFT_SCHEMA = "die.h03.channel-listing-draft.v1"


def load_registry() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "runtime" / "commerce-channel-registry.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != REGISTRY_SCHEMA or registry.get("holding_id") != "H03":
        raise ValueError("COMMERCE_REGISTRY_SCHEMA_INVALID")
    channels = registry.get("channels")
    if not isinstance(channels, list) or not channels:
        raise ValueError("COMMERCE_REGISTRY_CHANNELS_REQUIRED")
    ids: set[str] = set()
    for channel in channels:
        cid = channel.get("channel_id")
        if not cid or cid in ids:
            raise ValueError("COMMERCE_REGISTRY_CHANNEL_ID_INVALID")
        ids.add(cid)
        for field in ("family", "intake_state", "discovery"):
            if not isinstance(channel.get(field), str) or not channel[field].strip():
                raise ValueError(f"COMMERCE_REGISTRY_FIELD_REQUIRED:{cid}:{field}")
        for field in ("direct_artifact_types", "high_fit_forms", "medium_fit_forms", "derivative_types", "source_refs"):
            if not isinstance(channel.get(field), list):
                raise ValueError(f"COMMERCE_REGISTRY_LIST_REQUIRED:{cid}:{field}")
    return registry


def _artifact_types(delivery: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for item in delivery.get("files") or []:
        kind = str(item.get("artifact_type") or "").upper()
        if kind:
            result.add(kind)
    return result


def _fit(channel: dict[str, Any], *, form: str, vertical: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    required_vertical = channel.get("requires_vertical")
    if required_vertical and required_vertical != vertical:
        return "NONE", ["VERTICAL_MISMATCH"]
    if form in channel.get("high_fit_forms", []):
        return "HIGH", ["FORM_HIGH_FIT"]
    if form in channel.get("medium_fit_forms", []):
        return "MEDIUM", ["FORM_MEDIUM_FIT"]
    if channel.get("derivative_types"):
        return "LOW", ["FORM_REQUIRES_DERIVATIVE"]
    return "NONE", ["FORM_NOT_SUPPORTED"]


def _discovery_weight(discovery: str) -> int:
    if discovery in {"NATIVE_SEARCH", "NATIVE_BOOK_SEARCH", "DOWNSTREAM_RETAILER_NETWORK", "NATIVE_SEARCH_AND_SUBSCRIPTION"}:
        return 3
    if discovery in {"MIXED_DIRECT_AND_DISCOVER", "MIXED"}:
        return 2
    return 1


def route_channels(*, product_form: str, delivery: dict[str, Any], vertical: str = "GENERAL", registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = validate_registry(registry or load_registry())
    artifacts = _artifact_types(delivery)
    routes: list[dict[str, Any]] = []
    for channel in registry["channels"]:
        cid = channel["channel_id"]
        fit, reasons = _fit(channel, form=product_form, vertical=vertical)
        intake = channel["intake_state"]
        direct_types = set(channel.get("direct_artifact_types") or [])
        required_derivatives: list[str] = []
        if intake.startswith("PAUSED"):
            readiness = "PAUSED_INTAKE"
            account_gate = "NOT_APPLICABLE"
            reasons.append("PLATFORM_INTAKE_PAUSED")
        elif fit == "NONE":
            readiness = "NOT_ELIGIBLE"
            account_gate = "NOT_APPLICABLE"
        elif artifacts.intersection(direct_types):
            readiness = "CONTENT_READY"
            account_gate = "PREFLIGHT_REQUIRED"
            reasons.append("CURRENT_ARTIFACT_COMPATIBLE")
        else:
            readiness = "DERIVATIVE_REQUIRED"
            account_gate = "PREFLIGHT_REQUIRED"
            required_derivatives = list(channel.get("derivative_types") or [])
            if not required_derivatives:
                required_derivatives = [f"one_of:{','.join(sorted(direct_types))}"] if direct_types else ["CHANNEL_NATIVE_ARTIFACT"]
            reasons.append("CURRENT_ARTIFACT_INCOMPATIBLE")
        fit_weight = {"HIGH": 30, "MEDIUM": 20, "LOW": 10, "NONE": 0}[fit]
        ready_weight = {"CONTENT_READY": 10, "DERIVATIVE_REQUIRED": 3, "NOT_ELIGIBLE": 0, "PAUSED_INTAKE": 0}[readiness]
        route_score = fit_weight + ready_weight + _discovery_weight(channel["discovery"])
        routes.append({
            "channel_id": cid,
            "channel_name": channel["name"],
            "family": channel["family"],
            "discovery": channel["discovery"],
            "fit": fit,
            "content_readiness": readiness,
            "account_gate": account_gate,
            "reason_codes": reasons,
            "required_derivatives": required_derivatives,
            "route_score": route_score,
            "intake_state": intake,
            "source_refs": list(channel.get("source_refs") or []),
        })
    routes.sort(key=lambda r: (-r["route_score"], r["channel_id"]))
    return routes


def _keyword_seed(*, title: str, form: str, sections: list[str]) -> list[str]:
    raw = [title, form, "digital download"] + sections
    candidates: list[str] = []
    for text in raw:
        for token in str(text).lower().replace("/", " ").replace("-", " ").split():
            cleaned = "".join(c for c in token if c.isalnum())
            if len(cleaned) >= 3 and cleaned not in candidates:
                candidates.append(cleaned)
    return candidates[:24]


def build_commerce_package(*, review_card: dict[str, Any], blueprint: dict[str, Any], package_receipt: dict[str, Any], problem_seed_id: str, delivery_base_ref: str, vertical: str = "GENERAL", registry: dict[str, Any] | None = None) -> dict[str, Any]:
    if review_card.get("schema_version") != "die.h03.founder-review-card.v1" or review_card.get("decision") != "PASS":
        raise ValueError("COMMERCE_REVIEW_PASS_REQUIRED")
    if review_card.get("product_id") != blueprint.get("product_id") or package_receipt.get("product_id") != blueprint.get("product_id"):
        raise ValueError("COMMERCE_PRODUCT_LINEAGE_MISMATCH")
    if package_receipt.get("external_publication") is not False:
        raise ValueError("COMMERCE_LOCAL_PACKAGE_REQUIRED")
    sections = [s["heading"] for s in blueprint.get("sections") or []]
    title = blueprint["title"]
    subtitle = blueprint.get("subtitle", "")
    buyer = review_card["buyer"]
    problem = review_card["problem"]
    promise = review_card["promise"]
    benefits = [
        "Follow a bounded sequence instead of rediscovering the process from scratch.",
        "Use a repeatable recheck step so the workflow is not treated as a one-time guarantee.",
        "Keep the important limitation visible: exposure reduction is not total deletion of public records.",
    ]
    short_description = f"{title} is a concise {blueprint['form']} for {buyer} who want {promise}."
    long_description = (
        f"{title} turns a fragmented people-search opt-out task into a bounded sequence: find exposed listings, follow site opt-out instructions, repeat across relevant sites, and recheck periodically. "
        "It is designed as a practical execution aid rather than a promise of complete data erasure, and it preserves the product's evidence and rights lineage."
    )
    delivery = {
        "files": [
            {"name": package_receipt["pdf_file"], "artifact_type": "PDF", "sha256": package_receipt["pdf_sha256"], "ref": f"{delivery_base_ref}/{package_receipt['pdf_file']}"},
            {"name": package_receipt["zip_file"], "artifact_type": "ZIP", "sha256": package_receipt["zip_sha256"], "ref": f"{delivery_base_ref}/{package_receipt['zip_file']}"},
        ],
        "page_count": package_receipt["page_count"],
        "package_status": package_receipt["status"],
    }
    routes = route_channels(product_form=blueprint["form"], delivery=delivery, vertical=vertical, registry=registry)
    derivative_set: list[str] = []
    for route in routes:
        if route["content_readiness"] == "DERIVATIVE_REQUIRED":
            for derivative in route["required_derivatives"]:
                if derivative not in derivative_set:
                    derivative_set.append(derivative)
    keywords = _keyword_seed(title=title, form=blueprint["form"], sections=sections)
    package = {
        "schema_version": PACKAGE_SCHEMA,
        "commerce_package_id": f"H03-COM-{blueprint['product_id']}",
        "holding_id": "H03",
        "product_id": blueprint["product_id"],
        "problem_seed_id": problem_seed_id,
        "offer": {
            "title": title,
            "subtitle": subtitle,
            "buyer": buyer,
            "problem": problem,
            "promise": promise,
            "short_description": short_description,
            "long_description": long_description,
            "benefits": benefits,
            "contents": sections,
            "support_statement": "Digital product support covers delivery/access issues and material corrections; no outcome guarantee is made.",
        },
        "delivery": delivery,
        "seo": {"keywords": keywords, "tags": keywords[:13], "language": "en", "mature_content": False},
        "pricing_hypothesis": {
            "state": "UNTESTED",
            "currency": "USD",
            "candidate_price_minor": 900,
            "basis_codes": ["MEDIUM_WTP", "BOUNDED_GUIDE", "NO_OBSERVED_PRODUCT_SALES_YET"],
            "observed_sales": False,
        },
        "faq": [
            {"question": "Is this a done-for-you removal service?", "answer": "No. It is a DIY execution guide."},
            {"question": "Does opting out erase public records?", "answer": "No. The guide explicitly treats opt-out as exposure reduction rather than total erasure."},
            {"question": "Will the information stay removed forever?", "answer": "Not necessarily. The workflow includes periodic rechecking because listings can reappear."},
        ],
        "rights_disclosure": {
            "product_rights_basis": "GOVERNED_EXTERNAL_REFERENCE_PLUS_ORIGINAL_DERIVED_WRITING",
            "verbatim_external_reuse_authorized": False,
            "market_sources_used_as_product_content": False,
            "review_rights_flags": review_card.get("rights_flags") or [],
        },
        "lineage": {
            "review_card_id": review_card["review_card_id"],
            "knowledge_package_id": package_receipt["knowledge_package_id"],
            "local_package_schema": package_receipt["schema_version"],
            "pdf_sha256": package_receipt["pdf_sha256"],
            "zip_sha256": package_receipt["zip_sha256"],
        },
        "derivative_opportunities": [
            {"derivative_type": d, "state": "NOT_BUILT", "reason": "Expands eligible income surfaces without repeating deep research."}
            for d in derivative_set
        ],
        "route_matrix": routes,
        "publication_authority": {"founder_required": True, "external_publication_authorized": False},
    }
    return package


def _base_listing_fields(package: dict[str, Any]) -> dict[str, Any]:
    offer = package["offer"]
    return {
        "title": offer["title"],
        "subtitle": offer["subtitle"],
        "short_description": offer["short_description"],
        "long_description": offer["long_description"],
        "benefits": list(offer["benefits"]),
        "contents": list(offer["contents"]),
        "keywords": list(package["seo"]["keywords"]),
        "tags": list(package["seo"]["tags"]),
        "price_hypothesis": dict(package["pricing_hypothesis"]),
        "delivery_files": list(package["delivery"]["files"]),
        "rights_disclosure": dict(package["rights_disclosure"]),
    }


def build_channel_listing_draft(*, package: dict[str, Any], channel_id: str) -> dict[str, Any]:
    if package.get("schema_version") != PACKAGE_SCHEMA or package.get("publication_authority", {}).get("external_publication_authorized") is not False:
        raise ValueError("CHANNEL_DRAFT_COMMERCE_PACKAGE_INVALID")
    route = next((r for r in package["route_matrix"] if r["channel_id"] == channel_id), None)
    if route is None:
        raise ValueError(f"CHANNEL_NOT_IN_ROUTE_MATRIX:{channel_id}")
    fields = _base_listing_fields(package)
    if channel_id == "etsy":
        fields = {"listing_title": fields["title"], "description": fields["long_description"], "tags": fields["tags"][:13], "digital_files": fields["delivery_files"], "price_hypothesis": fields["price_hypothesis"], "category_hint": "digital guide / printable reference"}
    elif channel_id == "gumroad":
        fields = {"name": fields["title"], "description": fields["long_description"], "tags": fields["tags"], "files": fields["delivery_files"], "price_hypothesis": fields["price_hypothesis"]}
    elif channel_id == "google_play_books":
        fields = {"title": fields["title"], "subtitle": fields["subtitle"], "description": fields["long_description"], "language": package["seo"]["language"], "content_files": [f for f in fields["delivery_files"] if f["artifact_type"] in {"PDF", "EPUB"}], "price_hypothesis": fields["price_hypothesis"]}
    elif channel_id in {"amazon_kdp", "apple_books", "draft2digital"}:
        fields = {"book_title": fields["title"], "subtitle": fields["subtitle"], "description": fields["long_description"], "keywords": fields["keywords"], "required_derivatives": list(route["required_derivatives"]), "price_hypothesis": fields["price_hypothesis"]}
    elif channel_id == "notion_marketplace":
        fields = {"template_name": fields["title"], "brief_description": fields["short_description"], "full_description": fields["long_description"], "required_derivatives": list(route["required_derivatives"]), "keywords": fields["keywords"]}
    else:
        fields["channel_family"] = route["family"]
    return {
        "schema_version": DRAFT_SCHEMA,
        "holding_id": "H03",
        "product_id": package["product_id"],
        "channel_id": channel_id,
        "fit": route["fit"],
        "content_readiness": route["content_readiness"],
        "account_gate": route["account_gate"],
        "reason_codes": list(route["reason_codes"]),
        "required_derivatives": list(route["required_derivatives"]),
        "listing_fields": fields,
        "publication_authorized": False,
    }
