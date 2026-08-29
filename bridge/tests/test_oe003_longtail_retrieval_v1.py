from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "company" / "division" / "division001" / "engines" / "longtail"
ONTOLOGY = ENGINE / "MODIFIER_ONTOLOGY_V1.json"
PHRASE_SCHEMA = ENGINE / "die.division001.longtail-candidate.v1.schema.json"
HCTX_REGISTRY = ENGINE / "HUMAN_CONTEXT_REGISTRY_V1.json"
HCTX_SCHEMA = ENGINE / "die.human-atlas.context-registry.v1.schema.json"
HUMAN_CANON = ROOT / "company" / "atlas" / "human-centric" / "HUMAN_CENTRIC_ATLAS_CANON.md"
CROSSJOIN = ROOT / "company" / "atlas" / "human-centric" / "CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md"


def _load(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OBJ = _load("oe003_object_retrieval_test", ENGINE / "retrieve_object_seeds.py")
HCTX = _load("oe003_human_retrieval_test", ENGINE / "retrieve_human_contexts.py")


def _make_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE seeds (
        id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL UNIQUE, aliases TEXT,
        object_class TEXT, existence_type TEXT, category_path TEXT,
        visuality_score REAL, demand_score REAL, risk_score REAL,
        status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    rows = [
        ("OBJ-CABLE-001","cable organizer",json.dumps(["cable clip organizer"]),"office_accessory","real","office/organization",0.91,0.88,0.02,"approved","2026-08-01T00:00:00Z","2026-08-29T00:00:00Z"),
        ("OBJ-PILL-001","pill organizer",json.dumps(["medicine organizer"]),"health_accessory","real","health/organization",0.86,0.71,0.04,"approved","2026-08-01T00:00:00Z","2026-08-29T00:00:00Z"),
        ("OBJ-TROPHY-001","trophy",None,"award","real","education/award",0.94,0.79,0.01,"approved","2026-08-01T00:00:00Z","2026-08-29T00:00:00Z"),
        ("OBJ-REVIEW-001","unreviewed gadget",None,"gadget","real","misc",0.8,0.99,0.0,"review","2026-08-01T00:00:00Z","2026-08-29T00:00:00Z"),
    ]
    conn.executemany("INSERT INTO seeds VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close(); return path


def test_oe003a_modifier_ontology_is_bounded_typed_and_expression_separate() -> None:
    o=json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    ids={x["id"] for x in o["modifier_types"]}
    assert ids == {"function","buyer","audience","industry","use_case","problem","place","time","material","state","style","demographic","commercial_intent","product_expression"}
    assert o["max_modifiers_per_phrase"] == 4
    assert o["max_contexts_per_retrieval"] == 25
    assert o["max_objects_per_retrieval"] == 50
    assert [x["id"] for x in o["product_expression_levels"]] == ["L0","L1","L2","L3","L4","L5","L6"]
    assert "PARENT_SCORE_INHERITANCE" in o["forbidden_inference"]
    assert "EXHAUSTIVE_10D_CARTESIAN" in o["forbidden_inference"]


def test_oe003a_phrase_schema_requires_phrase_level_signals_and_forbids_parent_score_inheritance() -> None:
    schema=json.loads(PHRASE_SCHEMA.read_text(encoding="utf-8"))
    candidate={
      "schema_version":"die.division001.longtail-candidate.v1","candidate_id":"LT-CAND-CABLE-REMOTE-001","phrase":"desk cable organizer for remote work setup","locale":"en-US",
      "parent_seed":{"seed_id":"OBJ-CABLE-001","canonical_name":"cable organizer","object_class":"office_accessory","category_path":"office/organization","source_db_sha256":"1"*64,"retrieval_receipt_id":"OBJRET-ABC"},
      "human_context":{"context_id":"HCTX-REMOTE-WORK-CABLE-001","registry_sha256":"2"*64,"retrieval_receipt_id":"HCTXRET-ABC"},
      "modifiers":[{"type":"use_case","value":"remote work setup","source":"HUMAN_ATLAS"},{"type":"place","value":"home office","source":"HUMAN_ATLAS"}],
      "product_expression":{"level":"L0","name":"primitive_static_asset"},
      "generation":{"generator_id":"fixture","generator_version":"v1","bounded_budget":10,"legacy_expansion_dictionary_used_as_core":False},
      "evidence_state":"REQUIRES_PHRASE_LEVEL_OE001_OE002","parent_demand":{"parent_score_ref":"fixture://parent-score","inherited_by_child":False},"created_at":"2026-08-29T12:00:00Z"
    }
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(candidate)
    bad=json.loads(json.dumps(candidate)); bad["parent_demand"]["inherited_by_child"]=True
    with pytest.raises(jsonschema.ValidationError): jsonschema.Draft202012Validator(schema).validate(bad)


def test_oe003b_object_retrieval_is_approved_only_bounded_and_omits_legacy_demand_score(tmp_path: Path) -> None:
    db=_make_db(tmp_path/"object.db")
    result=OBJ.retrieve(db,{"category_prefix":"office","limit":10})
    assert result["policy"] == {"approved_only":True,"max_results":50,"arbitrary_sql":False,"dataset_finality_required":False}
    assert [x["seed_id"] for x in result["results"]] == ["OBJ-CABLE-001"]
    assert all(x["status"] == "approved" for x in result["results"])
    assert all("demand_score" not in x for x in result["results"])


def test_oe003b_object_retrieval_supports_id_name_class_and_is_deterministic(tmp_path: Path) -> None:
    db=_make_db(tmp_path/"object.db")
    a=OBJ.retrieve(db,{"seed_ids":["OBJ-PILL-001"],"limit":5})
    b=OBJ.retrieve(db,{"canonical_names":["pill organizer"],"limit":5},source_db_sha256=a["source_db"]["sha256"])
    c=OBJ.retrieve(db,{"object_class":"health_accessory","limit":5},source_db_sha256=a["source_db"]["sha256"])
    assert [x["seed_id"] for x in a["results"]] == ["OBJ-PILL-001"]
    assert [x["seed_id"] for x in b["results"]] == ["OBJ-PILL-001"]
    assert [x["seed_id"] for x in c["results"]] == ["OBJ-PILL-001"]
    assert OBJ.retrieve(db,{"seed_ids":["OBJ-PILL-001"],"limit":5},source_db_sha256=a["source_db"]["sha256"]) == a


def test_oe003b_object_retrieval_fails_closed_on_unbounded_or_arbitrary_query(tmp_path: Path) -> None:
    db=_make_db(tmp_path/"object.db")
    with pytest.raises(OBJ.RetrievalError,match="E_OBJECT_QUERY_UNBOUNDED"): OBJ.retrieve(db,{"limit":10})
    with pytest.raises(OBJ.RetrievalError,match="E_OBJECT_QUERY_KEY"): OBJ.retrieve(db,{"sql":"SELECT * FROM seeds","limit":10})
    with pytest.raises(OBJ.RetrievalError,match="E_OBJECT_LIMIT"): OBJ.retrieve(db,{"object_class":"award","limit":51})


def test_oe003b_readonly_connection_is_query_only(tmp_path: Path) -> None:
    db=_make_db(tmp_path/"object.db")
    conn=OBJ.connect_readonly(db)
    try:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError): conn.execute("UPDATE seeds SET status='approved'")
    finally: conn.close()


def test_oe003c_registry_is_valid_hypothesis_only_and_canon_hashes_are_current() -> None:
    registry=json.loads(HCTX_REGISTRY.read_text(encoding="utf-8")); schema=json.loads(HCTX_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(registry)
    assert len(registry["contexts"]) == 6
    assert {x["label"] for x in registry["contexts"]} == {"HYPOTHESIS"}
    refs={x["path"]:x["sha256"] for x in registry["source_canon"]}
    assert refs["company/atlas/human-centric/HUMAN_CENTRIC_ATLAS_CANON.md"] == HCTX._sha(HUMAN_CANON)
    assert refs["company/atlas/human-centric/CROSSJOIN_OBJECT_ATLAS_COMPLEMENT_V1.md"] == HCTX._sha(CROSSJOIN)


def test_oe003c_supply_first_object_retrieval_returns_bounded_compatible_context() -> None:
    result=HCTX.retrieve({"object_name":"cable organizer","limit":5})
    assert result["policy"]["exhaustive_cartesian"] is False
    assert result["policy"]["market_evidence"] is False
    assert result["policy"]["result_label"] == "HYPOTHESIS_CONTEXT_COMPATIBILITY"
    assert result["results"][0]["context"]["context_id"] == "HCTX-REMOTE-WORK-CABLE-001"
    assert result["results"][0]["compatibility_score"] == 1.0


def test_oe003c_multi_anchor_query_narrows_context_deterministically() -> None:
    query={"object_name":"pill organizer","industry":"health education","problem":"medication routine","limit":5}
    a=HCTX.retrieve(query); b=HCTX.retrieve(query)
    assert a == b
    assert a["result_count"] >= 1
    assert a["results"][0]["context"]["context_id"] == "HCTX-SENIOR-MEDICATION-001"


def test_oe003c_unbounded_and_over_limit_queries_fail_closed() -> None:
    with pytest.raises(HCTX.ContextRetrievalError,match="E_HCTX_QUERY_UNBOUNDED"): HCTX.retrieve({"limit":10})
    with pytest.raises(HCTX.ContextRetrievalError,match="E_HCTX_LIMIT"): HCTX.retrieve({"object_name":"trophy","limit":26})
    with pytest.raises(HCTX.ContextRetrievalError,match="E_HCTX_QUERY_KEY"): HCTX.retrieve({"object_name":"trophy","all_10d":True})


def test_oe003c_registry_context_does_not_claim_observed_market_demand() -> None:
    result=HCTX.retrieve({"object_name":"soil moisture meter","limit":5})
    top=result["results"][0]["context"]
    assert top["context_id"] == "HCTX-INDOOR-HERB-GARDEN-001"
    assert top["label"] == "HYPOTHESIS"
    assert result["policy"]["market_evidence"] is False


def test_crossjoin_examples_are_represented_as_retrievable_context_not_materialized_cartesian_space() -> None:
    for obj, expected in [("cable organizer","HCTX-REMOTE-WORK-CABLE-001"),("pill organizer","HCTX-SENIOR-MEDICATION-001"),("soil moisture meter","HCTX-INDOOR-HERB-GARDEN-001")]:
        out=HCTX.retrieve({"object_name":obj,"limit":3})
        assert out["results"][0]["context"]["context_id"] == expected
        assert out["result_count"] <= 3