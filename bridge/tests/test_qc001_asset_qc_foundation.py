from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

from income_os_bridge import asset_qc

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUBRIC = ROOT / "company" / "contracts" / "die.asset.qc-rubric.v1.json"
LABEL_SCHEMA = ROOT / "company" / "schemas" / "die.asset.qc-label.v1.schema.json"
CORPUS_SCHEMA = ROOT / "company" / "schemas" / "die.asset.qc-corpus.v1.schema.json"
RESULT_SCHEMA = ROOT / "company" / "schemas" / "die.asset.qc.v1.schema.json"
SAMPLING = ROOT / "company" / "contracts" / "die.asset.qc-sampling.v1.json"


def _write(path: pathlib.Path, value: dict) -> pathlib.Path:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _qa(asset_sha: str, *, hard_veto: bool = False, batch_state: str = "PASS", route: str = "PASS") -> dict:
    return {
        "schema_version": "die.asset.qa.v1",
        "batch_state": batch_state,
        "hard_veto": hard_veto,
        "asset_results": [{"asset_id": "ASSET-1", "source_sha256": asset_sha, "route": route, "defects": []}],
    }


def _observation(asset_sha: str, *, score: float = 4, confidence: float = 0.95, defects: list[str] | None = None) -> dict:
    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))
    defect_rows = defects or []
    return {
        "schema_version": "die.asset.qc-observation.v1",
        "asset_id": "ASSET-1",
        "asset_sha256": asset_sha,
        "blueprint_id": "BP-1",
        "blueprint_sha256": "b" * 64,
        "reviewer_id": "qc-evaluator-fixture",
        "reviewer_version": "v1",
        "factors": {
            name: {
                "score": score,
                "confidence": confidence,
                "defect_classes": defect_rows if name == "blueprint_adherence" else [],
                "evidence_refs": [f"evidence/{name}.json"],
            }
            for name in rubric["factors"]
        },
    }


def _files(tmp_path: pathlib.Path, **kwargs):
    asset_sha = hashlib.sha256(b"fixture-asset").hexdigest()
    qa = _write(tmp_path / "qa.json", _qa(asset_sha, **{k: v for k, v in kwargs.items() if k in {"hard_veto", "batch_state", "route"}}))
    obs = _write(tmp_path / "obs.json", _observation(asset_sha, **{k: v for k, v in kwargs.items() if k in {"score", "confidence", "defects"}}))
    return qa, obs


def test_rubric_is_shadow_only_and_authority_fail_closed() -> None:
    rubric = asset_qc.load_rubric(RUBRIC)
    assert rubric["mode"] == "SHADOW_ONLY"
    assert abs(sum(row["weight"] for row in rubric["factors"].values()) - 1.0) < 1e-9
    assert rubric["authority_boundary"] == {
        "release_authorized": False,
        "submission_authorized": False,
        "publication_authorized": False,
        "qa_hard_veto_waivable": False,
        "self_promotion_allowed": False,
        "delegation_thresholds_defined_here": False,
    }


def test_label_corpus_and_sampling_contract_do_not_request_private_reasoning_or_grant_authority() -> None:
    label = json.loads(LABEL_SCHEMA.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS_SCHEMA.read_text(encoding="utf-8"))
    sampling = json.loads(SAMPLING.read_text(encoding="utf-8"))
    result = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    assert "rationale_summary" in label["properties"]
    assert "chain_of_thought" not in json.dumps(label).lower()
    assert corpus["properties"]["labels"]["type"] == "array"
    assert sampling["ground_truth"]["private_reasoning_required"] is False
    assert sampling["authority_boundary"]["sampling_grants_qc_release_authority"] is False
    auth = result["properties"]["authority_boundary"]["properties"]
    assert auth["release_authorized"]["const"] is False
    assert auth["submission_authorized"]["const"] is False


def test_pass_recommendation_is_deterministic_and_never_release_authority(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path)
    first = asset_qc.evaluate(qa, obs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    second = asset_qc.evaluate(qa, obs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    assert first == second
    assert first["score"] == 100.0
    assert first["recommendation"] == "PASS_RECOMMENDED"
    assert first["mode"] == "SHADOW_ONLY"
    assert first["authority_boundary"]["release_authorized"] is False
    assert first["authority_boundary"]["submission_authorized"] is False


def test_critical_defect_forces_fail_recommendation(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path, defects=["BLUEPRINT_MISMATCH"])
    receipt = asset_qc.evaluate(qa, obs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    assert receipt["recommendation"] == "FAIL_RECOMMENDED"
    assert "BLUEPRINT_MISMATCH" in receipt["defect_classes"]


def test_low_confidence_forces_review_even_with_high_score(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path, confidence=0.5)
    receipt = asset_qc.evaluate(qa, obs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    assert receipt["score"] == 100.0
    assert receipt["recommendation"] == "REVIEW_RECOMMENDED"


def test_qa_hard_veto_cannot_be_overridden_by_qc_score(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path, hard_veto=True, batch_state="FAIL", route="BLOCK_SUBMISSION")
    receipt = asset_qc.evaluate(qa, obs, RUBRIC, evaluated_at="2026-08-30T00:00:00+00:00")
    assert receipt["score"] == 100.0
    assert receipt["recommendation"] == "BLOCKED_BY_QA"
    assert receipt["qa_gate"]["passed"] is False
    assert receipt["authority_boundary"]["qa_hard_veto_waivable"] is False


def test_lineage_mismatch_fails_closed(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path)
    value = json.loads(obs.read_text(encoding="utf-8"))
    value["asset_sha256"] = "c" * 64
    _write(obs, value)
    with pytest.raises(asset_qc.AssetQCError, match="lineage mismatch"):
        asset_qc.evaluate(qa, obs, RUBRIC)


def test_cli_writes_shadow_receipt(tmp_path: pathlib.Path) -> None:
    qa, obs = _files(tmp_path)
    out = tmp_path / "qc.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "die_asset_qc.py"), "--qa-receipt", str(qa), "--observation", str(obs), "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["recommendation"] == "PASS_RECOMMENDED"
    assert receipt["authority_boundary"]["release_authorized"] is False
