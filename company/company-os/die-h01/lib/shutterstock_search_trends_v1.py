from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from typing import Any

SOURCE_ID = "shutterstock_search_trends_v1"
SOURCE_URL = "https://www.shutterstock.com/trends"
SCHEMA = "die.h01.market-signal-evidence.v1"


class ShutterstockSearchTrendsLayoutError(ValueError):
    pass


class _SearchTrendsTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._anchor_depth = 0
        self._anchor_parts: list[str] = []
        self.anchor_texts: list[str] = []
        self.visible_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lowered == "a":
            self._anchor_depth += 1
            if self._anchor_depth == 1:
                self._anchor_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "noscript"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if lowered == "a" and self._anchor_depth:
            self._anchor_depth -= 1
            if self._anchor_depth == 0:
                text = _collapse_ws(" ".join(self._anchor_parts))
                if text:
                    self.anchor_texts.append(text)
                self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _collapse_ws(data)
        if not text:
            return
        self.visible_parts.append(text)
        if self._anchor_depth:
            self._anchor_parts.append(text)


def _collapse_ws(value: str) -> str:
    return " ".join(str(value).split())


_ROW_RE = re.compile(
    r"^(?P<term>.+?)\s*"
    r"Results\s*:\s*(?P<results>[0-9][0-9,]*)\s*"
    r"Demand\s*:\s*(?P<demand>[A-Za-z][A-Za-z -]{0,40}?)\s*"
    r"Growth\s*:\s*(?P<growth>[0-9][0-9,]*(?:\.[0-9]+)?)\s*%\s*$",
    re.IGNORECASE,
)

_GLOBAL_ROW_RE = re.compile(
    r"(?P<term>[^|]{1,160}?)\s*"
    r"Results\s*:\s*(?P<results>[0-9][0-9,]*)\s*"
    r"Demand\s*:\s*(?P<demand>[A-Za-z][A-Za-z -]{0,40}?)\s*"
    r"Growth\s*:\s*(?P<growth>[0-9][0-9,]*(?:\.[0-9]+)?)\s*%",
    re.IGNORECASE,
)


def build_request() -> dict[str, Any]:
    return {
        "method": "GET",
        "url": SOURCE_URL,
        "headers": {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "DIE-H01/1.0 (bounded first-party market-signal adapter)",
        },
    }


def parse_search_trends_html(html: str, *, max_rows: int = 100) -> list[dict[str, Any]]:
    if not isinstance(html, str):
        raise TypeError("E_SHUTTERSTOCK_TRENDS_TEXT_REQUIRED")
    if max_rows < 1 or max_rows > 500:
        raise ValueError("E_SHUTTERSTOCK_TRENDS_MAX_ROWS")

    parser = _SearchTrendsTextParser()
    parser.feed(html)
    parser.close()

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in parser.anchor_texts:
        match = _ROW_RE.match(candidate)
        if not match:
            continue
        row = _row_from_match(match, rank=len(rows) + 1)
        key = row["search_term"].casefold()
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= max_rows:
            break

    if not rows:
        visible = " | ".join(parser.visible_parts)
        for match in _GLOBAL_ROW_RE.finditer(visible):
            row = _row_from_match(match, rank=len(rows) + 1)
            term = row["search_term"]
            if "|" in term:
                term = term.rsplit("|", 1)[-1].strip()
                row["search_term"] = term
            key = term.casefold()
            if not term or key in seen:
                continue
            seen.add(key)
            rows.append(row)
            if len(rows) >= max_rows:
                break

    if not rows:
        raise ShutterstockSearchTrendsLayoutError("E_SHUTTERSTOCK_TRENDS_NO_ROWS")
    return rows


def _row_from_match(match: re.Match[str], *, rank: int) -> dict[str, Any]:
    term = _collapse_ws(match.group("term")).strip(" |")
    demand = _collapse_ws(match.group("demand")).title()
    results = int(match.group("results").replace(",", ""))
    growth_text = match.group("growth").replace(",", "")
    growth_value = float(growth_text)
    growth: int | float = int(growth_value) if growth_value.is_integer() else growth_value
    if not term:
        raise ShutterstockSearchTrendsLayoutError("E_SHUTTERSTOCK_TRENDS_EMPTY_TERM")
    return {
        "search_term": term,
        "rank": rank,
        "result_count": results,
        "demand_band": demand,
        "growth_percent": growth,
    }


def normalize_search_trends(
    html: str,
    retrieved_at: str,
    source_url: str,
    *,
    freshness: str = "FRESH",
    max_rows: int = 100,
) -> list[dict[str, Any]]:
    rows = parse_search_trends_html(html, max_rows=max_rows)
    return [
        _evidence_from_row(row, retrieved_at=retrieved_at, source_url=source_url, freshness=freshness)
        for row in rows
    ]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _evidence_id(term: str, row_sha256: str) -> str:
    seed = f"{SOURCE_ID}\n{term.casefold().strip()}\n{row_sha256}".encode("utf-8")
    return "H01-SIG-" + hashlib.sha256(seed).hexdigest()[:24].upper()


def _evidence_from_row(
    row: dict[str, Any], *, retrieved_at: str, source_url: str, freshness: str
) -> dict[str, Any]:
    source_metrics = {
        "search_term": row["search_term"],
        "rank": row["rank"],
        "result_count": row["result_count"],
        "demand_band": row["demand_band"],
        "growth_percent": row["growth_percent"],
    }
    row_hash = _sha256_hex(source_metrics)
    return {
        "schema": SCHEMA,
        "connector_id": SOURCE_ID,
        "evidence_id": _evidence_id(row["search_term"], row_hash),
        "evidence_sha256": row_hash,
        "signal_class": "DEMAND",
        "freshness": freshness,
        "query": row["search_term"],
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            "evidence_class": "DIRECT_CUSTOMER_SEARCH_TELEMETRY",
            "commercial_intent_tier": "DIRECT_MARKETPLACE_QUERY",
            "search_term_rank": row["rank"],
            "result_count": row["result_count"],
            "result_count_semantics": "CONTENT_RESULT_COUNT_NOT_CUSTOMER_QUERY_COUNT",
            "demand_band": row["demand_band"],
            "demand_band_semantics": "SOURCE_PUBLISHED_SEARCH_DEMAND_BAND",
            "growth_percent": row["growth_percent"],
            "growth_percent_semantics": "SOURCE_PUBLISHED_SEARCH_FREQUENCY_GROWTH_PERCENT",
            "customer_query_count": None,
            "visitor_query_count": None,
        },
        "policy": {
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
        },
    }


def acquire_search_trends(core: Any, *, max_rows: int = 100) -> dict[str, Any]:
    request = build_request()

    def normalizer(payload: str, retrieved_at: str, source_url: str) -> list[dict[str, Any]]:
        return normalize_search_trends(
            payload,
            retrieved_at,
            source_url,
            max_rows=max_rows,
        )

    return core.acquire(
        source_id=SOURCE_ID,
        query_key="shutterstock:search-trends:global",
        request=request,
        normalizer=normalizer,
    )
