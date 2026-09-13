from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA = "die.h01.market-signal-evidence.v1"


@dataclass(frozen=True)
class ConnectorPolicy:
    connector_id: str
    source_name: str
    access_mode: str
    auth_mode: str
    signal_classes: tuple[str, ...]
    max_requests_per_run: int
    min_interval_seconds: float
    cache_ttl_seconds: int
    official: bool = True
    autocomplete_core_dependency: bool = False
    dom_scraping_core_dependency: bool = False


REGISTRY: dict[str, ConnectorPolicy] = {
    "wikimedia_pageviews_v1": ConnectorPolicy(
        connector_id="wikimedia_pageviews_v1",
        source_name="Wikimedia Analytics API",
        access_mode="OFFICIAL_OPEN_API",
        auth_mode="NONE",
        signal_classes=("TREND",),
        max_requests_per_run=12,
        min_interval_seconds=1.0,
        cache_ttl_seconds=86400,
    ),
    "google_ads_keyword_historical_v1": ConnectorPolicy(
        connector_id="google_ads_keyword_historical_v1",
        source_name="Google Ads KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics",
        access_mode="OFFICIAL_AUTH_REQUIRED_API",
        auth_mode="OAUTH2_PLUS_DEVELOPER_TOKEN",
        signal_classes=("DEMAND", "COMPETITION", "COMMERCIAL_INTENT"),
        max_requests_per_run=12,
        min_interval_seconds=1.0,
        cache_ttl_seconds=2592000,
    ),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def evidence_id(connector_id: str, query_key: str, raw_sha256: str) -> str:
    seed = f"{connector_id}\n{query_key}\n{raw_sha256}".encode("utf-8")
    return "H01-SIG-" + hashlib.sha256(seed).hexdigest()[:24].upper()


def connector_registry() -> dict[str, dict[str, Any]]:
    return {key: asdict(value) for key, value in sorted(REGISTRY.items())}


def build_wikimedia_pageviews_request(
    article: str,
    start_yyyymmdd: str,
    end_yyyymmdd: str,
    *,
    project: str = "en.wikipedia.org",
) -> dict[str, Any]:
    if not article.strip():
        raise ValueError("E_ARTICLE_REQUIRED")
    title = urllib.parse.quote(article.strip().replace(" ", "_"), safe="")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{project}/all-access/user/{title}/daily/{start_yyyymmdd}/{end_yyyymmdd}"
    )
    return {
        "connector_id": "wikimedia_pageviews_v1",
        "method": "GET",
        "url": url,
        "headers": {
            "User-Agent": "DIE-H01/1.0 (market-signal research; operator contact configured at deployment)"
        },
        "max_requests_per_run": REGISTRY["wikimedia_pageviews_v1"].max_requests_per_run,
        "min_interval_seconds": REGISTRY["wikimedia_pageviews_v1"].min_interval_seconds,
    }


def normalize_wikimedia_pageviews(
    article: str,
    payload: dict[str, Any],
    *,
    retrieved_at: str,
    source_url: str,
    freshness: str = "FRESH",
) -> dict[str, Any]:
    items = payload.get("items") or []
    views = [row.get("views") for row in items if isinstance(row, dict)]
    views = [value for value in views if isinstance(value, int) and value >= 0]
    raw_hash = sha256_hex(payload)
    query_key = "wiki:" + article.strip().casefold()
    total = sum(views)
    return {
        "schema": SCHEMA,
        "connector_id": "wikimedia_pageviews_v1",
        "evidence_id": evidence_id("wikimedia_pageviews_v1", query_key, raw_hash),
        "evidence_sha256": raw_hash,
        "signal_class": "TREND",
        "freshness": freshness,
        "query": article.strip(),
        "retrieved_at": retrieved_at,
        "source_locator": source_url,
        "normalized_metrics": {
            "period_count": len(views),
            "pageviews_total": total,
            "pageviews_mean": total / len(views) if views else None,
        },
        "policy": _policy_flags(auth_required=False),
    }


def normalize_google_ads_historical(
    keyword: str,
    payload: dict[str, Any],
    *,
    retrieved_at: str,
    source_locator: str = "googleads:KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics",
    freshness: str = "FRESH",
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in payload.get("results") or []:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("keyword") or keyword).strip()
        metrics = row.get("keywordMetrics") or row.get("keyword_metrics") or {}
        raw = {"text": text, "metrics": metrics}
        raw_hash = sha256_hex(raw)
        query_key = "gads:" + text.casefold()
        output.append(
            {
                "schema": SCHEMA,
                "connector_id": "google_ads_keyword_historical_v1",
                "evidence_id": evidence_id("google_ads_keyword_historical_v1", query_key, raw_hash),
                "evidence_sha256": raw_hash,
                "signal_class": "DEMAND",
                "freshness": freshness,
                "query": text,
                "retrieved_at": retrieved_at,
                "source_locator": source_locator,
                "normalized_metrics": {
                    "avg_monthly_searches": _metric(metrics, "avgMonthlySearches", "avg_monthly_searches"),
                    "competition_index": _metric(metrics, "competitionIndex", "competition_index"),
                    "low_top_of_page_bid_micros": _metric(metrics, "lowTopOfPageBidMicros", "low_top_of_page_bid_micros"),
                    "high_top_of_page_bid_micros": _metric(metrics, "highTopOfPageBidMicros", "high_top_of_page_bid_micros"),
                },
                "policy": _policy_flags(auth_required=True),
            }
        )
    return output


def to_h01_130_ref(evidence: dict[str, Any]) -> dict[str, str]:
    return {
        "evidence_id": evidence["evidence_id"],
        "evidence_sha256": evidence["evidence_sha256"],
        "signal_class": evidence["signal_class"],
        "freshness": evidence["freshness"],
    }


def _metric(metrics: dict[str, Any], camel: str, snake: str) -> Any:
    return metrics.get(camel, metrics.get(snake))


def _policy_flags(*, auth_required: bool) -> dict[str, Any]:
    return {
        "official_source": True,
        "structured_source": True,
        "auth_required": auth_required,
        "autocomplete_used": False,
        "dom_scraping_used": False,
        "object_atlas_validity_effect": "NONE",
        "standalone_production_blocking_effect": "NONE",
        "production_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
        "spend_authorized": False,
    }
