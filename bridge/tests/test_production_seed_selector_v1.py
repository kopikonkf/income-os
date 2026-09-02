import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = ROOT / "company" / "die-agents" / "hermes" / "production_seed_selector.py"


def _db(path: Path) -> None:
    c = sqlite3.connect(path)
    c.execute(
        """
        CREATE TABLE seeds (
          id TEXT PRIMARY KEY, canonical_name TEXT, aliases TEXT,
          object_class TEXT, existence_type TEXT, category_path TEXT,
          visuality_score REAL, demand_score REAL, risk_score REAL,
          status TEXT, created_at TEXT, updated_at TEXT,
          canonical_lang TEXT, asset_tier TEXT, source_batch TEXT,
          master_source_id TEXT, demand_signal TEXT, demand_status TEXT
        )
        """
    )
    rows = [
        ("SEED-000001", "used high", "approved", "U1-raster", "validated_high", 0.95),
        ("SEED-000002", "next high", "approved", "U1-raster", "validated_high", 0.90),
        ("SEED-000003", "higher medium", "approved", "U1-raster", "validated_medium", 0.99),
        ("SEED-000004", "rejected", "rejected", "U1-raster", "validated_high", 1.00),
        ("SEED-000005", "speculative", "approved", "U1-raster", "speculative", 1.00),
        ("SEED-000006", "wrong tier", "approved", "vector", "validated_high", 1.00),
    ]
    for sid, name, status, tier, demand_status, score in rows:
        c.execute(
            "INSERT INTO seeds(id,canonical_name,object_class,existence_type,category_path,demand_score,status,asset_tier,demand_status) VALUES(?,?,?,?,?,?,?,?,?)",
            (sid, name, "object", "real", "Test", score, status, tier, demand_status),
        )
    c.commit(); c.close()


def test_selector_chooses_highest_ranked_approved_unused_seed(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    workspaces = tmp_path / "workspaces"; ws = workspaces / "OLD" / "qa"; ws.mkdir(parents=True)
    (ws / "manifest.json").write_text(json.dumps({"master_id": "SEED-000001"}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SELECTOR), "--db", str(db), "--workspaces", str(workspaces)], text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["status"] == "SELECTED"
    assert payload["seed"]["id"] == "SEED-000002"
    assert payload["seed"]["demand_status"] == "validated_high"
    assert payload["used_seed_ids"] == ["SEED-000001"]
    assert payload["authority_effect"] == "NONE"
    assert payload["existing_authority_unchanged"] is True
    assert "authority" not in payload


def test_selector_uses_job_context_as_legacy_used_seed_evidence(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    workspaces = tmp_path / "workspaces"; ws = workspaces / "OLD"; ws.mkdir(parents=True)
    (ws / "job.json").write_text(json.dumps({"context": "Canonical seed: SEED-000001, approved."}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SELECTOR), "--db", str(db), "--workspaces", str(workspaces)], text=True, capture_output=True, check=False)
    assert json.loads(proc.stdout)["seed"]["id"] == "SEED-000002"


def test_selector_fails_closed_when_database_is_missing(tmp_path: Path):
    proc = subprocess.run([sys.executable, str(SELECTOR), "--db", str(tmp_path / "missing.db"), "--workspaces", str(tmp_path)], text=True, capture_output=True, check=False)
    payload = json.loads(proc.stdout)
    assert proc.returncode == 2
    assert payload["status"] == "BLOCKED"


def test_selector_is_read_only(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    before = db.read_bytes()
    proc = subprocess.run([sys.executable, str(SELECTOR), "--db", str(db), "--workspaces", str(tmp_path / "workspaces")], text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    assert db.read_bytes() == before


def test_selector_never_revokes_existing_production_authority(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    proc = subprocess.run([sys.executable, str(SELECTOR), "--db", str(db), "--workspaces", str(tmp_path / "workspaces")], text=True, capture_output=True, check=False)
    payload = json.loads(proc.stdout)
    assert payload["status"] == "SELECTED"
    assert payload["authority_effect"] == "NONE"
    assert payload["existing_authority_unchanged"] is True
    assert "production_provider_authorized" not in json.dumps(payload)
