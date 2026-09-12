from __future__ import annotations
import importlib.util, json, subprocess, tempfile, time, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'company/company-os/die-h01'
MOD=H/'engineering/brave_round_robin_scheduler.py'
spec=importlib.util.spec_from_file_location('rr',MOD); rr=importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(); self.root=Path(self.td.name)
        profiles=[]
        for n in range(1,101):
            ui=(n-1)//5+1; profiles.append({'udd_id':f'h01-web-s{ui:02d}','udd_index':ui,'slot':(n-1)%5+1,'profile_id':f'h01-web-p{n:03d}','profile_number':n,'user_data_dir':str(self.root/f's{ui:02d}'),'profile_directory':f'h01-web-p{n:03d}','cdp_host':'127.0.0.1','cdp_port':9200+n,'state':'PROVISIONED_NOT_AUTHENTICATED'})
        self.manifest=self.root/'manifest.json'; self.manifest.write_text(json.dumps({'schema':'die.h01.brave-fabric.host-local.v1','topology':{'udd_count':20,'profiles_per_udd':5,'profile_count':100,'max_active_per_udd':1},'profiles':profiles}))
        self.policy=self.root/'policy.json'; self.set_policy([('a','READY'),('b','READY')],cap=5)
        self.ready=self.root/'ready.json'; self.set_ready([])
        self.state=self.root/'state.json'; self.runtime=self.root/'runtime'
    def tearDown(self): self.td.cleanup()
    def set_policy(self,providers,cap=5):
        self.policy.write_text(json.dumps({'schema':'die.h01.brave-round-robin-policy.v1','global_max_live_udd_owners':cap,'founder_approved_max_live_udd_owners':5,'absolute_max_udd_owners':20,'providers':[{'provider_id':p,'state':s} for p,s in providers]}))
    def set_ready(self,pids):
        rows={f'h01-web-p{i:03d}':{'state':'READY' if f'h01-web-p{i:03d}' in pids else 'NOT_READY'} for i in range(1,101)}
        self.ready.write_text(json.dumps({'schema':'die.h01.brave-profile-readiness.v1','profiles':rows}))
    def s(self): return rr.Scheduler(self.manifest,self.policy,self.ready,self.state,self.runtime)
    def complete(self,s,lease,cooldown=0):
        s.claim_dispatch(lease['lease_id'],lease['lease_token']); return s.complete(lease['lease_id'],lease['lease_token'],'SUCCEEDED',cooldown)

    def test_canon_policy_and_task(self):
        g=json.loads((H/'die-h01-task-graph.v1.json').read_text()); by={x['id']:x for x in g['tasks']}
        self.assertEqual(by['H01-023']['status'],'DONE'); self.assertEqual(by['H01-025']['status'],'DONE')
        p=json.loads((H/'runtime/h01-brave-round-robin-scheduler.v1.json').read_text())
        self.assertEqual(p['global_max_live_udd_owners'],5); self.assertEqual(p['absolute_max_udd_owners'],20)
        self.assertEqual([x['provider_id'] for x in p['providers'] if x['state']=='READY'],['claude','chatgpt','qwen','gemini','manus','copilot'])

    def test_profile_and_provider_round_robin_inside_one_udd(self):
        self.set_ready(['h01-web-p001','h01-web-p002','h01-web-p003']); s=self.s(); got=[]
        for i in range(4):
            x=s.acquire(dispatch_id=f'd{i}',job_id=f'j{i}')['lease']; got.append((x['profile_id'],x['provider_id'])); self.complete(s,x)
        self.assertEqual(got,[('h01-web-p001','a'),('h01-web-p002','b'),('h01-web-p003','a'),('h01-web-p001','b')])

    def test_same_udd_sibling_overlap_is_refused(self):
        self.set_ready(['h01-web-p001','h01-web-p002']); s=self.s(); first=s.acquire(dispatch_id='d1',job_id='j1')['lease']
        with self.assertRaisesRegex(rr.SchedulerError,'E_NO_ELIGIBLE_UDD'): s.acquire(dispatch_id='d2',job_id='j2')
        self.complete(s,first)

    def test_multi_udd_concurrency_is_allowed(self):
        self.set_ready(['h01-web-p001','h01-web-p006']); s=self.s(); a=s.acquire(dispatch_id='d1',job_id='j1')['lease']; b=s.acquire(dispatch_id='d2',job_id='j2')['lease']
        self.assertEqual({a['udd_id'],b['udd_id']},{'h01-web-s01','h01-web-s02'}); self.assertNotEqual(a['profile_id'],b['profile_id'])
        self.complete(s,a); self.complete(s,b)

    def test_policy_cannot_exceed_founder_approved_ceiling(self):
        self.set_policy([('a','READY')],cap=8)
        with self.assertRaisesRegex(rr.SchedulerError,'E_POLICY_CAP'): self.s().status()

    def test_global_admission_cap_five(self):
        self.set_ready([f'h01-web-p{i:03d}' for i in (1,6,11,16,21,26)]); s=self.s(); leases=[]
        for i in range(5): leases.append(s.acquire(dispatch_id=f'd{i}',job_id=f'j{i}')['lease'])
        with self.assertRaisesRegex(rr.SchedulerError,'E_GLOBAL_ADMISSION'): s.acquire(dispatch_id='d5',job_id='j5')
        for x in leases:self.complete(s,x)

    def test_exactly_once_dispatch_claim_and_terminal_dedupe(self):
        self.set_ready(['h01-web-p001']); s=self.s(); x=s.acquire(dispatch_id='stable-d',job_id='j')['lease']
        self.assertTrue(s.claim_dispatch(x['lease_id'],x['lease_token'])['dispatch_authorized'])
        self.assertFalse(s.claim_dispatch(x['lease_id'],x['lease_token'])['dispatch_authorized'])
        s.complete(x['lease_id'],x['lease_token'],'SUCCEEDED')
        again=s.acquire(dispatch_id='stable-d',job_id='j'); self.assertEqual(again['status'],'ALREADY_TERMINAL'); self.assertFalse(again['dispatch_authorized'])

    def test_preferred_provider_is_honored_and_fail_closed(self):
        self.set_ready(['h01-web-p001']); s=self.s()
        x=s.acquire(dispatch_id='pref-b',job_id='j',preferred_provider='b')['lease']; self.assertEqual(x['provider_id'],'b'); self.complete(s,x,60)
        with self.assertRaisesRegex(rr.SchedulerError,'E_PROVIDER_NOT_ELIGIBLE'): s.acquire(dispatch_id='pref-b2',job_id='j2',preferred_provider='b')
        with self.assertRaisesRegex(rr.SchedulerError,'E_PROVIDER_UNKNOWN'): s.acquire(dispatch_id='pref-x',job_id='j3',preferred_provider='x')

    def test_provider_cooldown_skips_provider_until_eligible(self):
        self.set_ready(['h01-web-p001']); s=self.s(); a=s.acquire(dispatch_id='d1',job_id='j1')['lease']; self.assertEqual(a['provider_id'],'a'); self.complete(s,a,60)
        b=s.acquire(dispatch_id='d2',job_id='j2')['lease']; self.assertEqual(b['provider_id'],'b'); self.complete(s,b)
        c=s.acquire(dispatch_id='d3',job_id='j3')['lease']; self.assertEqual(c['provider_id'],'b'); self.complete(s,c)

    def test_runtime_udd_mutex_is_respected(self):
        self.set_ready(['h01-web-p001']); self.runtime.mkdir(); lock=self.runtime/'h01-web-s01.lock'
        proc=subprocess.Popen(['flock',str(lock),'sleep','2'])
        try:
            time.sleep(.15)
            with self.assertRaisesRegex(rr.SchedulerError,'E_NO_ELIGIBLE_UDD'): self.s().acquire(dispatch_id='d',job_id='j')
        finally: proc.terminate(); proc.wait(timeout=3)

    def test_current_readiness_does_not_fake_100_authenticated_profiles(self):
        r=json.loads((H/'fixtures/h01-026/profile-readiness.current.json').read_text())['profiles']
        self.assertEqual([k for k,v in r.items() if v['state']=='READY'],['h01-web-p001'])

if __name__=='__main__': unittest.main()
