from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company/factory-asset/lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from fa122_load_evaluator import evaluate_fa122  # noqa: E402

CONTRACT = ROOT / "company/factory-asset/contracts/fa122-live-load.v1.json"
RUNNER = ROOT / "company/factory-asset/bin/run_fa122_live_load.mjs"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_image(path: Path, seed: int) -> None:
    rng = random.Random(seed)
    data = rng.randbytes(512 * 512 * 3)
    image = Image.frombytes("RGB", (512, 512), data)
    image.save(path, format="JPEG", quality=92)


def _live_result(tmp_path: Path, duplicate_last: bool = False) -> dict:
    jobs = []
    paths = []
    for i in range(20):
        p = tmp_path / f"master-{i:02d}.jpg"
        if duplicate_last and i == 19:
            p.write_bytes(paths[0].read_bytes())
        else:
            _make_image(p, i + 100)
        paths.append(p)
        jobs.append({
            "job_id": f"FA122-JOB-{i+1:03d}",
            "semantic_asset_id": f"FASA-FA122-{i+1:03d}",
            "provider_id": "qwen" if i % 2 == 0 else "chatgpt",
            "cluster_id": "cluster-a" if i % 2 == 0 else "cluster-b",
            "status": "SUCCEEDED",
            "dispatch_committed": True,
            "attempt": {"artifact": {"path": str(p), "sha256": _sha(p)}},
        })
    unique = len({_sha(p) for p in paths})
    return {
        "schema": "die.factory-asset.fa122-live-load-result.v1",
        "task_id": "FA-122",
        "result": "COMPLETE",
        "counts": {"terminal_jobs": 20, "dispatch_commits": 20, "successful_artifacts": 20, "unique_artifact_sha256": unique, "provider_failures": 0},
        "provider_counts": {"qwen": 10, "chatgpt": 10},
        "cluster_counts": {"cluster-a": 10, "cluster-b": 10},
        "failures": [],
        "jobs": jobs,
        "topology": {
            "safety_violation": None,
            "max_combined_browser_tree_rss_mb": 4200.0,
            "max_active_leases": {"cluster-a": 1, "cluster-b": 1},
            "max_open_pages": {"cluster-a": 4, "cluster-b": 3},
            "after": {"clusters": {"cluster-a": {"active_leases": 0}, "cluster-b": {"active_leases": 0}}},
        },
        "profile_integrity": {"preserved": True},
        "truth_boundaries": {
            "provider_calls_performed": 20,
            "packaging_derivatives_counted_as_unique_masters": False,
            "credential_values_read": False,
            "cookies_or_tokens_read": False,
            "spend_usd": 0,
            "account_actions": 0,
            "marketplace_actions": 0,
        },
    }


def test_fa122_contract_bounds_and_node_selftest():
    contract = json.loads(CONTRACT.read_text())
    assert contract["target_unique_masters"] == 20
    assert contract["max_provider_generation_commits"] == 24
    assert contract["max_concurrent_generations"] == 2
    assert contract["authority"]["spend_authorized"] is False
    assert contract["authority"]["packaging_derivatives_count_as_unique_masters"] is False
    result = subprocess.run(["node", str(RUNNER), "selftest"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["result"] == "PASS"


def test_fa122_evaluator_accepts_20_distinct_qa_masters(tmp_path):
    live = _live_result(tmp_path)
    live_path = tmp_path / "live.json"
    live_path.write_text(json.dumps(live), encoding="utf-8")
    result = evaluate_fa122(live_result_path=live_path, contract_path=CONTRACT)
    assert result["result"] == "PASS"
    assert result["counts"]["qa_passed_masters"] == 20
    assert result["counts"]["unique_qa_master_sha256"] == 20
    assert result["counts"]["exact_duplicate_hash_count"] == 0
    assert all(result["assertions"].values())


def test_fa122_evaluator_rejects_exact_duplicate_volume_inflation(tmp_path):
    live = _live_result(tmp_path, duplicate_last=True)
    live_path = tmp_path / "live.json"
    live_path.write_text(json.dumps(live), encoding="utf-8")
    result = evaluate_fa122(live_result_path=live_path, contract_path=CONTRACT)
    assert result["result"] == "FAIL"
    assert result["counts"]["unique_qa_master_sha256"] == 19
    assert result["counts"]["exact_duplicate_hash_count"] == 1
    assert result["assertions"]["target_unique_qa_masters_reached"] is False
    assert result["assertions"]["zero_exact_duplicate_master_hashes"] is False
