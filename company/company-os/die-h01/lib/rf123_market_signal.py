from __future__ import annotations

import hashlib
import urllib.parse
from html.parser import HTMLParser
from typing import Any

from market_signal_connectors import SCHEMA, evidence_id

CONNECTOR_ID = "123rf_trending_search_v1"
SOURCE_URL = "https://www.123rf.com/free-images/"
MAX_TERMS = 64


def build_123rf_request() -> dict[str, Any]:
    return {
        "method": "GET",
        "url": SOURCE_URL,
        "headers": {"User-Agent": "DIE-H01/1.0 (bounded first-party market-signal research)"},
    }


class RF123TrendingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._heading_mode = False
        self._heading_text: list[str] = []
        self.seen_trending_heading = False
        self._active_href = ""
        self._active_label = ""
        self.terms: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def handle_data(self, data: str) -> None:
        if self._heading_mode:
            self._heading_text.append(data)

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag != "img" or not self._active_href:
            return
        row = {k: "" if v is None else v for k, v in attrs}
        self._active_label = row.get("alt", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._heading_mode:
            heading = " ".join(" ".join(self._heading_text).split()).casefold()
            self.seen_trending_heading = heading == "trending searches"
            self._heading_mode = False
            self._heading_text = []
            return
        if tag == "a" and self._active_href:
            path = urllib.parse.urlparse(self._active_href).path
            slug = path.rsplit("/", 1)[-1].removesuffix(".html").replace("-", " ").strip()
            label = self._active_label or slug
            key = label.casefold()
            if label and key not in self._seen and len(self.terms) < MAX_TERMS:
                self.terms.append({
                    "presentation_position": len(self.terms) + 1,
                    "term": label[:120],
                    "path": path,
                })
                self._seen.add(key)
            self._active_href = ""
            self._active_label = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        row = {k: "" if v is None else v for k, v in attrs}
        classes = row.get("class", "")
        if tag == "h2" and "TrendingWords_mainTitle" in classes:
            self._heading_mode = True
            self._heading_text = []
            return
        if tag == "img" and self._active_href:
            self._active_label = row.get("alt", "").strip()
            return
        if not self.seen_trending_heading or tag != "a" or len(self.terms) >= MAX_TERMS:
            return
        href = row.get("href", "").strip()
        path = urllib.parse.urlparse(href).path
        if "TrendingWords_gridItem" in classes and path.startswith("/free-stock-images/") and path.endswith(".html"):
            self._active_href = href
            self._active_label = ""


def parse_123rf_trending_html(payload: str) -> dict[str, Any]:
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError("E_123RF_EMPTY_HTML")
    parser = RF123TrendingParser()
    parser.feed(payload)
    parser.close()
    if not parser.seen_trending_heading:
        raise RuntimeError("E_123RF_TRENDING_HEADING_LAYOUT")
    if not parser.terms:
        raise RuntimeError("E_123RF_TRENDING_TERMS_LAYOUT")
    return {"surface": "free-images", "terms": parser.terms[:MAX_TERMS]}


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


def normalize_123rf_trending(
    payload: str,
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    parsed = parse_123rf_trending_html(payload)
    raw_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA,
        "connector_id": CONNECTOR_ID,
        "evidence_id": evidence_id(CONNECTOR_ID, f"123rf:free-images:trending:{retrieved_at}", raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "TREND",
        "freshness": freshness,
        "query": "123RF Free Images Trending Searches",
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            "marketplace": "123RF",
            "source_first_party": True,
            "evidence_class": "MARKETPLACE_TRENDING_SEARCH_LABELS",
            "confidence": "MEDIUM",
            "telemetry_kind": "TRENDING_SEARCH_CATEGORY_LABELS",
            "surface": parsed["surface"],
            "observation_timestamp": retrieved_at,
            "term_count": len(parsed["terms"]),
            "terms": parsed["terms"],
            "rank_semantics": "UNRANKED_PRESENTATION_ORDER",
            "direct_customer_search_telemetry": False,
            "popular_query_ranking": False,
            "popularity_content_needs_proxy": False,
            "macro_trend": False,
            "search_volume": None,
            "visitor_query_count": None,
            "quantitative_customer_search_telemetry": False,
            "source_timestamp": None,
        },
        "policy": _policy(),
    }


def run_123rf(core: Any) -> dict[str, Any]:
    request = build_123rf_request()

    def normalize(payload: Any, retrieved_at: str, source_url: str):
        if not isinstance(payload, str):
            raise RuntimeError("E_123RF_TEXT_REQUIRED")
        return normalize_123rf_trending(payload, retrieved_at=retrieved_at, source_url=source_url)

    return core.acquire(
        source_id=CONNECTOR_ID,
        query_key="123rf:free-images:trending-labels:v1",
        request=request,
        normalizer=normalize,
    )
