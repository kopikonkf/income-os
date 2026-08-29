from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "demand-score"
SCHEMA_PATH = ENGINE / "die.division001.demand-score.v1.schema.json"
MODEL_PATH = ENGINE / "DEMAND_SCORE_MODEL_V1.contract.json"
FIXTURE_PATH = ENGINE / "fixtures" / "valid-partial-demand-score.json"
VALIDATOR_PATH = ENGINE / "validate_demand_score.py"
NORMALIZATION = ENGINE / "EVIDENCE_NORMALIZATION_V1.md"
UNKNOWN_POLICY = ENGINE / "UNKNOWN_FRESHNESS_POLICY_V1.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("oe002_validator", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = _load_validator()


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _model() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _errors(payload: dict) -> list[str]:
    return V.validate(payload, _schema(), _model())


def _component(payload: dict, cid: str) -> dict:
    return next(row for row in payload["components"] if row["component_id"] == cid)


def test_oe002a_partial_fixture_validates_and_pins_model_contract() -> None:
    payload = _fixture()
    assert _errors(payload) == []
    assert payload["model"]["model_id"] == "division001-demand-score-v1"
    assert payload["model"]["model_version"] == "1.0.0-contract"
    assert payload["model"]["contract_sha256"] == V.file_sha256(MODEL_PATH)
    assert payload["score_status"] == "PARTIAL"
    assert payload["final_score"] is None


def test_oe002a_model_contract_has_no_production_weights_yet() -> None:
    model = _model()
    assert model["status"] == "CONTRACT_ONLY"
    assert all(row["weight_status"] == "UNASSIGNED_UNTIL_OE-002D" for row in model["components"])
    assert model["legacy_v0_status"] == "CALIBRATION_PROVENANCE_ONLY_NOT_PRODUCTION_TRUTH"


def test_oe002b_component_mapping_separates_market_and_structural_evidence() -> None:
    model = {row["component_id"]: row for row in _model()["components"]}
    assert model["external_demand"]["allowed_signal_classes"] == ["DEMAND"]
    assert set(model["supply_competition"]["allowed_signal_classes"]) == {"SUPPLY", "COMPETITION"}
    assert model["commercial_intent"]["allowed_signal_classes"] == ["COMMERCIAL_INTENT"]
    assert model["niche_specificity"]["allowed_signal_classes"] == []
    assert model["production_feasibility"]["allowed_signal_classes"] == []
    assert "DETERMINISTIC_EVIDENCE" in model["niche_specificity"]["allowed_evidence_kinds"]


def test_oe002b_contract_explicitly_forbids_hidden_v0_priors() -> None:
    text = NORMALIZATION.read_text(encoding="utf-8")
    for phrase in (
        "missing search signal -> 0.30",
        "object class tools -> intent 0.60",
        "name == candle -> trend 0.75",
        "unknown seasonality -> 0.40",
        "LEGACY_HEURISTIC",
    ):
        assert phrase in text


def test_oe002c_no_evidence_is_not_zero_and_partial_score_is_null() -> None:
    text = UNKNOWN_POLICY.read_text(encoding="utf-8")
    assert "NO EVIDENCE != ZERO DEMAND" in text
    assert "`PARTIAL`" in text
    assert "`final_score` MUST be null" in text
    payload = _fixture()
    assert payload["final_score"] is None


def test_validator_rejects_numeric_final_score_for_partial() -> None:
    payload = _fixture()
    payload["final_score"] = 0.7
    assert "E_SCORE_STATUS:PARTIAL_contract" in _errors(payload)


def test_validator_rejects_unknown_component_with_fake_zero_default() -> None:
    payload = _fixture()
    comp = _component(payload, "commercial_intent")
    comp["normalized_score"] = 0.0
    assert "E_COMPONENT_STATE:commercial_intent:UNKNOWN_must_be_empty" in _errors(payload)


def test_validator_rejects_stale_signal_marked_known() -> None:
    payload = _fixture()
    payload["evaluated_at"] = "2026-08-30T12:00:00Z"
    payload["expires_at"] = "2026-08-31T05:02:15Z"
    errors = _errors(payload)
    assert "E_FRESHNESS:supply_competition:KNOWN_requires_fresh_signal" in errors


def test_validator_rejects_wrong_signal_class_for_component() -> None:
    payload = _fixture()
    comp = _component(payload, "external_demand")
    comp["evidence_refs"][0]["signal_class"] = "SUPPLY"
    assert "E_SIGNAL_CLASS:external_demand:SUPPLY" in _errors(payload)


def test_validator_rejects_legacy_heuristic_as_production_evidence() -> None:
    payload = _fixture()
    comp = _component(payload, "external_demand")
    comp["evidence_refs"][0]["evidence_kind"] = "LEGACY_HEURISTIC"
    errors = _errors(payload)
    assert "E_LEGACY_HEURISTIC:external_demand:not_production_evidence" in errors


def test_validator_rejects_same_evidence_double_counted_between_components() -> None:
    payload = _fixture()
    source = copy.deepcopy(_component(payload, "external_demand")["evidence_refs"][0])
    target = _component(payload, "supply_competition")
    target["evidence_refs"] = [source]
    target["normalized_score"] = 0.5
    errors = _errors(payload)
    assert any(e.startswith("E_EVIDENCE_DOUBLE_COUNT:") for e in errors)


def test_validator_rejects_coverage_fabrication() -> None:
    payload = _fixture()
    payload["evidence_coverage_ratio"] = 1.0
    payload["required_coverage_ratio"] = 1.0
    errors = _errors(payload)
    assert "E_COVERAGE:evidence_coverage_ratio_mismatch" in errors
    assert "E_COVERAGE:required_coverage_ratio_mismatch" in errors


def test_validator_rejects_complete_status_without_all_required_components() -> None:
    payload = _fixture()
    payload["score_status"] = "COMPLETE"
    payload["final_score"] = 0.75
    payload["confidence"] = "HIGH"
    payload["hard_veto"]["status"] = "CLEAR"
    assert "E_SCORE_STATUS:COMPLETE_contract" in _errors(payload)


def test_validator_rejects_output_expiry_beyond_earliest_known_signal() -> None:
    payload = _fixture()
    payload["expires_at"] = "2026-08-31T05:02:15Z"
    assert "E_OUTPUT_EXPIRY:exceeds_earliest_known_signal_expiry" in _errors(payload)


def test_validator_rejects_non_signal_evidence_claiming_signal_class() -> None:
    payload = _fixture()
    comp = _component(payload, "niche_specificity")
    comp.update({
        "state": "KNOWN",
        "normalized_score": 0.5,
        "confidence": "HIGH",
        "normalization_transform_id": "fixture-structural",
        "normalization_transform_version": "v1",
        "evidence_refs": [{
            "evidence_kind": "DETERMINISTIC_EVIDENCE",
            "evidence_id": "DET-NICHE-001",
            "evidence_sha256": "1" * 64,
            "signal_class": "DEMAND",
            "signal_type": "SEARCH_INTEREST_INDEX",
            "observed_at": None,
            "expires_at": None,
            "freshness_state": "VERSION_VALID",
            "source_ref": "fixture://deterministic/niche",
        }],
    })
    payload["evidence_coverage_ratio"] = round(3 / 9, 6)
    errors = _errors(payload)
    assert "E_EVIDENCE_PROVENANCE:niche_specificity:DETERMINISTIC_EVIDENCE_must_not_claim_signal" in errors


def test_required_complete_components_are_explicit_and_stable() -> None:
    required = {row["component_id"] for row in _model()["components"] if row["required_for_complete"]}
    assert required == {"external_demand", "supply_competition", "commercial_intent"}
    assert _fixture()["required_coverage_ratio"] == round(2 / 3, 6)