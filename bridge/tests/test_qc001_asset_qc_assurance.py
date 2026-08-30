from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from income_os_bridge import asset_qc_assurance

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUBRIC = ROOT / "company" / "contracts" / "die.asset.qc-rubric.v1.json"
SHADOW_POLICY = ROOT / "company" / "contracts" / "qc" / "die.asset.qc-delegation-policy.shadow.v1.json"
AUDIT_POLICY = ROOT / "company" / "contracts" / "qc" / "die.asset.qc-audit-policy.v1.json"


def _write(path: pathlib.Path, value: dict) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _qc(asset_id: str, *, recommendation: str, confidence: float, defects: list[str], reviewer_version: str = "v1") -> dict:
    asset_sha = _sha(f"asset:{asset_id}")
    qa_sha = _sha(f"qa:{asset_id}")
    return {
        "schema_version": "die.asset.qc.v1",
        "receipt_id": f"QC-{asset_id}",
        "evaluated_at": "2026-08-30T00:00:00+00:00",
        "asset_id": asset_id,
        "asset_sha256": asset_sha,
        "blueprint_id": f"BP-{asset_id}",
        "blueprint_sha256": _sha(f"bp:{asset_id}"),
        "qa_receipt_sha256": qa_sha,
        "rubric_id": "DIE-ASSET-QC-RUBRIC-V1",
        "rubric_version": 1,
        "reviewer_id": "fixture-reviewer",
        "reviewer_version": reviewer_version,
        "score": 90,
        "confidence": confidence,
        "recommendation": recommendation,
        "defect_classes": defects,
        "evidence_refs": [f"evidence/{asset_id}.json"],
        "mode": "SHADOW_ONLY",
        "qa_gate": {"passed": recommendation != "BLOCKED_BY_QA", "reason": "fixture"},
        "authority_boundary": {
            "release_authorized": False,
            "submission_authorized": False,
            "publication_authorized": False,
            "qa_hard_veto_waivable": False,
            "self_promotion_allowed": False,
        },
    }


def _label(asset_id: str, *, decision: str, defects: list[str], asset_class: str = "isolated-object") -> dict:
    return {
        "schema_version": "die.asset.qc-label.v1",
        "label_id": f"LABEL-{asset_id}",
        "labeled_at": "2026-08-30T00:00:00Z",
        "labeler_principal_id": "Founder",
        "asset_class": asset_class,
        "asset_id": asset_id,
        "asset_sha256": _sha(f"asset:{asset_id}"),
        "blueprint_id": f"BP-{asset_id}",
        "blueprint_sha256": _sha(f"bp:{asset_id}"),
        "qa_receipt_sha256": _sha(f"qa:{asset_id}"),
        "decision": decision,
        "defect_classes": defects,
        "rationale_summary": "bounded fixture rationale",
        "evidence_refs": [f"evidence/{asset_id}.json"],
    }


def _corpus(tmp_path: pathlib.Path, *, reviewer_version: str = "v1") -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    rows = [
        ("A", "PASS", [], "PASS_RECOMMENDED", 0.95, []),
        ("B", "FAIL", ["BLUEPRINT_MISMATCH"], "PASS_RECOMMENDED", 0.90, []),
        ("C", "PASS", [], "FAIL_RECOMMENDED", 0.85, ["AI_ARTIFACT_OBVIOUS"]),
        ("D", "REVIEW", [], "REVIEW_RECOMMENDED", 0.60, []),
    ]
    labels: list[pathlib.Path] = []
    qcs: list[pathlib.Path] = []
    for asset_id, founder, founder_defects, recommendation, confidence, engine_defects in rows:
        labels.append(_write(tmp_path / f"label-{asset_id}.json", _label(asset_id, decision=founder, defects=founder_defects)))
        qcs.append(_write(tmp_path / f"qc-{asset_id}.json", _qc(asset_id, recommendation=recommendation, confidence=confidence, defects=engine_defects, reviewer_version=reviewer_version)))
    return labels, qcs


def _report(tmp_path: pathlib.Path, *, reviewer_version: str = "v1") -> dict:
    labels, qcs = _corpus(tmp_path, reviewer_version=reviewer_version)
    return asset_qc_assurance.build_calibration_report(
        labels,
        qcs,
        RUBRIC,
        evaluated_at="2026-08-30T00:00:00+00:00",
    )


def _ratified_policy(report: dict, *, mode: str = "BOUNDED_AUTO_QC") -> dict:
    policy = {
        "schema_version": "die.asset.qc-delegation-policy.v1",
        "policy_id": "FOUNDER-QC-POLICY-V1",
        "policy_version": 1,
        "mode": mode,
        "status": "FOUNDER_RATIFIED",
        "scope": {
            "asset_classes": ["isolated-object"],
            "marketplaces": ["Adobe Stock"],
            "reviewer_ids": [report["reviewer_id"]],
            "reviewer_versions": [report["reviewer_version"]],
            "valid_from": "2026-08-30T00:00:00+00:00",
            "valid_until": "2026-09-30T00:00:00+00:00",
        },
        "thresholds": {
            "min_case_count": 4,
            "min_agreement_rate": 0.5,
            "max_false_pass_rate": 0.25,
            "max_hard_defect_miss_count": 1,
            "max_confidence_calibration_gap": 0.6,
        },
        "ratification": {"ratified_by": "Founder", "ratified_at": "2026-08-30T00:00:00+00:00", "policy_sha256": None},
        "authority_boundary": {
            "submission_authorized": False,
            "publication_authorized": False,
            "qa_hard_veto_waivable": False,
            "self_promotion_allowed": False,
        },
    }
    body = json.loads(json.dumps(policy))
    body["ratification"]["policy_sha256"] = None
    policy["ratification"]["policy_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return policy


def test_calibration_report_is_reproducible_and_measures_required_metrics(tmp_path: pathlib.Path) -> None:
    labels, qcs = _corpus(tmp_path)
    first = asset_qc_assurance.build_calibration_report(labels, qcs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    second = asset_qc_assurance.build_calibration_report(reversed(labels), reversed(qcs), RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    assert first == second
    assert first["case_count"] == 4
    assert first["metrics"]["agreement_rate"] == 0.5
    assert first["metrics"]["false_pass_rate"] == 0.25
    assert first["metrics"]["false_fail_rate"] == 0.25
    assert first["metrics"]["hard_defect_miss_count"] == 1
    assert 0 <= first["metrics"]["confidence_calibration_gap"] <= 1
    assert first["per_defect_class"]["BLUEPRINT_MISMATCH"]["miss_count"] == 1
    assert first["per_asset_class"]["isolated-object"]["count"] == 4
    assert first["authority_boundary"]["release_authorized"] is False


def test_calibration_refuses_mixed_model_versions(tmp_path: pathlib.Path) -> None:
    labels, qcs = _corpus(tmp_path)
    value = json.loads(qcs[-1].read_text(encoding="utf-8"))
    value["reviewer_version"] = "v2"
    _write(qcs[-1], value)
    with pytest.raises(asset_qc_assurance.AssetQCAssuranceError, match="cannot mix reviewer versions"):
        asset_qc_assurance.build_calibration_report(labels, qcs, RUBRIC)


def test_shadow_case_retains_disagreement_and_low_confidence_without_release_authority(tmp_path: pathlib.Path) -> None:
    label = _write(tmp_path / "label.json", _label("B", decision="FAIL", defects=["BLUEPRINT_MISMATCH"]))
    qc = _write(tmp_path / "qc.json", _qc("B", recommendation="PASS_RECOMMENDED", confidence=0.5, defects=[]))
    case = asset_qc_assurance.build_shadow_case(label, qc, RUBRIC)
    assert case["agreement"] is False
    assert case["queue_required"] is True
    assert set(case["queue_reasons"]) == {"DISAGREEMENT", "LOW_CONFIDENCE"}
    assert case["authority_boundary"] == {
        "release_authorized": False,
        "submission_authorized": False,
        "founder_final": True,
    }
    queue = asset_qc_assurance.build_disagreement_queue([case])
    assert queue["queue_count"] == 1
    assert queue["cases"][0]["case_id"] == case["case_id"]


def test_shadow_case_lineage_mismatch_fails_closed(tmp_path: pathlib.Path) -> None:
    label = _write(tmp_path / "label.json", _label("A", decision="PASS", defects=[]))
    qc_value = _qc("A", recommendation="PASS_RECOMMENDED", confidence=0.9, defects=[])
    qc_value["asset_sha256"] = "c" * 64
    qc = _write(tmp_path / "qc.json", qc_value)
    with pytest.raises(asset_qc_assurance.AssetQCAssuranceError, match="lineage mismatch"):
        asset_qc_assurance.build_shadow_case(label, qc, RUBRIC)


def test_default_shadow_policy_never_grants_release_or_submission(tmp_path: pathlib.Path) -> None:
    report = _report(tmp_path)
    result = asset_qc_assurance.evaluate_delegation(
        SHADOW_POLICY,
        report,
        asset_class="isolated-object",
        marketplace="Adobe Stock",
        now="2026-08-30T01:00:00+00:00",
    )
    assert result["mode"] == "SHADOW_ONLY"
    assert result["qc_release_authorized"] is False
    assert result["submission_authorized"] is False
    assert result["reasons"] == ["SHADOW_ONLY"]


def test_non_shadow_policy_requires_valid_founder_ratification_hash(tmp_path: pathlib.Path) -> None:
    report = _report(tmp_path)
    policy = _ratified_policy(report)
    policy["status"] = "UNRATIFIED"
    path = _write(tmp_path / "policy.json", policy)
    with pytest.raises(asset_qc_assurance.AssetQCAssuranceError, match="requires Founder ratification"):
        asset_qc_assurance.evaluate_delegation(path, report, asset_class="isolated-object", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")

    policy = _ratified_policy(report)
    policy["ratification"]["policy_sha256"] = "0" * 64
    path = _write(tmp_path / "policy.json", policy)
    with pytest.raises(asset_qc_assurance.AssetQCAssuranceError, match="ratification hash mismatch"):
        asset_qc_assurance.evaluate_delegation(path, report, asset_class="isolated-object", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")


def test_ratified_bounded_policy_is_scope_and_metric_bounded_and_never_submission_authority(tmp_path: pathlib.Path) -> None:
    report = _report(tmp_path)
    policy = _ratified_policy(report)
    path = _write(tmp_path / "policy.json", policy)
    allowed = asset_qc_assurance.evaluate_delegation(path, report, asset_class="isolated-object", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")
    assert allowed["qc_release_authorized"] is True
    assert allowed["submission_authorized"] is False
    assert allowed["reasons"] == []

    out_of_scope = asset_qc_assurance.evaluate_delegation(path, report, asset_class="portrait", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")
    assert out_of_scope["qc_release_authorized"] is False
    assert "ASSET_CLASS_OUT_OF_SCOPE" in out_of_scope["reasons"]

    degraded = json.loads(json.dumps(report))
    degraded["metrics"]["false_pass_rate"] = 0.5
    blocked = asset_qc_assurance.evaluate_delegation(path, degraded, asset_class="isolated-object", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")
    assert blocked["qc_release_authorized"] is False
    assert "FALSE_PASS_ABOVE_THRESHOLD" in blocked["reasons"]


def test_calibrated_recommender_retains_founder_final_even_when_ratified(tmp_path: pathlib.Path) -> None:
    report = _report(tmp_path)
    policy = _ratified_policy(report, mode="CALIBRATED_RECOMMENDER")
    path = _write(tmp_path / "policy.json", policy)
    result = asset_qc_assurance.evaluate_delegation(path, report, asset_class="isolated-object", marketplace="Adobe Stock", now="2026-08-30T01:00:00+00:00")
    assert result["qc_release_authorized"] is False
    assert "RECOMMENDER_MODE_RETAINS_FOUNDER_FINAL" in result["reasons"]


def test_audit_allows_same_pinned_corpus_across_model_version_and_blocks_regression(tmp_path: pathlib.Path) -> None:
    baseline = _report(tmp_path / "base", reviewer_version="v1")
    current = json.loads(json.dumps(baseline))
    current["reviewer_version"] = "v2"
    current["report_id"] = "QCCAL-V2"
    clean = asset_qc_assurance.compare_calibration_reports(baseline, current, AUDIT_POLICY)
    assert clean["status"] == "PASS"
    assert clean["authority_boundary"]["self_promotion_allowed"] is False

    regressed = json.loads(json.dumps(current))
    regressed["metrics"]["false_pass_rate"] = baseline["metrics"]["false_pass_rate"] + 0.01
    blocked = asset_qc_assurance.compare_calibration_reports(baseline, regressed, AUDIT_POLICY)
    assert blocked["status"] == "BLOCKED"
    assert "FALSE_PASS_REGRESSION" in blocked["blocking_reasons"]

    hard = json.loads(json.dumps(current))
    hard["metrics"]["hard_defect_miss_count"] = baseline["metrics"]["hard_defect_miss_count"] + 1
    blocked_hard = asset_qc_assurance.compare_calibration_reports(baseline, hard, AUDIT_POLICY)
    assert blocked_hard["status"] == "BLOCKED"
    assert "HARD_DEFECT_MISS_REGRESSION" in blocked_hard["blocking_reasons"]


def test_audit_rejects_unpinned_corpus_and_flags_noncritical_drift(tmp_path: pathlib.Path) -> None:
    baseline = _report(tmp_path / "base")
    mismatch = json.loads(json.dumps(baseline))
    mismatch["corpus_sha256"] = "f" * 64
    result = asset_qc_assurance.compare_calibration_reports(baseline, mismatch, AUDIT_POLICY)
    assert result["status"] == "BLOCKED"
    assert "CORPUS_MISMATCH" in result["blocking_reasons"]

    drift = json.loads(json.dumps(baseline))
    drift["metrics"]["agreement_rate"] = baseline["metrics"]["agreement_rate"] - 0.1
    result = asset_qc_assurance.compare_calibration_reports(baseline, drift, AUDIT_POLICY)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "AGREEMENT_DRIFT" in result["review_reasons"]
