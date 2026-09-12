import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MOD=ROOT/'company'/'company-os'/'die-h01'/'engineering'/'architect_browser_dispatcher.py'
DRIVER=ROOT/'company'/'company-os'/'die-h01'/'engineering'/'architect_browser_cdp_driver.mjs'
SPEC=importlib.util.spec_from_file_location('h01_arch_dispatch',MOD)
M=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=M; SPEC.loader.exec_module(M)

class FakeSession:
    instances=[]
    def __init__(self,binding):
        self.binding=binding; self.bootstrap=None; self.closed=False; self.dispatcher_finally=None
        self.__class__.instances.append(self)
    def open_and_submit(self,bootstrap):
        self.bootstrap=bootstrap
        return {'status':'SUBMITTED','browser_pid':1234,'debug_host':'127.0.0.1','debug_port':9222,'url':'https://chatgpt.com'}
    def close(self): self.closed=True; return True

class FailingSession(FakeSession):
    def open_and_submit(self,bootstrap): self.bootstrap=bootstrap; raise M.DispatchError('E_TEST_SUBMIT')

class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); FakeSession.instances.clear()
        self.req=M.DispatchRequest('REFACTOR DIE LINUX - DIE-H01 - SVG Isolated Asset','H01-999','chatgpt-architect','lt_SECRET_NOT_PERSIST','AD-TEST-ABC123')
        self.binding=M.BrowserBinding('h01-eng-architect-a','/fake/brave',str(self.root/'udd'),'Default','node',str(DRIVER),str(self.root/'leases'))
    def tearDown(self): self.tmp.cleanup()

    def checkpoint_task(self):
        return {'task':{'id':self.req.task_id,'owner_principal_id':self.req.principal_id,'status':'RUNNING','checkpoints':[{'id':42,'principal_id':self.req.principal_id,'progress':20}]}}

    def test_bootstrap_exact_authority_and_marker(self):
        text=M.build_bootstrap(self.req)
        self.assertIn('FIRST: recover relevant cross-session context',text)
        self.assertIn('THEN call mission.task.get',text)
        self.assertIn('Do not rely on this bootstrap for task details',text)
        self.assertIn('mission.task.checkpoint / mission.task.complete / mission.task.block',text)
        self.assertTrue(text.endswith('MC005_ARCHITECT_RESULT_AD-TEST-ABC123'))

    def test_dispatch_leases_submits_observes_checkpoint_closes_and_releases(self):
        receipt=M.dispatch_canary(self.req,self.binding,self.checkpoint_task,session_factory=FakeSession,poll_seconds=.001,observe_timeout=.1)
        s=FakeSession.instances[-1]
        self.assertTrue(s.closed)
        self.assertEqual(receipt['durable_evidence']['kind'],'CHECKPOINT')
        self.assertTrue(receipt['browser_closed']); self.assertTrue(receipt['profile_lease_released'])
        self.assertFalse((self.root/'leases'/'h01-eng-architect-a.lock').exists())
        self.assertIn(self.req.marker,s.bootstrap)
        self.assertNotIn(self.req.lease_token,json.dumps(receipt))
        self.assertEqual(receipt['canary_only_until'],'H01-302')

    def test_terminal_state_is_valid_durable_evidence(self):
        def state(): return {'task':{'id':self.req.task_id,'owner_principal_id':self.req.principal_id,'status':'DONE','checkpoints':[]}}
        receipt=M.dispatch_canary(self.req,self.binding,state,session_factory=FakeSession,poll_seconds=.001,observe_timeout=.1)
        self.assertEqual(receipt['durable_evidence'],{'kind':'TERMINAL','status':'DONE','checkpoint_count':0})

    def test_no_durable_evidence_times_out_but_closes_and_releases(self):
        def empty(): return {'task':{'id':self.req.task_id,'owner_principal_id':self.req.principal_id,'status':'RUNNING','checkpoints':[]}}
        with self.assertRaisesRegex(M.DispatchError,'E_DURABLE_EVIDENCE_TIMEOUT'):
            M.dispatch_canary(self.req,self.binding,empty,session_factory=FakeSession,poll_seconds=.001,observe_timeout=.005)
        self.assertTrue(FakeSession.instances[-1].closed)
        self.assertFalse((self.root/'leases'/'h01-eng-architect-a.lock').exists())

    def test_submit_failure_still_closes_and_releases(self):
        with self.assertRaisesRegex(M.DispatchError,'E_TEST_SUBMIT'):
            M.dispatch_canary(self.req,self.binding,self.checkpoint_task,session_factory=FailingSession,poll_seconds=.001,observe_timeout=.1)
        self.assertTrue(FailingSession.instances[-1].closed)
        self.assertFalse((self.root/'leases'/'h01-eng-architect-a.lock').exists())

    def test_profile_lease_is_exclusive_and_secret_free(self):
        a=M.ProfileLease(self.binding.lease_root,self.binding.resource_id,ttl_seconds=60)
        a.acquire(task_id=self.req.task_id,dispatch_id=self.req.dispatch_id,principal_id=self.req.principal_id)
        state=(Path(self.binding.lease_root)/(self.binding.resource_id+'.lock')/'lease.json').read_text()
        self.assertNotIn(self.req.lease_token,state)
        b=M.ProfileLease(self.binding.lease_root,self.binding.resource_id,ttl_seconds=60)
        with self.assertRaisesRegex(M.DispatchError,'E_PROFILE_BUSY'): b.acquire(task_id='H01-X',dispatch_id='AD-X',principal_id='other')
        a.release()

    def test_mission_identity_mismatch_fails_closed(self):
        bad={'task':{'id':'H01-OTHER','owner_principal_id':self.req.principal_id,'status':'DONE','checkpoints':[]}}
        with self.assertRaisesRegex(M.DispatchError,'E_MISSION_IDENTITY_MISMATCH'):
            M.dispatch_canary(self.req,self.binding,lambda:bad,session_factory=FakeSession,poll_seconds=.001,observe_timeout=.1)
        self.assertTrue(FakeSession.instances[-1].closed)

    def test_cdp_driver_is_loopback_ui_only_and_closes_browser(self):
        s=DRIVER.read_text(encoding='utf-8')
        self.assertIn('--remote-debugging-address=127.0.0.1',s)
        self.assertIn('https://chatgpt.com/',s)
        self.assertIn("await cdp?.send('Browser.close'",s)
        self.assertIn("document.querySelector('#prompt-textarea, textarea, [contenteditable=",s)
        for forbidden in ('Network.getAllCookies','Storage.getCookies','document.cookie','/backend-api/'):
            self.assertNotIn(forbidden,s)

if __name__=='__main__': unittest.main()
