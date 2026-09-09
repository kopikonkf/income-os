import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'semantic_producer.py'
spec=importlib.util.spec_from_file_location('semantic_producer',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
REG=json.loads((ROOT/'company'/'h03'/'runtime'/'provider-worker-registry.v1.json').read_text(encoding='utf-8'))

class SemanticProducerTests(unittest.TestCase):
    def kp(self):
        return {'schema_version':'die.h03.knowledge-package.v1','knowledge_package_id':'KP-001','holding_id':'H03','version':1,'rights_status':'INTERNAL_ORIGINAL','source_packet':{'source_id':'SRC-1','rights_status':'INTERNAL_ORIGINAL','evidence_units':[{'evidence_id':'E1','text':'Step one.'},{'evidence_id':'E2','text':'Step two.'},{'evidence_id':'E3','text':'Verify completion.'}]},'claims':[{'claim_id':'C1','text':'Perform step one first.','evidence_refs':['E1']},{'claim_id':'C2','text':'Then perform step two.','evidence_refs':['E2']},{'claim_id':'C3','text':'Verify the result.','evidence_refs':['E3']}]}
    def blueprint(self):
        return {'schema_version':'die.h03.product-blueprint.v1','product_id':'PROD-001','knowledge_package_id':'KP-001','form':'guide','title':'Two-Step Guide','subtitle':'','sections':[{'heading':'Do the work','claim_ids':['C1','C2']},{'heading':'Verify','claim_ids':['C3']}],'metadata':{'template_id':'guide.clean.v1','desired_outcome':'complete the task correctly'}}
    def pool(self):
        return {'schema_version':'die.h03.browser-profile-pool.v1','holding_id':'H03','pool_id':'knowledge','purpose':'KNOWLEDGE_WORKFORCE','session_material_policy':'HOST_LOCAL_NOT_PRODUCT_TRUTH','shards':[{'shard_id':'knowledge-a','state':'READY','providers':[{'provider_id':'qwen','state':'READY','available_slots':1,'transport_family':'SESSION_API'},{'provider_id':'gemini','state':'READY','available_slots':1,'transport_family':'BROWSER_CDP'}]}]}

    def test_one_section_becomes_one_standard_producer_work_card(self):
        cards=mod.build_producer_work_cards(blueprint=self.blueprint(),knowledge_package=self.kp())
        self.assertEqual(len(cards),2)
        self.assertTrue(all(c['role']=='PRODUCER' for c in cards))
        self.assertTrue(all(c['capability_requirements']=={'web_ai':True,'mcp':False,'shell':False,'local_filesystem':False} for c in cards))
        self.assertTrue(all(set(c)=={'schema_version','work_card_id','holding_id','task_id','role','queue','idempotency_key','input_artifacts','output_contract','capability_requirements','terminal_policy'} for c in cards))

    def test_dispatch_fans_out_across_observed_slots(self):
        d=mod.allocate_producer_dispatches(blueprint=self.blueprint(),knowledge_package=self.kp(),registry=REG,pool=self.pool())
        self.assertEqual([x['route']['provider_id'] for x in d],['qwen','gemini'])
        self.assertEqual([x['section_id'] for x in d],['SEC-001','SEC-002'])
        self.assertNotIn('evidence_refs',json.dumps(d[0]['request']['context']))

    def test_producer_output_gets_evidence_attached_deterministically(self):
        d=mod.allocate_producer_dispatches(blueprint=self.blueprint(),knowledge_package=self.kp(),registry=REG,pool=self.pool())[0]
        model={'blocks':[{'block_id':'B1','kind':'STEP','text':'Start with step one, then continue to step two.','claim_ids':['C1','C2']}]}
        batch=mod.normalize_producer_output(dispatch=d,knowledge_package=self.kp(),model_output=model)
        self.assertEqual(batch['truth_status'],'DERIVED_SEMANTIC_CONTENT')
        self.assertEqual(batch['blocks'][0]['evidence_refs'],['E1','E2'])
        self.assertEqual(batch['producer_observation']['provider_id'],'qwen')

    def test_model_cannot_reference_claim_outside_assigned_section(self):
        d=mod.allocate_producer_dispatches(blueprint=self.blueprint(),knowledge_package=self.kp(),registry=REG,pool=self.pool())[0]
        model={'blocks':[{'block_id':'B1','kind':'PARAGRAPH','text':'Try to use another section claim.','claim_ids':['C3']}]}
        with self.assertRaisesRegex(ValueError,'BLOCK_CLAIM_OUT_OF_SECTION'):
            mod.normalize_producer_output(dispatch=d,knowledge_package=self.kp(),model_output=model)

    def test_json_code_fence_is_accepted_but_invalid_json_fails(self):
        d=mod.allocate_producer_dispatches(blueprint=self.blueprint(),knowledge_package=self.kp(),registry=REG,pool=self.pool())[0]
        fenced='```json\n{"blocks":[{"block_id":"B1","kind":"BULLET","text":"Do step one.","claim_ids":["C1"]}]}\n```'
        self.assertEqual(mod.normalize_producer_output(dispatch=d,knowledge_package=self.kp(),model_output=fenced)['blocks'][0]['kind'],'BULLET')
        with self.assertRaisesRegex(ValueError,'MODEL_JSON_INVALID'):
            mod.normalize_producer_output(dispatch=d,knowledge_package=self.kp(),model_output='{bad json')

    def test_noncanonical_knowledge_candidate_is_rejected(self):
        candidate={'schema_version':'die.h03.knowledge-package-candidate.v1','holding_id':'H03','canonical_truth':False}
        with self.assertRaisesRegex(ValueError,'ACCEPTED_KNOWLEDGE_REQUIRED'):
            mod.build_producer_work_cards(blueprint=self.blueprint(),knowledge_package=candidate)
