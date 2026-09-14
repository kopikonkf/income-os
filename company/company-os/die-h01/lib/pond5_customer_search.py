"""Pond5 Data & Trends customer-search adapter for H01-131C.

The contributor portal is a first-party, public observation surface.  This
adapter deliberately treats the page as a bounded published data document,
not as a marketplace search or authenticated contributor session.  It does
not infer search volume, visitor counts, sales, or any action authority.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = "die.h01.market-signal-evidence.v1"
SOURCE_ID = "pond5_customer_search_data_trends_v1"
SOURCE_NAME = "Pond5 Contributor Portal Data & Trends"
SOURCE_HOST = "contributor.pond5.com"
DATA_TRENDS_BASE_URL = f"https://{SOURCE_HOST}/data-trends/"
EVIDENCE_CLASS = "DIRECT_CUSTOMER_SEARCH_TELEMETRY"
COMMERCIAL_INTENT_TIER = "DIRECT_MARKETPLACE_QUERY"
MAX_TERMS = 100
_MISSING = object()

MEDIA_TYPES = {
    "footage": "footage",
    "music": "music",
    "after-effects": "after-effects",
    "sound-effects": "sound-effects",
    "photos": "photos",
    "illustrations": "illustrations",
}

_MONTH_YEAR = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}\b",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"(?<![A-Za-z0-9])([+-]?\d+(?:\.\d+)?)\s*%")
_SPACE = re.compile(r"\s+")


class Pond5ParseError(ValueError):
    """Raised when a Pond5 payload is not a supported published shape."""


@dataclass(frozen=True)
class PublicImportResponse:
    """Small response-shaped value for importing an operator-provided public snapshot."""

    body: bytes
    content_type: str
    final_url: str


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def evidence_id(
    query_key_or_connector: str,
    payload_sha256_or_query: str,
    legacy_payload_sha256: str | None = None,
) -> str:
    query_key = payload_sha256_or_query if legacy_payload_sha256 is not None else query_key_or_connector
    payload_sha256 = legacy_payload_sha256 or payload_sha256_or_query
    seed = f"{SOURCE_ID}\n{query_key}\n{payload_sha256}".encode("utf-8")
    return "H01-SIG-" + hashlib.sha256(seed).hexdigest()[:24].upper()


def connector_policy() -> dict[str, Any]:
    """Return the source-local policy used by tests and operators."""

    return {
        "connector_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "access_mode": "OFFICIAL_PUBLIC_DATA_TRENDS_PAGE",
        "auth_mode": "NONE",
        "signal_classes": ["DEMAND", "TREND", "COMMERCIAL_INTENT"],
        "max_requests_per_run": 1,
        "min_interval_seconds": 2.0,
        "cache_ttl_seconds": 86400,
        "official": True,
        "autocomplete_core_dependency": False,
        "dom_scraping_core_dependency": False,
        "evidence_class": EVIDENCE_CLASS,
        "commercial_intent_tier": COMMERCIAL_INTENT_TIER,
    }


def build_pond5_data_trends_request(media_type: str = "illustrations") -> dict[str, Any]:
    media_slug = _media_slug(media_type)
    return {
        "connector_id": SOURCE_ID,
        "method": "GET",
        "url": f"{DATA_TRENDS_BASE_URL}{media_slug}/",
        "headers": {
            "User-Agent": "DIE-H01/1.0 (bounded market-signal research; operator contact configured at deployment)"
        },
        "max_requests_per_run": 1,
        "min_interval_seconds": 2.0,
    }


def acquire_pond5_data_trends(
    core: Any,
    *,
    media_type: str = "illustrations",
    query_key: str | None = None,
) -> dict[str, Any]:
    """Acquire one bounded Pond5 page through H01-131A's AcquisitionCore."""

    media_slug = _media_slug(media_type)
    request = build_pond5_data_trends_request(media_slug)
    key = query_key or f"pond5:{media_slug}:data-trends"

    def normalize(payload: Any, retrieved_at: str, source_url: str) -> dict[str, Any]:
        return normalize_pond5_data_trends(
            payload,
            media_type=media_slug,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    return core.acquire(
        source_id=SOURCE_ID,
        query_key=key,
        request=request,
        normalizer=normalize,
    )


def load_public_snapshot(path: Path, *, max_bytes: int = 2_097_152) -> bytes:
    """Read a bounded public HTML/JSON snapshot without touching browser state."""

    if max_bytes <= 0:
        raise ValueError("E_POND5_IMPORT_LIMIT")
    target = Path(path)
    with target.open("rb") as handle:
        body = handle.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise Pond5ParseError("E_POND5_IMPORT_TOO_LARGE")
    return body


def acquire_pond5_data_trends_from_import(
    core: Any,
    snapshot: bytes | str | dict[str, Any] | list[Any],
    *,
    media_type: str = "illustrations",
    source_url: str | None = None,
    query_key: str | None = None,
) -> dict[str, Any]:
    """Run a bounded first-party snapshot import through the same core path.

    The caller must supply a locator on the Pond5 contributor host.  The
    import replaces only the core's injected fetch function for this call and
    never reads cookies, credentials, or browser session data.
    """

    media_slug = _media_slug(media_type)
    locator = source_url or build_pond5_data_trends_request(media_slug)["url"]
    if (urlparse(locator).scheme, (urlparse(locator).hostname or "").casefold().rstrip(".")) != ("https", SOURCE_HOST):
        raise ValueError("E_POND5_IMPORT_SOURCE_SCOPE")
    if isinstance(snapshot, bytes):
        body = snapshot
    elif isinstance(snapshot, str):
        body = snapshot.encode("utf-8")
    else:
        body = canonical_bytes(snapshot)
    if len(body) > 2_097_152:
        raise Pond5ParseError("E_POND5_IMPORT_TOO_LARGE")
    stripped = body.lstrip()
    content_type = "application/json" if stripped.startswith((b"{", b"[")) else "text/html"
    response = PublicImportResponse(body=body, content_type=content_type, final_url=locator)
    original_fetch = core.fetch_fn
    core.fetch_fn = lambda request, capability: response
    try:
        return acquire_pond5_data_trends(core, media_type=media_slug, query_key=query_key)
    finally:
        core.fetch_fn = original_fetch


def normalize_pond5_data_trends(
    payload: Any,
    legacy_payload: Any = _MISSING,
    *,
    media_type: str = "illustrations",
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    """Normalize JSON or published HTML without inventing quantitative data."""

    # Match the H01-131A connector convention as well as the source-local
    # payload-first API: normalize_pond5_data_trends("illustrations", payload).
    if legacy_payload is not _MISSING:
        media_type, payload = payload, legacy_payload
    media_slug = _media_slug(media_type)
    parsed = parse_pond5_data_trends(payload, media_type=media_slug)
    payload_sha256 = _payload_sha256(payload)
    query_key = f"pond5:{media_slug}:data-trends"
    return {
        "schema": SCHEMA,
        "connector_id": SOURCE_ID,
        "evidence_id": evidence_id(query_key, payload_sha256),
        "evidence_sha256": payload_sha256,
        "signal_class": "DEMAND",
        "confidence": "HIGH",
        "freshness": freshness,
        "query": media_slug,
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "evidence_class": EVIDENCE_CLASS,
        "commercial_intent_tier": COMMERCIAL_INTENT_TIER,
        "media_type": media_slug,
        "observation_period": parsed["observation_period"],
        "normalized_metrics": {
            "media_type": media_slug,
            "observation_period": parsed["observation_period"],
            "top_search_terms": parsed["top_search_terms"],
            "trending_up": parsed["trending_up"],
            "trending_down": parsed["trending_down"],
            "trend_comparison_period": parsed["comparison_period"],
            "evidence_class": EVIDENCE_CLASS,
            "commercial_intent_tier": COMMERCIAL_INTENT_TIER,
            "source_payload_sha256": payload_sha256,
            "search_volume": None,
            "visitor_query_count": None,
            "quantitative_counts_provided": False,
        },
        "policy": _policy_flags(),
    }


def parse_pond5_data_trends(payload: Any, *, media_type: str = "illustrations") -> dict[str, Any]:
    """Parse a Pond5 JSON import or the public Data & Trends HTML document."""

    media_slug = _media_slug(media_type)
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Pond5ParseError("E_POND5_UTF8") from exc

    if isinstance(payload, str):
        json_payload = _try_json(payload)
        result = _parse_json(json_payload, media_slug) if json_payload is not None else _parse_html(payload, media_slug)
    elif isinstance(payload, (dict, list)):
        result = _parse_json(payload, media_slug)
    else:
        raise Pond5ParseError("E_POND5_PAYLOAD_TYPE")

    result["top_search_terms"] = _dedupe_terms(result.get("top_search_terms", []))[:MAX_TERMS]
    result["trending_up"] = _dedupe_trends(result.get("trending_up", []), direction="UP")[:MAX_TERMS]
    result["trending_down"] = _dedupe_trends(result.get("trending_down", []), direction="DOWN")[:MAX_TERMS]
    for row in result["trending_up"] + result["trending_down"]:
        row["comparison_period"] = row.get("comparison_period") or result.get("comparison_period")
    if not result["top_search_terms"] and not result["trending_up"] and not result["trending_down"]:
        raise Pond5ParseError("E_POND5_NO_SUPPORTED_DATA")
    return result


def to_h01_130_ref(evidence: dict[str, Any]) -> dict[str, str]:
    return {
        "evidence_id": evidence["evidence_id"],
        "evidence_sha256": evidence["evidence_sha256"],
        "signal_class": evidence["signal_class"],
        "freshness": evidence["freshness"],
    }


def build_pond5_request(media_type: str = "illustrations") -> dict[str, Any]:
    """Compatibility alias for callers using the shorter connector name."""

    return build_pond5_data_trends_request(media_type)


def normalize_pond5_customer_search(
    media_type: str,
    payload: Any,
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    """Compatibility alias with the media-type-first connector convention."""

    return normalize_pond5_data_trends(
        payload,
        media_type=media_type,
        retrieved_at=retrieved_at,
        source_url=source_url,
        freshness=freshness,
    )


class _Pond5HTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[dict[str, Any]] = []
        self.page_text: list[str] = []
        self.scripts: list[str] = []
        self.meta: dict[str, str] = {}
        self._section: dict[str, Any] | None = None
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self._item: dict[str, Any] | None = None
        self._item_tag: str | None = None
        self._anchor_depth = 0
        self._in_script = False
        self._script_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attr_map = {key.casefold(): value or "" for key, value in attrs}
        if tag == "script":
            self._in_script = True
            self._script_text = []
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            self._heading_tag = tag
            self._heading_text = []
        if tag == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").casefold()
            content = attr_map.get("content", "")
            if name and content:
                self.meta[name] = content
        if tag == "li" and self._item is None:
            self._item = {"text": [], "attrs": attr_map}
            self._item_tag = "li"
        elif tag == "a":
            self._anchor_depth += 1
            if self._item is None:
                self._item = {"text": [], "attrs": attr_map}
                self._item_tag = "a"
            else:
                self._item.setdefault("attrs", {}).update(attr_map)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "script":
            self.scripts.append("".join(self._script_text))
            self._in_script = False
            self._script_text = []
        if self._heading_tag == tag:
            heading = _clean_text("".join(self._heading_text))
            self._section = {"heading": heading, "items": [], "text": []}
            self.sections.append(self._section)
            self._heading_tag = None
            self._heading_text = []
        if tag == "a" and self._anchor_depth:
            self._anchor_depth -= 1
            if self._item_tag == "a" and self._anchor_depth == 0:
                self._finish_item()
        if tag == "li" and self._item_tag == "li":
            self._finish_item()

    def handle_data(self, data: str) -> None:
        self.page_text.append(data)
        if self._in_script:
            self._script_text.append(data)
        if self._heading_tag:
            self._heading_text.append(data)
        if self._item is not None:
            self._item.setdefault("text", []).append(data)
        if self._section is not None:
            self._section.setdefault("text", []).append(data)

    def _finish_item(self) -> None:
        if self._section is not None and self._item is not None:
            item = {
                "text": _clean_text("".join(self._item.get("text", []))),
                "attrs": dict(self._item.get("attrs", {})),
            }
            if item["text"]:
                self._section["items"].append(item)
        self._item = None
        self._item_tag = None


def _parse_html(document: str, media_type: str) -> dict[str, Any]:
    parser = _Pond5HTMLParser()
    try:
        parser.feed(document)
        parser.close()
    except Exception as exc:  # HTMLParser should be fail-soft for layout drift.
        raise Pond5ParseError("E_POND5_HTML_PARSE") from exc

    top: list[dict[str, Any]] = []
    up: list[dict[str, Any]] = []
    down: list[dict[str, Any]] = []
    comparison = _comparison_period(" ".join(parser.page_text))
    for section in parser.sections:
        heading = _clean_text(section.get("heading", ""))
        heading_folded = heading.casefold()
        items = section.get("items", [])
        if "top search term" in heading_folded:
            top.extend(_term_from_item(item, index) for index, item in enumerate(items))
        elif "trend" in heading_folded and "up" in heading_folded:
            up.extend(_trend_from_item(item, index, direction="UP") for index, item in enumerate(items))
        elif "trend" in heading_folded and "down" in heading_folded:
            down.extend(_trend_from_item(item, index, direction="DOWN") for index, item in enumerate(items))
        elif "trend" in heading_folded:
            for index, item in enumerate(items):
                trend = _trend_from_item(item, index, direction=None)
                if trend["direction"] == "UP":
                    up.append(trend)
                elif trend["direction"] == "DOWN":
                    down.append(trend)

    # Some published versions put structured JSON in a script tag.  Prefer
    # its explicit fields while retaining the semantic HTML fallback.
    observation_period = None
    for script in parser.scripts:
        candidate = _try_json(script)
        if candidate is None:
            continue
        json_result = _parse_json(candidate, media_type, require_data=False)
        top.extend(json_result["top_search_terms"])
        up.extend(json_result["trending_up"])
        down.extend(json_result["trending_down"])
        comparison = comparison or json_result["comparison_period"]
        period = json_result["observation_period"]
        if period:
            observation_period = period
            break

    observation_period = observation_period or _observation_period(parser, document)
    return {
        "media_type": media_type,
        "observation_period": observation_period,
        "comparison_period": comparison,
        "top_search_terms": top,
        "trending_up": up,
        "trending_down": down,
    }


def _parse_json(payload: Any, media_type: str, *, require_data: bool = True) -> dict[str, Any]:
    mappings = list(_walk_mappings(payload))
    top: list[dict[str, Any]] = []
    up: list[dict[str, Any]] = []
    down: list[dict[str, Any]] = []
    period: str | None = None
    comparison: str | None = None
    top_keys = {
        "top_search_terms", "topsearchterms", "top_customer_search_terms", "topcustomersearchterms",
        "customer_search_terms", "customersearchterms", "top_customer_searches", "topcustomersearches",
        "top_searches", "topsearches", "top_terms", "topterms", "search_terms", "searchterms",
    }
    up_keys = {"trending_up", "trendingup", "trending_up_percentages", "trendinguppercentages", "trend_up", "trendup"}
    down_keys = {"trending_down", "trendingdown", "trending_down_percentages", "trendingdownpercentages", "trend_down", "trenddown"}
    for mapping in mappings:
        for key, value in mapping.items():
            folded = _key(key)
            if folded in top_keys:
                top.extend(_terms_from_value(value))
            elif folded in up_keys:
                up.extend(_trends_from_value(value, direction="UP"))
            elif folded in down_keys:
                down.extend(_trends_from_value(value, direction="DOWN"))
            elif folded in {"trending", "trendingterms", "trends"} and isinstance(value, dict):
                up.extend(_trends_from_value(_first(value, "up", "increasing", "rising") or [], direction="UP"))
                down.extend(_trends_from_value(_first(value, "down", "decreasing", "falling") or [], direction="DOWN"))
            elif folded in {"observation_period", "observationperiod", "period", "month", "reportingperiod"}:
                period = period or _string_value(value)
            elif folded in {"comparison_period", "comparisonperiod", "relative_to", "relativeto", "compared_to", "comparedto"}:
                comparison = comparison or _comparison_period(_string_value(value))

    # A compact list payload is also a valid import: each row is a term item.
    if isinstance(payload, list) and not top:
        top.extend(_terms_from_value(payload))
    comparison = comparison or _comparison_period(json.dumps(payload, ensure_ascii=False))
    for row in up + down:
        row["comparison_period"] = row.get("comparison_period") or comparison
    result = {
        "media_type": media_type,
        "observation_period": period,
        "comparison_period": comparison,
        "top_search_terms": top,
        "trending_up": up,
        "trending_down": down,
    }
    if require_data and not any(result[key] for key in ("top_search_terms", "trending_up", "trending_down")):
        raise Pond5ParseError("E_POND5_NO_SUPPORTED_JSON_DATA")
    return result


def _walk_mappings(value: Any, *, depth: int = 0):
    if depth > 5:
        return
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_mappings(child, depth=depth + 1)
    elif isinstance(value, list):
        for child in value[:MAX_TERMS]:
            yield from _walk_mappings(child, depth=depth + 1)


def _terms_from_value(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if _first(value, "term", "query", "search_term", "searchTerm", "text", "name", "keyword") is not None:
            return [_term_from_value(value, 0)]
        return [_term_from_value(term, index) for index, term in enumerate(value.values())]
    if not isinstance(value, list):
        value = [value]
    return [_term_from_value(term, index) for index, term in enumerate(value)]


def _trends_from_value(value: Any, *, direction: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if _first(value, "term", "query", "search_term", "searchTerm", "text", "name", "keyword") is not None:
            return [_trend_from_value(value, 0, direction=direction)]
        value = list(value.values())
    if not isinstance(value, list):
        value = [value]
    return [_trend_from_value(term, index, direction=direction) for index, term in enumerate(value)]


def _term_from_value(value: Any, index: int) -> dict[str, Any]:
    if isinstance(value, dict):
        term = _first(value, "term", "query", "search_term", "searchTerm", "text", "name", "keyword")
        rank = _positive_int(_first(value, "rank", "position", "order")) or index + 1
        return {"term": _clean_text(_string_value(term)), "rank": rank}
    return {"term": _clean_text(_string_value(value)), "rank": index + 1}


def _trend_from_value(value: Any, index: int, *, direction: str | None) -> dict[str, Any]:
    if isinstance(value, dict):
        term = _first(value, "term", "query", "search_term", "searchTerm", "text", "name", "keyword")
        percent = _first(
            value,
            "change_percent", "changePercent", "percent_change", "percentChange",
            "trend_percent", "trendPercent", "percentage", "percent", "change",
        )
        item_direction = _first(value, "direction", "trend_direction", "trendDirection")
        rank = _positive_int(_first(value, "rank", "position", "order")) or index + 1
        comparison = _comparison_period(_string_value(_first(value, "comparison_period", "comparisonPeriod", "relative_to", "relativeTo")))
        term_text = _clean_text(_string_value(term))
    else:
        rank = index + 1
        comparison = None
        item_direction = None
        percent = None
        term_text = _clean_text(_string_value(value))
    if not term_text:
        term_text, extracted = _split_percent(term_text)
        percent = percent if percent is not None else extracted
    else:
        stripped, extracted = _split_percent(term_text)
        if extracted is not None:
            term_text = stripped
            percent = percent if percent is not None else extracted
    parsed_percent = _percent_value(percent)
    final_direction = _direction(item_direction) or direction
    if final_direction in {"UP", "DOWN"} and parsed_percent is not None:
        parsed_percent = abs(parsed_percent) if final_direction == "UP" else -abs(parsed_percent)
    return {
        "term": term_text,
        "rank": rank,
        "direction": final_direction,
        "change_percent": parsed_percent,
        "comparison_period": comparison,
    }


def _term_from_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    text = _clean_text(item.get("text", ""))
    attrs = item.get("attrs", {})
    label = attrs.get("aria-label") or attrs.get("data-term") or attrs.get("data-query") or text
    rank = _positive_int(attrs.get("data-rank") or attrs.get("data-position")) or index + 1
    term, _ = _split_percent(_clean_text(label))
    return {"term": term, "rank": rank}


def _trend_from_item(item: dict[str, Any], index: int, *, direction: str | None) -> dict[str, Any]:
    attrs = item.get("attrs", {})
    text = _clean_text(item.get("text", ""))
    percent = _first(
        attrs,
        "data-change-percent", "data-percent", "data-change", "data-trend-change",
        "aria-label", "title",
    )
    candidate = _trend_from_value(
        {
            "term": text,
            "change_percent": percent,
            "rank": _positive_int(attrs.get("data-rank")) or index + 1,
            "direction": direction,
        },
        index,
        direction=direction,
    )
    if candidate["change_percent"] is None:
        _, extracted = _split_percent(text)
        candidate["change_percent"] = extracted
        if candidate["direction"] == "DOWN" and extracted is not None:
            candidate["change_percent"] = -abs(extracted)
    return candidate


def _dedupe_terms(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        term = _clean_text(row.get("term", ""))
        key = term.casefold()
        if not term or key in seen:
            continue
        seen.add(key)
        output.append({"term": term, "rank": _positive_int(row.get("rank")) or index + 1})
    return output


def _dedupe_trends(rows: list[dict[str, Any]], *, direction: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        term = _clean_text(row.get("term", ""))
        if not term:
            continue
        row_direction = _direction(row.get("direction")) or direction
        key = (term.casefold(), row_direction)
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "term": term,
                "rank": _positive_int(row.get("rank")) or index + 1,
                "direction": row_direction,
                "change_percent": _percent_value(row.get("change_percent")),
                "comparison_period": _comparison_period(row.get("comparison_period")),
            }
        )
    return output


def _observation_period(parser: _Pond5HTMLParser, document: str) -> str | None:
    for value in parser.meta.values():
        match = _MONTH_YEAR.search(value)
        if match:
            return match.group(0)
    match = _MONTH_YEAR.search(document)
    return match.group(0) if match else None


def _comparison_period(value: Any) -> str | None:
    text = _clean_text(_string_value(value))
    folded = text.casefold()
    if not text:
        return None
    if re.search(r"(?:prior|previous|preceding)(?:\s+\d+)?\s+weeks?", folded):
        return "prior_weeks"
    if re.search(r"(?:prior|previous)(?:\s+\d+)?\s+months?", folded):
        return "prior_months"
    if re.search(r"week\s+over\s+week|month\s+over\s+month|compared\s+to", folded):
        return text[:120]
    return None


def _payload_sha256(payload: Any) -> str:
    if isinstance(payload, bytes):
        return sha256_bytes(payload)
    if isinstance(payload, str):
        return sha256_bytes(payload.encode("utf-8"))
    return sha256_value(payload)


def _try_json(text: str) -> Any | None:
    candidate = text.strip()
    if not candidate or candidate.startswith("//"):
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _split_percent(text: str) -> tuple[str, float | None]:
    match = _PERCENT.search(text)
    if not match:
        return _clean_text(text), None
    remainder = _clean_text((text[: match.start()] + " " + text[match.end() :]).strip(" -:|"))
    return remainder, float(match.group(1))


def _percent_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        _, extracted = _split_percent(_string_value(value))
        if extracted is None:
            return None
        numeric = extracted
    if not math.isfinite(numeric) or abs(numeric) > 10000:
        return None
    return numeric


def _direction(value: Any) -> str | None:
    folded = _string_value(value).casefold()
    if folded in {"up", "upward", "increase", "increasing", "rising", "positive"}:
        return "UP"
    if folded in {"down", "downward", "decrease", "decreasing", "falling", "negative"}:
        return "DOWN"
    return None


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    normalized = {_key(key): value for key, value in mapping.items()}
    for key in keys:
        value = normalized.get(_key(key))
        if value is not None:
            return value
    return None


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return str(value)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


def _clean_text(value: Any) -> str:
    text = html.unescape(_string_value(value))
    return _SPACE.sub(" ", text).strip()


def _media_slug(value: str) -> str:
    key = _clean_text(value).casefold()
    if key not in MEDIA_TYPES:
        raise ValueError(f"E_POND5_MEDIA_TYPE:{value}")
    return MEDIA_TYPES[key]


def _policy_flags() -> dict[str, Any]:
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
