import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company/company-os/die-h01"
sys.path.insert(0, str(H01 / "lib"))
sys.path.insert(0, str(H01 / "engineering"))

spec = importlib.util.spec_from_file_location("h01_133a_cycle", H01 / "lib/daily_demand_cycle.py")
M = importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[spec.name] = M; spec.loader.exec_module(M)
from h01_daily_selector import build_manifest


def queue_rows(count=120):
    rows=[]
    names=["food","travel","cat"]+[f"noun-{i}" for i in range(count-3)]
    for i,name in enumerate(names[:count],1):
        rows.append({"queue_item_id":f"H01-SVGQ-CAND-{i:07d}","queue_position":i,"dispatch_eligible":True,"idempotency_key":f"k{i}","source":{"canonical_name":name,"id":f"CAND-{i:07d}","source_tier":"pass","suitability":"test"}})
    return rows


def cap(source,tier,state="ACTIVE"):
    return {"source_id":source,"commercial_intent_tier":tier,"adapter_state":state}


def evidence(source,eid,query,metrics,freshness="FRESH"):
    return {"schema":"die.h01.market-signal-evidence.v1","connector_id":source,"evidence_id":eid,"evidence_sha256":"a"*64,"freshness":freshness,"normalized_metrics":metrics,"policy":{},"query":query,"retrieved_at":"2026-09-14T00:00:00Z","signal_class":"TREND","source_locator":"https://example.invalid/first-party"}


def test_complete_utc_window_uses_seven_full_days_before_day_key():
    assert M.complete_utc_window("2026-09-14") == ("2026090700","2026091300")


def test_refresh_exception_is_fail_soft():
    result=M._safe_refresh("broken",lambda: (_ for _ in ()).throw(RuntimeError("outage")))
    assert result["status"]=="DEGRADED_REFRESH_EXCEPTION"
    assert result["source"]=="broken"
    assert result["evidence_ids"]==[]


def test_no_evidence_cycle_is_frozen_with_source_order_fallback():
    cycle=M.build_cycle(queue_rows=queue_rows(120),produced=set(),evidence_rows=[],capabilities={},day_key="2026-09-14",selector_builder=build_manifest,limit=100,providers=("gemini","qwen"))
    assert cycle["status"]=="FROZEN"
    assert cycle["materialization"]["ranked_count"]==0
    assert cycle["selector"]["selection"]["ranked_selected"]==0
    assert cycle["selector"]["selection"]["fallback_selected"]==100
    assert [x["canonical_name"] for x in cycle["selector"]["items"][:3]]==["food","travel","cat"]
    assert cycle["policy"]["source_refresh_failure_blocks_cycle"] is False
    assert all(v is False for v in cycle["authority"].values())


def test_realistic_market_evidence_produces_ranked_selected_without_changing_authority():
    ev=evidence("market","H01-SIG-000000000000000000000001","market trending",{"confidence":"MEDIUM","evidence_class":"MARKETPLACE_TRENDING_SEARCH_LABELS","terms":[{"term":"Food"},{"term":"Travel"}]})
    cycle=M.build_cycle(queue_rows=queue_rows(120),produced=set(),evidence_rows=[ev],capabilities={"market":cap("market","MARKETPLACE_POPULAR_QUERY")},day_key="2026-09-14",selector_builder=build_manifest,limit=100,providers=("gemini","qwen"))
    assert cycle["materialization"]["ranked_count"]==2
    assert cycle["selector"]["selection"]["ranked_selected"]==2
    assert cycle["selector"]["selection"]["fallback_selected"]==98
    assert [x["canonical_name"] for x in cycle["selector"]["items"][:2]]==["food","travel"]
    assert all(x["selection_reason"]=="EVIDENCE_RANKED" for x in cycle["selector"]["items"][:2])
    assert cycle["selector"]["authority"]=={"production_dispatch_authorized":False,"submission_authorized":False,"publication_authorized":False,"spend_authorized":False}


def test_produced_items_remain_excluded_and_do_not_mutate_generation_truth():
    rows=queue_rows(120); produced={rows[0]["queue_item_id"]}
    ev=evidence("market","H01-SIG-000000000000000000000002","food",{"confidence":"MEDIUM"})
    cycle=M.build_cycle(queue_rows=rows,produced=produced,evidence_rows=[ev],capabilities={"market":cap("market","MARKETPLACE_POPULAR_QUERY")},day_key="2026-09-14",selector_builder=build_manifest,limit=100,providers=("gemini",))
    assert cycle["selector"]["source_queue"]["produced_generation_complete_count"]==1
    assert rows[0]["queue_item_id"] not in {x["queue_item_id"] for x in cycle["selector"]["items"]}
    assert cycle["policy"]["generation_validity_mutated"] is False


def test_cycle_identity_is_deterministic_for_identical_inputs():
    kwargs=dict(queue_rows=queue_rows(120),produced=set(),evidence_rows=[],capabilities={},day_key="2026-09-14",selector_builder=build_manifest,limit=100,providers=("gemini",))
    a=M.build_cycle(**kwargs); b=M.build_cycle(**kwargs)
    assert a==b
    assert a["cycle_id"]==b["cycle_id"]
    assert a["selector"]["selection_id"]==b["selector"]["selection_id"]


def test_persist_cycle_writes_immutable_cycle_and_separate_refresh_attempt_receipt():
    cycle=M.build_cycle(queue_rows=queue_rows(120),produced=set(),evidence_rows=[],capabilities={},day_key="2026-09-14",selector_builder=build_manifest,limit=100,providers=("gemini",))
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); queue=td/"queue.jsonl"
        queue.write_text("".join(json.dumps(x)+"\n" for x in queue_rows(120)),encoding="utf-8")
        refresh=[{"source":"123rf_trending_search_v1","status":"DEGRADED_REFRESH_EXCEPTION","acquisition_id":None,"evidence_ids":[],"error":{"type":"RuntimeError","message":"outage"}}]
        result=M.persist_cycle(cycle,output_root=td/"daily",queue_path=queue,effective_evidence_rows=[],refresh_results=refresh)
        receipt=Path(result["paths"]["cycle_receipt"]); attempt=Path(result["paths"]["refresh_attempt_receipt"])
        assert receipt.is_file() and attempt.is_file()
        rr=json.loads(receipt.read_text()); ar=json.loads(attempt.read_text())
        assert rr["status"]=="PASS"
        assert rr["selector"]["fallback_selected"]==100
        assert ar["status"]=="DEGRADED"
        assert ar["source_failure_blocks_cycle"] is False
        second=M.persist_cycle(cycle,output_root=td/"daily",queue_path=queue,effective_evidence_rows=[],refresh_results=refresh)
        assert second["paths"]["cycle_receipt"]==result["paths"]["cycle_receipt"]


def test_refresh_success_summary_preserves_acquisition_and_evidence_ids():
    result=M._safe_refresh("source",lambda:{"status":"CACHE_HIT_FRESH","acquisition_id":"A1","evidence":[{"evidence_id":"E1"}]})
    assert result=={"source":"source","status":"CACHE_HIT_FRESH","acquisition_id":"A1","evidence_ids":["E1"],"error":None}
