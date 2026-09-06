from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERMES = ROOT / "company/die-agents/hermes"
RUNTIME = HERMES / "production-runtime"
for p in (HERMES, RUNTIME):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from production_seed_replenisher import replenish_seed_pool
from production_seed_selector import select_seed, produced_seed_ids


def _db(path: Path) -> None:
    c = sqlite3.connect(path)
    c.executescript(
        """
        CREATE TABLE seeds (
          id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, aliases TEXT,
          object_class TEXT, existence_type TEXT, category_path TEXT,
          visuality_score REAL, demand_score REAL, risk_score REAL,
          status TEXT NOT NULL DEFAULT 'review', created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, canonical_lang TEXT DEFAULT 'en-US',
          asset_tier TEXT DEFAULT 'U1-raster', source_batch TEXT,
          master_source_id TEXT, demand_signal TEXT, demand_status TEXT
        );
        CREATE TABLE candidate_seeds (
          id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, aliases TEXT DEFAULT '[]',
          word_count INTEGER DEFAULT 1, concreteness_score REAL DEFAULT 0,
          suitability TEXT DEFAULT 'pending', ip_risk TEXT DEFAULT 'none',
          source_tier TEXT, wave3_status TEXT DEFAULT 'pending',
          promoted_to_seed_id TEXT, status TEXT DEFAULT 'pending', updated_at TEXT
        );
        """
    )
    c.execute(
        "INSERT INTO seeds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("SEED-000001", "legacy object", "[]", "concrete_visual", "real_world", "legacy", 0.9, 0.7, 0.0, "approved", "x", "x", "en-US", "U1-raster", "legacy", None, "HIGH", "validated_high"),
    )
    rows = [
        ("CAND-000001", "flower", "[]", 1, 0.90, "lexname=noun.plant", "none", "pass", "eligible", None, "pending", "x"),
        ("CAND-000002", "apron", "[]", 1, 0.95, "lexname=noun.artifact", "none", "pass", "eligible", None, "pending", "x"),
        ("CAND-000003", "bell", "[]", 1, 0.95, "lexname=noun.artifact", "none", "pass", "eligible", None, "pending", "x"),
        ("CAND-000004", "blocked logo thing", "[]", 3, 0.95, "lexname=noun.artifact", "high", "pass", "eligible", None, "pending", "x"),
        ("CAND-000005", "review object", "[]", 2, 0.95, "lexname=noun.artifact", "none", "review", "eligible", None, "pending", "x"),
    ]
    c.executemany("INSERT INTO candidate_seeds VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    c.commit(); c.close()


def _policy(path: Path) -> None:
    value = json.loads((RUNTIME / "production_seed_replenishment_policy.v1.json").read_text())
    value["low_watermark"] = 2
    value["target_pool_size"] = 3
    value["max_promotions_per_run"] = 3
    value["direct_terms"] = ["flower"]
    value["utility_terms"] = ["apron", "bell", "blocked logo thing", "review object"]
    path.write_text(json.dumps(value))


def test_replenisher_promotes_only_gated_candidates_and_binds_expression(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    work = tmp_path / "workspaces"; work.mkdir()
    used = work / "PRODOLD"; used.mkdir(); (used / "seed-selection.json").write_text(json.dumps({"seed":{"id":"SEED-000001"}}))
    policy = tmp_path / "policy.json"; _policy(policy)
    state = tmp_path / "state"

    dry = replenish_seed_pool(db, work, policy_path=policy, state_root=state, dry_run=True)
    assert dry["status"] == "DRY_RUN" and dry["planned_count"] == 3
    assert [x["canonical_name"] for x in dry["planned"]] == ["flower", "apron", "bell"]
    assert dry["planned"][0]["evidence_level"] == "DIRECT_TERM_OBSERVED"
    assert all(x["demand_status"] in {"validated_high", "validated_medium"} for x in dry["planned"])

    done = replenish_seed_pool(db, work, policy_path=policy, state_root=state)
    assert done["status"] == "PROMOTED" and done["promoted_count"] == 3
    assert done["remaining_before"] == 0 and done["remaining_after"] == 3
    assert Path(done["receipt_path"]).is_file()

    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    try:
        promoted = c.execute("SELECT canonical_name,source_batch,demand_signal,demand_status,master_source_id FROM seeds WHERE source_batch='PROD-SEED-REPLENISH-V1' ORDER BY id").fetchall()
        assert [r["canonical_name"] for r in promoted] == ["flower", "apron", "bell"]
        assert promoted[0]["demand_signal"] == "REPLENISH_DIRECT_TERM"
        assert promoted[1]["demand_signal"] == "REPLENISH_CATEGORY_LEVEL"
        assert all(str(r["master_source_id"]).startswith("EXPR-") for r in promoted)
        expr = c.execute("SELECT count(*) FROM production_seed_expressions").fetchone()[0]
        assert expr == 3
        assert c.execute("SELECT promoted_to_seed_id FROM candidate_seeds WHERE id='CAND-000004'").fetchone()[0] is None
        assert c.execute("SELECT promoted_to_seed_id FROM candidate_seeds WHERE id='CAND-000005'").fetchone()[0] is None
    finally:
        c.close()


def test_selector_returns_expression_and_seed_selection_marks_it_used(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    work = tmp_path / "workspaces"; work.mkdir()
    used = work / "PRODOLD"; used.mkdir(); (used / "seed-selection.json").write_text(json.dumps({"seed":{"id":"SEED-000001"}}))
    policy = tmp_path / "policy.json"; _policy(policy)
    replenish_seed_pool(db, work, policy_path=policy, state_root=tmp_path / "state")

    first = select_seed(db, work)
    assert first["status"] == "SELECTED"
    assert first["seed"]["canonical_name"] == "flower"
    assert first["commercial_expression"]["expression_id"].startswith("EXPR-")
    assert first["commercial_expression"]["evidence_level"] == "DIRECT_TERM_OBSERVED"

    w = work / "PRODNEW"; w.mkdir(); (w / "seed-selection.json").write_text(json.dumps(first))
    assert first["seed"]["id"] in produced_seed_ids(work)
    second = select_seed(db, work)
    assert second["status"] == "SELECTED" and second["seed"]["id"] != first["seed"]["id"]

    # With two remaining seeds and low-watermark=2, top-up is intentionally a no-op.
    again = replenish_seed_pool(db, work, policy_path=policy, state_root=tmp_path / "state")
    assert again["status"] == "NOOP_POOL_HEALTHY" and again["promoted_count"] == 0


def test_policy_truth_boundary_does_not_claim_exact_noun_transactions():
    p = json.loads((RUNTIME / "production_seed_replenishment_policy.v1.json").read_text())
    truth = p["evidence"]["truth_boundary"]
    assert truth["absolute_search_volume_available"] is False
    assert truth["exact_noun_transaction_observed"] is False
    assert truth["category_level_market_utility_observed"] is True
    assert p["authority"] == {"provider_call": False, "submission": False, "publication": False, "marketplace_upload": False, "spend_usd": 0}

def test_runtime_start_seed_replenishes_then_starts_without_provider_call(tmp_path: Path, monkeypatch):
    import production_runtime_tick as rt
    db = tmp_path / "atlas.db"; _db(db)
    work = tmp_path / "workspaces"; work.mkdir()
    old = work / "PRODOLD"; old.mkdir(); (old / "seed-selection.json").write_text(json.dumps({"seed":{"id":"SEED-000001"}}))
    policy = tmp_path / "policy.json"; _policy(policy)
    state = tmp_path / "state"
    monkeypatch.setattr(rt, "DB", db)
    monkeypatch.setattr(rt, "WORKSPACES", work)
    monkeypatch.setattr(rt, "REPLENISH_POLICY", policy)
    monkeypatch.setattr(rt, "REPLENISH_STATE", state)
    def fake_shared(w: Path):
        provider = w / "provider"
        provider.mkdir(exist_ok=True)
        return provider
    monkeypatch.setattr(rt, "ensure_shared_workspace", fake_shared)
    monkeypatch.setattr(rt.factory_v2, "telegram_event", lambda *args, **kwargs: None)
    result = rt.start_seed()
    assert result["status"] == "STARTED"
    assert result["provider_call_performed"] is False
    assert result["replenishment"]["status"] == "PROMOTED"
    workspace = work / result["task_id"]
    selection = json.loads((workspace / "seed-selection.json").read_text())
    assert selection["seed"]["id"] == result["seed_id"]
    assert selection["commercial_expression"]["expression_id"].startswith("EXPR-")
    progress = (workspace / "PROGRESS.md").read_text()
    assert "State: BLUEPRINT_REQUIRED" in progress
    assert "Commercial expression:" in progress


def test_audit_surface_must_be_writable_before_db_mutation(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    work = tmp_path / "workspaces"; work.mkdir()
    old = work / "PRODOLD"; old.mkdir(); (old / "seed-selection.json").write_text(json.dumps({"seed":{"id":"SEED-000001"}}))
    policy = tmp_path / "policy.json"; _policy(policy)
    state = tmp_path / "state"; state.mkdir(); state.chmod(0o555)
    try:
        failed = False
        try:
            replenish_seed_pool(db, work, policy_path=policy, state_root=state)
        except OSError:
            failed = True
        assert failed is True
    finally:
        state.chmod(0o755)
    c = sqlite3.connect(db)
    try:
        assert c.execute("SELECT count(*) FROM seeds").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM candidate_seeds WHERE promoted_to_seed_id IS NOT NULL").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='production_seed_expressions'").fetchone()[0] == 0
    finally:
        c.close()


def test_pending_receipt_blocks_future_replenishment_until_reconciled(tmp_path: Path):
    db = tmp_path / "atlas.db"; _db(db)
    work = tmp_path / "workspaces"; work.mkdir()
    old = work / "PRODOLD"; old.mkdir(); (old / "seed-selection.json").write_text(json.dumps({"seed":{"id":"SEED-000001"}}))
    policy = tmp_path / "policy.json"; _policy(policy)
    state = tmp_path / "state"; state.mkdir()
    pending = state / "REPLENISH-TEST.json"
    pending.write_text(json.dumps({"schema":"die.production-seed-replenishment.v1","status":"PENDING_DB_COMMIT"}))
    message = ""
    try:
        replenish_seed_pool(db, work, policy_path=policy, state_root=state)
    except RuntimeError as exc:
        message = str(exc)
    assert "E_PENDING_REPLENISHMENT_RECEIPT" in message
    c = sqlite3.connect(db)
    try:
        assert c.execute("SELECT count(*) FROM seeds").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM candidate_seeds WHERE promoted_to_seed_id IS NOT NULL").fetchone()[0] == 0
    finally:
        c.close()
