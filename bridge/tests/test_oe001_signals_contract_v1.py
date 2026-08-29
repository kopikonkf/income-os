from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "opportunity-signals"
SCHEMA = ENGINE / "die.division001.opportunity-signals.v1.schema.json"
FIXTURE = ENGINE / "fixtures" / "valid-search-results-count.json"
VALIDATOR = ENGINE / "validate_signal_receipt.py"
TAXONOMY = ENGINE / "SIGNAL_TAXONOMY_V1.md"
ACQUISITION = ENGINE / "ACQUISITION_CONTRACT_V1.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("oe001_signal_validator", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _errors(payload: dict, as_of: str = "2026-08-29T12:00:00Z") -> list[str]:
    module = _load_validator()
    return module.validate(payload, _schema(), as_of=module.parse_time(as_of))


def test_oe001_schema_and_valid_fixture_pass() -> None:
    schema = _schema()
    assert schema["$id"].endswith("die.division001.opportunity-signals.v1.schema.json")
    assert schema["additionalProperties"] is False
    assert _errors(_payload()) == []


def test_oe001_signal_is_observation_not_score_or_decision() -> None:
    text = TAXONOMY.read_text(encoding="utf-8")
    assert "evidence input" in text
    assert "not a Demand Score" in text
    assert "Worth-Making" in text
    assert "production authority" in text
    assert "Adapters MUST NOT convert UNKNOWN into zero" in text


def test_oe001_taxonomy_covers_demand_supply_competition_commercial_trend_and_fit() -> None:
    schema = _schema()
    classes = set(schema["properties"]["signal_class"]["enum"])
    assert classes == {"DEMAND", "SUPPLY", "COMPETITION", "COMMERCIAL_INTENT", "TREND", "PLATFORM_FIT"}
    kinds = set(schema["properties"]["value"]["properties"]["kind"]["enum"])
    assert {"COUNT", "RANK", "RATIO", "INDEX", "DELTA", "BOOLEAN", "TEXT"} <= kinds


def test_oe001_schema_rejects_negative_count() -> None:
    payload = _payload()
    payload["value"]["numeric_value"] = -1
    assert any(e.startswith("E_SCHEMA:") for e in _errors(payload))


def test_oe001_validator_rejects_stale_receipt() -> None:
    assert "E_SIGNAL_STALE:expired" in _errors(_payload(), as_of="2026-08-31T00:00:00Z")


def test_oe001_validator_rejects_policy_method_mismatch() -> None:
    payload = _payload()
    payload["policy"]["classification"] = "OFFICIAL_API_ONLY"
    assert "E_POLICY_METHOD:OFFICIAL_API_ONLY:SYNTHETIC_FIXTURE" in _errors(payload)


def test_oe001_validator_rejects_synthetic_receipt_labeled_live() -> None:
    payload = _payload()
    payload["evidence_label"] = "OBSERVED"
    assert "E_SYNTHETIC_BOUNDARY:live_label_on_fixture" in _errors(payload)


def test_oe001_validator_rejects_signal_class_type_mismatch() -> None:
    payload = _payload()
    payload["signal_class"] = "DEMAND"
    assert "E_SIGNAL_CLASS_TYPE:DEMAND:SEARCH_RESULTS_COUNT" in _errors(payload)


def test_oe001_validator_rejects_wrong_value_kind_for_signal_type() -> None:
    payload = _payload()
    payload["value"] = {"kind": "BOOLEAN", "numeric_value": None, "boolean_value": True, "text_value": None, "unit": "presence"}
    assert "E_SIGNAL_VALUE_KIND:SEARCH_RESULTS_COUNT:expected_COUNT" in _errors(payload)


def test_oe001_validator_rejects_inconsistent_freshness_window() -> None:
    payload = _payload()
    payload["freshness_window_seconds"] = 3600
    assert "E_FRESHNESS_WINDOW:mismatch" in _errors(payload)


def test_oe001_acquisition_contract_is_fail_closed_and_separates_submission_policy() -> None:
    text = ACQUISITION.read_text(encoding="utf-8")
    for phrase in (
        "extract cookies",
        "private/internal backend endpoints",
        "bypass CAPTCHA",
        "stealth/fingerprinting evasion",
        "rate limits",
        "does **not** automatically authorize",
        "Unknown policy is fail-closed",
    ):
        assert phrase in text


def test_oe001_b01_contains_no_live_collector_network_implementation() -> None:
    validator = VALIDATOR.read_text(encoding="utf-8")
    forbidden_imports = ("import requests", "import httpx", "playwright", "selenium", "urllib.request")
    for token in forbidden_imports:
        assert token not in validator


def test_oe001_source_scope_supports_marketplaces_and_search_sources_without_granting_permission() -> None:
    sources = set(_schema()["properties"]["source"]["properties"]["source_id"]["enum"])
    assert {"ADOBE_STOCK", "DREAMSTIME", "SHUTTERSTOCK", "FREEPIK", "123RF", "VECTEEZY", "MOTIONELEMENTS"} <= sources
    assert {"GOOGLE_TRENDS", "GOOGLE_SEARCH", "BING_SEARCH"} <= sources
    assert "This contract authorizes **no specific platform adapter by itself**" in ACQUISITION.read_text(encoding="utf-8")