import importlib.util, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENG=ROOT/'company'/'company-os'/'die-h01'/'engineering'
sys.path.insert(0,str(ENG))
import architect_browser_dispatcher as D
import architect_worker_completion as C

class FakeSession:
    instances=[]
    def __init__(self,binding):
        self.binding=binding; self.closed=False; self.obs={'status':'OBSERVATION','assistant_nodes':1,'assistant_chars':10,'stop_visible':False,'composer_ready':True,'marker_found':False,'marker_candidates':[]}
        self.alive=True; self.__class__.instances.append(self)
    def open_and_submit(self,bootstrap): self.bootstrap=bootstrap; return {'status':'SUBMITTED','browser_pid':111,'debug_host':'127.0.0.1','debug_port':9222,'url':'https://chatgpt.com'}
    def poll_observation(self): return dict(self.obs)
    def is_alive(self): return self.alive
    def close(self): self.closed=True; self.alive=False; return True

class Clock:
    def __init__(self): self.m=0.0; self.e=1_000.0
    def mono(self): return self.m
    def epoch(self): return self.e+self.m
    def sleep(self,s): self.m+=s

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); FakeSession.instances.clear()
        self.req=D.DispatchRequest('P','H01-999','chatgpt-architect','ephemeral-test-capability','AD-TEST-123')
        self.binding=D.BrowserBinding('h01-eng-a','/fake/brave',str(self.root/'udd'),'Default','node','driver',str(self.root/'leases'))
        self.policy=C.CompletionPolicy(poll_seconds=.25,stall_seconds=300,mission_error_grace_seconds=60,marker_reconcile_seconds=30,minimum_stall_seconds=300)
    def tearDown(self): self.tmp.cleanup()

    def task(self,status='RUNNING',*,progress=10,lease=True,ended=False,result=False,dispatch='AD-TEST-123'):
        cps=[]
        if progress is not None:
            payload={'result':{'ok':True},'artifacts':[{'path':'x'}]} if result else {}
            cps=[{'id':7,'principal_id':'chatgpt-architect','progress':progress,'summary':'durable','payload':payload,'created_at':'2099-01-01T00:00:01Z'}]
        attempt={'task_id':'H01-999','attempt_no':1,'owner_principal_id':'chatgpt-architect','dispatch_id':dispatch,'status':'COMPLETED' if ended else 'PROTOCOL_ACTIVE','ended_at':'2099-01-01T00:00:02Z' if ended else None,'updated_at':'2099-01-01T00:00:01Z'}
        return {'id':'H01-999','owner_principal_id':'chatgpt-architect','status':status,'lease':{'heartbeat_at':'2099-01-01T00:00:01Z','expires_at':'2099-01-01T01:00:00Z'} if lease else None,'owner_attempts':[attempt],'checkpoints':cps,'blocked_reason':'because'}

    def test_rendered_done_text_never_completes(self):
        tr=C.ProgressTracker(0); obs={'rendered_text':'DONE all green','assistant_nodes':1,'assistant_chars':20,'composer_ready':True,'stop_visible':False,'marker_found':False,'marker_candidates':[]}
        d=C.evaluate_snapshot(self.task(),self.req,obs,tr,self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)
        self.assertEqual((d['action'],d['reason']),('WAIT','ACTIVE_PROGRESS_AWARE'))

    def test_marker_alone_waits_for_durable_protocol(self):
        tr=C.ProgressTracker(0); obs={'assistant_nodes':2,'assistant_chars':80,'composer_ready':True,'stop_visible':False,'marker_found':True,'marker_candidates':[self.req.marker]}
        d1=C.evaluate_snapshot(self.task(),self.req,obs,tr,self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)
        d2=C.evaluate_snapshot(self.task(),self.req,obs,tr,self.policy,browser_alive=True,now_monotonic=31,now_epoch=1031)
        self.assertEqual(d1['action'],'WAIT'); self.assertEqual((d2['action'],d2['reason']),('WAIT','MARKER_AHEAD_OF_PROTOCOL'))

    def test_ui_progress_and_generating_control_prevent_stall(self):
        tr=C.ProgressTracker(0); t=self.task()
        C.evaluate_snapshot(t,self.req,{'assistant_nodes':1,'assistant_chars':10,'stop_visible':False},tr,self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)
        d=C.evaluate_snapshot(t,self.req,{'assistant_nodes':1,'assistant_chars':11,'stop_visible':False},tr,self.policy,browser_alive=True,now_monotonic=301,now_epoch=1301)
        self.assertEqual(d['action'],'WAIT')
        d=C.evaluate_snapshot(t,self.req,{'assistant_nodes':1,'assistant_chars':11,'stop_visible':True},tr,self.policy,browser_alive=True,now_monotonic=700,now_epoch=1700)
        self.assertEqual(d['action'],'WAIT')

    def test_true_inactivity_becomes_recovery_not_done(self):
        tr=C.ProgressTracker(0); t=self.task(); obs={'assistant_nodes':1,'assistant_chars':10,'stop_visible':False}
        C.evaluate_snapshot(t,self.req,obs,tr,self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)
        d=C.evaluate_snapshot(t,self.req,obs,tr,self.policy,browser_alive=True,now_monotonic=301,now_epoch=1301)
        self.assertEqual((d['action'],d['reason']),('RECOVERY_REQUIRED','STALLED_NO_DURABLE_OR_UI_PROGRESS'))

    def test_browser_exit_auth_and_expired_lease_recover_not_complete(self):
        tr=C.ProgressTracker(0); t=self.task()
        self.assertEqual(C.evaluate_snapshot(t,self.req,None,tr,self.policy,browser_alive=False,now_monotonic=0,now_epoch=1000)['reason'],'BROWSER_EXITED')
        self.assertEqual(C.evaluate_snapshot(t,self.req,{'auth_required':True},C.ProgressTracker(0),self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)['reason'],'AUTH_REQUIRED')
        t['lease']['expires_at']='1970-01-01T00:00:01Z'
        self.assertEqual(C.evaluate_snapshot(t,self.req,None,C.ProgressTracker(0),self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)['reason'],'LEASE_EXPIRED')

    def test_done_ingests_final_checkpoint_even_without_marker(self):
        t=self.task('DONE',progress=100,lease=False,ended=True,result=True)
        r=C.ingest_terminal_result(t,self.req,{'marker_found':False,'marker_candidates':[]})
        self.assertEqual(r['classification'],'SUCCESS'); self.assertEqual(r['result'],{'ok':True}); self.assertEqual(r['marker_correlation'],'MISSING'); self.assertEqual(r['completion_authority'],'MISSION_CONTROL_DURABLE_STATE')

    def test_verifying_and_blocked_are_distinct_terminal_outcomes(self):
        v=C.ingest_terminal_result(self.task('VERIFYING',progress=100,lease=False,ended=True,result=True),self.req,None)
        b=C.ingest_terminal_result(self.task('BLOCKED',progress=None,lease=False,ended=True),self.req,None)
        self.assertEqual(v['classification'],'REVIEW_PENDING'); self.assertEqual(b['classification'],'BLOCKED'); self.assertEqual(b['blocked_reason'],'because')

    def test_done_without_final_result_fails_closed(self):
        with self.assertRaisesRegex(C.CompletionError,'E_DURABLE_RESULT_MISSING'):
            C.ingest_terminal_result(self.task('DONE',progress=90,lease=False,ended=True),self.req,None)

    def test_stale_dispatch_fails_closed(self):
        with self.assertRaisesRegex(C.CompletionError,'E_STALE_DISPATCH'):
            C.evaluate_snapshot(self.task(dispatch='AD-OTHER'),self.req,None,C.ProgressTracker(0),self.policy,browser_alive=True,now_monotonic=0,now_epoch=1000)

    def test_result_journal_is_idempotent_and_secret_fail_closed(self):
        j=C.ResultJournal(self.root/'results')
        record={'dispatch_id':self.req.dispatch_id,'status':'PASS','nested':{'ok':True}}
        s1,p1=j.commit(record); s2,p2=j.commit(record)
        self.assertEqual((s1,s2,p1,p2),('CREATED','UNCHANGED',p1,p1))
        with self.assertRaisesRegex(C.CompletionError,'E_RESULT_SECRET_FIELD'):
            j.commit({'dispatch_id':'AD-X','nested':{'mission_lease_token':'secret'}})

    def test_policy_rejects_aggressive_stall_cut(self):
        with self.assertRaisesRegex(C.CompletionError,'E_POLICY_STALL_TOO_AGGRESSIVE'):
            C.CompletionPolicy(stall_seconds=299)

    def test_monitor_terminal_ingests_then_closes_and_releases(self):
        clock=Clock(); journal=C.ResultJournal(self.root/'results')
        sequence=[self.task(),self.task('DONE',progress=100,lease=False,ended=True,result=True)]
        def get(): return {'task':sequence.pop(0) if len(sequence)>1 else sequence[0]}
        policy=C.CompletionPolicy(poll_seconds=1,stall_seconds=300,mission_error_grace_seconds=60,marker_reconcile_seconds=30,minimum_stall_seconds=300)
        r=C.monitor_worker(self.req,self.binding,get,result_journal=journal,policy=policy,session_factory=FakeSession,monotonic=clock.mono,epoch=clock.epoch,sleep=clock.sleep)
        self.assertEqual(r['status'],'TERMINAL_INGESTED'); self.assertEqual(r['result']['classification'],'SUCCESS')
        self.assertTrue(r['browser_closed']); self.assertTrue(r['profile_lease_released']); self.assertEqual(r['journal_status'],'CREATED')
        self.assertTrue(FakeSession.instances[-1].closed); self.assertFalse((self.root/'leases'/'h01-eng-a.lock').exists())
        self.assertNotIn(self.req.lease_token,(self.root/'results'/f'{self.req.dispatch_id}.json').read_text())

    def test_monitor_stall_returns_recovery_without_scheduler_action(self):
        clock=Clock(); t=self.task()
        def get(): return {'task':t}
        policy=C.CompletionPolicy(poll_seconds=1,stall_seconds=2,mission_error_grace_seconds=60,marker_reconcile_seconds=1,minimum_stall_seconds=0)
        r=C.monitor_worker(self.req,self.binding,get,policy=policy,session_factory=FakeSession,monotonic=clock.mono,epoch=clock.epoch,sleep=clock.sleep)
        self.assertEqual(r['status'],'RECOVERY_REQUIRED'); self.assertEqual(r['recovery']['reason'],'STALLED_NO_DURABLE_OR_UI_PROGRESS')
        self.assertFalse(r['completion_inferred']); self.assertFalse(r['scheduler_action_taken']); self.assertTrue(r['browser_closed']); self.assertTrue(r['profile_lease_released'])

    def test_mission_observer_outage_does_not_cut_active_generating_ui(self):
        class GeneratingSession(FakeSession):
            def __init__(self,binding):
                super().__init__(binding); self.obs['stop_visible']=True
        clock=Clock(); calls={'n':0}
        done=self.task('DONE',progress=100,lease=False,ended=True,result=True)
        def get():
            calls['n']+=1
            if calls['n']<=3: raise RuntimeError('temporary mission read outage')
            return {'task':done}
        policy=C.CompletionPolicy(poll_seconds=30,stall_seconds=300,mission_error_grace_seconds=60,marker_reconcile_seconds=30,minimum_stall_seconds=300)
        r=C.monitor_worker(self.req,self.binding,get,policy=policy,session_factory=GeneratingSession,monotonic=clock.mono,epoch=clock.epoch,sleep=clock.sleep)
        self.assertEqual(r['status'],'TERMINAL_INGESTED'); self.assertGreaterEqual(clock.m,90); self.assertTrue(r['browser_closed'])

    def test_driver_emits_metadata_only_progress_observation(self):
        src=(ENG/'architect_browser_cdp_driver.mjs').read_text()
        for required in ('OBSERVATION','assistant_nodes','assistant_chars','stop_visible','marker_found','marker_candidates','auth_required'):
            self.assertIn(required,src)
        for forbidden in ('Network.getAllCookies','Storage.getCookies','document.cookie','response_text'):
            self.assertNotIn(forbidden,src)

if __name__=='__main__': unittest.main()
