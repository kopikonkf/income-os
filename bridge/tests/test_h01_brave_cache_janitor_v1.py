import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company" / "company-os" / "die-h01"
POLICY = json.loads((H01 / "runtime" / "h01-brave-cache-janitor-policy.v1.json").read_text())
RECEIPT = json.loads((H01 / "receipts" / "H01-028-brave-cache-janitor.receipt.json").read_text())
ENGINE = (H01 / "engineering" / "brave_storage_gate.py").read_text()


def test_h01_028_threshold_and_receipt_are_mandatory():
    assert POLICY["task_id"] == "H01-028"
    assert POLICY["threshold"]["bytes"] == 64 * 1024**2
    assert POLICY["requirements"]["udd_closed"] is True
    assert POLICY["requirements"]["udd_mutex_required"] is True
    assert POLICY["requirements"]["receipt_required_for_cleanup"] is True
    assert POLICY["requirements"]["protected_entries_touched"] is False


def test_h01_028_live_receipt_proves_thresholded_cleanup():
    assert RECEIPT["status"] == "PASS"
    assert RECEIPT["threshold_met"] is True
    assert RECEIPT["before_reclaimable_bytes"] >= RECEIPT["threshold_bytes"]
    assert RECEIPT["after_reclaimable_bytes"] == 0
    assert RECEIPT["reclaimed_bytes"] == RECEIPT["before_reclaimable_bytes"] - RECEIPT["after_reclaimable_bytes"]
    assert RECEIPT["udd_closed"] is True
    assert RECEIPT["lock_acquired"] is True
    assert RECEIPT["protected_entries_touched"] is False
    assert RECEIPT["receipt_required_for_each_accepted_cleanup"] is True


def test_h01_028_reuses_h01_024_allowlist_and_protected_boundary():
    for cache_name in ("Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache"):
        assert cache_name in ENGINE
    for protected_name in ("Cookies", "Local Storage", "IndexedDB", "Session Storage", "Sessions", "Preferences", "Secure Preferences"):
        assert protected_name in ENGINE
    assert "E_UDD_ACTIVE" in ENGINE
    assert "E_UDD_LOCKED" in ENGINE
