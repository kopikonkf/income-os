"""Operational H01-131H adapters for bounded macro search/trend evidence.

The Wikimedia adapter uses the existing public JSON connector as an attention
proxy.  The Google Ads adapter accepts only an already-authorized, bounded
response payload; it never obtains or reads credentials and routes persistence,
freshness, cache and rate limiting through ``AcquisitionCore``.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from typing import Any

from market_signal_acquisition import AcquisitionCore, PublicHttpResponse
from market_signal_connectors import (
    build_wikimedia_pageviews_request,
    evidence_id,
    normalize_google_ads_historical,
    normalize_wikimedia_pageviews,
)

WIKIMEDIA_CONNECTOR_ID = "wikimedia_pageviews_v1"
GOOGLE_ADS_CONNECTOR_ID = "google_ads_keyword_historical_v1"
GOOGLE_TRENDS_CONNECTOR_ID = "google_trends_macro_v1"
GOOGLE_ADS_IMPORT_URL = "https://googleads.googleapis.com/v18/customers/authorized:generateKeywordHistoricalMetrics"
GOOGLE_TRENDS_IMPORT_URL = "https://trends.google.com/trends/explore"
USER_AGENT = "DIE-H01/1.0 (bounded first-party market-signal research)"
_UTC_HOUR = re.compile(r"^\d{10}$")


def _require_nonempty(value: str, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"E_{field.upper()}_REQUIRED")
    return result


def _validate_utc_hour(value: str, field: str) -> str:
    result = _require_nonempty(value, field)
    if not _UTC_HOUR.fullmatch(result):
        raise ValueError(f"E_{field.upper()}_FORMAT")
    return result


def _classification(
    *,
    evidence_class: str,
    confidence: str,
    commercial_intent_tier: str,
    telemetry_kind: str,
    macro_trend: bool,
    search_volume: Any = None,
) -> dict[str, Any]:
    return {
        "evidence_class": evidence_class,
        "confidence": confidence,
        "commercial_intent_tier": commercial_intent_tier,
        "telemetry_kind": telemetry_kind,
        "direct_customer_search_telemetry": False,
        "popular_query_ranking": False,
        "popularity_content_needs_proxy": False,
        "macro_trend": macro_trend,
        "search_volume": search_volume,
        "visitor_query_count": None,
        "quantitative_customer_search_telemetry": False,
    }


def _with_classification(evidence: dict[str, Any], **classification: Any) -> dict[str, Any]:
    output = dict(evidence)
    metrics = dict(output.get("normalized_metrics") or {})
    metrics.update(classification)
    output["normalized_metrics"] = metrics
    return output


def build_wikimedia_attention_request(
    article: str,
    start_yyyymmddhh: str,
    end_yyyymmddhh: str,
    *,
    project: str = "en.wikipedia.org",
) -> dict[str, Any]:
    """Build the existing bounded Wikimedia first-party request."""

    start = _validate_utc_hour(start_yyyymmddhh, "start")
    end = _validate_utc_hour(end_yyyymmddhh, "end")
    if start > end:
        raise ValueError("E_DATE_RANGE")
    return build_wikimedia_pageviews_request(
        _require_nonempty(article, "article"),
        start,
        end,
        project=_require_nonempty(project, "project"),
    )


def normalize_wikimedia_attention(
    article: str,
    payload: dict[str, Any],
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    """Normalize Wikimedia pageviews as an attention proxy, never search intent."""

    evidence = normalize_wikimedia_pageviews(
        article,
        payload,
        retrieved_at=retrieved_at,
        source_url=source_url,
        freshness=freshness,
    )
    return _with_classification(
        evidence,
        **_classification(
            evidence_class="ATTENTION_PROXY",
            confidence="LOW",
            commercial_intent_tier="ATTENTION_PROXY",
            telemetry_kind="PAGEVIEW_ATTENTION",
            macro_trend=False,
        ),
    )


def run_wikimedia_attention(
    core: AcquisitionCore,
    *,
    article: str,
    start_yyyymmddhh: str,
    end_yyyymmddhh: str,
    project: str = "en.wikipedia.org",
) -> dict[str, Any]:
    request = build_wikimedia_attention_request(
        article,
        start_yyyymmddhh,
        end_yyyymmddhh,
        project=project,
    )
    query_key = (
        f"wikimedia:{project.casefold()}:{article.strip().casefold()}:"
        f"{start_yyyymmddhh}:{end_yyyymmddhh}:attention-v1"
    )

    def normalize(payload: Any, retrieved_at: str, source_url: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RuntimeError("E_WIKIMEDIA_JSON_OBJECT_REQUIRED")
        return normalize_wikimedia_attention(
            article,
            payload,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    return core.acquire(
        source_id=WIKIMEDIA_CONNECTOR_ID,
        query_key=query_key,
        request=request,
        normalizer=normalize,
    )


def build_google_ads_import_request(
    keyword: str,
    *,
    source_locator: str = GOOGLE_ADS_IMPORT_URL,
) -> dict[str, Any]:
    """Build a first-party locator for an already-authorized Google Ads import.

    This descriptor is deliberately GET-shaped because it is handed to the
    acquisition core's bounded fetch seam; no network request is made by this
    function and no Authorization header can be supplied here.
    """

    _require_nonempty(keyword, "keyword")
    parsed = urllib.parse.urlparse(str(source_locator).strip())
    host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme != "https" or not host or not (
        host == "googleads.googleapis.com" or host.endswith(".googleads.googleapis.com")
    ):
        raise ValueError("E_GOOGLE_ADS_IMPORT_URL_SCOPE")
    return {
        "method": "GET",
        "url": parsed.geturl(),
        "headers": {"User-Agent": USER_AGENT},
    }


def build_google_trends_import_request(
    query: str,
    *,
    source_locator: str = GOOGLE_TRENDS_IMPORT_URL,
) -> dict[str, Any]:
    """Build a locator for a bounded, caller-supplied Google Trends import.

    H01-131H deliberately does not fetch Google Trends pages or undocumented
    endpoints.  This descriptor is used only when an authorized/compliant
    importer supplies the source response to ``run_google_trends_import``.
    """

    _require_nonempty(query, "query")
    parsed = urllib.parse.urlparse(str(source_locator).strip())
    host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme != "https" or host != "trends.google.com":
        raise ValueError("E_GOOGLE_TRENDS_IMPORT_URL_SCOPE")
    return {
        "method": "GET",
        "url": parsed.geturl(),
        "headers": {"User-Agent": USER_AGENT},
    }


def normalize_google_ads_macro(
    keyword: str,
    payload: dict[str, Any],
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> list[dict[str, Any]]:
    """Normalize source-provided Google Ads historical search metrics.

    ``avg_monthly_searches`` is copied only when the authorized source gives
    it.  It is macro search demand, not direct marketplace customer telemetry.
    """

    if not isinstance(payload, dict):
        raise RuntimeError("E_GOOGLE_ADS_JSON_OBJECT_REQUIRED")
    if not isinstance(payload.get("results"), list):
        raise RuntimeError("E_GOOGLE_ADS_RESULTS_LIST_REQUIRED")
    rows = normalize_google_ads_historical(
        keyword,
        payload,
        retrieved_at=retrieved_at,
        source_locator=source_url,
        freshness=freshness,
    )
    output: list[dict[str, Any]] = []
    for row in rows:
        metrics = row.get("normalized_metrics") or {}
        output.append(
            _with_classification(
                row,
                **_classification(
                    evidence_class="MACRO_TREND",
                    confidence="HIGH",
                    commercial_intent_tier="MACRO_SEARCH",
                    telemetry_kind="HISTORICAL_KEYWORD_METRICS",
                    macro_trend=True,
                    search_volume=metrics.get("avg_monthly_searches"),
                ),
            )
        )
    return output


def _import_policy() -> dict[str, Any]:
    return {
        "official_source": True,
        "structured_source": True,
        "auth_required": True,
        "autocomplete_used": False,
        "dom_scraping_used": False,
        "object_atlas_validity_effect": "NONE",
        "standalone_production_blocking_effect": "NONE",
        "production_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
        "spend_authorized": False,
    }


def normalize_google_trends_macro(
    query: str,
    payload: dict[str, Any],
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    """Normalize only source-provided Google Trends interest-index values."""

    clean_query = _require_nonempty(query, "query")
    if not isinstance(payload, dict):
        raise RuntimeError("E_GOOGLE_TRENDS_JSON_OBJECT_REQUIRED")
    payload_query = payload.get("query")
    if payload_query is not None and str(payload_query).strip().casefold() != clean_query.casefold():
        raise RuntimeError("E_GOOGLE_TRENDS_QUERY_MISMATCH")
    timeline = payload.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise RuntimeError("E_GOOGLE_TRENDS_TIMELINE_REQUIRED")
    points: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for item in timeline:
        if not isinstance(item, dict):
            raise RuntimeError("E_GOOGLE_TRENDS_TIMELINE_ROW")
        date = str(item.get("date") or "").strip()
        value = item.get("value")
        if not date or date in seen_dates or isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise RuntimeError("E_GOOGLE_TRENDS_TIMELINE_VALUE")
        seen_dates.add(date)
        points.append({"date": date, "interest_index": value})
    points.sort(key=lambda row: row["date"])
    raw_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    source_timestamp = payload.get("source_timestamp")
    if source_timestamp is not None and not isinstance(source_timestamp, str):
        raise RuntimeError("E_GOOGLE_TRENDS_SOURCE_TIMESTAMP")
    return {
        "schema": "die.h01.market-signal-evidence.v1",
        "connector_id": GOOGLE_TRENDS_CONNECTOR_ID,
        "evidence_id": evidence_id(GOOGLE_TRENDS_CONNECTOR_ID, f"trends:{clean_query.casefold()}", raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "TREND",
        "freshness": freshness,
        "query": clean_query,
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            "source_first_party": True,
            "evidence_class": "MACRO_TREND",
            "confidence": "MEDIUM",
            "commercial_intent_tier": "MACRO_SEARCH",
            "telemetry_kind": "GOOGLE_TRENDS_INTEREST_INDEX",
            "direct_customer_search_telemetry": False,
            "popular_query_ranking": False,
            "popularity_content_needs_proxy": False,
            "macro_trend": True,
            "observation_period": f"{points[0]['date']}/{points[-1]['date']}",
            "source_timestamp": source_timestamp,
            "period_count": len(points),
            "interest_index_points": points,
            "search_volume": None,
            "visitor_query_count": None,
            "quantitative_customer_search_telemetry": False,
        },
        "policy": _import_policy(),
    }


class _AuthorizedImportRegistry:
    """Narrow capability view for a caller-supplied authorized response.

    H01-131A already owns the persistence and freshness implementation.  The
    existing Google Ads capability intentionally stays AUTH_CONTEXT_REQUIRED
    for ordinary calls; this view activates only the import call for a payload
    supplied by an authorized runtime and cannot add headers or grant authority.
    """

    def __init__(self, base_registry: Any, source_id: str):
        self.base_registry = base_registry
        self.source_id = source_id

    def get(self, source_id: str) -> dict[str, Any]:
        row = self.base_registry.get(source_id)
        if source_id == self.source_id:
            row["adapter_state"] = "ACTIVE"
            row["acquisition_mode"] = "PUBLIC_HTTPS_JSON"
        return row


def _canonical_import_bytes(payload: dict[str, Any]) -> bytes:
    if not isinstance(payload, dict):
        raise ValueError("E_AUTHORIZED_IMPORT_OBJECT_REQUIRED")
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("E_AUTHORIZED_IMPORT_JSON") from exc


def run_google_ads_historical(
    core: AcquisitionCore,
    *,
    keyword: str,
    authorized_payload: dict[str, Any] | None = None,
    source_locator: str = GOOGLE_ADS_IMPORT_URL,
) -> dict[str, Any]:
    """Acquire Google Ads metrics or degrade honestly when auth is absent.

    ``authorized_payload`` must be the response data from a separately
    authorized first-party context.  Supplying no payload invokes the normal
    H01-131A AUTH_CONTEXT_REQUIRED path and performs no network I/O.
    """

    clean_keyword = _require_nonempty(keyword, "keyword")
    request = build_google_ads_import_request(clean_keyword, source_locator=source_locator)
    query_key = f"google-ads:{clean_keyword.casefold()}:historical-metrics-v1"

    def normalize(payload: Any, retrieved_at: str, source_url: str) -> list[dict[str, Any]]:
        return normalize_google_ads_macro(
            clean_keyword,
            payload,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    if authorized_payload is None:
        return core.acquire(
            source_id=GOOGLE_ADS_CONNECTOR_ID,
            query_key=query_key,
            request=request,
            normalizer=normalize,
        )

    import_bytes = _canonical_import_bytes(authorized_payload)

    def import_fetch(_request: dict[str, Any], _capability: dict[str, Any]) -> PublicHttpResponse:
        return PublicHttpResponse(
            body=import_bytes,
            content_type="application/json",
            final_url=request["url"],
        )

    import_core = AcquisitionCore(
        registry=_AuthorizedImportRegistry(core.registry, GOOGLE_ADS_CONNECTOR_ID),
        state_root=core.state_root,
        now_fn=core.now_fn,
        sleep_fn=core.sleep_fn,
        fetch_fn=import_fetch,
    )
    return import_core.acquire(
        source_id=GOOGLE_ADS_CONNECTOR_ID,
        query_key=query_key,
        request=request,
        normalizer=normalize,
    )


def run_google_trends_import(
    core: AcquisitionCore,
    *,
    query: str,
    authorized_payload: dict[str, Any] | None = None,
    source_locator: str = GOOGLE_TRENDS_IMPORT_URL,
) -> dict[str, Any]:
    """Admit Google Trends only through a bounded external import payload."""

    clean_query = _require_nonempty(query, "query")
    request = build_google_trends_import_request(clean_query, source_locator=source_locator)
    query_key = f"google-trends:{clean_query.casefold()}:interest-index-v1"

    def normalize(payload: Any, retrieved_at: str, source_url: str) -> dict[str, Any]:
        return normalize_google_trends_macro(
            clean_query,
            payload,
            retrieved_at=retrieved_at,
            source_url=source_url,
        )

    if authorized_payload is None:
        return core.acquire(
            source_id=GOOGLE_TRENDS_CONNECTOR_ID,
            query_key=query_key,
            request=request,
            normalizer=normalize,
        )

    import_bytes = _canonical_import_bytes(authorized_payload)

    def import_fetch(_request: dict[str, Any], _capability: dict[str, Any]) -> PublicHttpResponse:
        return PublicHttpResponse(
            body=import_bytes,
            content_type="application/json",
            final_url=request["url"],
        )

    import_core = AcquisitionCore(
        registry=_AuthorizedImportRegistry(core.registry, GOOGLE_TRENDS_CONNECTOR_ID),
        state_root=core.state_root,
        now_fn=core.now_fn,
        sleep_fn=core.sleep_fn,
        fetch_fn=import_fetch,
    )
    return import_core.acquire(
        source_id=GOOGLE_TRENDS_CONNECTOR_ID,
        query_key=query_key,
        request=request,
        normalizer=normalize,
    )
