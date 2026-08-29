from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "opportunity-signals"
ADAPTERS = ENGINE / "adapters"
SCHEMA = json.loads((ENGINE / "die.division001.opportunity-signals.v1.schema.json").read_text(encoding="utf-8"))


def _load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load("oe001_validator_b02", ENGINE / "validate_signal_receipt.py")
REGISTRY = _load("oe001_registry_b02", ENGINE / "signal_registry.py")
PUBLIC = _load("oe001_public_fixture_adapter", ADAPTERS / "public_search_ui_fixture.py")
OFFICIAL = _load("oe001_official_fixture_adapter", ADAPTERS / "official_api_fixture.py")


def _raw_public() -> dict:
    return json.loads((ENGINE / "fixtures" / "raw" / "public-search-ui-adobe.json").read_text(encoding="utf-8"))


def _raw_official() -> dict:
    return json.loads((ENGINE / "fixtures" / "raw" / "official-api-interest.json").read_text(encoding="utf-8"))


def _as_of(value: str):
    return VALIDATOR.parse_time(value)


def test_oe001d_public_search_ui_fixture_adapter_is_deterministic_and_valid() -> None:
    a = PUBLIC.adapt(_raw_public())
    b = PUBLIC.adapt(_raw_public())
    assert a == b
    assert a["source"]["source_id"] == "ADOBE_STOCK"
    assert a["signal_class"] == "SUPPLY"
    assert a["signal_type"] == "SEARCH_RESULTS_COUNT"
    assert a["value"]["numeric_value"] == 1842
    assert a["evidence_label"] == "SYNTHETIC"
    assert a["acquisition_method"] == "SYNTHETIC_FIXTURE"
    assert a["policy"]["classification"] == "SYNTHETIC_ONLY"
    assert VALIDATOR.validate(a, SCHEMA, as_of=_as_of("2026-08-29T12:00:00Z")) == []


def test_oe001e_official_api_fixture_adapter_is_deterministic_and_valid() -> None:
    a = OFFICIAL.adapt(_raw_official())
    b = OFFICIAL.adapt(_raw_official())
    assert a == b
    assert a["source"]["source_id"] == "OTHER_APPROVED"
    assert a["signal_class"] == "DEMAND"
    assert a["signal_type"] == "SEARCH_INTEREST_INDEX"
    assert a["value"]["numeric_value"] == 63.5
    assert a["evidence_label"] == "SYNTHETIC"
    assert a["acquisition_method"] == "SYNTHETIC_FIXTURE"
    assert VALIDATOR.validate(a, SCHEMA, as_of=_as_of("2026-08-29T12:00:00Z")) == []


def test_fixture_adapter_can_model_real_source_id_but_cannot_masquerade_as_live() -> None:
    payload = PUBLIC.adapt(_raw_public())
    assert payload["source"]["source_id"] == "ADOBE_STOCK"
    payload["evidence_label"] = "OBSERVED"
    errors = VALIDATOR.validate(payload, SCHEMA, as_of=_as_of("2026-08-29T12:00:00Z"))
    assert "E_SYNTHETIC_BOUNDARY:live_label_on_fixture" in errors


def test_fixture_adapters_reject_invalid_raw_values() -> None:
    bad = _raw_public(); bad["visible_result_count"] = -1
    try:
        PUBLIC.adapt(bad)
    except ValueError as exc:
        assert "non-negative integer" in str(exc)
    else:
        raise AssertionError("negative public result count accepted")
    bad2 = _raw_official(); bad2["search_interest_index"] = 101
    try:
        OFFICIAL.adapt(bad2)
    except ValueError as exc:
        assert "0..100" in str(exc)
    else:
        raise AssertionError("out-of-range index accepted")


def test_registry_inserts_two_independent_sources_and_queries_by_subject(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        a = PUBLIC.adapt(_raw_public()); b = OFFICIAL.adapt(_raw_official())
        assert REGISTRY.ingest(conn, a, as_of=_as_of("2026-08-29T12:00:00Z"))["status"] == "INSERTED"
        assert REGISTRY.ingest(conn, b, as_of=_as_of("2026-08-29T12:00:00Z"))["status"] == "INSERTED"
        assert REGISTRY.count(conn) == 2
        rows = REGISTRY.query(conn, subject_id=a["subject"]["id"], as_of=_as_of("2026-08-29T12:00:00Z"))
        assert len(rows) == 2
        assert {row["source"]["source_id"] for row in rows} == {"ADOBE_STOCK", "OTHER_APPROVED"}
        assert all(row["registry_freshness"] == "FRESH" for row in rows)
    finally:
        conn.close()


def test_registry_duplicate_is_idempotent_and_not_counted_twice(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        payload = PUBLIC.adapt(_raw_public())
        first = REGISTRY.ingest(conn, payload, as_of=_as_of("2026-08-29T12:00:00Z"))
        second = REGISTRY.ingest(conn, payload, as_of=_as_of("2026-08-29T12:00:00Z"))
        assert first["status"] == "INSERTED"
        assert second["status"] == "DUPLICATE"
        assert REGISTRY.count(conn) == 1
    finally:
        conn.close()


def test_registry_detects_dedupe_conflict_instead_of_inflating_evidence(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        payload = PUBLIC.adapt(_raw_public())
        assert REGISTRY.ingest(conn, payload, as_of=_as_of("2026-08-29T12:00:00Z"))["status"] == "INSERTED"
        conflicting = copy.deepcopy(payload)
        conflicting["value"]["numeric_value"] = 999999
        result = REGISTRY.ingest(conn, conflicting, as_of=_as_of("2026-08-29T12:00:00Z"))
        assert result["status"] == "CONFLICT"
        assert result["errors"] == ["E_DEDUPE_CONFLICT"]
        assert REGISTRY.count(conn) == 1
    finally:
        conn.close()


def test_registry_rejects_stale_receipt_at_ingest_time(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        result = REGISTRY.ingest(conn, PUBLIC.adapt(_raw_public()), as_of=_as_of("2026-08-31T12:00:00Z"))
        assert result["status"] == "REJECTED"
        assert "E_SIGNAL_STALE:expired" in result["errors"]
        assert REGISTRY.count(conn) == 0
    finally:
        conn.close()


def test_registry_freshness_query_filters_stale_by_default(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        a = PUBLIC.adapt(_raw_public()); b = OFFICIAL.adapt(_raw_official())
        assert REGISTRY.ingest(conn, a, as_of=_as_of("2026-08-29T12:00:00Z"))["status"] == "INSERTED"
        assert REGISTRY.ingest(conn, b, as_of=_as_of("2026-08-29T12:00:00Z"))["status"] == "INSERTED"
        # Public UI expires Aug 30; official API fixture expires Aug 31.
        fresh = REGISTRY.query(conn, subject_id=a["subject"]["id"], as_of=_as_of("2026-08-30T12:00:00Z"))
        assert len(fresh) == 1 and fresh[0]["source"]["source_id"] == "OTHER_APPROVED"
        all_rows = REGISTRY.query(conn, subject_id=a["subject"]["id"], as_of=_as_of("2026-08-30T12:00:00Z"), include_stale=True)
        assert len(all_rows) == 2
        states = {row["source"]["source_id"]: row["registry_freshness"] for row in all_rows}
        assert states == {"ADOBE_STOCK": "STALE", "OTHER_APPROVED": "FRESH"}
    finally:
        conn.close()


def test_registry_query_filters_source_signal_type_and_parent_candidate(tmp_path: Path) -> None:
    conn = REGISTRY.connect(tmp_path / "signals.db")
    try:
        a = PUBLIC.adapt(_raw_public()); b = OFFICIAL.adapt(_raw_official())
        REGISTRY.ingest(conn, a, as_of=_as_of("2026-08-29T12:00:00Z")); REGISTRY.ingest(conn, b, as_of=_as_of("2026-08-29T12:00:00Z"))
        assert len(REGISTRY.query(conn, source_id="ADOBE_STOCK", as_of=_as_of("2026-08-29T12:00:00Z"))) == 1
        assert len(REGISTRY.query(conn, signal_type="SEARCH_INTEREST_INDEX", as_of=_as_of("2026-08-29T12:00:00Z"))) == 1
        assert len(REGISTRY.query(conn, parent_candidate_id="CAND-FIXTURE-001", as_of=_as_of("2026-08-29T12:00:00Z"))) == 2
    finally:
        conn.close()


def test_oe001_engine_code_has_no_network_collection_dependency() -> None:
    files = list(ADAPTERS.glob("*.py")) + [ENGINE / "signal_registry.py", ENGINE / "validate_signal_receipt.py"]
    forbidden = ("import requests", "import httpx", "urllib.request", "playwright", "selenium", "socket.")
    for path in files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"network collector dependency {token} in {path}"