from __future__ import annotations

import ipaddress
import socket
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import source_ingestion

BUNDLE_SCHEMA = "die.h03.live-verified-source-bundle.v1"
_ALLOWED_SOURCE_CLASSES = {
    "OFFICIAL_PRIMARY", "ACADEMIC_PAPER", "GOVERNMENT_PUBLIC_DATA",
    "SPECIALIST_PUBLICATION", "MARKETPLACE_LISTING", "CUSTOMER_REVIEW",
    "COMMUNITY_DISCUSSION", "SEARCH_DEMAND", "COMPETITOR_PRODUCT",
}


def validate_public_url(url: str, *, resolver: Callable[..., Any] = socket.getaddrinfo) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("LIVE_SOURCE_URL_REQUIRED")
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("LIVE_SOURCE_URL_SCHEME_INVALID")
    if parsed.username or parsed.password:
        raise ValueError("LIVE_SOURCE_URL_USERINFO_FORBIDDEN")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("LIVE_SOURCE_URL_PORT_FORBIDDEN")
    host = parsed.hostname.strip().lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("LIVE_SOURCE_PRIVATE_HOST_FORBIDDEN")
    try:
        infos = resolver(host, parsed.port or (443 if parsed.scheme.lower() == "https" else 80), type=socket.SOCK_STREAM)
    except Exception as exc:
        raise ValueError("LIVE_SOURCE_DNS_RESOLUTION_FAILED") from exc
    addresses = {row[4][0] for row in infos if row and row[4]}
    if not addresses:
        raise ValueError("LIVE_SOURCE_DNS_EMPTY")
    for value in addresses:
        ip = ipaddress.ip_address(value)
        if not ip.is_global:
            raise ValueError("LIVE_SOURCE_PRIVATE_ADDRESS_FORBIDDEN")
    return url.strip()


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _select_evidence_units(units: list[dict[str, Any]], relevance_terms: list[str], max_units: int) -> list[dict[str, Any]]:
    if max_units < 1:
        raise ValueError("LIVE_SOURCE_MAX_UNITS_INVALID")
    terms = [" ".join(str(term).lower().split()) for term in relevance_terms if str(term).strip()]
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, unit in enumerate(units):
        text = " ".join(str(unit.get("text", "")).lower().split())
        score = sum(1 for term in terms if term and term in text)
        scored.append((score, -index, unit))
    if terms:
        ranked = [row[2] for row in sorted(scored, key=lambda row: (row[0], row[1]), reverse=True)]
        chosen = ranked[:max_units]
        # Restore source order for readable downstream context.
        order = {unit.get("evidence_id"): i for i, unit in enumerate(units)}
        return sorted(chosen, key=lambda unit: order.get(unit.get("evidence_id"), 10**9))
    return list(units[:max_units])


def fetch_public_reference(
    *,
    source_id: str,
    url: str,
    source_class: str,
    relevance_terms: list[str] | None = None,
    timeout_seconds: float = 15.0,
    max_bytes: int = 250_000,
    max_evidence_units: int = 5,
    opener: Any | None = None,
) -> dict[str, Any]:
    if not source_id or source_class not in _ALLOWED_SOURCE_CLASSES:
        raise ValueError("LIVE_SOURCE_ID_OR_CLASS_INVALID")
    safe_url = validate_public_url(url)
    request = Request(
        safe_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    client = opener or build_opener(_SafeRedirectHandler())
    with client.open(request, timeout=timeout_seconds) as response:
        final_url = validate_public_url(response.geturl())
        content_type = str(response.headers.get_content_type()).lower()
        if content_type not in {"text/html", "text/plain"}:
            raise ValueError("LIVE_SOURCE_CONTENT_TYPE_UNSUPPORTED")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("LIVE_SOURCE_MAX_BYTES_EXCEEDED")
        if not raw.strip():
            raise ValueError("LIVE_SOURCE_EMPTY")

    snapshot = source_ingestion.ingest_external_bytes(
        source_id=source_id,
        source_uri=final_url,
        raw_bytes=raw,
        media_type=content_type,
        acquisition_method="HTTP_CLIENT",
        rights_state="REVIEWED_REFERENCE_ONLY",
        rights_basis="Public factual reference only; no verbatim reuse in the H03 product.",
        verbatim_reuse_allowed=False,
    )
    governed = source_ingestion.approve_for_knowledge(
        snapshot,
        reviewer_kind="GOVERNED_RULESET",
        reviewer_id="H03-LIVE-SOURCE-GATE-V1",
        decision_basis=(
            "Fetched from a public HTTP(S) origin after public-network validation; retained as factual reference only; "
            "verbatim reuse forbidden; Web-AI does not own review authority."
        ),
    )
    governed["source_class"] = source_class
    governed["evidence_units"] = _select_evidence_units(
        governed["evidence_units"], relevance_terms or [], max_evidence_units
    )
    if not governed["evidence_units"]:
        raise ValueError("LIVE_SOURCE_NO_EVIDENCE_AFTER_SELECTION")
    return governed


def verify_source_bundle(
    *,
    run_id: str,
    source_requests: list[dict[str, Any]],
    max_sources: int = 12,
    fetcher: Callable[..., dict[str, Any]] = fetch_public_reference,
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("LIVE_SOURCE_RUN_ID_REQUIRED")
    if not isinstance(source_requests, list) or not source_requests:
        raise ValueError("LIVE_SOURCE_REQUESTS_REQUIRED")
    accepted: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    for raw in source_requests[:max_sources]:
        source_id = str(raw.get("source_id") or "").strip()
        url = str(raw.get("url") or raw.get("source_uri") or "").strip()
        source_class = str(raw.get("source_class") or "").strip()
        if source_id in seen_ids or url in seen_urls:
            continue
        if not source_id or not url:
            failures.append({"source_id": source_id or "UNKNOWN", "url": url or "UNKNOWN", "error": "SOURCE_ID_OR_URL_MISSING"})
            continue
        seen_ids.add(source_id)
        seen_urls.add(url)
        try:
            snapshot = fetcher(
                source_id=source_id,
                url=url,
                source_class=source_class,
                relevance_terms=list(raw.get("relevance_terms") or []),
            )
            snapshot["candidate_id"] = raw.get("candidate_id")
            snapshot["signal_hint"] = raw.get("signal_hint")
            accepted.append(snapshot)
        except Exception as exc:
            failures.append({"source_id": source_id, "url": url, "error": f"{type(exc).__name__}:{exc}"[:500]})
    return {
        "schema_version": BUNDLE_SCHEMA,
        "holding_id": "H03",
        "run_id": run_id,
        "verified_sources": accepted,
        "failures": failures,
        "verified_count": len(accepted),
        "requested_count": min(len(source_requests), max_sources),
        "truth_status": "VERIFIED_PUBLIC_REFERENCE_SNAPSHOTS",
    }
