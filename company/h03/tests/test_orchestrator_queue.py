import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'orchestrator_queue.py'
spec=importlib.util.spec_from_file_location('orchestrator_queue',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
CP=ROOT/'company'/'h03'/'lib'/'cognition_work_card.py'
cspec=importlib.util.spec_from_file_location('cognition_work_card_test_dep',CP); cardmod=importlib.util.module_from_spec(cspec); assert cspec.loader; cspec.loader.exec_module(cardmod)

class OrchestratorQueueTests(unittest.TestCase):
    def card(self,i):
        return {'schema_version':cardmod.CARD_SCHEMA,'work_card_id':f'H03-WC-{i}','holding_id':'H03','task_id':'H03-RSCH-002','role':'KNOWLEDGE_RESEARCHER','queue':'research','idempotency_key':f'h03-job-{i}-0001','input_artifacts':[{'artifact_id':'RP1','kind':'research_plan','ref':'artifact://rp/1','sha256':None}],'output_contract':{'artifact_kind':'research_packet','schema_version':'die.h03.research-packet.v1'},'capability_requirements':cardmod.standard_web_ai_capabilities(),'terminal_policy':{'max_attempts':3,'retryable_failures':['RATE_LIMITED']}}
    def success(self,card,i):
        return {'schema_version':cardmod.RESULT_SCHEMA,'work_card_id':card['work_card_id'],'attempt':1,'status':'SUCCEEDED','output_artifacts':[{'artifact_id':f'RP-{i}','kind':'research_packet','ref':f'artifact://research/{i}','sha256':None}],'worker_observation':{'provider_id':'qwen'}}
    def test_enqueue_is_idempotent_by_key(self):
        s=mod.create_state('B1'); c=self.card('1'); mod.enqueue(s,c); mod.enqueue(s,c); self.assertEqual(len(s['jobs']),1)
    def test_transition_rules_are_explicit(self):
        s=mod.create_state('B1'); c=self.card('1'); mod.enqueue(s,c); mod.transition(s,c['work_card_id'],'DISPATCHED'); mod.transition(s,c['work_card_id'],'RUNNING'); self.assertEqual(s['jobs'][c['work_card_id']]['attempt'],1)
        with self.assertRaisesRegex(ValueError,'QUEUE_TRANSITION_INVALID'): mod.transition(s,c['work_card_id'],'QUEUED')
    def test_bounded_fanout_and_fanin_collects_only_durable_artifacts(self):
        s=mod.create_state('B1'); cards=[self.card(str(i)) for i in range(3)]
        for c in cards: mod.enqueue(s,c)
        mod.add_fan_in_group(s,group_id='G1',child_work_card_ids=[c['work_card_id'] for c in cards],target_work_card_id='SYNTH-1',max_children=4)
        self.assertEqual(mod.fan_in_status(s,'G1'),'WAITING')
        for i,c in enumerate(cards): mod.transition(s,c['work_card_id'],'DISPATCHED'); mod.apply_result(s,c,self.success(c,i))
        self.assertEqual(mod.fan_in_status(s,'G1'),'READY'); artifacts=mod.collect_fan_in_artifacts(s,'G1'); self.assertEqual(len(artifacts),3); self.assertTrue(all('ref' in a for a in artifacts))
    def test_fanout_bound_rejects_oversized_group(self):
        s=mod.create_state('B1'); cards=[self.card(str(i)) for i in range(3)]
        for c in cards: mod.enqueue(s,c)
        with self.assertRaisesRegex(ValueError,'FANOUT_BOUND_EXCEEDED'): mod.add_fan_in_group(s,group_id='G1',child_work_card_ids=[c['work_card_id'] for c in cards],target_work_card_id='SYNTH-1',max_children=2)
    def test_terminal_failure_blocks_fanin(self):
        s=mod.create_state('B1'); c=self.card('1'); mod.enqueue(s,c); mod.add_fan_in_group(s,group_id='G1',child_work_card_ids=[c['work_card_id']],target_work_card_id='SYNTH-1')
        mod.transition(s,c['work_card_id'],'DISPATCHED'); fail={'schema_version':cardmod.RESULT_SCHEMA,'work_card_id':c['work_card_id'],'attempt':1,'status':'FAILED_TERMINAL','output_artifacts':[],'worker_observation':{}}; mod.apply_result(s,c,fail); self.assertEqual(mod.fan_in_status(s,'G1'),'BLOCKED_FAILURE')
