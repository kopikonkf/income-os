import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company'/'company-os'/'die-h01'
MANIFEST=H01/'runtime'/'h01-architect-browser-worker-session.v1.json'
SCHEMA=H01/'contracts'/'h01-architect-browser-worker-session.v1.schema.json'
DOC=H01/'DIE_H01_ARCHITECT_BROWSER_WORKER_SESSION_V1.md'

class BrowserWorkerSessionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads(MANIFEST.read_text())
        cls.s=json.loads(SCHEMA.read_text())
        cls.d=DOC.read_text()

    def test_one_session_one_task_principal_lease_dispatch(self):
        c=self.m['cardinality']
        self.assertEqual(c['tasks_per_session'],1)
        self.assertEqual(c['principals_per_session'],1)
        self.assertEqual(c['owner_leases_per_session'],1)
        self.assertEqual(c['dispatch_attempts_per_session'],1)
        self.assertEqual(c['mutable_worktrees_per_task'],1)
        self.assertTrue(self.m['mission_control_is_scheduler'])
        self.assertFalse(self.m['worker_is_scheduler'])

    def test_bootstrap_is_ephemeral_and_requires_authoritative_intake(self):
        b=self.m['bootstrap']
        self.assertEqual(set(b['required_ephemeral_fields']),{
            'project_name','task_id','mission_principal_id','mission_lease_token','dispatch_id','completion_marker'
        })
        self.assertTrue(b['lease_token_ephemeral'])
        self.assertFalse(b['lease_token_persisted'])
        self.assertFalse(b['bootstrap_is_task_truth'])
        self.assertTrue(b['must_recover_project_context_first'])
        self.assertTrue(b['must_reconcile_current_canon'])
        self.assertTrue(b['must_call_mission_task_get_before_execution'])

    def test_durable_mission_state_not_chat_text_is_authority(self):
        a=self.m['durable_authority']
        self.assertEqual(a['checkpoint_method'],'mission.task.checkpoint')
        self.assertEqual(a['complete_method'],'mission.task.complete')
        self.assertEqual(a['block_method'],'mission.task.block')
        self.assertFalse(a['chat_text_can_mark_done'])
        self.assertFalse(a['marker_can_mark_done_alone'])

    def test_workspace_and_publication_isolation(self):
        w=self.m['workspace']; p=self.m['publication']
        self.assertEqual(w['path_template'],'/home/kopiko/die-sessions/<task_id>')
        self.assertEqual(w['lifecycle_helper'],'bin/die_h01_worktree.py')
        self.assertEqual(w['protected_root'],'/srv/die')
        self.assertFalse(w['protected_root_engineering_mutation_allowed'])
        self.assertFalse(w['shared_mutable_worktree_allowed'])
        self.assertEqual(p['resources'],['income-os.repo-write','company-os.<task_id>'])
        self.assertTrue(p['acquire_immediately_before_remote_mutation'])
        self.assertTrue(p['release_in_finally'])
        self.assertFalse(p['session_owner_lease_is_repo_write_permission'])

    def test_marker_is_dispatch_bound_and_never_authority_alone(self):
        m=self.m['completion_marker']
        self.assertEqual(m['prefix'],'MC005_ARCHITECT_RESULT_')
        self.assertEqual(m['bound_to'],'dispatch_id')
        self.assertTrue(m['must_be_final_non_whitespace_line'])
        self.assertTrue(m['emit_only_after_mission_complete_ok'])
        self.assertFalse(m['emit_on_block'])
        self.assertFalse(m['emit_on_lease_loss'])
        self.assertEqual(m['authority'],'CORRELATION_ONLY')
        dispatch='AD-EXAMPLE-123456'
        self.assertEqual(m['prefix']+dispatch,'MC005_ARCHITECT_RESULT_AD-EXAMPLE-123456')

    def test_durable_result_schema_does_not_persist_owner_capability(self):
        result=self.s['$defs']['durable_result']
        props=set(result['properties'])
        self.assertFalse(props & {'mission_lease_token','leaseToken','review_token','reviewToken'})
        boot=self.s['$defs']['bootstrap']
        self.assertTrue(boot['properties']['mission_lease_token']['writeOnly'])
        forbidden={x.lower() for x in self.m['forbidden_persisted_keys']}
        for key in ('mission_lease_token','leasetoken','cookies','authorization','session_bytes'):
            self.assertIn(key,forbidden)

    def test_contract_keeps_implementation_tasks_downstream(self):
        self.assertEqual(self.m['downstream_tasks'],{
            'dispatcher':'H01-301','completion_detector':'H01-302','parallel_isolation':'H01-303',
            'two_worker_canary':'H01-304','graph_width_scaling':'H01-305'
        })
        self.assertEqual(self.m['implementation_status'],'CONTRACT_ONLY_NOT_DISPATCHER_IMPLEMENTATION')
        for phrase in ('no chat-memory-only completion','H01-301/302/303','Mission Control is the sole durable task/graph authority','MC005_ARCHITECT_RESULT_<dispatch_id>'):
            self.assertIn(phrase,self.d)

if __name__=='__main__': unittest.main()
