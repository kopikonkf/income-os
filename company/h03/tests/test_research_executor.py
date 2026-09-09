import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'research_executor.py'
spec=importlib.util.spec_from_file_location('research_executor',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
REG=json.loads((ROOT/'company'/'h03'/'runtime'/'provider-worker-registry.v1.json').read_text(encoding='utf-8'))

class ResearchExecutorTests(unittest.TestCase):
    def plan(self):
        return {'schema_version':'die.h03.research-plan.v1','research_plan_id':'RP-EXEC-1','holding_id':'H03','problem_seed_id':'H03-PS-A1','worth_making_decision_id':'WM-1','questions':[{'question_id':'Q1','question':'What evidence shows customers already pay for solutions?','lane':'MARKET_WTP','critical':True,'required_source_classes':['MARKETPLACE_LISTING'],'minimum_independent_sources':1},{'question_id':'Q2','question':'What official procedures constrain the useful solution?','lane':'OFFICIAL_DOMAIN','critical':True,'required_source_classes':['OFFICIAL_PRIMARY'],'minimum_independent_sources':1},{'question_id':'Q3','question':'What additional source-grounded facts improve the product?','lane':'GENERAL_KNOWLEDGE','critical':False,'required_source_classes':['SPECIALIST_PUBLICATION'],'minimum_independent_sources':1}],'budget':{'max_research_jobs':3,'max_sources':12},'stop_policy':{'minimum_source_classes':2,'diminishing_returns_window_packets':2,'minimum_new_supported_findings_in_window':1},'truth_status':'PLAN'}
    def pool(self):
        return {'schema_version':'die.h03.browser-profile-pool.v1','holding_id':'H03','pool_id':'knowledge-pool','purpose':'KNOWLEDGE_WORKFORCE','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','shards':[{'shard_id':'knowledge-a','state':'READY','providers':[{'provider_id':'qwen','state':'READY','available_slots':1,'transport_family':'SESSION_API'},{'provider_id':'gemini','state':'READY','available_slots':1,'transport_family':'BROWSER_CDP'},{'provider_id':'manus','state':'READY','available_slots':1,'transport_family':'BROWSER_CDP'}]}]}
    def test_dispatch_allocator_spreads_across_available_worker_slots(self):
        dispatches=mod.build_research_dispatches(plan=self.plan(),registry=REG,pool=self.pool())
        self.assertEqual([d['route']['provider_id'] for d in dispatches],['qwen','gemini','manus'])
        self.assertTrue(all(d['request']['role'] in {'MARKET_RESEARCHER','KNOWLEDGE_RESEARCHER'} for d in dispatches))
    def test_worker_source_text_is_ingested_through_kf002_and_remains_pending_review(self):
        d=mod.build_research_dispatches(plan=self.plan(),registry=REG,pool=self.pool())[0]
        out={'source_documents':[{'source_id':'SRC-MKT-1','source_uri':'https://example.invalid/market','text':'A marketplace listing offers a paid solution for the target problem.','media_type':'text/plain','acquisition_method':'WEB_TOOL_SNAPSHOT'}],'findings':[{'finding_id':'F1','text':'A paid substitute exists.','source_ids':['SRC-MKT-1']}]}
        packet=mod.ingest_worker_research_output(dispatch=d,worker_output=out)
        self.assertEqual(packet['truth_status'],'UNVERIFIED_RESEARCH_PACKET')
        self.assertEqual(packet['source_snapshots'][0]['review_state'],'PENDING_REVIEW')
        self.assertFalse(packet['source_snapshots'][0]['canonical_truth'])
        self.assertTrue(packet['findings'][0]['evidence_refs'])
    def test_hyphenated_question_ids_are_preserved_exactly(self):
        plan=self.plan()
        plan["questions"][0]["question_id"]="Q-MARKET-1"
        plan["questions"][1]["question_id"]="Q-OFFICIAL-1"
        plan["questions"][2]["question_id"]="Q-MARKET-2"
        dispatches=mod.build_research_dispatches(plan=plan,registry=REG,pool=self.pool())
        self.assertEqual([d["question"]["question_id"] for d in dispatches],["Q-MARKET-1","Q-OFFICIAL-1","Q-MARKET-2"])

    def test_finding_cannot_reference_unknown_source(self):
        d=mod.build_research_dispatches(plan=self.plan(),registry=REG,pool=self.pool())[0]
        out={'source_documents':[{'source_id':'SRC-1','source_uri':'https://example.invalid/a','text':'Evidence text.'}],'findings':[{'finding_id':'F1','text':'Claim','source_ids':['MISSING']} ]}
        with self.assertRaisesRegex(ValueError,'RESEARCH_FINDING_UNKNOWN_SOURCE'): mod.ingest_worker_research_output(dispatch=d,worker_output=out)
