from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LONGTAIL = ROOT / "company" / "division" / "division001" / "engines" / "longtail"
WORTH = ROOT / "company" / "division" / "division001" / "engines" / "worth-making"
SIGNALS = ROOT / "company" / "division" / "division001" / "engines" / "opportunity-signals"


def _load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HCTX = _load("oe004_hctx_test", LONGTAIL / "retrieve_human_contexts.py")
GEN = _load("oe004_gen_test", LONGTAIL / "generate_longtail.py")
GUARD = _load("oe004_guard_test", LONGTAIL / "guard_longtail.py")
PHRASE = _load("oe004_phrase_test", LONGTAIL / "phrase_signal_score.py")
PRE = _load("oe004_precheck_test", WORTH / "precheck_worth_making.py")
WM = _load("oe004_wm_validator_test", WORTH / "validate_worth_making.py")
EXEC = _load("oe004_exec_validator_test", WORTH / "validate_executive_review.py")

BASE_MAIN = "6dbf40683fee6c78d5b0a5295c0d24d5a3697e01"
CREATED = "2026-08-29T12:00:00Z"
SCORE_AT = "2026-08-29T12:10:00Z"
PRECHECK_AT = "2026-08-29T12:20:00Z"


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _longtail_chain(tmp_path: Path):
    fixture = json.loads((LONGTAIL / "fixtures" / "synthetic-canary-v1.json").read_text(encoding="utf-8"))
    contexts = HCTX.retrieve(fixture["human_context_query"])
    generation = GEN.generate(
        fixture["object_receipt"],
        contexts,
        budget=fixture["budget"],
        expression_level=fixture["expression_level"],
        created_at=fixture["created_at"],
    )
    guard = GUARD.apply(generation)
    candidate = generation["candidates"][0]
    outcome = guard["outcomes"][0]
    score = PHRASE.synthetic_canary(
        candidate,
        outcome,
        fixture["signal_plans"][0],
        fixture["hard_veto"],
        registry_db=tmp_path / "signals.db",
        evaluated_at=fixture["evaluated_at"],
    )["demand_score"]
    return fixture, contexts, generation, guard, candidate, outcome, score


def _clear_gate(name: str) -> dict:
    return {
        "status": "CLEAR",
        "evidence_ref": f"fixture://worth-making/{name}/clear",
        "evidence_sha256": _sha_text("worth-making-" + name + "-clear"),
        "observed_at": "2026-08-29T12:00:00Z",
        "expires_at": "2026-08-30T12:00:00Z",
        "notes": "fixture clear gate",
    }


def _precheck_input(tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    fixture, contexts, generation, guard, candidate, outcome, score = _longtail_chain(tmp_path)
    payload = {
        "schema_version": "die.division001.worth-making-precheck-input.v1",
        "precheck_id": "WMPRE-FIXTURE-CABLE-0001",
        "evaluated_at": PRECHECK_AT,
        "candidate": candidate,
        "demand_score": score,
        "longtail_guard": {
            "status": outcome["status"],
            "receipt_id": guard["guard_receipt_id"],
            "receipt_sha256": PRE.canonical_sha(guard),
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": PRE.canonical_sha(candidate),
        },
        "hard_gates": {
            "rights_ip": _clear_gate("rights-ip"),
            "safety_deception": _clear_gate("safety-deception"),
            "platform_expression_eligibility": _clear_gate("platform-expression"),
            "production_tool_rights": _clear_gate("tool-rights"),
        },
        "spend": {
            "estimated_cost_usd": 0,
            "authorization_status": "NOT_REQUIRED",
            "authorization_ref": None,
            "authorization_sha256": None,
        },
        "buyer_hypothesis_seed": {
            "source_kind": "HUMAN_ATLAS_HYPOTHESIS",
            "source_ref": "fixture://human-context/" + contexts["results"][0]["context"]["context_id"],
            "source_sha256": contexts["registry"]["sha256"],
            "buyer_label": contexts["results"][0]["context"]["target_buyers"][0],
            "use_case": contexts["results"][0]["context"]["buyer_jobs"][0],
            "falsification_test": "Test whether a bounded buyer-facing utility asset gets measurable acceptance or buyer engagement.",
        },
    }
    return payload, candidate, score, guard


def _source_signals(score: dict) -> list[dict]:
    out = []
    seen = set()
    for comp in score["components"]:
        for ref in comp["evidence_refs"]:
            if ref["evidence_kind"] == "OPPORTUNITY_SIGNAL" and ref["evidence_id"] not in seen:
                out.append({"signal_id": ref["evidence_id"], "sha256": ref["evidence_sha256"]})
                seen.add(ref["evidence_id"])
    return out


def _factor_ref(kind: str, ref: str, digest: str) -> list[dict]:
    return [{"kind": kind, "ref": ref, "sha256": digest}]


def _division_artifact(precheck: dict, candidate: dict, score: dict) -> dict:
    psha = WM.canonical_sha(precheck)
    factor_values = {
        "demand_evidence": 82,
        "commercial_intent": 80,
        "buyer_utility": 85,
        "competition_gap": 70,
        "differentiation": 78,
        "production_feasibility": 90,
        "eligible_platform_fit": 80,
        "repurposing_potential": 65,
        "speed_to_cheapest_falsification": 85,
    }
    weights = {x["factor_id"]: x["weight"] for x in json.loads((WORTH / "WORTH_MAKING_FACTOR_MODEL_V1.json").read_text())["factors"]}
    factors = []
    for fid, value in factor_values.items():
        if fid in {"demand_evidence", "commercial_intent", "competition_gap", "eligible_platform_fit"}:
            refs = _factor_ref("DEMAND_SCORE", "fixture://demand-score/" + score["score_id"], precheck["demand_score_sha256"])
            label = "VERIFIED"
        elif fid in {"buyer_utility", "differentiation"}:
            refs = _factor_ref("HYPOTHESIS_SOURCE", "fixture://human-context/buyer-hypothesis", precheck["buyer_hypothesis_seed_sha256"])
            label = "HYPOTHESIS"
        elif fid in {"production_feasibility", "repurposing_potential"}:
            refs = _factor_ref("CANON_EVIDENCE", "fixture://canon/product-expression-policy", _sha_text("canon-product-expression-policy"))
            label = "INFERRED"
        else:
            refs = _factor_ref("PRECHECK", "fixture://precheck/" + precheck["precheck_id"], psha)
            label = "VERIFIED"
        factors.append({"factor_id": fid, "weight": weights[fid], "score": value, "evidence_label": label, "evidence_refs": refs, "rationale": "Fixture rationale grounded in the cited evidence class."})
    total = sum(factor_values[fid] * weights[fid] for fid in factor_values) / 100.0
    return {
        "schema_version": "die.division001.worth-making.v1",
        "artifact_id": "WM-DIV001-FIXTURE-CABLE-0001",
        "decision_class": "WORTH_MAKING",
        "principal": {"principal_id": "division-head-division01", "role": "AUTHOR", "division_id": "division001"},
        "snapshot": {"repository_sha": BASE_MAIN, "snapshot_id": "fixture://division01/snapshot/oe004", "as_of": "2026-08-29T12:25:00Z", "expires_at": "2026-08-30T12:25:00Z"},
        "upstream": {
            "precheck_id": precheck["precheck_id"], "precheck_sha256": psha,
            "demand_score_id": precheck["demand_score_id"], "demand_score_sha256": precheck["demand_score_sha256"],
            "longtail_candidate_sha256": precheck["candidate_sha256"], "source_signals": _source_signals(score),
        },
        "candidate": {"candidate_id": candidate["candidate_id"], "family_id": "FAM-FIXTURE-CABLE-001", "phrase": candidate["phrase"]},
        "buyer": {"buyer_or_payer": "office-supply marketer", "end_user": "remote worker", "job_to_be_done": "Show a practical way to organize desk cables in remote-work content.", "buyer_utility": "Provide a clear commercially usable visual concept for explaining cable-management utility."},
        "commercial_use_hypothesis": "A buyer may license a clean utility asset to explain or advertise desk organization for remote work.",
        "competition_interpretation": "Supply exists, but utility-specific contextual framing may create a narrower competitive lane.",
        "differentiation_thesis": "Differentiate through buyer-relevant remote-work context rather than a generic isolated organizer object.",
        "production_feasibility": "The concept is feasible as a bounded static utility asset with low production complexity.",
        "product_expression_recommendation": {"level": "L0", "name": "primitive_static_asset", "rationale": "Start with the cheapest static falsification before expanding into families or templates."},
        "factors": factors, "total_score": total, "confidence": "MEDIUM",
        "cheapest_falsification": {"test": "Produce a minimal bounded validation set and measure platform acceptance plus buyer-facing engagement proxy.", "success_criterion": "At least one predefined acceptance or engagement threshold is met.", "failure_criterion": "The bounded test misses all predefined acceptance and engagement thresholds.", "estimated_cost_usd": 0, "timebox": "one bounded validation cycle"},
        "assumptions": [{"claim": "Remote-work framing improves buyer usefulness versus a generic object-only asset.", "label": "HYPOTHESIS", "falsification_ref": "fixture://falsification/remote-work-framing"}],
        "recommendation": "VALIDATE", "precheck_status": "PASS", "production_authority_granted": False,
    }


def _executive_review(precheck: dict, artifact: dict, assessment: str = "PASS", outcome: str = "NO_VETO") -> dict:
    ahash = EXEC.canonical_sha(artifact)
    ids = [
        "evidence_weakness_contradiction", "score_inflation_double_counting", "portfolio_overlap_cannibalization",
        "strategic_opportunity_cost", "product_expression_fit", "hypotheses_remaining",
    ]
    challenges = []
    for cid in ids:
        challenges.append({"challenge_id": cid, "assessment": assessment, "rationale": "Executive fixture review of this required challenge domain.", "evidence_refs": [{"ref": "fixture://division-artifact/" + artifact["artifact_id"], "sha256": ahash}]})
    actions = [] if outcome == "NO_VETO" else ["Return the issue to Division01 or acquire the missing evidence before promotion."]
    escalation = "Founder policy judgment required." if outcome == "ESCALATE_FOUNDER" else None
    return {
        "schema_version": "die.executive.worth-making-review.v1", "review_id": "WM-EXEC-FIXTURE-CABLE-0001",
        "principal": {"principal_id": "chatgpt-plus-executive", "role": "REVIEWER"},
        "snapshot": {"repository_sha": BASE_MAIN, "snapshot_id": "fixture://executive/snapshot/oe004", "as_of": "2026-08-29T12:30:00Z"},
        "division_artifact": {"artifact_id": artifact["artifact_id"], "sha256": ahash, "author_principal_id": artifact["principal"]["principal_id"], "recommendation": artifact["recommendation"], "total_score": artifact["total_score"], "confidence": artifact["confidence"]},
        "precheck": {"precheck_id": precheck["precheck_id"], "sha256": EXEC.canonical_sha(precheck), "status": "PASS"},
        "challenges": challenges, "outcome": outcome, "required_actions": actions, "escalation_reason": escalation,
        "review_mode": "READ_ONLY_CHALLENGE", "division_artifact_edited": False, "production_authority_granted": False,
        "reviewed_at": "2026-08-29T12:30:00Z", "expires_at": "2026-08-30T12:30:00Z",
    }


def test_oe004a_valid_precheck_passes_without_authoring_semantics(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    result = PRE.evaluate(payload)
    assert result["status"] == "PASS"
    assert result["hard_veto"] == "CLEAR"
    assert result["blocking_codes"] == [] and result["unknown_codes"] == []
    assert result["worth_making_semantics_authored"] is False


def test_oe004a_tampered_demand_score_arithmetic_fails_semantic_validation(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["demand_score"]["final_score"] = 0.999999
    with pytest.raises(PRE.PrecheckError, match="E_DEMAND_SCORE_SEMANTIC"):
        PRE.evaluate(payload)


def test_oe004a_longtail_guard_must_bind_exact_candidate_hash(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["longtail_guard"]["candidate_sha256"] = "0" * 64
    with pytest.raises(PRE.PrecheckError, match="E_LONGTAIL_GUARD_CANDIDATE_BINDING"):
        PRE.evaluate(payload)


def test_oe004a_stale_score_or_gate_waits_for_evidence(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["demand_score"]["expires_at"] = "2026-08-29T12:15:00Z"
    result = PRE.evaluate(payload)
    assert result["status"] == "WAITING_EVIDENCE"
    assert "DEMAND_SCORE_STALE" in result["unknown_codes"]

    payload2, _, _, _ = _precheck_input(tmp_path / "b")
    payload2["hard_gates"]["rights_ip"]["expires_at"] = "2026-08-29T12:10:00Z"
    result2 = PRE.evaluate(payload2)
    assert result2["status"] == "WAITING_EVIDENCE"
    assert "HARD_GATE_RIGHTS_IP_STALE" in result2["unknown_codes"]


def test_oe004a_blocked_gate_and_spend_denial_are_hard_vetoes(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["hard_gates"]["safety_deception"]["status"] = "BLOCKED"
    result = PRE.evaluate(payload)
    assert result["status"] == "BLOCKED" and result["hard_veto"] == "BLOCKED"
    assert "HARD_GATE_SAFETY_DECEPTION" in result["blocking_codes"]

    payload2, _, _, _ = _precheck_input(tmp_path / "c")
    payload2["spend"].update({"estimated_cost_usd": 1.0, "authorization_status": "DENIED"})
    result2 = PRE.evaluate(payload2)
    assert result2["status"] == "BLOCKED"
    assert "SPEND_DENIED" in result2["blocking_codes"]


def test_oe004a_positive_spend_requires_authorization_receipt(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["spend"].update({"estimated_cost_usd": 1.0, "authorization_status": "MISSING"})
    result = PRE.evaluate(payload)
    assert result["status"] == "WAITING_EVIDENCE"
    assert "SPEND_AUTH_REQUIRED" in result["unknown_codes"]


def test_oe004a_review_longtail_is_not_promotable(tmp_path: Path) -> None:
    payload, _, _, _ = _precheck_input(tmp_path)
    payload["longtail_guard"]["status"] = "REVIEW"
    result = PRE.evaluate(payload)
    assert result["status"] == "WAITING_EVIDENCE"
    assert "LONGTAIL_GUARD_REVIEW" in result["unknown_codes"]


def test_oe004b_valid_division_author_artifact_passes_with_pinned_precheck(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload)
    artifact = _division_artifact(precheck, candidate, score)
    assert artifact["total_score"] == 80.45
    assert WM.validate(artifact, precheck=precheck) == []
    assert artifact["principal"]["principal_id"] == "division-head-division01"
    assert artifact["production_authority_granted"] is False


def test_oe004b_factor_weight_total_and_evidence_are_semantically_locked(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    bad = copy.deepcopy(artifact); bad["factors"][0]["weight"] = 19
    assert any("weight_mismatch" in x for x in WM.validate(bad, precheck=precheck))
    bad2 = copy.deepcopy(artifact); bad2["total_score"] = 99
    assert "E_TOTAL:weighted_total_mismatch" in WM.validate(bad2, precheck=precheck)
    bad3 = copy.deepcopy(artifact); bad3["factors"][0]["evidence_refs"] = []
    assert any("numeric_score_requires_evidence" in x for x in WM.validate(bad3, precheck=precheck))


def test_oe004b_unknown_is_null_not_zero_and_blocks_validate(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    row = artifact["factors"][0]; row["score"] = None; row["evidence_label"] = "UNKNOWN"; row["evidence_refs"] = []
    artifact["total_score"] = None; artifact["confidence"] = "LOW"; artifact["recommendation"] = "RESEARCH"
    assert WM.validate(artifact, precheck=precheck) == []
    artifact["recommendation"] = "VALIDATE"
    assert "E_RECOMMENDATION:VALIDATE_requires_complete_factors" in WM.validate(artifact, precheck=precheck)


def test_oe004b_recommendation_thresholds_are_maximum_aggressiveness(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    low = copy.deepcopy(artifact)
    for row in low["factors"]:
        row["score"] = 50
    low["total_score"] = 50
    low["recommendation"] = "RESEARCH"
    errors = WM.validate(low, precheck=precheck)
    assert "E_RECOMMENDATION:RESEARCH_below_threshold" in errors
    assert "E_RECOMMENDATION:below_60_requires_DEFER" in errors
    low["recommendation"] = "DEFER"
    assert WM.validate(low, precheck=precheck) == []


def test_oe004b_wrong_principal_or_production_authority_is_schema_rejected(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    bad = copy.deepcopy(artifact); bad["principal"]["principal_id"] = "hermes"
    assert any(x.startswith("E_SCHEMA:") for x in WM.validate(bad, precheck=precheck))
    bad2 = copy.deepcopy(artifact); bad2["production_authority_granted"] = True
    assert any(x.startswith("E_SCHEMA:") for x in WM.validate(bad2, precheck=precheck))


def test_oe004b_precheck_hash_and_candidate_lineage_are_pinned(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    artifact["upstream"]["precheck_sha256"] = "1" * 64
    assert "E_PRECHECK:hash_mismatch" in WM.validate(artifact, precheck=precheck)


def test_oe004c_valid_no_veto_is_read_only_and_has_no_production_authority(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact)
    before = EXEC.canonical_sha(artifact)
    assert EXEC.validate(review, division_artifact=artifact, precheck=precheck) == []
    assert EXEC.canonical_sha(artifact) == before
    assert review["review_mode"] == "READ_ONLY_CHALLENGE"
    assert review["division_artifact_edited"] is False
    assert review["production_authority_granted"] is False


def test_oe004c_no_veto_forbids_material_concern_or_unknown(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact)
    review["challenges"][0]["assessment"] = "MATERIAL_CONCERN"
    assert "E_OUTCOME:NO_VETO_with_material_or_unknown" in EXEC.validate(review, division_artifact=artifact, precheck=precheck)
    review["challenges"][0]["assessment"] = "UNKNOWN"
    assert "E_OUTCOME:NO_VETO_with_material_or_unknown" in EXEC.validate(review, division_artifact=artifact, precheck=precheck)


def test_oe004c_revise_requires_concern_and_actions(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact, assessment="CONCERN", outcome="REVISE")
    assert EXEC.validate(review, division_artifact=artifact, precheck=precheck) == []
    review["required_actions"] = []
    assert "E_OUTCOME:REVISE_requires_actions" in EXEC.validate(review, division_artifact=artifact, precheck=precheck)


def test_oe004c_veto_pending_evidence_requires_unknown_and_actions(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact, assessment="UNKNOWN", outcome="VETO_PENDING_EVIDENCE")
    assert EXEC.validate(review, division_artifact=artifact, precheck=precheck) == []
    review2 = _executive_review(precheck, artifact, assessment="PASS", outcome="VETO_PENDING_EVIDENCE")
    assert "E_OUTCOME:VETO_PENDING_EVIDENCE_requires_UNKNOWN" in EXEC.validate(review2, division_artifact=artifact, precheck=precheck)


def test_oe004c_escalation_requires_reason(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact, outcome="ESCALATE_FOUNDER")
    assert EXEC.validate(review, division_artifact=artifact, precheck=precheck) == []
    review["escalation_reason"] = None
    assert "E_OUTCOME:ESCALATE_requires_reason" in EXEC.validate(review, division_artifact=artifact, precheck=precheck)


def test_oe004c_exact_division_hash_and_author_principal_are_required(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact)
    review["division_artifact"]["sha256"] = "2" * 64
    assert "E_DIVISION_ARTIFACT:hash_mismatch" in EXEC.validate(review, division_artifact=artifact, precheck=precheck)
    review2 = _executive_review(precheck, artifact); review2["principal"]["principal_id"] = "division-head-division01"
    assert any(x.startswith("E_SCHEMA:") for x in EXEC.validate(review2, division_artifact=artifact, precheck=precheck))


def test_oe004c_schema_prevents_in_place_edit_and_authority_laundering(tmp_path: Path) -> None:
    payload, candidate, score, _ = _precheck_input(tmp_path)
    precheck = PRE.evaluate(payload); artifact = _division_artifact(precheck, candidate, score)
    review = _executive_review(precheck, artifact)
    review["division_artifact_edited"] = True
    assert any(x.startswith("E_SCHEMA:") for x in EXEC.validate(review, division_artifact=artifact, precheck=precheck))
    review2 = _executive_review(precheck, artifact); review2["production_authority_granted"] = True
    assert any(x.startswith("E_SCHEMA:") for x in EXEC.validate(review2, division_artifact=artifact, precheck=precheck))