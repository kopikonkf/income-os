import importlib.util
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company/company-os/die-h01"
LIB = H01 / "lib/demand_signal_materializer.py"
CONTRACT = H01 / "lib/demand_signal_contract.py"
SCHEMA = json.loads((H01 / "contracts/h01-demand-signal-ranking.v1.schema.json").read_text())

spec = importlib.util.spec_from_file_location("h01_130a_mat", LIB)
M = importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name] = M; spec.loader.exec_module(M)
spec2 = importlib.util.spec_from_file_location("h01_130_contract", CONTRACT)
C = importlib.util.module_from_spec(spec2); assert spec2 and spec2.loader; sys.modules[spec2.name] = C; spec2.loader.exec_module(C)


def q(name, n):
    return {"queue_item_id": f"H01-SVGQ-CAND-{n:07d}", "source": {"canonical_name": name}}


def cap(source, tier, state="ACTIVE"):
    return {"source_id": source, "commercial_intent_tier": tier, "adapter_state": state}


def ev(source, eid, query, *, freshness="FRESH", confidence="MEDIUM", signal="TREND", metrics=None):
    m = dict(metrics or {})
    if confidence is not None:
        m.setdefault("confidence", confidence)
    return {
        "schema": "die.h01.market-signal-evidence.v1",
        "connector_id": source,
        "evidence_id": eid,
        "evidence_sha256": (eid[-1].lower() if eid[-1].lower() in "abcdef0123456789" else "a") * 64,
        "signal_class": signal,
        "freshness": freshness,
        "query": query,
        "retrieved_at": "2026-09-14T00:00:00Z",
        "source_locator": "https://example.invalid/first-party",
        "normalized_metrics": m,
        "policy": {},
    }


def record_for(manifest, name):
    for rec, ex in zip(manifest["records"], manifest["explanations"]):
        if ex["canonical_name"] == name:
            return rec, ex
    raise AssertionError(name)


def test_no_evidence_is_honest_unranked_and_nonblocking():
    manifest = M.materialize([q("chair", 1)], [], {})
    rec, ex = record_for(manifest, "chair")
    assert rec["signal_state"] == "NO_EVIDENCE"
    assert rec["rank_state"] == "UNRANKED"
    assert rec["rank_score"] is None
    assert rec["confidence"] == "NONE"
    assert rec["evidence_refs"] == []
    assert all(value is False for value in rec["authority"].values())
    assert all(value == "NONE" for value in rec["effects"].values())
    assert C.validate_record(rec) == []
    jsonschema.Draft202012Validator(SCHEMA).validate(rec)
    assert ex["contributions"] == []


def test_exact_marketplace_term_match_ranks_real_noun_without_using_presentation_position():
    source = "market_v1"
    evidence = ev(
        source, "H01-SIG-00000000000000000000000A", "generic market trending searches",
        metrics={
            "confidence": "MEDIUM",
            "rank_semantics": "UNRANKED_PRESENTATION_ORDER",
            "terms": [
                {"term": "Food", "presentation_position": 13},
                {"term": "Travel", "presentation_position": 22},
            ],
            "search_volume": None,
            "visitor_query_count": None,
        },
    )
    manifest = M.materialize(
        [q("food", 1), q("travel", 2), q("chair", 3)],
        [evidence],
        {source: cap(source, "MARKETPLACE_POPULAR_QUERY")},
    )
    food, food_ex = record_for(manifest, "food")
    travel, travel_ex = record_for(manifest, "travel")
    chair, _ = record_for(manifest, "chair")
    assert food["rank_state"] == travel["rank_state"] == "RANKED"
    assert food["rank_score"] == travel["rank_score"]
    assert food["rank_score"] > 0
    assert food_ex["contributions"][0]["match_type"] == "TERM_EXACT"
    assert travel_ex["contributions"][0]["match_type"] == "TERM_EXACT"
    assert chair["rank_state"] == "UNRANKED"
    assert manifest["policy"]["presentation_order_inferred_as_volume_or_rank"] is False


def test_source_tier_hierarchy_is_strict_for_equivalent_evidence():
    tiers = [
        "DIRECT_MARKETPLACE_QUERY",
        "MARKETPLACE_POPULAR_QUERY",
        "MARKETPLACE_POPULARITY_PROXY",
        "MACRO_SEARCH",
        "ATTENTION_PROXY",
        "LEGACY_PRIOR",
    ]
    scores = []
    for idx, tier in enumerate(tiers):
        source = f"s{idx}"
        row = ev(source, f"H01-SIG-{idx:024X}", "cat", confidence="MEDIUM")
        manifest = M.materialize([q("cat", 1)], [row], {source: cap(source, tier)})
        rec, _ = record_for(manifest, "cat")
        scores.append(rec["rank_score"])
    assert all(a > b for a, b in zip(scores, scores[1:]))


def test_query_specific_wikimedia_attention_is_ranked_but_lower_confidence():
    row = ev(
        "wiki", "H01-SIG-00000000000000000000000B", "Cat", confidence=None,
        metrics={"pageviews_total": 80887, "pageviews_mean": 11555.2, "period_count": 7},
    )
    manifest = M.materialize([q("cat", 1)], [row], {"wiki": cap("wiki", "ATTENTION_PROXY")})
    rec, ex = record_for(manifest, "cat")
    assert rec["rank_state"] == "RANKED"
    assert 0 < rec["rank_score"] < 0.3
    assert rec["confidence"] == "LOW"
    assert ex["contributions"][0]["match_type"] == "QUERY_EXACT"


def test_multiple_independent_fresh_sources_corrobate_without_exceeding_one():
    rows = [
        ev("market", "H01-SIG-00000000000000000000000C", "food", confidence="MEDIUM"),
        ev("macro", "H01-SIG-00000000000000000000000D", "food", confidence="MEDIUM"),
    ]
    caps = {"market": cap("market", "MARKETPLACE_POPULAR_QUERY"), "macro": cap("macro", "MACRO_SEARCH")}
    together = M.materialize([q("food", 1)], rows, caps)
    market_only = M.materialize([q("food", 1)], rows[:1], caps)
    a, _ = record_for(together, "food"); b, _ = record_for(market_only, "food")
    assert b["rank_score"] < a["rank_score"] <= 1
    assert a["confidence"] == "MEDIUM"
    assert len(a["evidence_refs"]) == 2


def test_stale_only_evidence_is_preserved_but_not_ranked():
    row = ev("market", "H01-SIG-00000000000000000000000E", "food", freshness="STALE")
    manifest = M.materialize([q("food", 1)], [row], {"market": cap("market", "MARKETPLACE_POPULAR_QUERY")})
    rec, _ = record_for(manifest, "food")
    assert rec["signal_state"] == "STALE"
    assert rec["rank_state"] == "UNRANKED"
    assert rec["rank_score"] is None
    assert len(rec["evidence_refs"]) == 1
    assert C.validate_record(rec) == []


def test_disabled_connector_evidence_is_ignored():
    row = ev("blocked", "H01-SIG-00000000000000000000000F", "cat")
    manifest = M.materialize([q("cat", 1)], [row], {"blocked": cap("blocked", "DIRECT_MARKETPLACE_QUERY", state="DISABLED")})
    rec, _ = record_for(manifest, "cat")
    assert rec["signal_state"] == "NO_EVIDENCE"
    assert rec["evidence_refs"] == []


def test_no_fuzzy_or_plural_guessing_in_v1():
    row = ev("market", "H01-SIG-000000000000000000000010", "generic", metrics={"terms": [{"term": "Animals"}]})
    manifest = M.materialize([q("animal", 1), q("animals", 2)], [row], {"market": cap("market", "MARKETPLACE_POPULAR_QUERY")})
    singular, _ = record_for(manifest, "animal")
    plural, _ = record_for(manifest, "animals")
    assert singular["rank_state"] == "UNRANKED"
    assert plural["rank_state"] == "RANKED"
    assert manifest["policy"]["matching"] == "EXACT_NORMALIZED_TEXT_ONLY"


def test_materialization_is_deterministic_for_same_inputs():
    rows = [ev("market", "H01-SIG-000000000000000000000011", "food")]
    caps = {"market": cap("market", "MARKETPLACE_POPULAR_QUERY")}
    queue = [q("food", 1), q("chair", 2)]
    first = M.materialize(queue, rows, caps)
    second = M.materialize(queue, rows, caps)
    assert first == second
    assert first["materialization_id"] == second["materialization_id"]


def test_discoveries_are_empty_until_a_separate_evidence_grounded_context_stage_exists():
    row = ev("market", "H01-SIG-000000000000000000000012", "food")
    manifest = M.materialize([q("food", 1)], [row], {"market": cap("market", "MARKETPLACE_POPULAR_QUERY")})
    rec, _ = record_for(manifest, "food")
    assert rec["discoveries"] == {"buyers": [], "use_cases": [], "family_hypotheses": []}
    assert manifest["policy"]["buyer_use_case_family_discovery_authorized"] is False


def test_evidence_semantics_can_downgrade_broad_source_capability_but_never_promote_it():
    adobe = ev(
        "adobe", "H01-SIG-000000000000000000000013", "texture", confidence="MEDIUM_HIGH",
        metrics={"confidence": "MEDIUM_HIGH", "evidence_class": "MACRO_TREND", "macro_trend": True},
    )
    direct_claim_on_attention_source = ev(
        "attention", "H01-SIG-000000000000000000000014", "cat", confidence="HIGH",
        metrics={"confidence": "HIGH", "direct_customer_search_telemetry": True},
    )
    manifest = M.materialize(
        [q("texture", 1), q("cat", 2)],
        [adobe, direct_claim_on_attention_source],
        {
            "adobe": cap("adobe", "MARKETPLACE_POPULARITY_PROXY"),
            "attention": cap("attention", "ATTENTION_PROXY"),
        },
    )
    _, adobe_ex = record_for(manifest, "texture")
    _, attention_ex = record_for(manifest, "cat")
    assert adobe_ex["contributions"][0]["tier"] == "MACRO_SEARCH"
    assert attention_ex["contributions"][0]["tier"] == "ATTENTION_PROXY"


def test_adapter_pending_connector_is_ignored_even_if_diagnostic_evidence_file_exists():
    row = ev("pending", "H01-SIG-000000000000000000000015", "cat", confidence="HIGH")
    manifest = M.materialize(
        [q("cat", 1)],
        [row],
        {"pending": cap("pending", "DIRECT_MARKETPLACE_QUERY", state="ADAPTER_PENDING")},
    )
    rec, _ = record_for(manifest, "cat")
    assert rec["signal_state"] == "NO_EVIDENCE"
    assert rec["rank_score"] is None
