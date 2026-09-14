from __future__ import annotations
import hashlib
import urllib.parse
from html.parser import HTMLParser
from typing import Any
from market_signal_connectors import SCHEMA, evidence_id

CONNECTOR_ID = "vecteezy_popular_search_v1"
BASE_URL = "https://www.vecteezy.com"
SURFACES = {
    "svg": ("/popular-svgs", "SVG", "/free-svg/"),
    "vector": ("/popular-vectors", "VECTOR", "/free-vector/"),
}
MAX_TERMS = 64
MAX_CATEGORIES = 16


def _spec(surface: str):
    key = str(surface).strip().casefold()
    if key not in SURFACES:
        raise ValueError(f"E_VECTEEZY_SURFACE:{surface}")
    return key, SURFACES[key]


def build_vecteezy_request(surface: str) -> dict[str, Any]:
    _, (path, _, _) = _spec(surface)
    return {
        "method": "GET",
        "url": BASE_URL + path,
        "headers": {"User-Agent": "DIE-H01/1.0 (bounded first-party market-signal research)"},
    }


class VecteezyHTMLParser(HTMLParser):
    def __init__(self, term_prefix: str):
        super().__init__(convert_charrefs=True)
        self.term_prefix = term_prefix
        self.terms = []
        self.categories = []
        self._category_keys = set()
        self.rank = None
        self.mode = None
        self.text = []
        self.href = ""
        self.category_key = ""

    def handle_starttag(self, tag, attrs):
        row = {k: "" if v is None else v for k, v in attrs}
        classes = set(row.get("class", "").split())
        if tag == "span" and "popular-searches__list__counter" in classes:
            self.mode, self.text = "rank", []
            return
        if tag != "a":
            return
        href = row.get("href", "")
        if self.rank is not None and self.term_prefix in urllib.parse.urlparse(href).path and "top-popular-searches#trackPopularClick" in row.get("data-action", ""):
            self.mode, self.text, self.href = "term", [], href
            return
        category = row.get("data-menu-tracking-category-param", "").strip()
        ctype = row.get("data-menu-tracking-content-type-param", "").strip().casefold()
        if category and ctype == "vector" and len(self.categories) < MAX_CATEGORIES:
            self.mode, self.text, self.href, self.category_key = "category", [], href, category

    def handle_data(self, data):
        if self.mode:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self.mode == "rank":
            value = " ".join(" ".join(self.text).split())
            self.rank = int(value) if value.isdigit() else None
            self.mode, self.text = None, []
        elif tag == "a" and self.mode == "term":
            term = " ".join(" ".join(self.text).split()).strip()
            if term and self.rank is not None and len(self.terms) < MAX_TERMS:
                row = {"rank": self.rank, "term": term[:120], "path": urllib.parse.urlparse(self.href).path}
                if row not in self.terms:
                    self.terms.append(row)
            self.rank, self.mode, self.text, self.href = None, None, [], ""
        elif tag == "a" and self.mode == "category":
            label = " ".join(" ".join(self.text).split()).strip() or self.category_key
            row = {"term": self.category_key, "label": label[:120], "path": urllib.parse.urlparse(self.href).path}
            semantic_key = label.casefold()
            if semantic_key not in self._category_keys:
                self.categories.append(row)
                self._category_keys.add(semantic_key)
            self.mode, self.text, self.href, self.category_key = None, [], "", ""


def parse_vecteezy_html(payload: str, *, surface: str) -> dict[str, Any]:
    key, (_, media_type, term_prefix) = _spec(surface)
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError("E_VECTEEZY_EMPTY_HTML")
    parser = VecteezyHTMLParser(term_prefix)
    parser.feed(payload)
    parser.close()
    terms = sorted(parser.terms, key=lambda row: (row["rank"], row["term"].casefold()))[:MAX_TERMS]
    ranks = [row["rank"] for row in terms]
    if not terms or ranks[0] != 1 or len(ranks) != len(set(ranks)):
        raise RuntimeError("E_VECTEEZY_POPULAR_LAYOUT")
    categories = parser.categories[:MAX_CATEGORIES]
    return {"surface": key, "media_type": media_type, "popular_terms": terms, "trending_vector_categories": categories}


def _policy() -> dict[str, Any]:
    return {
        "official_source": True,
        "structured_source": True,
        "auth_required": False,
        "autocomplete_used": False,
        "dom_scraping_used": False,
        "object_atlas_validity_effect": "NONE",
        "standalone_production_blocking_effect": "NONE",
        "production_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
        "spend_authorized": False,
    }


def normalize_vecteezy_popular(payload: str, *, surface: str, retrieved_at: str, source_url: str, freshness: str = "FRESH") -> list[dict[str, Any]]:
    parsed = parse_vecteezy_html(payload, surface=surface)
    raw_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    common = {
        "marketplace": "Vecteezy",
        "source_first_party": True,
        "observation_timestamp": retrieved_at,
        "search_volume": None,
        "visitor_query_count": None,
        "quantitative_customer_search_telemetry": False,
    }
    media_type = parsed["media_type"]
    popular = {
        "schema": SCHEMA,
        "connector_id": CONNECTOR_ID,
        "evidence_id": evidence_id(CONNECTOR_ID, f"vecteezy:{surface}:popular:{retrieved_at}", raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "DEMAND",
        "freshness": freshness,
        "query": f"Vecteezy Top {media_type} Searches",
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            **common,
            "evidence_class": "MARKETPLACE_POPULAR_QUERY",
            "confidence": "MEDIUM_HIGH",
            "telemetry_kind": "POPULAR_QUERY_RANKING",
            "media_type": media_type,
            "rank_semantics": "ORDINAL_POPULARITY_ONLY",
            "ranked_term_count": len(parsed["popular_terms"]),
            "ranked_terms": parsed["popular_terms"],
        },
        "policy": _policy(),
    }
    trend = {
        "schema": SCHEMA,
        "connector_id": CONNECTOR_ID,
        "evidence_id": evidence_id(CONNECTOR_ID, f"vecteezy:vector:trending:{retrieved_at}", raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "TREND",
        "freshness": freshness,
        "query": "Vecteezy Trending Vector Search Categories",
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            **common,
            "evidence_class": "MARKETPLACE_POPULAR_QUERY",
            "confidence": "MEDIUM",
            "telemetry_kind": "TRENDING_CATEGORY_LABELS",
            "media_type": "VECTOR",
            "category_count": len(parsed["trending_vector_categories"]),
            "categories": parsed["trending_vector_categories"],
            "trend_percentage": None,
            "trend_direction_count": None,
        },
        "policy": _policy(),
    }
    if parsed["surface"] == "vector" and parsed["trending_vector_categories"]:
        return [popular, trend]
    return [popular]


def run_vecteezy(core: Any, *, surface: str) -> dict[str, Any]:
    key, _ = _spec(surface)
    request = build_vecteezy_request(key)

    def normalize(payload: Any, retrieved_at: str, source_url: str):
        if not isinstance(payload, str):
            raise RuntimeError("E_VECTEEZY_TEXT_REQUIRED")
        return normalize_vecteezy_popular(payload, surface=key, retrieved_at=retrieved_at, source_url=source_url)

    return core.acquire(
        source_id=CONNECTOR_ID,
        query_key=f"vecteezy:{key}:partial-safe:v1",
        request=request,
        normalizer=normalize,
    )
