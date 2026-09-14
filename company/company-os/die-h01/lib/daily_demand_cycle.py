from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from demand_signal_contract import validate_record
from demand_signal_materializer import load_capabilities, load_evidence, materialize, sha256_value
from macro_search_trend_signal import run_google_ads_historical, run_wikimedia_attention
from market_signal_acquisition import AcquisitionCore, SourceCapabilityRegistry
from rf123_market_signal import run_123rf

SCHEMA = "die.h01.daily-demand-intelligence-cycle.v1"
RECEIPT_SCHEMA = "die.h01.h01-133a.daily-demand-cycle.receipt.v1"
REFRESH_RECEIPT_SCHEMA = "die.h01.h01-133a.refresh-attempt.v1"
POLICY_VERSION = "H01-133A-V1"
DEFAULT_CONNECTORS = ("123rf_trending_search_v1", "wikimedia_pageviews_v1", "google_ads_keyword_historical_v1")
AUTHORITY_FALSE = {
    "production_authorized": False,
    "submission_authorized": False,
    "publication_authorized": False,
    "spend_authorized": False,
}


class DailyDemandCycleError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def complete_utc_window(day_key: str, days: int = 7) -> tuple[str, str]:
    if not 1 <= days <= 90:
        raise ValueError("E_WINDOW_DAYS")
    target = date.fromisoformat(day_key)
    end = target - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return start.strftime("%Y%m%d00"), end.strftime("%Y%m%d00")


def _safe_refresh(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = fn()
        return {
            "source": name,
            "status": str(payload.get("status") or "UNKNOWN"),
            "acquisition_id": payload.get("acquisition_id"),
            "evidence_ids": sorted(
                str(row.get("evidence_id"))
                for row in payload.get("evidence") or []
                if isinstance(row, dict) and row.get("evidence_id")
            ),
            "error": payload.get("error"),
        }
    except Exception as exc:  # source errors are fail-soft by task contract
        return {
            "source": name,
            "status": "DEGRADED_REFRESH_EXCEPTION",
            "acquisition_id": None,
            "evidence_ids": [],
            "error": {"type": type(exc).__name__, "message": str(exc)[:1000]},
        }


def refresh_default_sources(
    *,
    state_root: Path,
    registry_dir: Path,
    day_key: str,
    article: str = "Cat",
    keyword: str = "cat",
    core: AcquisitionCore | None = None,
) -> list[dict[str, Any]]:
    core = core or AcquisitionCore(
        registry=SourceCapabilityRegistry(Path(registry_dir)),
        state_root=Path(state_root),
    )
    start, end = complete_utc_window(day_key, 7)
    return [
        _safe_refresh("123rf_trending_search_v1", lambda: run_123rf(core)),
        _safe_refresh(
            "wikimedia_pageviews_v1",
            lambda: run_wikimedia_attention(core, article=article, start_yyyymmddhh=start, end_yyyymmddhh=end),
        ),
        _safe_refresh(
            "google_ads_keyword_historical_v1",
            lambda: run_google_ads_historical(core, keyword=keyword),
        ),
    ]


def _validate_materialization(materialization: dict[str, Any]) -> None:
    bad = []
    for record in materialization.get("records") or []:
        errors = validate_record(record)
        if errors:
            bad.append({"queue_item_id": record.get("queue_item_id"), "errors": errors})
    if bad:
        raise DailyDemandCycleError("E_MATERIALIZATION_INVALID:" + json.dumps(bad[:10], sort_keys=True))


def _write_immutable_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != body:
            raise DailyDemandCycleError(f"E_IMMUTABLE_COLLISION:{path}")
        return
    path.write_text(body, encoding="utf-8")


def _write_latest_pointer(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_cycle(
    *,
    queue_rows: list[dict[str, Any]],
    produced: set[str],
    evidence_rows: list[dict[str, Any]],
    capabilities: dict[str, dict[str, Any]],
    day_key: str,
    selector_builder: Callable[..., dict[str, Any]],
    limit: int = 100,
    providers: tuple[str, ...] = ("gemini", "qwen", "claude", "chatgpt", "manus", "copilot"),
) -> dict[str, Any]:
    materialization = materialize(queue_rows, evidence_rows, capabilities)
    _validate_materialization(materialization)
    demand_map = {str(row["queue_item_id"]): row for row in materialization["records"]}
    selector = selector_builder(
        queue_rows,
        produced=produced,
        demand=demand_map,
        connectors={},
        contexts={},
        limit=limit,
        providers=providers,
        day_key=day_key,
    )
    if selector.get("status") != "FROZEN":
        raise DailyDemandCycleError("E_SELECTOR_NOT_FROZEN")
    identity = {
        "policy_version": POLICY_VERSION,
        "day_key": day_key,
        "materialization_id": materialization["materialization_id"],
        "selection_id": selector["selection_id"],
        "queue_item_ids": [str(row.get("queue_item_id")) for row in queue_rows],
        "produced_queue_item_ids": sorted(produced),
    }
    cycle_id = "H01-DCYCLE-" + sha(identity)[:24].upper()
    return {
        "schema": SCHEMA,
        "policy_version": POLICY_VERSION,
        "status": "FROZEN",
        "cycle_id": cycle_id,
        "day_key": day_key,
        "materialization": materialization,
        "selector": selector,
        "policy": {
            "source_refresh_failure_blocks_cycle": False,
            "missing_evidence_blocks_standalone_production": False,
            "no_evidence_selector_policy": "SOURCE_ORDER_FALLBACK",
            "queue_identity_mutated": False,
            "object_atlas_validity_mutated": False,
            "rights_mutated": False,
            "feasibility_mutated": False,
            "generation_validity_mutated": False,
        },
        "authority": dict(AUTHORITY_FALSE),
    }


def persist_cycle(
    cycle: dict[str, Any],
    *,
    output_root: Path,
    queue_path: Path,
    effective_evidence_rows: list[dict[str, Any]],
    refresh_results: list[dict[str, Any]],
) -> dict[str, Any]:
    day_root = Path(output_root) / cycle["day_key"]
    cycle_root = day_root / cycle["cycle_id"]
    demand_path = cycle_root / "demand-signal-ranking.v1.json"
    selector_path = cycle_root / "daily-selector.frozen.json"
    receipt_path = cycle_root / "cycle.receipt.json"

    _write_immutable_json(demand_path, cycle["materialization"])
    _write_immutable_json(selector_path, cycle["selector"])

    evidence_refs = sorted(
        {
            (str(row.get("connector_id") or ""), str(row.get("evidence_id") or ""), str(row.get("evidence_sha256") or ""))
            for row in effective_evidence_rows
            if row.get("evidence_id")
        }
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "task_id": "H01-133A",
        "status": "PASS",
        "cycle_id": cycle["cycle_id"],
        "day_key": cycle["day_key"],
        "policy_version": POLICY_VERSION,
        "queue": {"path": str(queue_path), "sha256": file_sha256(queue_path), "row_count": cycle["materialization"]["source_queue_item_count"]},
        "evidence": {
            "record_count": len(effective_evidence_rows),
            "refs": [
                {"connector_id": connector_id, "evidence_id": evidence_id, "evidence_sha256": evidence_sha}
                for connector_id, evidence_id, evidence_sha in evidence_refs
            ],
        },
        "materialization": {
            "materialization_id": cycle["materialization"]["materialization_id"],
            "ranked_count": cycle["materialization"]["ranked_count"],
            "unranked_count": cycle["materialization"]["unranked_count"],
            "path": str(demand_path),
            "sha256": file_sha256(demand_path),
        },
        "selector": {
            "selection_id": cycle["selector"]["selection_id"],
            "selected": len(cycle["selector"]["items"]),
            "ranked_selected": cycle["selector"]["selection"]["ranked_selected"],
            "fallback_selected": cycle["selector"]["selection"]["fallback_selected"],
            "path": str(selector_path),
            "sha256": file_sha256(selector_path),
        },
        "policy": dict(cycle["policy"]),
        "authority": dict(AUTHORITY_FALSE),
    }
    _write_immutable_json(receipt_path, receipt)

    refresh_receipt = {
        "schema": REFRESH_RECEIPT_SCHEMA,
        "cycle_id": cycle["cycle_id"],
        "day_key": cycle["day_key"],
        "status": "PASS" if all(not str(row.get("status") or "").startswith("DEGRADED_REFRESH_EXCEPTION") for row in refresh_results) else "DEGRADED",
        "source_results": refresh_results,
        "source_failure_blocks_cycle": False,
        "authority": dict(AUTHORITY_FALSE),
    }
    attempt_id = "H01-DREFRESH-" + sha(refresh_receipt)[:24].upper()
    refresh_path = day_root / "refresh-attempts" / f"{attempt_id}.json"
    _write_immutable_json(refresh_path, {**refresh_receipt, "attempt_id": attempt_id})

    latest = {
        "schema": "die.h01.daily-demand-intelligence-latest.v1",
        "day_key": cycle["day_key"],
        "cycle_id": cycle["cycle_id"],
        "cycle_receipt": str(receipt_path),
        "refresh_attempt_receipt": str(refresh_path),
        "selection_id": cycle["selector"]["selection_id"],
    }
    _write_latest_pointer(day_root / "latest.json", latest)
    return {"receipt": receipt, "refresh_receipt": {**refresh_receipt, "attempt_id": attempt_id}, "paths": latest}
