from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "demand-score"
CAL = ENGINE / "fixtures" / "calibration"
EXPECTED = ENGINE / "fixtures" / "calibration-expected.json"
LEGACY = ROOT / "company" / "atlas" / "object-centric" / "object-asset-engine" / "source" / "scripts" / "scoring" / "demand_score.py"


def _load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCORE = _load("oe002_score_engine_test", ENGINE / "score_demand.py")
RANK = _load("oe002_rank_engine_test", ENGINE / "rank_demand.py")
LEGACY_V0 = _load("oe002_legacy_v0_test", LEGACY)


def _input(name: str) -> dict:
    return json.loads((CAL / name).read_text(encoding="utf-8"))


def _component(payload: dict, cid: str) -> dict:
    return next(row for row in payload["components"] if row["component_id"] == cid)


def test_oe002d_weight_model_is_explicit_and_required_market_weight_is_70_percent() -> None:
    model = json.loads((ENGINE / "DEMAND_SCORE_MODEL_V1.contract.json").read_text(encoding="utf-8"))
    weights = {row["component_id"]: row["weight"] for row in model["components"]}
    assert weights["external_demand"] == 0.30
    assert weights["supply_competition"] == 0.20
    assert weights["commercial_intent"] == 0.20
    assert abs(sum(v for k, v in weights.items() if k != "risk_penalty") - 1.0) < 1e-9
    assert abs(model["required_base_weight"] - 0.70) < 1e-9
    assert model["scoring_policy"]["missing_optional"] == "RENORMALIZE_KNOWN_WEIGHTS_NEVER_IMPUTE_ZERO"


def test_oe002e_calibration_high_medium_low_is_monotonic() -> None:
    high = SCORE.score(_input("high.json"))
    medium = SCORE.score(_input("medium.json"))
    low = SCORE.score(_input("low.json"))
    assert high["score_status"] == medium["score_status"] == low["score_status"] == "COMPLETE"
    assert high["final_score"] > medium["final_score"] > low["final_score"]
    assert high["final_score"] == 0.821907
    assert medium["final_score"] == 0.613474
    assert low["final_score"] == 0.109096


def test_oe002e_saturation_changes_ranking_with_other_inputs_held_constant() -> None:
    low_supply = SCORE.score(_input("saturation-low-supply.json"))
    high_supply = SCORE.score(_input("saturation-high-supply.json"))
    assert _component(low_supply, "external_demand")["normalized_score"] == _component(high_supply, "external_demand")["normalized_score"]
    assert _component(low_supply, "commercial_intent")["normalized_score"] == _component(high_supply, "commercial_intent")["normalized_score"]
    assert _component(low_supply, "supply_competition")["normalized_score"] > _component(high_supply, "supply_competition")["normalized_score"]
    assert low_supply["final_score"] > high_supply["final_score"]


def test_oe002e_missing_stale_insufficient_and_veto_have_no_numeric_score() -> None:
    missing = SCORE.score(_input("missing.json"))
    stale = SCORE.score(_input("stale.json"))
    insufficient = SCORE.score(_input("insufficient.json"))
    veto = SCORE.score(_input("hard-veto.json"))
    veto_unknown = SCORE.score(_input("veto-unknown.json"))
    assert (missing["score_status"], missing["final_score"]) == ("PARTIAL", None)
    assert (stale["score_status"], stale["final_score"]) == ("PARTIAL", None)
    assert _component(stale, "supply_competition")["state"] == "STALE"
    assert (insufficient["score_status"], insufficient["final_score"]) == ("INSUFFICIENT_EVIDENCE", None)
    assert (veto["score_status"], veto["final_score"]) == ("HARD_VETO", None)
    assert (veto_unknown["score_status"], veto_unknown["final_score"]) == ("PARTIAL", None)
    assert veto_unknown["required_coverage_ratio"] == 1.0


def test_unknown_optional_evidence_is_not_implicit_zero() -> None:
    unknown = SCORE.score(_input("required-only.json"))
    zero = SCORE.score(_input("explicit-optional-zero.json"))
    assert unknown["score_status"] == zero["score_status"] == "COMPLETE"
    assert unknown["known_weight_ratio"] == 0.70
    assert zero["known_weight_ratio"] == 1.0
    assert unknown["confidence"] == "LOW"
    assert unknown["final_score"] > zero["final_score"]
    assert unknown["risk_adjustment"]["state"] == "UNKNOWN"
    assert zero["risk_adjustment"]["state"] == "APPLIED"


def test_risk_penalty_is_separate_bounded_deduction() -> None:
    high = SCORE.score(_input("high.json"))
    assert high["risk_adjustment"] == {"state": "APPLIED", "raw_penalty": 0.05, "multiplier": 0.15, "applied_deduction": 0.0075}


def test_deterministic_replay_is_byte_equivalent_as_data() -> None:
    payload = _input("medium.json")
    a = SCORE.score(copy.deepcopy(payload))
    b = SCORE.score(copy.deepcopy(payload))
    assert a == b
    assert json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(b, sort_keys=True, separators=(",", ":"))


def test_exact_duplicate_input_evidence_is_idempotent() -> None:
    payload = _input("high.json")
    baseline = SCORE.score(copy.deepcopy(payload))
    payload["evidence"].append(copy.deepcopy(payload["evidence"][0]))
    duplicate = SCORE.score(payload)
    assert duplicate == baseline


def test_conflicting_same_evidence_identity_fails_closed() -> None:
    payload = _input("high.json")
    conflict = copy.deepcopy(payload["evidence"][0])
    conflict["receipt"]["value"]["numeric_value"] = 1
    payload["evidence"].append(conflict)
    with pytest.raises(SCORE.ScoreError, match="E_INPUT_EVIDENCE_CONFLICT"):
        SCORE.score(payload)


def test_source_median_prevents_same_source_burst_from_dominating() -> None:
    payload = _input("required-only.json")
    # Replace external demand with two observations from source A (0.9, 0.1)
    # and one from source B (0.8). Expected per-source medians: A=0.5, B=0.8;
    # cross-source median=0.65, not raw-observation mean 0.60.
    template = copy.deepcopy(payload["evidence"][0])
    payload["evidence"] = payload["evidence"][1:]
    rows=[]
    for suffix, source, value in [("A1", "ADOBE_STOCK", 90), ("A2", "ADOBE_STOCK", 10), ("B1", "OTHER_APPROVED", 80)]:
        row=copy.deepcopy(template)
        row["receipt"]["signal_id"] = "OPSIG-CAL-MEDIAN-" + suffix
        row["receipt"]["source"]["source_id"] = source
        row["receipt"]["source"]["source_name"] = source + " synthetic calibration"
        row["receipt"]["value"]["numeric_value"] = value
        row["receipt"]["source_ref"] = "fixture://oe002/median/" + suffix
        row["receipt"]["dedupe_key"] = "oppsig:v1:cal:median:" + suffix
        rows.append(row)
    payload["evidence"] = rows + payload["evidence"]
    out=SCORE.score(payload)
    assert _component(out, "external_demand")["normalized_score"] == 0.65


def test_unsupported_commercial_signal_does_not_get_invented_transform() -> None:
    payload = _input("required-only.json")
    intent = payload["evidence"][2]["receipt"]
    intent["signal_type"] = "VISIBLE_PRICE_POINT"
    intent["value"] = {"kind":"TEXT","numeric_value":None,"boolean_value":None,"text_value":"$5 visible fixture","unit":"display_text"}
    out = SCORE.score(payload)
    assert out["score_status"] == "PARTIAL"
    assert out["final_score"] is None
    assert _component(out, "commercial_intent")["state"] == "REJECTED"


def test_subject_mismatch_rejects_signal_instead_of_scoring_other_candidate() -> None:
    payload = _input("required-only.json")
    payload["evidence"][0]["receipt"]["subject"]["id"] = "different phrase"
    out = SCORE.score(payload)
    assert out["score_status"] == "PARTIAL"
    assert _component(out, "external_demand")["state"] == "REJECTED"


def test_ranker_only_ranks_complete_and_defers_noncomplete() -> None:
    names = ["high.json","medium.json","low.json","missing.json","stale.json","hard-veto.json"]
    scores = [SCORE.score(_input(name)) for name in names]
    result = RANK.rank(scores)
    assert [row["score_id"] for row in result["ranked"]] == ["DSCORE-CAL-HIGH-0001","DSCORE-CAL-MEDIUM-0001","DSCORE-CAL-LOW-0001"]
    assert result["ranked_count"] == 3
    assert result["deferred_count"] == 3
    assert {row["score_status"] for row in result["deferred"]} == {"PARTIAL","HARD_VETO"}


def test_ranker_replay_is_deterministic_and_exact_duplicate_score_collapses() -> None:
    scores = [SCORE.score(_input("high.json")), SCORE.score(_input("medium.json"))]
    a=RANK.rank(copy.deepcopy(scores))
    b=RANK.rank(copy.deepcopy(scores)+[copy.deepcopy(scores[0])])
    assert a == b


def test_ranker_rejects_tampered_final_score_via_arithmetic_validator() -> None:
    score = SCORE.score(_input("high.json"))
    score["final_score"] = 0.999999
    with pytest.raises(RANK.RankError, match="E_SCORE_ARITHMETIC:final_score_mismatch"):
        RANK.rank([score])


def test_ranker_rejects_conflicting_duplicate_score_id() -> None:
    score = SCORE.score(_input("high.json"))
    altered = copy.deepcopy(score)
    altered["score_id"] = score["score_id"]
    altered["components"][0]["notes"] = "different but schema-valid payload"
    with pytest.raises(RANK.RankError, match="E_SCORE_ID_CONFLICT"):
        RANK.rank([score, altered])


def test_legacy_v0_missing_signal_still_emits_numeric_while_v1_refuses_imputation() -> None:
    row = {
        "id": "LEGACY-CAL-001",
        "canonical_name": "generic widget",
        "source_batch": "calibration",
        "category_path": "tools",
        "object_class": "tools",
        "demand_signal": None,
        "existence_type": "real",
    }
    legacy = LEGACY_V0.score_row(row)
    v1 = SCORE.score(_input("insufficient.json"))
    assert isinstance(legacy["demand_score"], float)
    assert legacy["components"]["search"] == 0.30
    assert legacy["components"]["marketplace"] == 0.30
    assert v1["score_status"] == "INSUFFICIENT_EVIDENCE"
    assert v1["final_score"] is None


def test_compact_calibration_expectations_and_pinned_ranking_match_current_engine() -> None:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    scores = []
    for input_path in sorted(CAL.glob("*.json")):
        actual = SCORE.score(json.loads(input_path.read_text(encoding="utf-8")))
        scores.append(actual)
        compact = {
            "score_status": actual["score_status"],
            "final_score": actual["final_score"],
            "confidence": actual["confidence"],
            "evidence_coverage_ratio": actual["evidence_coverage_ratio"],
            "required_coverage_ratio": actual["required_coverage_ratio"],
            "known_weight_ratio": actual["known_weight_ratio"],
            "risk_adjustment": actual["risk_adjustment"],
            "component_states": {c["component_id"]: c["state"] for c in actual["components"]},
        }
        assert compact == expected[input_path.name]
    pinned = json.loads((ENGINE / "fixtures" / "calibration-ranking.json").read_text(encoding="utf-8"))
    assert RANK.rank(scores) == pinned
