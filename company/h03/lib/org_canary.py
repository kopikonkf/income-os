from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import demand_wtp
import h03_factory
import knowledge_synthesis
import product_packager
import product_planner
import problem_discovery
import research_executor
import research_plan
import semantic_producer
import source_ingestion
import worth_making

CANARY_SCHEMA = "die.h03.organism-canary.v1"
FIXTURE_EXECUTION_MODE = "NONLIVE_ROLE_FIXTURE"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _find_evidence(source_packet: dict[str, Any], *phrases: str) -> str:
    lowered = tuple(p.lower() for p in phrases)
    for unit in source_packet.get("evidence_units") or []:
        text = str(unit.get("text") or "").lower()
        if all(p in text for p in lowered):
            return unit["evidence_id"]
    raise ValueError("CANARY_EVIDENCE_NOT_FOUND:" + "+".join(phrases))


def _find_any_evidence(source_packet: dict[str, Any], phrase_sets: list[tuple[str, ...]]) -> str:
    for phrases in phrase_sets:
        try:
            return _find_evidence(source_packet, *phrases)
        except ValueError:
            pass
    raise ValueError("CANARY_EVIDENCE_NOT_FOUND_ANY:" + repr(phrase_sets))


def _fixture_research_registry() -> dict[str, Any]:
    return {
        "schema_version":"die.h03.provider-worker-registry.v1",
        "holding_id":"H03",
        "providers":[
            {
                "provider_id":"fixture-market-a",
                "model_route":"fixture://market-a",
                "roles":["MARKET_RESEARCHER"],
                "capabilities":["web_research","text_generation"],
                "transport_families":["OPENAI_COMPATIBLE"],
                "priority":100,
            },
            {
                "provider_id":"fixture-knowledge-a",
                "model_route":"fixture://knowledge-a",
                "roles":["KNOWLEDGE_RESEARCHER"],
                "capabilities":["web_research","text_generation"],
                "transport_families":["OPENAI_COMPATIBLE"],
                "priority":95,
            },
            {
                "provider_id":"fixture-market-b",
                "model_route":"fixture://market-b",
                "roles":["MARKET_RESEARCHER"],
                "capabilities":["web_research","text_generation"],
                "transport_families":["OPENAI_COMPATIBLE"],
                "priority":90,
            },
        ],
    }


def _fixture_research_pool() -> dict[str, Any]:
    return {
        "schema_version":"die.h03.browser-profile-pool.v1",
        "holding_id":"H03",
        "pool_id":"canary-fixture-research-pool",
        "purpose":"KNOWLEDGE_WORKFORCE",
        "session_material_policy":"HOST_LOCAL_NOT_PRODUCT_TRUTH",
        "shards":[
            {
                "shard_id":"fixture-research-shard",
                "state":"READY",
                "providers":[
                    {"provider_id":"fixture-market-a","state":"READY","available_slots":1,"transport_family":"OPENAI_COMPATIBLE"},
                    {"provider_id":"fixture-knowledge-a","state":"READY","available_slots":1,"transport_family":"OPENAI_COMPATIBLE"},
                    {"provider_id":"fixture-market-b","state":"READY","available_slots":1,"transport_family":"OPENAI_COMPATIBLE"},
                ],
            }
        ],
    }


def _fixture_producer_registry() -> dict[str, Any]:
    return {
        "schema_version":"die.h03.provider-worker-registry.v1",
        "holding_id":"H03",
        "providers":[
            {
                "provider_id":"fixture-producer-a",
                "model_route":"fixture://producer-a",
                "roles":["PRODUCER"],
                "capabilities":["text_generation"],
                "transport_families":["OPENAI_COMPATIBLE"],
                "priority":100,
            },
            {
                "provider_id":"fixture-producer-b",
                "model_route":"fixture://producer-b",
                "roles":["PRODUCER"],
                "capabilities":["text_generation"],
                "transport_families":["OPENAI_COMPATIBLE"],
                "priority":90,
            },
        ],
    }


def _fixture_producer_pool() -> dict[str, Any]:
    return {
        "schema_version":"die.h03.browser-profile-pool.v1",
        "holding_id":"H03",
        "pool_id":"canary-fixture-producer-pool",
        "purpose":"KNOWLEDGE_WORKFORCE",
        "session_material_policy":"HOST_LOCAL_NOT_PRODUCT_TRUTH",
        "shards":[
            {
                "shard_id":"fixture-producer-shard",
                "state":"READY",
                "providers":[
                    {"provider_id":"fixture-producer-a","state":"READY","available_slots":3,"transport_family":"OPENAI_COMPATIBLE"},
                    {"provider_id":"fixture-producer-b","state":"READY","available_slots":2,"transport_family":"OPENAI_COMPATIBLE"},
                ],
            }
        ],
    }


def _govern_snapshot(snapshot: dict[str, Any], *, basis: str) -> dict[str, Any]:
    reviewed = copy.deepcopy(snapshot)
    reviewed["rights_policy"] = {
        "state":"REVIEWED_REFERENCE_ONLY",
        "basis":basis,
        "verbatim_reuse_allowed":False,
    }
    return source_ingestion.approve_for_knowledge(
        reviewed,
        reviewer_kind="ARCHITECT",
        reviewer_id="chatgpt-architect",
        decision_basis="H03-ORG-001 bounded public-reference review; paraphrase/reference use only",
    )


def run_canary(*, evidence_root: Path) -> dict[str, Any]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    source_root = evidence_root / "sources"
    required_sources = {
        "FTC": source_root / "ftc-people-search-sites.html",
        "INCOGNI": source_root / "incogni-pricing.html",
        "DELETEME": source_root / "deleteme-home.html",
    }
    for path in required_sources.values():
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"CANARY_SOURCE_MISSING:{path}")

    stage_dir = evidence_root / "stages"
    package_root = evidence_root / "package"

    # 1. Problem seed: a real, bounded consumer privacy job.
    problem_seed = {
        "schema_version":"die.h03.human-problem-seed.v1",
        "problem_seed_id":"H03-PS-PEOPLESEARCH-DIY-001",
        "holding_id":"H03",
        "persona":{"actor":"privacy-conscious consumer","qualifier":"wants to reduce exposed contact and identity information on people-search sites without delegating the whole job to a paid service"},
        "context":"personal information can appear across multiple people-search and data-broker sites",
        "trigger":"the consumer discovers searchable personal information and wants a bounded removal workflow",
        "job_to_be_done":"find exposed records, submit opt-out requests, repeat across relevant people-search sites, and periodically recheck for reappearance",
        "pain":{
            "statement":"manual opt-outs are fragmented across many sites and can be time-consuming to repeat and monitor",
            "severity_state":"OBSERVED",
            "frequency_state":"OBSERVED",
            "urgency_state":"UNKNOWN",
        },
        "desired_outcome":"a concise repeatable DIY sequence for finding, opting out, and rechecking people-search listings while understanding the limits of removal",
        "commercial_signals":{
            "demand":{"state":"UNKNOWN","evidence_refs":[]},
            "willingness_to_pay":{"state":"UNKNOWN","evidence_refs":[]},
        },
        "source_refs":[],
        "truth_status":"CANDIDATE",
    }
    import problem_seed as problem_seed_module
    problem_seed_module.validate_problem_seed(problem_seed)
    _write_json(stage_dir / "01-problem-seed.json", problem_seed)

    # 2. Seed curation uses the normal SEED_CURATOR Work Card contract.
    seed_curator_card = problem_discovery.build_seed_curator_work_card(
        batch_id="ORG001-001",
        signal_artifact_ref="artifact://canary/problem-signal/people-search-diy",
    )
    seed_batch = problem_discovery.build_problem_seed_batch(
        batch_id="ORG001-001",
        source_signal_refs=["artifact://canary/problem-signal/people-search-diy"],
        candidates=[problem_seed],
    )
    problem_seed = seed_batch["candidates"][0]
    _write_json(stage_dir / "02-seed-curator-work-card.json", seed_curator_card)
    _write_json(stage_dir / "03-problem-seed-batch.json", seed_batch)

    # 3. Cheap opportunity evidence precedes the expensive research fan-out.
    opportunity_sources = {}
    opportunity_specs = [
        ("ORG001-INCOGNI-PRICING", "https://incogni.com/pricing", required_sources["INCOGNI"]),
        ("ORG001-FTC-PEOPLESEARCH", "https://consumer.ftc.gov/articles/what-know-about-people-search-sites-sell-your-information", required_sources["FTC"]),
        ("ORG001-DELETEME-HOME", "https://joindeleteme.com/", required_sources["DELETEME"]),
    ]
    for source_id, source_uri, source_path in opportunity_specs:
        snap = source_ingestion.ingest_external_bytes(
            source_id=source_id,
            source_uri=source_uri,
            raw_bytes=source_path.read_bytes(),
            media_type="text/html",
            acquisition_method="HTTP_CLIENT",
            rights_state="REVIEWED_REFERENCE_ONLY",
            rights_basis="Public webpage retained only as reference evidence for bounded internal opportunity validation",
            verbatim_reuse_allowed=False,
        )
        opportunity_sources[source_id] = source_ingestion.approve_for_knowledge(
            snap,
            reviewer_kind="ARCHITECT",
            reviewer_id="chatgpt-architect",
            decision_basis="H03-ORG-001 bounded opportunity evidence review; reference/paraphrase only",
        )
    _write_json(stage_dir / "04-opportunity-source-packets.json", list(opportunity_sources.values()))

    op_ftc = opportunity_sources["ORG001-FTC-PEOPLESEARCH"]
    op_incogni = opportunity_sources["ORG001-INCOGNI-PRICING"]
    op_deleteme = opportunity_sources["ORG001-DELETEME-HOME"]
    ftc_time_ref = _find_any_evidence(op_ftc, [
        ("time-consuming", "repeat"), ("one by one", "time-consuming"), ("repeat steps",),
    ])
    ftc_free_or_paid_ref = _find_any_evidence(op_ftc, [
        ("do it on your own", "pay a service"), ("pay a service",),
    ])
    ftc_steps_ref = _find_any_evidence(op_ftc, [
        ("search for your name", "opt out"), ("look for a link", "opt out"),
    ])
    ftc_recheck_ref = _find_any_evidence(op_ftc, [("periodically check",), ("re-appear",)])
    ftc_limits_ref = _find_any_evidence(op_ftc, [("public records",), ("doesn", "delete your information from public records")])
    incogni_price_ref = _find_any_evidence(op_incogni, [
        ("$7.99", "month"), ("95.88", "annually"), ("standard", "monthly"),
    ])
    deleteme_usage_ref = _find_any_evidence(op_deleteme, [
        ("141m", "successful opt-out removals"), ("100 million", "listings removed"), ("customers say",),
    ])

    # 4. Demand/WTP before Worth-Making: observed paid substitutes and usage proxies, never invented user spend.
    demand_packet = {
        "schema_version":"die.h03.demand-wtp-evidence.v1",
        "packet_id":"H03-DMD-ORG001-001",
        "holding_id":"H03",
        "problem_seed_id":problem_seed["problem_seed_id"],
        "pain_observation":{"severity":"MEDIUM","frequency":"MEDIUM","urgency":"UNKNOWN"},
        "buyer_intent_state":"MEDIUM",
        "evidence":[
            {"evidence_id":"DMD-PAID-SUBSTITUTE","signal_type":"PAID_SUBSTITUTE","evidence_refs":[incogni_price_ref,ftc_free_or_paid_ref],"money":None},
            {"evidence_id":"DMD-USAGE-PROXY","signal_type":"MARKETPLACE_SALE_PROXY","evidence_refs":[deleteme_usage_ref],"money":None},
            {"evidence_id":"DMD-REPEATED-PAIN","signal_type":"REPEATED_PAIN","evidence_refs":[ftc_time_ref,ftc_recheck_ref],"money":None},
        ],
        "wtp_assessment":"MEDIUM",
        "truth_status":"VALIDATED",
    }
    demand_wtp.validate_demand_packet(demand_packet)
    _write_json(stage_dir / "05-demand-wtp.json", demand_packet)

    # 5. Worth-Making is the expensive-research gate.
    worth = worth_making.evaluate_worth_making(
        decision_id="H03-WM-ORG001-001",
        seed=problem_seed,
        demand_packet=demand_packet,
        productability={"state":"HIGH","evidence_refs":[ftc_steps_ref,ftc_recheck_ref,ftc_limits_ref]},
    )
    if worth["decision"] != "MAKE":
        raise AssertionError(f"CANARY_WORTH_MAKING_NOT_MAKE:{worth}")
    _write_json(stage_dir / "06-worth-making.json", worth)

    # 6. Only after MAKE do we authorize the bounded deep-research plan.
    plan = {
        "schema_version":"die.h03.research-plan.v1",
        "research_plan_id":"H03-RPLAN-ORG001-001",
        "holding_id":"H03",
        "problem_seed_id":problem_seed["problem_seed_id"],
        "worth_making_decision_id":"H03-WM-ORG001-001",
        "questions":[
            {
                "question_id":"Q-MARKET-1",
                "question":"Is there a current paid substitute for people-search and data-broker removal, and what nonzero price does it advertise?",
                "lane":"MARKET_WTP",
                "critical":True,
                "required_source_classes":["COMPETITOR_PRODUCT"],
                "minimum_independent_sources":1,
            },
            {
                "question_id":"Q-OFFICIAL-1",
                "question":"What official consumer guidance describes the DIY people-search opt-out process, its repetition burden, and its limitations?",
                "lane":"OFFICIAL_DOMAIN",
                "critical":True,
                "required_source_classes":["OFFICIAL_PRIMARY"],
                "minimum_independent_sources":1,
            },
            {
                "question_id":"Q-MARKET-2",
                "question":"Is there evidence that consumers actually use data-removal services rather than paid offerings existing only in theory?",
                "lane":"MARKET_WTP",
                "critical":True,
                "required_source_classes":["COMPETITOR_PRODUCT","CUSTOMER_REVIEW"],
                "minimum_independent_sources":1,
            },
        ],
        "budget":{"max_research_jobs":3,"max_sources":3},
        "stop_policy":{"minimum_source_classes":2,"diminishing_returns_window_packets":2,"minimum_new_supported_findings_in_window":1},
        "truth_status":"PLAN",
    }
    research_plan.validate_research_plan(plan)
    _write_json(stage_dir / "07-research-plan.json", plan)

    # 7. Multi-provider research allocation through the normal router, but with fixture providers.
    dispatches = research_executor.build_research_dispatches(
        plan=plan,
        registry=_fixture_research_registry(),
        pool=_fixture_research_pool(),
    )
    expected_routes = ["fixture-market-a","fixture-knowledge-a","fixture-market-b"]
    actual_routes = [d["route"]["provider_id"] for d in dispatches]
    if actual_routes != expected_routes:
        raise AssertionError(f"CANARY_RESEARCH_ROUTE_UNEXPECTED:{actual_routes}")

    source_by_question = {
        "Q-MARKET-1": {
            "source_id":"ORG001-INCOGNI-PRICING",
            "source_uri":"https://incogni.com/pricing",
            "path":required_sources["INCOGNI"],
            "finding_id":"F-MARKET-PRICE",
            "finding_text":"A paid data-removal substitute is actively offered at a nonzero recurring price.",
        },
        "Q-OFFICIAL-1": {
            "source_id":"ORG001-FTC-PEOPLESEARCH",
            "source_uri":"https://consumer.ftc.gov/articles/what-know-about-people-search-sites-sell-your-information",
            "path":required_sources["FTC"],
            "finding_id":"F-OFFICIAL-DIY",
            "finding_text":"Official FTC consumer guidance describes a free DIY opt-out path, repeated site-by-site work, periodic rechecking, and limits such as public records remaining available.",
        },
        "Q-MARKET-2": {
            "source_id":"ORG001-DELETEME-HOME",
            "source_uri":"https://joindeleteme.com/",
            "path":required_sources["DELETEME"],
            "finding_id":"F-MARKET-USAGE",
            "finding_text":"A current paid removal provider publishes customer usage/removal activity and customer feedback, supporting that the category has actual users rather than only theoretical pricing.",
        },
    }

    research_packets = []
    governed_packets = []
    for dispatch in dispatches:
        qid = dispatch["question"]["question_id"]
        src = source_by_question[qid]
        worker_output = {
            "execution_mode":FIXTURE_EXECUTION_MODE,
            "source_documents":[{
                "source_id":src["source_id"],
                "source_uri":src["source_uri"],
                "text":src["path"].read_text(encoding="utf-8", errors="replace"),
                "media_type":"text/html",
                "acquisition_method":"HTTP_CLIENT",
            }],
            "findings":[{
                "finding_id":src["finding_id"],
                "text":src["finding_text"],
                "source_ids":[src["source_id"]],
            }],
        }
        packet = research_executor.ingest_worker_research_output(dispatch=dispatch, worker_output=worker_output)
        packet["provider_observation"]["execution_mode"] = FIXTURE_EXECUTION_MODE
        research_packets.append(packet)
        snap = packet["source_snapshots"][0]
        governed = _govern_snapshot(
            snap,
            basis="Public webpage retained only as hashed reference evidence for bounded internal research; no verbatim commercial reuse authorized",
        )
        governed_packet = copy.deepcopy(packet)
        governed_packet["source_snapshots"] = [governed]
        governed_packets.append(governed_packet)

    _write_json(stage_dir / "08-research-dispatches.json", [
        {
            "work_card_id":d["work_card"]["work_card_id"],
            "question_id":d["question"]["question_id"],
            "provider_id":d["route"]["provider_id"],
            "execution_mode":FIXTURE_EXECUTION_MODE,
        } for d in dispatches
    ])
    _write_json(stage_dir / "09-research-packets.json", research_packets)
    _write_json(stage_dir / "10-governed-research-packets.json", governed_packets)

    by_source = {p["source_snapshots"][0]["source_id"]: p["source_snapshots"][0] for p in governed_packets}
    ftc = by_source["ORG001-FTC-PEOPLESEARCH"]
    incogni = by_source["ORG001-INCOGNI-PRICING"]
    deleteme = by_source["ORG001-DELETEME-HOME"]
    # Raw bytes and source IDs are identical to opportunity evidence, so evidence IDs must remain stable.
    for ref, packet in [
        (ftc_time_ref, ftc), (ftc_free_or_paid_ref, ftc), (ftc_steps_ref, ftc),
        (ftc_recheck_ref, ftc), (ftc_limits_ref, ftc), (incogni_price_ref, incogni),
        (deleteme_usage_ref, deleteme),
    ]:
        ids={u["evidence_id"] for u in packet.get("evidence_units") or []}
        if ref not in ids:
            raise AssertionError(f"CANARY_EVIDENCE_ID_DRIFT:{ref}")

    # 8. Research stop check after the bounded three-source research set.
    stop = research_plan.evaluate_stop(plan, {
        "completed_jobs":3,
        "source_count":3,
        "covered_question_ids":["Q-MARKET-1","Q-OFFICIAL-1","Q-MARKET-2"],
        "source_classes_seen":["COMPETITOR_PRODUCT","OFFICIAL_PRIMARY","CUSTOMER_REVIEW"],
        "unresolved_critical_contradictions":0,
        "recent_new_supported_findings":[1,1,1],
    })
    if stop["decision"] not in {"STOP_CONFIDENCE","STOP_BUDGET"}:
        raise AssertionError(f"CANARY_RESEARCH_NOT_STOPPED:{stop}")
    _write_json(stage_dir / "11-research-stop.json", stop)

    # 9. Synthesis: bounded non-live fixture output, evidence refs must resolve to governed packets.
    synth_artifacts = [
        {"artifact_id":p["research_packet_id"],"kind":"research_packet","ref":f"artifact://research/{p['research_packet_id']}","sha256":None}
        for p in governed_packets
    ]
    synth_card = knowledge_synthesis.build_synthesis_work_card(
        knowledge_map_id="H03-KM-ORG001-001",
        research_packet_artifacts=synth_artifacts,
    )
    synth_request = knowledge_synthesis.build_synthesis_request(
        card=synth_card,
        packets=governed_packets,
        model_route="fixture://synthesizer",
    )
    synth_fixture = {
        "supported_findings":[
            {"finding_id":"SF-1","text":"People-search sites compile personal information and provide opt-out mechanisms.","evidence_refs":[ftc_steps_ref]},
            {"finding_id":"SF-2","text":"DIY removal can be performed for free but requires repeated site-by-site work and periodic rechecking.","evidence_refs":[ftc_free_or_paid_ref,ftc_time_ref,ftc_recheck_ref]},
            {"finding_id":"SF-3","text":"Paid substitutes exist and the category shows active usage, supporting medium willingness-to-pay evidence.","evidence_refs":[incogni_price_ref,deleteme_usage_ref]},
        ],
        "contradictions":[],
        "gaps":[],
        "market_wtp_findings":[
            {"finding_id":"MW-1","text":"A paid removal substitute advertises nonzero recurring pricing.","evidence_refs":[incogni_price_ref],"signal_type":"PAID_SUBSTITUTE"},
            {"finding_id":"MW-2","text":"Published removal/customer activity supports actual category usage.","evidence_refs":[deleteme_usage_ref],"signal_type":"MARKETPLACE_SALE_PROXY"},
        ],
        "claims":[
            {"claim_id":"C1","text":"Start by searching a people-search site for your name or other identifying information such as a phone number or address.","evidence_refs":[ftc_steps_ref]},
            {"claim_id":"C2","text":"When you find a report about yourself, locate the site's opt-out or removal instructions and follow them.","evidence_refs":[ftc_steps_ref]},
            {"claim_id":"C3","text":"Repeat the opt-out process across other relevant people-search sites; doing this one by one can be time-consuming.","evidence_refs":[ftc_time_ref]},
            {"claim_id":"C4","text":"Periodically recheck people-search sites and submit new opt-out requests if your information reappears.","evidence_refs":[ftc_recheck_ref]},
            {"claim_id":"C5","text":"Opting out of people-search sites does not delete information from public records, so the workflow reduces exposure rather than guaranteeing total deletion.","evidence_refs":[ftc_limits_ref]},
            {"claim_id":"C6","text":"Consumers can perform people-search opt-outs themselves for free or pay a service to perform the work on their behalf.","evidence_refs":[ftc_free_or_paid_ref]},
        ],
    }
    knowledge_map, candidate = knowledge_synthesis.normalize_synthesis_output(
        knowledge_map_id="H03-KM-ORG001-001",
        candidate_id="H03-KPC-ORG001-001",
        packets=governed_packets,
        model_output=synth_fixture,
    )
    if candidate["promotion_state"] != "ELIGIBLE_FOR_KNOWLEDGE_VALIDATION":
        raise AssertionError(f"CANARY_SYNTHESIS_NOT_ELIGIBLE:{candidate['promotion_state']}")
    _write_json(stage_dir / "12-synthesis-work-card.json", synth_card)
    _write_json(stage_dir / "13-synthesis-request.json", {**synth_request,"execution_mode":FIXTURE_EXECUTION_MODE})
    _write_json(stage_dir / "14-knowledge-map.json", knowledge_map)
    _write_json(stage_dir / "15-knowledge-package-candidate.json", candidate)

    # 10. Knowledge Package: only FTC-supported product claims become accepted product truth.
    product_claims = [c for c in synth_fixture["claims"] if all(ref.startswith("ORG001-FTC-PEOPLESEARCH-") for ref in c["evidence_refs"])]
    knowledge_package = {
        "schema_version":"die.h03.knowledge-package.v1",
        "knowledge_package_id":"H03-KP-ORG001-001",
        "holding_id":"H03",
        "version":1,
        "rights_status":"GOVERNED_EXTERNAL",
        "source_packet":ftc,
        "claims":product_claims,
    }
    h03_factory.validate_knowledge_package(knowledge_package)
    _write_json(stage_dir / "16-knowledge-package.json", knowledge_package)

    # 11. Product form selection: sequential task -> guide, not ebook.
    profile = {
        "schema_version":"die.h03.product-planning-profile.v1",
        "planning_profile_id":"H03-PPLAN-ORG001-001",
        "holding_id":"H03",
        "problem_seed_id":problem_seed["problem_seed_id"],
        "knowledge_package_id":knowledge_package["knowledge_package_id"],
        "desired_outcome":problem_seed["desired_outcome"],
        "delivery_shape":"EXECUTE_SEQUENCE",
        "recurrence":"REPEATED",
        "decision_complexity":"LOW",
        "explanation_depth":"MEDIUM",
        "input_capture":"NONE",
        "lookup_frequency":"LOW",
        "evidence_density":"MEDIUM",
        "reusable_structure":False,
        "section_plan":[
            {"heading":"1. Find your exposed listing","claim_ids":["C1"]},
            {"heading":"2. Submit the opt-out","claim_ids":["C2"]},
            {"heading":"3. Repeat across sites","claim_ids":["C3"]},
            {"heading":"4. Recheck periodically","claim_ids":["C4"]},
            {"heading":"5. Know the limits","claim_ids":["C5","C6"]},
        ],
    }
    blueprint = product_planner.build_product_blueprint(
        product_id="H03-PROD-ORG001-001",
        title="DIY People-Search Opt-Out Guide",
        subtitle="A bounded repeatable workflow for reducing exposed personal information",
        profile=profile,
        knowledge_package=knowledge_package,
    )
    if blueprint["form"] != "guide":
        raise AssertionError(f"CANARY_PRODUCT_FORM_UNEXPECTED:{blueprint['form']}")
    _write_json(stage_dir / "17-product-planning-profile.json", profile)
    _write_json(stage_dir / "18-product-blueprint.json", blueprint)

    # 12. Semantic producer fan-out through the normal routing contract, still non-live fixtures.
    producer_dispatches = semantic_producer.allocate_producer_dispatches(
        blueprint=blueprint,
        knowledge_package=knowledge_package,
        registry=_fixture_producer_registry(),
        pool=_fixture_producer_pool(),
    )
    producer_fixture_outputs = {
        "SEC-001":{"blocks":[{"block_id":"B-001","kind":"STEP","text":"Search the people-search site for your name, phone number, or address and open the listing that appears to describe you.","claim_ids":["C1"]}]},
        "SEC-002":{"blocks":[{"block_id":"B-002","kind":"STEP","text":"Use the site's opt-out or removal instructions for the listing you found and complete the requested steps.","claim_ids":["C2"]}]},
        "SEC-003":{"blocks":[{"block_id":"B-003","kind":"STEP","text":"Move to the next relevant people-search site and repeat the same search-and-opt-out workflow.","claim_ids":["C3"]}]},
        "SEC-004":{"blocks":[{"block_id":"B-004","kind":"CHECKLIST_ITEM","text":"Schedule a periodic recheck and submit another opt-out request if your information appears again.","claim_ids":["C4"]}]},
        "SEC-005":{"blocks":[
            {"block_id":"B-005A","kind":"CALLOUT","text":"Treat this as exposure reduction, not total erasure: public records may still remain available.","claim_ids":["C5"]},
            {"block_id":"B-005B","kind":"PARAGRAPH","text":"DIY opt-outs can be done for free; a paid service is an alternative if you prefer to delegate the repeated work.","claim_ids":["C6"]},
        ]},
    }
    content_batches = []
    for dispatch in producer_dispatches:
        sid = dispatch["section_id"]
        batch = semantic_producer.normalize_producer_output(
            dispatch=dispatch,
            knowledge_package=knowledge_package,
            model_output=producer_fixture_outputs[sid],
        )
        batch["producer_observation"]["execution_mode"] = FIXTURE_EXECUTION_MODE
        content_batches.append(batch)
    _write_json(stage_dir / "19-producer-dispatches.json", [
        {
            "work_card_id":d["work_card"]["work_card_id"],
            "section_id":d["section_id"],
            "provider_id":d["route"]["provider_id"],
            "execution_mode":FIXTURE_EXECUTION_MODE,
        } for d in producer_dispatches
    ])
    _write_json(stage_dir / "20-content-block-batches.json", content_batches)

    # 13. Deterministic compile/QA/package.
    package_receipt = product_packager.build_local_product_package(
        output_root=package_root,
        blueprint=blueprint,
        knowledge_package=knowledge_package,
        content_batches=content_batches,
    )
    _write_json(stage_dir / "21-package-receipt.json", package_receipt)

    lineage = {
        "schema_version":CANARY_SCHEMA,
        "canary_id":"H03-ORG-001-CANARY-001",
        "holding_id":"H03",
        "status":"PASS",
        "problem_seed_id":problem_seed["problem_seed_id"],
        "worth_making_decision":worth["decision"],
        "research_execution_mode":FIXTURE_EXECUTION_MODE,
        "research_provider_ids":actual_routes,
        "research_sources":[p["source_snapshots"][0]["source_uri"] for p in governed_packets],
        "synthesis_execution_mode":FIXTURE_EXECUTION_MODE,
        "knowledge_package_id":knowledge_package["knowledge_package_id"],
        "product_form":blueprint["form"],
        "producer_execution_mode":FIXTURE_EXECUTION_MODE,
        "producer_provider_ids":[d["route"]["provider_id"] for d in producer_dispatches],
        "content_batch_ids":[b["content_batch_id"] for b in content_batches],
        "package":package_receipt,
        "live_browser_preflight_performed":False,
        "live_web_ai_provider_call_claimed":False,
        "external_publication":False,
        "paid_ads":False,
        "founder_publication_gate_crossed":False,
    }
    _write_json(evidence_root / "organism-lineage.json", lineage)
    return lineage
