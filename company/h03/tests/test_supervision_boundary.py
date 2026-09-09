import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'supervision_boundary.py'
spec=importlib.util.spec_from_file_location('supervision_boundary',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
BOUNDARY=json.loads((ROOT/'company'/'h03'/'runtime'/'mission-control-boundary.v1.json').read_text(encoding='utf-8'))

class SupervisionBoundaryTests(unittest.TestCase):
    def state(self,status='RUNNING',progress=40,microjobs=250):
        return {
            'schema_version':mod.SCHEMA,'holding_id':'H03','batch_id':'H03-BATCH-042','mission_task_id':'MC-H03-BATCH-042',
            'status':status,'progress_percent':progress,'product_ids':['H03-PROD-001','H03-PROD-002'],
            'stage_counts':{'curation_done':2,'research_running':4,'production_queued':1},'microjob_count':microjobs,
            'artifact_refs':['artifact://batch/H03-BATCH-042/standing.json'],'failure_summary':None,'recovery_summary':None,'founder_gate':None
        }
    def test_boundary_reuses_canonical_mission_protocol_methods(self):
        self.assertEqual(BOUNDARY['mission_protocol'],'mc-mission-v1')
        self.assertEqual(BOUNDARY['mission_control_reference_sha'],'5557e3738cc11d82c53dfb68072b1f09a388e22a')
        self.assertEqual(BOUNDARY['universal_mcp_reference_sha'],'07239a1ab00a9ad66f1e1b64c660c1f8e160d614')
        self.assertIn('mission.task.checkpoint',BOUNDARY['supported_methods'])
        self.assertIn('mission.founder.request',BOUNDARY['supported_methods'])
        self.assertFalse(BOUNDARY['microjob_protocol_required'])
    def test_checkpoint_is_batch_aggregate_not_microjob_hot_path(self):
        s=self.state(microjobs=10000)
        intent=mod.build_mission_intent(event='BATCH_CHECKPOINT',state=s,summary='Batch progressing normally.')
        self.assertEqual(intent['mission_method'],'mission.task.checkpoint')
        self.assertFalse(intent['microjob_protocol_call'])
        self.assertEqual(intent['payload']['microjob_count'],10000)
        self.assertNotIn('jobs',intent['payload'])
        self.assertNotIn('leaseToken',str(intent))
    def test_prompt_or_secret_material_cannot_enter_supervision_state(self):
        for key in ('prompt','cookies','lease_token','profile_path'):
            s=self.state(); s[key]='forbidden'
            with self.assertRaisesRegex(ValueError,'SUPERVISION_SECRET_OR_MICROJOB_PAYLOAD_FORBIDDEN'):
                mod.validate_batch_state(s)
    def test_ephemeral_lease_capability_is_injected_only_at_invoke(self):
        s=self.state(); intent=mod.build_mission_intent(event='BATCH_CHECKPOINT',state=s,summary='Checkpoint')
        seen={}
        def fake(method,payload): seen.update({'method':method,'payload':payload}); return {'ok':True}
        result=mod.invoke_mission_intent(intent=intent,principal_id='chatgpt-architect',lease_token='ephemeral-lease',transport=fake)
        self.assertTrue(result['ok']); self.assertEqual(seen['method'],'mission.task.checkpoint'); self.assertEqual(seen['payload']['leaseToken'],'ephemeral-lease')
        self.assertNotIn('ephemeral-lease',json.dumps(intent))
    def test_recovery_summary_is_checkpointed_as_batch_aggregate(self):
        s=self.state(); s['recovery_summary']={'failure_class':'RATE_LIMIT','action':'FALLBACK_ALTERNATE_WORKER','recovered':True}
        intent=mod.build_mission_intent(event='BATCH_CHECKPOINT',state=s,summary='Recovered by alternate worker')
        self.assertEqual(intent['payload']['recovery_summary']['action'],'FALLBACK_ALTERNATE_WORKER')
        self.assertFalse(intent['microjob_protocol_call'])

    def test_complete_requires_completed_100_percent(self):
        s=self.state(status='COMPLETED',progress=100)
        intent=mod.build_mission_intent(event='BATCH_COMPLETED',state=s,summary='Batch complete')
        self.assertEqual(intent['mission_method'],'mission.task.complete')
        self.assertEqual(intent['artifacts'],s['artifact_refs'])
        s['progress_percent']=99
        with self.assertRaisesRegex(ValueError,'SUPERVISION_COMPLETE_STATE_INVALID'):
            mod.build_mission_intent(event='BATCH_COMPLETED',state=s,summary='Too early')
    def test_block_and_founder_gate_map_to_existing_protocol(self):
        s=self.state(status='BLOCKED',progress=50); s['failure_summary']={'reason':'Provider pool exhausted','retryable':True,'founder_required':False}
        intent=mod.build_mission_intent(event='BATCH_BLOCKED',state=s,summary='Blocked')
        self.assertEqual(intent['mission_method'],'mission.task.block'); self.assertTrue(intent['retryable'])
        s=self.state(status='AWAITING_FOUNDER',progress=80); s['founder_gate']={'kind':'H03_PUBLICATION_GATE','title':'Review H03 product','body':'Review package before external publication.'}
        intent=mod.build_mission_intent(event='FOUNDER_GATE_REQUIRED',state=s,summary='Founder review required')
        self.assertEqual(intent['mission_method'],'mission.founder.request'); self.assertIn('Review H03 product',intent['title'])
