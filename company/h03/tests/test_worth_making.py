import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'worth_making.py'
spec=importlib.util.spec_from_file_location('worth_making',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class WorthMakingTests(unittest.TestCase):
    def seed(self):
        return {'schema_version':'die.h03.human-problem-seed.v1','problem_seed_id':'H03-PS-A1','holding_id':'H03','persona':{'actor':'freelancer','qualifier':'uses many online services'},'context':'manages scattered accounts','trigger':'needs a cleanup workflow','job_to_be_done':'reduce repeated manual searching','pain':{'statement':'instructions are fragmented','severity_state':'UNKNOWN','frequency_state':'UNKNOWN','urgency_state':'UNKNOWN'},'desired_outcome':'one actionable sequence','commercial_signals':{'demand':{'state':'UNKNOWN','evidence_refs':[]},'willingness_to_pay':{'state':'UNKNOWN','evidence_refs':[]}},'source_refs':['signal://1'],'truth_status':'CANDIDATE'}
    def demand(self,wtp='MEDIUM',intent='MEDIUM',levels=('MEDIUM','MEDIUM','MEDIUM')):
        signal='PAID_SUBSTITUTE' if wtp=='MEDIUM' else ('REVEALED_SPEND' if wtp=='STRONG' else ('PURCHASE_INTENT_SEARCH' if wtp=='WEAK' else None))
        evidence=[] if signal is None else [{'evidence_id':'E1','signal_type':signal,'evidence_refs':['source://market'],'money':({'currency':'USD','amount_minor':900} if signal=='REVEALED_SPEND' else None)}]
        return {'schema_version':'die.h03.demand-wtp-evidence.v1','packet_id':'D1','holding_id':'H03','problem_seed_id':'H03-PS-A1','pain_observation':{'severity':levels[0],'frequency':levels[1],'urgency':levels[2]},'buyer_intent_state':intent,'evidence':evidence,'wtp_assessment':wtp,'truth_status':'CANDIDATE'}
    def test_make_requires_commercial_and_productability_evidence(self):
        d=mod.evaluate_worth_making(decision_id='WM1',seed=self.seed(),demand_packet=self.demand(),productability={'state':'HIGH','evidence_refs':['evidence://productability']})
        self.assertEqual(d['decision'],'MAKE')
    def test_unknown_wtp_research_more_not_reject(self):
        d=mod.evaluate_worth_making(decision_id='WM2',seed=self.seed(),demand_packet=self.demand('UNKNOWN','UNKNOWN',('UNKNOWN','UNKNOWN','UNKNOWN')),productability={'state':'UNKNOWN','evidence_refs':[]})
        self.assertEqual(d['decision'],'RESEARCH_MORE'); self.assertIn('WTP_UNKNOWN',d['reason_codes'])
    def test_low_productability_rejects(self):
        d=mod.evaluate_worth_making(decision_id='WM3',seed=self.seed(),demand_packet=self.demand(),productability={'state':'LOW','evidence_refs':['evidence://not-productizable']})
        self.assertEqual(d['decision'],'REJECT')
    def test_low_commercial_pressure_rejects(self):
        d=mod.evaluate_worth_making(decision_id='WM4',seed=self.seed(),demand_packet=self.demand('WEAK','WEAK',('LOW','LOW','LOW')),productability={'state':'MEDIUM','evidence_refs':['evidence://productability']})
        self.assertEqual(d['decision'],'REJECT'); self.assertIn('LOW_COMMERCIAL_PRESSURE',d['reason_codes'])
