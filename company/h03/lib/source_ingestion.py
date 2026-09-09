from __future__ import annotations

import hashlib
import html
import re
from html.parser import HTMLParser
from typing import Any

SCHEMA = "die.h03.external-source-snapshot.v1"
_ALLOWED_ACQUISITION = {"WEB_TOOL_SNAPSHOT", "BROWSER_EXPORT", "HTTP_CLIENT", "USER_FILE", "CONNECTOR_EXPORT"}
_ALLOWED_RIGHTS = {"UNKNOWN", "REVIEWED_REFERENCE_ONLY", "REVIEWED_LICENSED_REUSE", "USER_OWNED_ORIGINAL"}
_ALLOWED_REVIEWERS = {"FOUNDER", "ARCHITECT", "GOVERNED_RULESET"}
_FORBIDDEN_REVIEWERS = {"LLM", "CRAWLER", "PROVIDER_MODEL", "WEB_AI"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _VisibleTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip += 1
        elif tag.lower() in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        elif tag.lower() in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _normalize_text(raw: bytes, media_type: str) -> str:
    decoded = raw.decode("utf-8", errors="replace")
    if media_type == "text/plain":
        text = decoded
    elif media_type == "text/html":
        parser = _VisibleTextHTMLParser()
        parser.feed(decoded)
        text = html.unescape("".join(parser.parts))
    else:
        raise ValueError("UNSUPPORTED_MEDIA_TYPE")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _chunk_evidence(source_id: str, normalized: str, raw_sha: str, max_chars: int = 700) -> list[dict[str, Any]]:
    paragraphs = [p.strip() for p in normalized.split("\n") if p.strip()]
    if not paragraphs:
        raise ValueError("NO_VISIBLE_SOURCE_TEXT")
    units: list[dict[str, Any]] = []
    for p in paragraphs:
        pieces: list[str] = []
        remaining = p
        while len(remaining) > max_chars:
            split = remaining.rfind(" ", 0, max_chars + 1)
            if split < max_chars // 2:
                split = max_chars
            pieces.append(remaining[:split].strip())
            remaining = remaining[split:].strip()
        if remaining:
            pieces.append(remaining)
        for piece in pieces:
            eid = f"{source_id}-E{len(units)+1:04d}"
            units.append({
                "evidence_id": eid,
                "text": piece,
                "sha256": sha256_bytes(piece.encode("utf-8")),
                "source_raw_sha256": raw_sha,
            })
    return units


def ingest_external_bytes(*, source_id: str, source_uri: str, raw_bytes: bytes, media_type: str,
                          acquisition_method: str, rights_state: str = "UNKNOWN", rights_basis: str = "",
                          verbatim_reuse_allowed: bool = False) -> dict[str, Any]:
    if not source_id or not source_uri:
        raise ValueError("SOURCE_IDENTITY_REQUIRED")
    if acquisition_method not in _ALLOWED_ACQUISITION:
        raise ValueError("ACQUISITION_METHOD_INVALID")
    if rights_state not in _ALLOWED_RIGHTS:
        raise ValueError("RIGHTS_STATE_INVALID")
    raw_sha = sha256_bytes(raw_bytes)
    normalized = _normalize_text(raw_bytes, media_type)
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "source_uri": source_uri,
        "media_type": media_type,
        "acquisition_method": acquisition_method,
        "raw_sha256": raw_sha,
        "normalized_text_sha256": sha256_bytes(normalized.encode("utf-8")),
        "review_state": "PENDING_REVIEW",
        "canonical_truth": False,
        "rights_policy": {
            "state": rights_state,
            "basis": rights_basis,
            "verbatim_reuse_allowed": bool(verbatim_reuse_allowed),
        },
        "evidence_units": _chunk_evidence(source_id, normalized, raw_sha),
    }


def approve_for_knowledge(snapshot: dict[str, Any], *, reviewer_kind: str, reviewer_id: str,
                          decision_basis: str) -> dict[str, Any]:
    if snapshot.get("schema_version") != SCHEMA or snapshot.get("review_state") != "PENDING_REVIEW":
        raise ValueError("SNAPSHOT_STATE_INVALID")
    rk = reviewer_kind.upper()
    if rk in _FORBIDDEN_REVIEWERS or rk not in _ALLOWED_REVIEWERS:
        raise ValueError("REVIEWER_AUTHORITY_FORBIDDEN")
    rights = snapshot.get("rights_policy") or {}
    if rights.get("state") == "UNKNOWN":
        raise ValueError("RIGHTS_REVIEW_REQUIRED")
    if not reviewer_id or not decision_basis:
        raise ValueError("REVIEW_EVIDENCE_REQUIRED")
    return {
        "source_id": snapshot["source_id"],
        "source_uri": snapshot["source_uri"],
        "rights_status": "GOVERNED_EXTERNAL",
        "raw_sha256": snapshot["raw_sha256"],
        "normalized_text_sha256": snapshot["normalized_text_sha256"],
        "acquisition_method": snapshot["acquisition_method"],
        "rights_policy": rights,
        "review": {
            "status": "ACCEPTED_FOR_KNOWLEDGE",
            "reviewer_kind": rk,
            "reviewer_id": reviewer_id,
            "decision_basis": decision_basis,
            "crawler_or_llm_authority": False,
        },
        "canonical_truth": False,
        "evidence_units": snapshot["evidence_units"],
    }
