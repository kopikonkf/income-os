from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

from market_signal_connectors import SCHEMA, evidence_id

CONNECTOR_ID = "adobe_stock_demand_observation_v1"
SOURCE_URL = "https://blog.adobe.com/en/publish/2026/01/08/how-creators-leveraging-adobe-2026-creative-trends"
MAX_TRENDS = 16


def build_adobe_stock_request() -> dict[str, Any]:
    return {
        "method": "GET",
        "url": SOURCE_URL,
        "headers": {"User-Agent": "DIE-H01/1.0 (bounded first-party market-signal research)"},
    }


class AdobeCreativeTrendsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.trends: list[str] = []
        self._mode: str | None = None
        self._heading_id = ""
        self._text: list[str] = []
        self._all_text: list[str] = []
        self._reached_horizon = False

    def handle_starttag(self, tag: str, attrs) -> None:
        row = {str(k).casefold(): "" if v is None else str(v) for k, v in attrs}
        if tag == "meta":
            name = row.get("name", "").casefold().strip()
            if name in {"author", "publication-date", "content-type"}:
                self.meta[name] = row.get("content", "").strip()
            return
        if tag == "h1":
            self._mode, self._text = "h1", []
            return
        if tag == "h2":
            self._mode, self._text = "h2", []
            self._heading_id = row.get("id", "").casefold().strip()

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self._all_text.append(text)
        if self._mode:
            self._text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._mode == "h1":
            self.title = " ".join(self._text).strip()[:300]
            self._mode, self._text = None, []
            return
        if tag == "h2" and self._mode == "h2":
            heading = " ".join(self._text).strip()
            if self._heading_id == "a-new-horizon":
                self._reached_horizon = True
            elif heading and not self._reached_horizon and len(self.trends) < MAX_TRENDS:
                if heading.casefold() not in {value.casefold() for value in self.trends}:
                    self.trends.append(heading[:160])
            self._mode, self._text, self._heading_id = None, [], ""

    @property
    def document_text(self) -> str:
        return " ".join(self._all_text)


def _iso_publication_date(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def parse_adobe_creative_trends_html(payload: str) -> dict[str, Any]:
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError("E_ADOBE_EMPTY_HTML")
    parser = AdobeCreativeTrendsHTMLParser()
    parser.feed(payload)
    parser.close()

    text = " ".join(parser.document_text.split())
    if "Adobe Stock" not in text or "Creative Trends" not in (parser.title + " " + text):
        raise RuntimeError("E_ADOBE_SOURCE_LAYOUT")
    if not parser.trends:
        raise RuntimeError("E_ADOBE_TREND_LAYOUT")

    growth = re.search(
        r"search history[^.]{0,500}?increased\s+by\s+(\d+(?:\.\d+)?)\s+percent[^.]{0,500}?since\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    return {
        "article_title": parser.title,
        "author": parser.meta.get("author") or None,
        "publication_date": _iso_publication_date(parser.meta.get("publication-date", "")),
        "trends": list(parser.trends),
        "search_history_growth_percent": float(growth.group(1)) if growth else None,
        "search_history_growth_since_year": int(growth.group(2)) if growth else None,
        "methodology_mentions_customer_feedback": "feedback from our customers" in text.casefold(),
        "methodology_mentions_search_history": "track search history" in text.casefold(),
    }


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


def normalize_adobe_creative_trends(
    payload: str,
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    parsed = parse_adobe_creative_trends_html(payload)
    raw_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    publication_date = parsed["publication_date"]
    query_key = f"adobe-stock:creative-trends:{publication_date or 'unknown'}"
    return {
        "schema": SCHEMA,
        "connector_id": CONNECTOR_ID,
        "evidence_id": evidence_id(CONNECTOR_ID, query_key, raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "TREND",
        "freshness": freshness,
        "query": "Adobe 2026 Creative Trends",
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            "marketplace": "Adobe Stock",
            "source_first_party": True,
            "observation_timestamp": retrieved_at,
            "source_publication_date": publication_date,
            "article_title": parsed["article_title"],
            "author": parsed["author"],
            "evidence_class": "MACRO_TREND",
            "confidence": "MEDIUM_HIGH",
            "telemetry_kind": "EDITORIAL_CREATIVE_TREND_SYNTHESIS",
            "direct_customer_search_telemetry": False,
            "popular_query_ranking": False,
            "popularity_content_needs_proxy": False,
            "macro_trend": True,
            "quantitative_customer_search_telemetry": False,
            "rank_semantics": "NOT_APPLICABLE",
            "search_volume": None,
            "visitor_query_count": None,
            "trend_count": len(parsed["trends"]),
            "trends": parsed["trends"],
            "search_history_growth_percent": parsed["search_history_growth_percent"],
            "search_history_growth_since_year": parsed["search_history_growth_since_year"],
            "growth_semantics": "AGGREGATE_KEYWORDS_RELATED_TO_2026_TRENDS" if parsed["search_history_growth_percent"] is not None else None,
            "methodology_mentions_customer_feedback": parsed["methodology_mentions_customer_feedback"],
            "methodology_mentions_search_history": parsed["methodology_mentions_search_history"],
        },
        "policy": _policy(),
    }


def run_adobe_stock(core: Any) -> dict[str, Any]:
    request = build_adobe_stock_request()

    def normalize(payload: Any, retrieved_at: str, source_url: str):
        if not isinstance(payload, str):
            raise RuntimeError("E_ADOBE_TEXT_REQUIRED")
        return normalize_adobe_creative_trends(
            payload,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    return core.acquire(
        source_id=CONNECTOR_ID,
        query_key="adobe-stock:creative-trends:2026:v1",
        request=request,
        normalizer=normalize,
    )
