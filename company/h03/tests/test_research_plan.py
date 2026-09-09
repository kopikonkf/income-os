import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'research_plan.py'
spec=importlib.util.spec_from_file_location('research_plan',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class ResearchPlanTests(unittest.TestCase):
    def plan(self):
        return {'schema_version':mod.SCHEMA,'research_plan_id':'RP-001','holding_id':'H03','problem_seed_id':'H03-PS-A1','worth_making_decision_id':'WM-1','questions':[{'question_id':'Q1','question':'What evidence shows people already pay to solve this problem?','lane':'MARKET_WTP','critical':True,'required_source_classes':['MARKETPLACE_LISTING','CUSTOMER_REVIEW'],'minimum_independent_sources':2},{'question_id':'Q2','question':'What official procedures or constraints determine the correct solution?','lane':'OFFICIAL_DOMAIN','critical':True,'required_source_classes':['OFFICIAL_PRIMARY'],'minimum_independent_sources':1}],'budget':{'max_research_jobs':4,'max_sources':20},'stop_policy':{'minimum_source_classes':2,'diminishing_returns_window_packets':2,'minimum_new_supported_findings_in_window':1},'truth_status':'PLAN'}
    def test_plan_builds_role_separated_work_cards(self):
        cards=mod.build_research_work_cards(self.plan()); self.assertEqual(len(cards),2); self.assertEqual(cards[0]['role'],'MARKET_RESEARCHER'); self.assertEqual(cards[1]['role'],'KNOWLEDGE_RESEARCHER'); self.assertTrue(all(c['capability_requirements']['mcp'] is False for c in cards))
    def test_question_count_must_fit_budget(self):
        p=self.plan(); p['budget']['max_research_jobs']=1
        with self.assertRaisesRegex(ValueError,'QUESTIONS_EXCEED_JOB_BUDGET'): mod.validate_research_plan(p)
    def test_confidence_stop_requires_critical_coverage_and_source_diversity(self):
        p=self.plan(); d=mod.evaluate_stop(p,{'completed_jobs':2,'source_count':5,'covered_question_ids':['Q1','Q2'],'source_classes_seen':['MARKETPLACE_LISTING','OFFICIAL_PRIMARY'],'unresolved_critical_contradictions':0,'recent_new_supported_findings':[2,2]}); self.assertEqual(d['decision'],'STOP_CONFIDENCE')
    def test_unknown_critical_coverage_continues(self):
        p=self.plan(); d=mod.evaluate_stop(p,{'completed_jobs':1,'source_count':3,'covered_question_ids':['Q1'],'source_classes_seen':['MARKETPLACE_LISTING','CUSTOMER_REVIEW'],'unresolved_critical_contradictions':0,'recent_new_supported_findings':[2]}); self.assertEqual(d['decision'],'CONTINUE')
    def test_budget_stop_is_bounded(self):
        p=self.plan(); d=mod.evaluate_stop(p,{'completed_jobs':4,'source_count':5,'covered_question_ids':['Q1'],'source_classes_seen':['MARKETPLACE_LISTING'],'unresolved_critical_contradictions':0,'recent_new_supported_findings':[0,0]}); self.assertEqual(d['decision'],'STOP_BUDGET')
