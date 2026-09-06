from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
R = ROOT / "company/factory-asset/receipts/FA-205-founder-qc.receipt.json"
G = ROOT / "company/factory-asset/task-graph-v1.json"


def test_fa205_founder_approval_is_exact_hash_bound_and_no_submission_authority():
    r = json.loads(R.read_text())
    assert r["result"] == "APPROVE"
    assert r["founder_verdict"]["decision"] == "APPROVE"
    assert r["founder_verdict"]["silence_is_approval"] is False
    assert r["package_state_at_review"] == "PACKAGE_READY"
    assert r["exact_hashes"]["master_png"] == "5630d1fd2c2591a5f6b3a99418a8af3b6d0154b206a78eff8101fbece3470a06"
    assert r["exact_hashes"]["listing_jpeg"] == "d097dbce84ec47ef4e70ccdc819e82fe9fbd5bb460e8c5b913fb3ff03cdf7cb8"
    assert r["authority_boundary"]["founder_qc_approved"] is True
    assert r["authority_boundary"]["submission_authorized"] is False
    assert r["authority_boundary"]["publication_authorized"] is False


def test_fa205_done_unlocks_fa206():
    g = json.loads(G.read_text())
    by = {x["id"]: x for x in g["tasks"]}
    assert by["FA-205"]["status"] == "DONE"
    assert by["FA-206"]["status"] in {"READY", "DONE"}
    if by["FA-206"]["status"] == "DONE":
        r = json.loads((ROOT / "company/factory-asset/receipts/FA-206-factory-asset-v1-acceptance.receipt.json").read_text())
        assert r["result"] == "PASS"
