from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
OBJECT = ROOT / "company" / "atlas" / "object-centric" / "object-asset-engine"
SOURCE = OBJECT / "source"
MIGRATION = OBJECT / "migration"
FOUNDATION = ROOT / "company" / "atlas" / "human-centric" / "foundations" / "qwen-crossjoin-v1"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_die203_linux_source_manifest_is_clean_and_portable() -> None:
    manifest = json.loads((SOURCE / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "die.object-engine-linux-source.v1"
    assert manifest["linux_runnable"] is True
    assert manifest["source_python_files"] == 23
    assert len(manifest["files"]) == 23
    assert manifest["windows_path_literal_hits"] == 0
    assert manifest["generated_bytecode_included"] is False
    assert not list(SOURCE.rglob("*.pyc"))
    assert not list(SOURCE.rglob("__pycache__"))
    excluded = manifest["excluded_windows_source"]
    assert len(excluded) == 1
    assert excluded[0]["path"] == "scripts/audit/gemini_audit_parallel.py"
    assert "SyntaxError" in excluded[0]["reason"]

    forbidden = ("D:\\object-asset-engine", "D:\\Dee_Workspace", "D:/object-asset-engine")
    for path in SOURCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into {path}"


def test_die203_all_linux_python_source_compiles_without_bytecode_side_effect() -> None:
    for path in sorted(SOURCE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def test_die203_path_contract_and_credential_gate_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DIE_OBJECT_ENGINE_ROOT", str(tmp_path / "engine"))
    monkeypatch.delenv("DIE_OBJECT_ENGINE_GEMINI_KEY_FILE", raising=False)
    module = _load_module("die203_paths_no_cred", SOURCE / "object_engine_paths.py")
    assert module.ROOT == (tmp_path / "engine").resolve()
    assert module.CANON_DB == module.ROOT / "db" / "object_asset_engine.db"
    assert module.SEED_LIBRARY_DB == module.ROOT / "db" / "seed_library.db"
    with pytest.raises(RuntimeError, match="DIE_OBJECT_ENGINE_GEMINI_KEY_FILE_REQUIRED"):
        module.require_gemini_key_file()


def test_die203_path_contract_accepts_explicit_credential_file(tmp_path: Path, monkeypatch) -> None:
    secret = tmp_path / "gemini.txt"
    secret.write_text("fixture-only", encoding="utf-8")
    monkeypatch.setenv("DIE_OBJECT_ENGINE_ROOT", str(tmp_path / "engine"))
    monkeypatch.setenv("DIE_OBJECT_ENGINE_GEMINI_KEY_FILE", str(secret))
    module = _load_module("die203_paths_cred", SOURCE / "object_engine_paths.py")
    assert module.require_gemini_key_file() == secret.resolve()


def test_die203_sqlite_online_backup_is_consistent_and_does_not_copy_wal(tmp_path: Path) -> None:
    source = tmp_path / "live.db"
    dest = tmp_path / "snapshot.db"
    receipt = tmp_path / "receipt.json"
    conn = sqlite3.connect(source)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE items(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
    conn.executemany("INSERT INTO items(value) VALUES(?)", [(f"v{i}",) for i in range(1000)])
    conn.commit()
    conn.execute("INSERT INTO items(value) VALUES('after-commit')")
    conn.commit()

    proc = subprocess.run(
        [
            sys.executable,
            str(MIGRATION / "sqlite_online_backup.py"),
            "--source", str(source),
            "--dest", str(dest),
            "--receipt", str(receipt),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    conn.close()
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema"] == "die.sqlite-online-backup.v1"
    assert payload["quick_check"] == "ok"
    assert payload["raw_wal_shm_copied"] is False
    assert payload["source_open_mode"] == "read-only"
    assert payload["backup_api"] == "sqlite3.Connection.backup"
    with sqlite3.connect(dest) as snap:
        assert snap.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 1001
        assert snap.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_die203_install_contract_never_starts_writer_or_copies_windows_secret() -> None:
    text = (OBJECT / "install-linux.sh").read_text(encoding="utf-8")
    assert "/var/lib/die" in text
    assert "/etc/die/object-asset-engine" in text
    assert "DIE_OBJECT_ENGINE_GEMINI_KEY_FILE" in text
    assert "makan.txt" in text  # documentation says never copy it
    assert "SERVICE_STARTED=NO" in text
    assert "WINDOWS_CREDENTIAL_COPIED=NO" in text
    assert "systemctl start" not in text
    assert "gemini_audit_scale.py --run" not in text


def test_die203_human_atlas_foundations_are_provenance_not_normative_canon() -> None:
    manifest = json.loads((FOUNDATION / "FOUNDATION_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "die.human-atlas.foundation-corpus.v1"
    assert manifest["normative_canon"] is False
    assert manifest["canon_promotion_requires_founder_ratification"] is True
    assert len(manifest["files"]) == 4
    statuses = {row["status"] for row in manifest["files"]}
    assert "FOUNDATION_REFERENCE_NOT_RATIFIED" in statuses
    assert "FOUNDATION_REFERENCE_BRAINSTORM" in statuses
    for row in manifest["files"]:
        path = FOUNDATION / row["path"]
        assert path.is_file()
        assert path.stat().st_size == row["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_die203_crossjoin_foundation_preserves_core_primitives() -> None:
    manifest = json.loads((FOUNDATION / "FOUNDATION_MANIFEST.json").read_text(encoding="utf-8"))
    primitives = set(manifest["architectural_primitives_worth_preserving"])
    assert "10D dimension model" in primitives
    assert "coherence constraint filtering" in primitives
    assert "weighted sampling instead of exhaustive Cartesian enumeration" in primitives
    assert "Worth-Making Gate" in primitives
    assert "event-driven scaling" in primitives

def test_die203_final_promotion_receipt_seals_475560_baseline() -> None:
    receipt = json.loads((ROOT / "company" / "muxia" / "receipts" / "DIE-203-final-promotion.receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["decision"]["seed_library_final_475560_is_die203_final_baseline"] is True
    runtime = receipt["linux_authoritative_runtime"]
    assert runtime["promotion_status"] == "LINUX_AUTHORITATIVE_VERIFIED"
    assert runtime["main_db"]["sha256"] == "e6e43fbd4bbee712de651c31a159bb66872a91b1b555f809d0177ba856eeb891"
    assert runtime["main_db"]["audit_done"] == 744259
    assert runtime["seed_library"]["sha256"] == "3035b179ba435a9cc4983ca567528b15941b1a9f205451d425cd40ce5925ab77"
    assert runtime["seed_library"]["objects"] == 475560
    assert runtime["seed_library"]["distinct_lower_trim_word"] == 475560
    assert runtime["checkpoint_seed_library"]["objects"] == 433835
    assert receipt["safety"]["raw_windows_wal_shm_copied"] is False
    assert receipt["safety"]["linux_writer_started"] is False


def test_die203_task_graph_is_done_after_verified_final_promotion() -> None:
    graph = json.loads((ROOT / "company" / "muxia-task-graph-v1.json").read_text(encoding="utf-8"))
    tasks = {row["id"]: row for row in graph["tasks"]}
    assert tasks["DIE-203"]["status"] == "DONE"
    assert tasks["DIE-204"]["status"] == "BLOCKED"
