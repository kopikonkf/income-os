from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CAPABILITY_SCHEMA = "die.h01.market-signal-source-capability.v1"
RECEIPT_SCHEMA = "die.h01.market-signal-acquisition-receipt.v1"
SECRET_HEADER_NAMES = {"authorization", "cookie", "proxy-authorization", "x-api-key", "x-goog-api-key"}
AUTHORITY_FALSE = {
    "credential_read_authorized": False,
    "production_authorized": False,
    "submission_authorized": False,
    "publication_authorized": False,
    "spend_authorized": False,
}
POLICY_FALSE = {
    "source_failure_blocks_production": False,
    "credential_values_read": False,
    "cookies_or_tokens_read": False,
    "production_authorized": False,
    "submission_authorized": False,
    "publication_authorized": False,
    "spend_authorized": False,
}


class AcquisitionPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class PublicHttpResponse:
    body: bytes
    content_type: str
    final_url: str


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def acquisition_id(source_id: str, query_key: str, request_sha256: str, status: str, retrieved_at: str) -> str:
    seed = f"{source_id}\n{query_key}\n{request_sha256}\n{status}\n{retrieved_at}".encode("utf-8")
    return "H01-ACQ-" + hashlib.sha256(seed).hexdigest()[:24].upper()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _immutable_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise AcquisitionPolicyError(f"E_IMMUTABLE_COLLISION:{path.name}")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o640)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def _immutable_json(path: Path, value: dict[str, Any]) -> None:
    _immutable_bytes(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _validate_capability(row: dict[str, Any], *, filename: str | None = None) -> None:
    if row.get("schema") != CAPABILITY_SCHEMA:
        raise AcquisitionPolicyError("E_CAPABILITY_SCHEMA")
    source_id = row.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise AcquisitionPolicyError("E_SOURCE_ID")
    if filename and filename != f"{source_id}.json":
        raise AcquisitionPolicyError(f"E_SOURCE_FILENAME:{filename}")
    if row.get("first_party") is not True or row.get("production_blocking") is not False:
        raise AcquisitionPolicyError("E_SOURCE_POLICY")
    if row.get("authority") != AUTHORITY_FALSE:
        raise AcquisitionPolicyError("E_SOURCE_AUTHORITY")
    hosts = row.get("allowed_hosts")
    if not isinstance(hosts, list) or not hosts or any(not isinstance(x, str) or not x.strip() for x in hosts):
        raise AcquisitionPolicyError("E_ALLOWED_HOSTS")
    if row.get("adapter_state") not in {"ACTIVE", "ADAPTER_PENDING", "AUTH_CONTEXT_REQUIRED", "DISABLED"}:
        raise AcquisitionPolicyError("E_ADAPTER_STATE")
    if row.get("acquisition_mode") not in {"PUBLIC_HTTPS_JSON", "PUBLIC_HTTPS_TEXT", "AUTHORIZED_EXTERNAL_IMPORT"}:
        raise AcquisitionPolicyError("E_ACQUISITION_MODE")
    for field in ("max_requests_per_run", "cache_ttl_seconds", "max_response_bytes"):
        if not isinstance(row.get(field), int) or isinstance(row.get(field), bool) or row[field] <= 0:
            raise AcquisitionPolicyError(f"E_CAPABILITY_INT:{field}")
    interval = row.get("min_interval_seconds")
    if not isinstance(interval, (int, float)) or isinstance(interval, bool) or interval < 0:
        raise AcquisitionPolicyError("E_MIN_INTERVAL")


class SourceCapabilityRegistry:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._rows: dict[str, dict[str, Any]] = {}
        for path in sorted(self.directory.glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            _validate_capability(row, filename=path.name)
            source_id = row["source_id"]
            if source_id in self._rows:
                raise AcquisitionPolicyError(f"E_DUPLICATE_SOURCE:{source_id}")
            self._rows[source_id] = row

    def get(self, source_id: str) -> dict[str, Any]:
        if source_id not in self._rows:
            raise AcquisitionPolicyError(f"E_SOURCE_UNKNOWN:{source_id}")
        return dict(self._rows[source_id])

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in sorted(self._rows.items())}


class SourceLease:
    def __init__(self, path: Path, *, stale_after_seconds: float):
        self.path = path
        self.stale_after_seconds = max(30.0, stale_after_seconds)
        self.acquired = False

    def __enter__(self) -> "SourceLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({"pid": os.getpid(), "created_epoch": time.time()}))
                self.acquired = True
                return self
            except FileExistsError:
                try:
                    age = max(0.0, time.time() - self.path.stat().st_mtime)
                except FileNotFoundError:
                    continue
                if age > self.stale_after_seconds:
                    try:
                        self.path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                return self
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def host_allowed(url: str, allowed_hosts: list[str]) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme != "https" or not host:
        return False
    for allowed in allowed_hosts:
        base = allowed.casefold().rstrip(".")
        if host == base or host.endswith("." + base):
            return True
    return False


def sanitize_request(request: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    method = str(request.get("method") or "GET").upper()
    url = str(request.get("url") or "")
    headers = request.get("headers") or {}
    if method != "GET":
        raise AcquisitionPolicyError("E_PUBLIC_METHOD")
    if not host_allowed(url, capability["allowed_hosts"]):
        raise AcquisitionPolicyError("E_PUBLIC_URL_SCOPE")
    if not isinstance(headers, dict):
        raise AcquisitionPolicyError("E_HEADERS")
    for name in headers:
        if str(name).casefold() in SECRET_HEADER_NAMES:
            raise AcquisitionPolicyError(f"E_SECRET_HEADER:{name}")
    return {
        "method": method,
        "url": url,
        "headers": {str(k): str(v) for k, v in sorted(headers.items(), key=lambda kv: str(kv[0]).casefold())},
    }


def public_http_fetch(request: dict[str, Any], capability: dict[str, Any], *, timeout_seconds: float = 20.0) -> PublicHttpResponse:
    sanitized = sanitize_request(request, capability)
    req = urllib.request.Request(sanitized["url"], headers=sanitized["headers"], method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not host_allowed(final_url, capability["allowed_hosts"]):
                raise RuntimeError("E_REDIRECT_SCOPE")
            content_type = (response.headers.get_content_type() or "application/octet-stream").casefold()
            allowed = {str(x).casefold() for x in capability["allowed_content_types"]}
            if content_type not in allowed:
                raise RuntimeError(f"E_CONTENT_TYPE:{content_type}")
            limit = int(capability["max_response_bytes"])
            body = response.read(limit + 1)
            if len(body) > limit:
                raise RuntimeError("E_RESPONSE_TOO_LARGE")
            return PublicHttpResponse(body=body, content_type=content_type, final_url=final_url)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"E_HTTP_STATUS:{exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"E_HTTP_TRANSPORT:{exc.reason}") from exc


def _decode_response(response: PublicHttpResponse, capability: dict[str, Any]) -> Any:
    mode = capability["acquisition_mode"]
    if mode == "PUBLIC_HTTPS_JSON":
        return json.loads(response.body.decode("utf-8"))
    if mode == "PUBLIC_HTTPS_TEXT":
        return response.body.decode("utf-8")
    raise AcquisitionPolicyError("E_DECODE_MODE")


def _error_payload(code: str, exc: Exception | None = None) -> dict[str, str]:
    detail = "" if exc is None else " ".join(str(exc).split())[:500]
    return {"code": code, "type": type(exc).__name__ if exc else code, "detail": detail}


def _normalize_evidence_result(value: Any) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) else [value]
    output: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise AcquisitionPolicyError("E_NORMALIZER_ROW")
        evidence_id = row.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise AcquisitionPolicyError("E_NORMALIZER_EVIDENCE_ID")
        output.append(row)
    return output


class AcquisitionCore:
    def __init__(
        self,
        *,
        registry: SourceCapabilityRegistry,
        state_root: Path,
        now_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], None] = time.sleep,
        fetch_fn: Callable[[dict[str, Any], dict[str, Any]], PublicHttpResponse] | None = None,
    ):
        self.registry = registry
        self.state_root = Path(state_root)
        self.now_fn = now_fn
        self.sleep_fn = sleep_fn
        self.fetch_fn = fetch_fn or (lambda request, capability: public_http_fetch(request, capability))
        self._request_counts: dict[str, int] = {}

    def _source_root(self, source_id: str) -> Path:
        return self.state_root / "sources" / source_id

    def _query_root(self, source_id: str, query_key: str) -> Path:
        return self._source_root(source_id) / "queries" / hashlib.sha256(query_key.casefold().strip().encode("utf-8")).hexdigest()[:24]

    def _latest_success(self, source_id: str, query_key: str) -> tuple[dict[str, Any], float | None, str | None]:
        pointer = _load_json(self._query_root(source_id, query_key) / "latest-success.json")
        rel = pointer.get("receipt_relative_path")
        epoch = pointer.get("data_retrieved_epoch")
        if not isinstance(rel, str) or not isinstance(epoch, (int, float)):
            return {}, None, None
        receipt = _load_json(self.state_root / rel)
        if not receipt:
            return {}, None, None
        return receipt, float(epoch), rel

    def _write_receipt(self, receipt: dict[str, Any], query_root: Path) -> dict[str, Any]:
        target = query_root / "acquisitions" / f"{receipt['acquisition_id']}.json"
        _immutable_json(target, receipt)
        return receipt

    def _base_receipt(
        self,
        *,
        capability: dict[str, Any],
        query_key: str,
        status: str,
        request_sha256: str,
        source_locator: str,
        retrieved_at: str,
        freshness: str,
        cache_hit: bool,
        cache_age: float | None,
        latest_receipt: str | None,
        raw: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        error: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "task_id": "H01-131A",
            "acquisition_id": acquisition_id(capability["source_id"], query_key, request_sha256, status, retrieved_at),
            "source_id": capability["source_id"],
            "query_key": query_key,
            "status": status,
            "request_sha256": request_sha256,
            "source_locator": source_locator,
            "retrieved_at": retrieved_at,
            "effective_freshness": freshness,
            "cache": {
                "hit": cache_hit,
                "age_seconds": None if cache_age is None else round(max(0.0, cache_age), 6),
                "ttl_seconds": int(capability["cache_ttl_seconds"]),
                "latest_receipt": latest_receipt,
            },
            "raw": raw or {"sha256": None, "bytes": None, "content_type": None, "relative_path": None},
            "evidence": evidence or [],
            "error": error,
            "policy": dict(POLICY_FALSE),
        }
        return receipt

    def acquire(
        self,
        *,
        source_id: str,
        query_key: str,
        request: dict[str, Any],
        normalizer: Callable[[Any, str, str], Any],
    ) -> dict[str, Any]:
        capability = self.registry.get(source_id)
        sanitized = sanitize_request(request, capability)
        request_hash = sha256_value(sanitized)
        source_locator = sanitized["url"]
        query_root = self._query_root(source_id, query_key)
        now_epoch = self.now_fn()
        now_iso = datetime.fromtimestamp(now_epoch, timezone.utc).isoformat().replace("+00:00", "Z")
        cached, cached_epoch, cached_rel = self._latest_success(source_id, query_key)
        cache_age = None if cached_epoch is None else max(0.0, now_epoch - cached_epoch)
        ttl = float(capability["cache_ttl_seconds"])
        if cached and cache_age is not None and cache_age <= ttl:
            receipt = self._base_receipt(
                capability=capability,
                query_key=query_key,
                status="CACHE_HIT_FRESH",
                request_sha256=request_hash,
                source_locator=source_locator,
                retrieved_at=now_iso,
                freshness="FRESH",
                cache_hit=True,
                cache_age=cache_age,
                latest_receipt=cached_rel,
                raw=dict(cached.get("raw") or {}),
                evidence=list(cached.get("evidence") or []),
            )
            return self._write_receipt(receipt, query_root)

        state = capability["adapter_state"]
        if state == "AUTH_CONTEXT_REQUIRED" or capability["acquisition_mode"] == "AUTHORIZED_EXTERNAL_IMPORT":
            receipt = self._base_receipt(
                capability=capability, query_key=query_key, status="DEGRADED_AUTH_REQUIRED",
                request_sha256=request_hash, source_locator=source_locator, retrieved_at=now_iso,
                freshness="STALE" if cached else "UNKNOWN", cache_hit=bool(cached), cache_age=cache_age,
                latest_receipt=cached_rel, raw=dict(cached.get("raw") or {}) if cached else None,
                evidence=list(cached.get("evidence") or []) if cached else None,
                error=_error_payload("E_AUTH_CONTEXT_REQUIRED"),
            )
            return self._write_receipt(receipt, query_root)
        if state != "ACTIVE":
            receipt = self._base_receipt(
                capability=capability, query_key=query_key, status="DEGRADED_ADAPTER_UNAVAILABLE",
                request_sha256=request_hash, source_locator=source_locator, retrieved_at=now_iso,
                freshness="STALE" if cached else "UNKNOWN", cache_hit=bool(cached), cache_age=cache_age,
                latest_receipt=cached_rel, raw=dict(cached.get("raw") or {}) if cached else None,
                evidence=list(cached.get("evidence") or []) if cached else None,
                error=_error_payload("E_ADAPTER_UNAVAILABLE"),
            )
            return self._write_receipt(receipt, query_root)

        count = self._request_counts.get(source_id, 0)
        if count >= int(capability["max_requests_per_run"]):
            raise AcquisitionPolicyError("E_REQUEST_BUDGET")

        source_root = self._source_root(source_id)
        lease_path = source_root / "source.lock"
        with SourceLease(lease_path, stale_after_seconds=max(60.0, float(capability["min_interval_seconds"]) * 4)) as lease:
            if not lease.acquired:
                receipt = self._base_receipt(
                    capability=capability, query_key=query_key, status="DEGRADED_SOURCE_BUSY",
                    request_sha256=request_hash, source_locator=source_locator, retrieved_at=now_iso,
                    freshness="STALE" if cached else "UNKNOWN", cache_hit=bool(cached), cache_age=cache_age,
                    latest_receipt=cached_rel, raw=dict(cached.get("raw") or {}) if cached else None,
                    evidence=list(cached.get("evidence") or []) if cached else None,
                    error=_error_payload("E_SOURCE_BUSY"),
                )
                return self._write_receipt(receipt, query_root)

            source_state_path = source_root / "source-state.json"
            source_state = _load_json(source_state_path)
            last_epoch = source_state.get("last_request_epoch")
            if isinstance(last_epoch, (int, float)):
                wait = float(capability["min_interval_seconds"]) - max(0.0, self.now_fn() - float(last_epoch))
                if wait > 0:
                    self.sleep_fn(wait)
            request_epoch = self.now_fn()
            _atomic_json(source_state_path, {"schema": "die.h01.market-signal-source-state.v1", "source_id": source_id, "last_request_epoch": request_epoch})
            self._request_counts[source_id] = count + 1

            try:
                response = self.fetch_fn(sanitized, capability)
                if not host_allowed(response.final_url, capability["allowed_hosts"]):
                    raise RuntimeError("E_RESPONSE_URL_SCOPE")
                allowed_types = {str(x).casefold() for x in capability["allowed_content_types"]}
                if response.content_type.casefold() not in allowed_types:
                    raise RuntimeError(f"E_CONTENT_TYPE:{response.content_type}")
                if len(response.body) > int(capability["max_response_bytes"]):
                    raise RuntimeError("E_RESPONSE_TOO_LARGE")
                decoded = _decode_response(response, capability)
                retrieved_epoch = self.now_fn()
                retrieved_at = datetime.fromtimestamp(retrieved_epoch, timezone.utc).isoformat().replace("+00:00", "Z")
                evidence_rows = _normalize_evidence_result(normalizer(decoded, retrieved_at, response.final_url))
                raw_hash = sha256_bytes(response.body)
                raw_path = query_root / "raw" / f"{raw_hash}.bin"
                _immutable_bytes(raw_path, response.body)
                evidence_refs: list[dict[str, str]] = []
                for evidence in evidence_rows:
                    evidence_path = query_root / "evidence" / f"{evidence['evidence_id']}.json"
                    _immutable_json(evidence_path, evidence)
                    evidence_refs.append({
                        "evidence_id": evidence["evidence_id"],
                        "sha256": sha256_value(evidence),
                        "relative_path": _relative(evidence_path, self.state_root),
                    })
                raw_ref = {
                    "sha256": raw_hash,
                    "bytes": len(response.body),
                    "content_type": response.content_type,
                    "relative_path": _relative(raw_path, self.state_root),
                }
                receipt = self._base_receipt(
                    capability=capability, query_key=query_key, status="ACQUIRED",
                    request_sha256=request_hash, source_locator=response.final_url, retrieved_at=retrieved_at,
                    freshness="FRESH", cache_hit=False, cache_age=cache_age, latest_receipt=cached_rel,
                    raw=raw_ref, evidence=evidence_refs,
                )
                self._write_receipt(receipt, query_root)
                receipt_path = query_root / "acquisitions" / f"{receipt['acquisition_id']}.json"
                _atomic_json(query_root / "latest-success.json", {
                    "schema": "die.h01.market-signal-latest-success.v1",
                    "source_id": source_id,
                    "query_key": query_key,
                    "data_retrieved_epoch": retrieved_epoch,
                    "receipt_relative_path": _relative(receipt_path, self.state_root),
                    "raw_sha256": raw_hash,
                    "evidence_ids": [x["evidence_id"] for x in evidence_refs],
                })
                return receipt
            except AcquisitionPolicyError:
                raise
            except Exception as exc:
                status = "DEGRADED_STALE_CACHE" if cached else "DEGRADED_NO_EVIDENCE"
                receipt = self._base_receipt(
                    capability=capability, query_key=query_key, status=status,
                    request_sha256=request_hash, source_locator=source_locator, retrieved_at=now_iso,
                    freshness="STALE" if cached else "UNKNOWN", cache_hit=bool(cached), cache_age=cache_age,
                    latest_receipt=cached_rel, raw=dict(cached.get("raw") or {}) if cached else None,
                    evidence=list(cached.get("evidence") or []) if cached else None,
                    error=_error_payload("E_SOURCE_UNAVAILABLE", exc),
                )
                return self._write_receipt(receipt, query_root)
