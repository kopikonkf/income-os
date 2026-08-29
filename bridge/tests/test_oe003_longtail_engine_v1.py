from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "longtail"
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


OBJ = _load("oe003b_obj_engine_test", ENGINE / "retrieve_object_seeds.py")
HCTX = _load("oe003c_hctx_engine_test", ENGINE / "retrieve_human_contexts.py")
GEN = _load("oe003d_generator_test", ENGINE / "generate_longtail.py")
GUARD = _load("oe003e_guard_test", ENGINE / "guard_longtail.py")
PHRASE = _load("oe003f_phrase_score_test", ENGINE / "phrase_signal_score.py")
REG = _load("oe003g_registry_test", ENGINE / "longtail_registry.py")
RUNNER = _load("oe003_runner_test", ENGINE / "run_synthetic_canary.py")
SIGVAL = _load("oe003_signal_validator_test", SIGNALS / "validate_signal_receipt.py")

CREATED = "2026-08-29T12:00:00Z"
EVALUATED = "2026-08-29T12:10:00Z"
CLEAR_VETO = {
    "status": "CLEAR",
    "receipt_ref": "fixture://longtail/hard-veto-clear-v1",
    "receipt_sha256": hashlib.sha256(b"longtail-hard-veto-clear-v1").hexdigest(),
}
UNKNOWN_VETO = {"status": "UNKNOWN", "receipt_ref": None, "receipt_sha256": None}
BLOCKED_VETO = {
    "status": "BLOCKED",
    "receipt_ref": "fixture://longtail/hard-veto-blocked-v1",
    "receipt_sha256": hashlib.sha256(b"longtail-hard-veto-blocked-v1").hexdigest(),
}


def _make_object_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE seeds(
      id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL UNIQUE, aliases TEXT,
      object_class TEXT, existence_type TEXT, category_path TEXT,
      visuality_score REAL, demand_score REAL, risk_score REAL,
      status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    rows = [
        ("OBJ-CABLE-001", "cable organizer", "[]", "office_accessory", "real", "office/organization", 0.91, 0.88, 0.02, "approved", "2026-08-01T00:00:00Z", "2026-08-29T00:00:00Z"),
        ("OBJ-REVIEW-001", "review gadget", "[]", "gadget", "real", "misc", 0.90, 0.99, 0.01, "review", "2026-08-01T00:00:00Z", "2026-08-29T00:00:00Z"),
    ]
    conn.executemany("INSERT INTO seeds VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close(); return path


def _foundation(tmp_path: Path, budget: int = 6):
    db = _make_object_db(tmp_path / "object.db")
    objects = OBJ.retrieve(db, {"canonical_names": ["cable organizer"], "limit": 1})
    contexts = HCTX.retrieve({"object_name": "cable organizer", "limit": 1})
    generation = GEN.generate(objects, contexts, budget=budget, expression_level="L0", created_at=CREATED)
    guard = GUARD.apply(generation)
    return db, objects, contexts, generation, guard


def _plan(search: float = 80, supply: int = 500, buyer: bool = True, observed: str = "2026-08-29T12:00:00Z", window: int = 86400) -> dict:
    return {
        "search_interest_index": search,
        "visible_result_count": supply,
        "buyer_term_presence": buyer,
        "observed_at": observed,
        "freshness_window_seconds": window,
    }


def _reid(candidate: dict, phrase: str) -> dict:
    out = copy.deepcopy(candidate)
    out["phrase"] = GEN.normalize_phrase(phrase)
    expression = out["product_expression"]["level"] if out.get("product_expression") else ""
    out["candidate_id"] = GEN._hash_id(out["parent_seed"]["seed_id"], out["human_context"]["context_id"], out["phrase"], expression)
    return out


def test_oe003d_dynamic_generation_is_bounded_deterministic_and_not_legacy_dictionary(tmp_path: Path) -> None:
    _, objects, contexts, a, _ = _foundation(tmp_path, budget=6)
    b = GEN.generate(objects, contexts, budget=6, expression_level="L0", created_at=CREATED)
    assert a == b
    assert a["generated_count"] == 6
    assert a["budget"] == 6
    assert all(c["generation"]["legacy_expansion_dictionary_used_as_core"] is False for c in a["candidates"])
    code = (ENGINE / "generate_longtail.py").read_text(encoding="utf-8")
    assert "EXPANSIONS =" not in code


def test_oe003d_every_child_requires_own_evidence_and_no_parent_score_inheritance(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    for c in generation["candidates"]:
        assert c["evidence_state"] == "REQUIRES_PHRASE_LEVEL_OE001_OE002"
        assert c["parent_demand"]["inherited_by_child"] is False
        assert c["parent_demand"]["parent_score_ref"] is None
        assert 1 <= len(c["modifiers"]) <= 4


def test_oe003d_budget_and_expression_fail_closed(tmp_path: Path) -> None:
    _, objects, contexts, _, _ = _foundation(tmp_path)
    with pytest.raises(GEN.GenerationError, match="E_GENERATION_BUDGET"):
        GEN.generate(objects, contexts, budget=51, expression_level="L0", created_at=CREATED)
    with pytest.raises(GEN.GenerationError, match="E_EXPRESSION_LEVEL"):
        GEN.generate(objects, contexts, budget=2, expression_level="L9", created_at=CREATED)


def test_oe003e_baseline_guard_accepts_structurally_distinct_candidates(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    assert guard["counts"] == {"ACCEPTED": 6, "REVIEW": 0, "REJECTED": 0}
    assert [x["candidate_id"] for x in guard["outcomes"]] == [x["candidate_id"] for x in generation["candidates"]]


def test_oe003e_exact_duplicate_parent_redundancy_and_quota_are_rejected(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    dup = copy.deepcopy(generation); dup["candidates"].append(copy.deepcopy(generation["candidates"][0]))
    guarded = GUARD.apply(dup)
    assert guarded["outcomes"][-1]["status"] == "REJECTED"
    assert "EXACT_DUPLICATE" in guarded["outcomes"][-1]["reasons"]

    parent = copy.deepcopy(generation); parent["candidates"] = [_reid(generation["candidates"][0], "cable organizer")]
    g2 = GUARD.apply(parent)
    assert g2["outcomes"][0]["status"] == "REJECTED"
    assert "PARENT_REDUNDANCY" in g2["outcomes"][0]["reasons"]

    quota = GUARD.apply(generation, max_per_seed=2)
    assert quota["counts"]["ACCEPTED"] == 2
    assert sum("SEED_QUOTA_EXCEEDED" in x["reasons"] for x in quota["outcomes"]) == 4


def test_oe003e_near_duplicate_reject_and_review_thresholds(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    base = generation["candidates"][0]
    p1 = _reid(base, "cable organizer for remote work desk setup home office team")
    p2 = _reid(base, "cable organizer for remote work desk setup home office team daily")
    p3 = _reid(base, "cable organizer for remote work desk setup home office team daily routine")
    custom = copy.deepcopy(generation); custom["candidates"] = [p1, p2, p3]
    guarded = GUARD.apply(custom)
    assert guarded["outcomes"][0]["status"] == "ACCEPTED"
    assert guarded["outcomes"][1]["status"] == "REJECTED"
    assert any(x.startswith("NEAR_DUPLICATE_GE_") for x in guarded["outcomes"][1]["reasons"])
    assert guarded["outcomes"][2]["status"] == "REVIEW"
    assert any(x.startswith("NEAR_DUPLICATE_0.75_0.90") for x in guarded["outcomes"][2]["reasons"])


def test_oe003e_ip_term_routes_to_review_not_silent_kill(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    branded = _reid(generation["candidates"][0], "nike cable organizer for remote work")
    custom = copy.deepcopy(generation); custom["candidates"] = [branded]
    guarded = GUARD.apply(custom)
    assert guarded["outcomes"][0]["status"] == "REVIEW"
    assert "IP_TERM_REVIEW:nike" in guarded["outcomes"][0]["reasons"]
    assert guarded["policy"]["ip_terms_are_complete_legal_clearance"] is False


def test_oe003e_candidate_id_tamper_fails_closed(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    bad = copy.deepcopy(generation); bad["candidates"][0]["candidate_id"] = "LT-CAND-TAMPERED000000000000000"
    with pytest.raises(GUARD.GuardError, match="E_CANDIDATE_ID_MISMATCH"):
        GUARD.apply(bad)


def test_oe003f_synthetic_fixture_chain_produces_three_valid_child_specific_oe001_receipts(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    candidate = generation["candidates"][0]; outcome = guard["outcomes"][0]
    receipts = PHRASE.synthetic_receipts(candidate, _plan())
    schema = json.loads((SIGNALS / "die.division001.opportunity-signals.v1.schema.json").read_text(encoding="utf-8"))
    as_of = SIGVAL.parse_time(EVALUATED)
    assert len(receipts) == 3
    assert {r["signal_class"] for r in receipts} == {"DEMAND", "SUPPLY", "COMMERCIAL_INTENT"}
    for receipt in receipts:
        assert SIGVAL.validate(receipt, schema, as_of=as_of) == []
        assert receipt["subject"]["id"] == candidate["phrase"]
        assert receipt["subject"]["parent_seed_id"] == candidate["parent_seed"]["seed_id"]
        assert receipt["subject"]["parent_candidate_id"] == candidate["candidate_id"]
        assert receipt["evidence_label"] == "SYNTHETIC"
        assert receipt["policy"]["classification"] == "SYNTHETIC_ONLY"
    assert outcome["status"] == "ACCEPTED"


def test_oe003f_phrase_level_oe001_to_oe002_complete_score_and_replay(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    candidate = generation["candidates"][0]; outcome = guard["outcomes"][0]
    registry = tmp_path / "signals.db"
    a = PHRASE.synthetic_canary(candidate, outcome, _plan(85, 500, True), CLEAR_VETO, registry_db=registry, evaluated_at=EVALUATED)
    b = PHRASE.synthetic_canary(candidate, outcome, _plan(85, 500, True), CLEAR_VETO, registry_db=registry, evaluated_at=EVALUATED)
    assert a == b
    assert a["demand_score"]["score_status"] == "COMPLETE"
    assert isinstance(a["demand_score"]["final_score"], float)
    assert a["parent_score_inherited"] is False
    assert a["fresh_signal_count"] == 3


def test_oe003f_missing_required_signal_returns_partial_not_fake_numeric(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    candidate = generation["candidates"][0]; outcome = guard["outcomes"][0]
    receipts = PHRASE.synthetic_receipts(candidate, _plan())[:2]
    result = PHRASE.score_from_receipts(candidate, outcome, receipts, CLEAR_VETO, registry_db=tmp_path / "signals.db", evaluated_at=EVALUATED)
    assert result["demand_score"]["score_status"] == "PARTIAL"
    assert result["demand_score"]["final_score"] is None


def test_oe003f_veto_unknown_and_blocked_never_emit_numeric(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    c = generation["candidates"][0]; o = guard["outcomes"][0]
    unknown = PHRASE.synthetic_canary(c, o, _plan(), UNKNOWN_VETO, registry_db=tmp_path / "u.db", evaluated_at=EVALUATED)
    blocked = PHRASE.synthetic_canary(c, o, _plan(), BLOCKED_VETO, registry_db=tmp_path / "b.db", evaluated_at=EVALUATED)
    assert (unknown["demand_score"]["score_status"], unknown["demand_score"]["final_score"]) == ("PARTIAL", None)
    assert (blocked["demand_score"]["score_status"], blocked["demand_score"]["final_score"]) == ("HARD_VETO", None)


def test_oe003f_stale_subject_mismatch_and_review_guard_fail_closed(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    c = generation["candidates"][0]; o = guard["outcomes"][0]
    with pytest.raises(PHRASE.PhraseScoreError, match="E_SIGNAL_INVALID"):
        PHRASE.synthetic_canary(c, o, _plan(observed="2026-08-20T00:00:00Z", window=60), CLEAR_VETO, registry_db=tmp_path / "stale.db", evaluated_at=EVALUATED)
    receipts = PHRASE.synthetic_receipts(c, _plan()); receipts[0]["subject"]["id"] = "other phrase"
    with pytest.raises(PHRASE.PhraseScoreError, match="E_SIGNAL_SUBJECT_MISMATCH"):
        PHRASE.score_from_receipts(c, o, receipts, CLEAR_VETO, registry_db=tmp_path / "mismatch.db", evaluated_at=EVALUATED)
    review = copy.deepcopy(o); review["status"] = "REVIEW"
    with pytest.raises(PHRASE.PhraseScoreError, match="E_GUARD_NOT_ACCEPTED"):
        PHRASE.synthetic_canary(c, review, _plan(), CLEAR_VETO, registry_db=tmp_path / "review.db", evaluated_at=EVALUATED)


def test_oe003g_registry_is_idempotent_and_separate_from_object_db(tmp_path: Path) -> None:
    object_db, _, _, generation, guard = _foundation(tmp_path)
    before = hashlib.sha256(object_db.read_bytes()).hexdigest()
    conn = REG.connect(tmp_path / "longtail.db")
    try:
        first = REG.ingest_guard(conn, guard)
        second = REG.ingest_guard(conn, guard)
        assert first == {"INSERTED": 6, "DUPLICATE": 0, "CONFLICT": 0}
        assert second == {"INSERTED": 0, "DUPLICATE": 6, "CONFLICT": 0}
        assert REG.count(conn) == generation["generated_count"]
    finally:
        conn.close()
    after = hashlib.sha256(object_db.read_bytes()).hexdigest()
    assert before == after


def test_oe003g_attach_score_idempotency_conflict_and_complete_only_ranking(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    lt = REG.connect(tmp_path / "longtail.db")
    signal_db = tmp_path / "signals.db"
    try:
        REG.ingest_guard(lt, guard)
        high = PHRASE.synthetic_canary(generation["candidates"][0], guard["outcomes"][0], _plan(90, 300, True), CLEAR_VETO, registry_db=signal_db, evaluated_at=EVALUATED)
        low = PHRASE.synthetic_canary(generation["candidates"][1], guard["outcomes"][1], _plan(25, 90000, False), CLEAR_VETO, registry_db=signal_db, evaluated_at=EVALUATED)
        assert REG.attach_score(lt, high) == "ATTACHED"
        assert REG.attach_score(lt, low) == "ATTACHED"
        assert REG.attach_score(lt, high) == "DUPLICATE"
        tampered = copy.deepcopy(high); tampered["signal_ids"] = tampered["signal_ids"] + ["OPSIG-TAMPERED-00000001"]
        assert REG.attach_score(lt, tampered) == "CONFLICT"
        ranking = REG.ranking(lt)
        assert ranking["ranked_count"] == 2
        assert [x["candidate_id"] for x in ranking["ranked"]] == [high["candidate_id"], low["candidate_id"]]
        assert ranking["ranked"][0]["final_score"] > ranking["ranked"][1]["final_score"]
        assert sum(x["count"] for x in ranking["deferred"]) == 4
    finally:
        lt.close()


def test_oe003g_partial_scores_are_persisted_but_deferred_from_ranking(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    c = generation["candidates"][0]; o = guard["outcomes"][0]
    partial = PHRASE.score_from_receipts(c, o, PHRASE.synthetic_receipts(c, _plan())[:2], CLEAR_VETO, registry_db=tmp_path / "signals.db", evaluated_at=EVALUATED)
    conn = REG.connect(tmp_path / "longtail.db")
    try:
        REG.ingest_guard(conn, guard)
        assert REG.attach_score(conn, partial) == "ATTACHED"
        ranking = REG.ranking(conn)
        assert ranking["ranked_count"] == 0
        assert {x["score_status"] for x in ranking["deferred"]} >= {"PARTIAL", "UNSCORED"}
    finally:
        conn.close()


def test_oe003g_review_candidate_cannot_receive_score(tmp_path: Path) -> None:
    _, _, _, generation, _ = _foundation(tmp_path)
    branded = _reid(generation["candidates"][0], "nike cable organizer for remote work")
    custom = copy.deepcopy(generation); custom["candidates"] = [branded]
    guard = GUARD.apply(custom)
    conn = REG.connect(tmp_path / "longtail.db")
    try:
        REG.ingest_guard(conn, guard)
        fake = {"schema": "die.division001.longtail-phrase-score.v1", "candidate_id": branded["candidate_id"], "demand_score": {"score_status": "COMPLETE", "final_score": 0.9, "evaluated_at": EVALUATED}}
        with pytest.raises(REG.RegistryError, match="E_CANDIDATE_NOT_ACCEPTED"):
            REG.attach_score(conn, fake)
    finally:
        conn.close()


def test_oe003g_registry_detects_same_seed_phrase_collision(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    conn = REG.connect(tmp_path / "longtail.db")
    try:
        REG.ingest_guard(conn, guard)
        conflict = copy.deepcopy(guard)
        conflict["guard_receipt_id"] = "LTGUARD-CONFLICT-000000000001"
        conflict["outcomes"] = [copy.deepcopy(guard["outcomes"][0])]
        conflict["outcomes"][0]["candidate"]["candidate_id"] = "LT-CAND-CONFLICT000000000000001"
        conflict["outcomes"][0]["candidate_id"] = "LT-CAND-CONFLICT000000000000001"
        stats = REG.ingest_guard(conn, conflict)
        assert stats["CONFLICT"] == 1
    finally:
        conn.close()


def test_oe003g_ranking_replay_is_deterministic_across_reopen(tmp_path: Path) -> None:
    _, _, _, generation, guard = _foundation(tmp_path)
    db = tmp_path / "longtail.db"; signal_db = tmp_path / "signals.db"
    conn = REG.connect(db)
    REG.ingest_guard(conn, guard)
    for idx, plan in [(0, _plan(82, 500, True)), (1, _plan(55, 8000, True)), (2, _plan(30, 70000, False))]:
        score = PHRASE.synthetic_canary(generation["candidates"][idx], guard["outcomes"][idx], plan, CLEAR_VETO, registry_db=signal_db, evaluated_at=EVALUATED)
        assert REG.attach_score(conn, score) == "ATTACHED"
    first = REG.ranking(conn); conn.close()
    conn2 = REG.connect(db)
    try:
        second = REG.ranking(conn2)
        assert first == second
        assert [x["final_score"] for x in first["ranked"]] == sorted([x["final_score"] for x in first["ranked"]], reverse=True)
    finally:
        conn2.close()

def test_oe003_full_synthetic_canary_fixture_replays_exactly(tmp_path: Path) -> None:
    fixture = json.loads((ENGINE / "fixtures" / "synthetic-canary-v1.json").read_text(encoding="utf-8"))
    contexts = HCTX.retrieve(fixture["human_context_query"])
    assert contexts["results"][0]["context"]["context_id"] == fixture["expected"]["human_context_id"]
    generation = GEN.generate(
        fixture["object_receipt"],
        contexts,
        budget=fixture["budget"],
        expression_level=fixture["expression_level"],
        created_at=fixture["created_at"],
    )
    assert generation["generated_count"] == fixture["expected"]["generated_count"]
    guard = GUARD.apply(generation)
    assert guard["counts"] == fixture["expected"]["guard_counts"]
    conn = REG.connect(tmp_path / "longtail.db")
    try:
        assert REG.ingest_guard(conn, guard)["CONFLICT"] == 0
        actual = []
        for idx, plan in enumerate(fixture["signal_plans"]):
            scored = PHRASE.synthetic_canary(
                generation["candidates"][idx],
                guard["outcomes"][idx],
                plan,
                fixture["hard_veto"],
                registry_db=tmp_path / "signals.db",
                evaluated_at=fixture["evaluated_at"],
            )
            assert REG.attach_score(conn, scored) == "ATTACHED"
            actual.append({
                "candidate_id": scored["candidate_id"],
                "phrase": scored["phrase"],
                "final_score": scored["demand_score"]["final_score"],
                "confidence": scored["demand_score"]["confidence"],
            })
        assert actual == fixture["expected"]["scored"]
        ranking = REG.ranking(conn)
        assert [row["candidate_id"] for row in ranking["ranked"]] == fixture["expected"]["ranking_candidate_ids"]
        assert ranking["ranked_count"] == 3
    finally:
        conn.close()

def test_oe003_canary_runner_is_idempotent(tmp_path: Path) -> None:
    fixture = json.loads((ENGINE / "fixtures" / "synthetic-canary-v1.json").read_text(encoding="utf-8"))
    a = RUNNER.run(copy.deepcopy(fixture), tmp_path / "runner-state")
    b = RUNNER.run(copy.deepcopy(fixture), tmp_path / "runner-state")
    assert a["registry_ingest"] == {"INSERTED": 6, "DUPLICATE": 0, "CONFLICT": 0}
    assert b["registry_ingest"] == {"INSERTED": 0, "DUPLICATE": 6, "CONFLICT": 0}
    assert [x["status"] for x in a["score_attach"]] == ["ATTACHED", "ATTACHED", "ATTACHED"]
    assert [x["status"] for x in b["score_attach"]] == ["DUPLICATE", "DUPLICATE", "DUPLICATE"]
    assert a["ranking"] == b["ranking"]
    assert a["network_collection_performed"] is False
    assert a["object_atlas_written"] is False