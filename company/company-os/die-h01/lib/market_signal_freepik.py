from __future__ import annotations

from typing import Any

SOURCE_ID = "freepik_trending_vector_searches_v1"
SOURCE_NAME = "Freepik/Magnific Trending Vector Searches"
SOURCE_URL = "https://www.magnific.com/vectors"
QUERY_KEY = "freepik:trending-vector-searches:vector:en"
EVIDENCE_CLASS = "MARKETPLACE_POPULAR_QUERY"
MEDIA_TYPE = "VECTOR"
BLOCK_REASON_CODE = "E_FREEPIK_AUTOMATED_TREND_ACQUISITION_NOT_COMPLIANT"
BLOCK_REASON = (
    "The first-party web page exposes a Trending Vector Searches section, but Magnific's "
    "current Acceptable Use Policy prohibits automation, bots, scraping, and automated "
    "extraction of content or metadata. The documented Stock Content API requires an API "
    "key and exposes resource search/listing rather than trending-search-term telemetry."
)


def build_freepik_trending_vector_request() -> dict[str, Any]:
    """Return the bounded first-party locator used by the fail-soft acquisition guard.

    The capability is intentionally ADAPTER_PENDING. AcquisitionCore therefore emits a
    DEGRADED_ADAPTER_UNAVAILABLE receipt before network I/O. No browser/session/account
    context, Cookie, Authorization header, API key, submission, publication, or spend
    capability is used.
    """
    return {
        "method": "GET",
        "url": SOURCE_URL,
        "headers": {
            "Accept": "text/html",
            "User-Agent": "DIE-H01/1.0 market-signal capability probe",
        },
    }


def acquire_freepik_trending_vectors(core: Any) -> dict[str, Any]:
    """Fail soft through H01-131A until a compliant first-party trend-term surface exists."""

    def unreachable_normalizer(payload: Any, retrieved_at: str, source_url: str) -> list[dict[str, Any]]:
        raise RuntimeError(BLOCK_REASON_CODE)

    return core.acquire(
        source_id=SOURCE_ID,
        query_key=QUERY_KEY,
        request=build_freepik_trending_vector_request(),
        normalizer=unreachable_normalizer,
    )


def evidence_semantics() -> dict[str, Any]:
    """Declare the only evidence class this task may emit once compliant acquisition exists."""
    return {
        "source_id": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "evidence_class": EVIDENCE_CLASS,
        "media_type": MEDIA_TYPE,
        "direct_customer_search_telemetry": False,
        "popular_query_ranking": True,
        "popularity_content_needs_proxy": False,
        "macro_trend": False,
        "query_volume_available": False,
        "visitor_query_count_available": False,
        "provenance_confidence_if_first_party_observed": "HIGH",
        "quantitative_confidence": "NONE",
        "commercial_signal_confidence": "MEDIUM_HIGH",
        "adapter_state": "ADAPTER_PENDING",
        "block_reason_code": BLOCK_REASON_CODE,
        "block_reason": BLOCK_REASON,
    }
