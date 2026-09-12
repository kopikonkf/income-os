import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ENG=ROOT/'company'/'company-os'/'die-h01'/'engineering'
sys.path.insert(0,str(ENG))
import recovery_supervisor as R

class RecoverySupervisorTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.ledger=R.RecoveryLedger(Path(self.t.name)/'ledger.json'); self.sup=R.RecoverySupervisor(self.ledger)
 def tearDown(self): self.t.cleanup()
 def inc(self,**kw):
  v={'schema':R.SCHEMA,'incident_id':'INC-001','fingerprint':'fp-abc','level':'L1','component_id':'factory.cluster-b-broker','requested_playbook':R.L1_PLAYBOOK,'ownership':{'status':'UNAMBIGUOUS'},'reconciliation':{'active_business_work':False,'same_work_reconciled_safe':True,'ambiguous_external_side_effect':False,'browser_job_active':False,'udd_lock_held':False}}
  v.update(kw); return v
 def test_l0_reobserve_is_nonmutating(self):
  d=self.sup.evaluate(self.inc(level='L0',requested_playbook='L0_REOBSERVE'),now=1000); self.assertEqual(d['decision'],'ALLOW_L0'); self.assertFalse(d['mutation_authorized']); self.assertFalse(d['scheduler_authorized'])
  r=self.sup.execute(self.inc(level='L0',requested_playbook='L0_REOBSERVE'),d,now=1000); self.assertFalse(r['mutation_performed']); self.assertFalse(r['business_work_generated'])
 def test_hidden_scheduler_fields_fail_closed(self):
  i=self.inc(); i['provider_selection']='qwen'
  with self.assertRaisesRegex(R.SupervisorError,'E_HIDDEN_AUTHORITY_FIELD'): self.sup.evaluate(i)
 def test_l1_allowlisted_service_only(self):
  d=self.sup.evaluate(self.inc(),now=1000); self.assertEqual(d['decision'],'ALLOW_L1'); self.assertEqual(d['systemd_service'],'die-muxia-cluster-b.service')
  d=self.sup.evaluate(self.inc(component_id='unknown.service'),now=1000); self.assertEqual(d['decision'],'ESCALATE'); self.assertEqual(d['reason'],'COMPONENT_NOT_ALLOWLISTED')
 def test_mission_control_is_observe_only(self):
  d=self.sup.evaluate(self.inc(component_id='mission-control'),now=1000); self.assertEqual(d['decision'],'ESCALATE'); self.assertEqual(d['reason'],'REMOTE_CONTROL_PLANE_RECOVERY_NOT_H01_AUTHORITY')
 def test_ambiguous_ownership_quarantines(self):
  i=self.inc(); i['ownership']['status']='AMBIGUOUS'; d=self.sup.evaluate(i,now=1000); self.assertEqual(d['decision'],'QUARANTINE')
 def test_active_work_requires_safe_reconciliation(self):
  i=self.inc(); i['reconciliation']['active_business_work']=True; i['reconciliation']['same_work_reconciled_safe']=False
  self.assertEqual(self.sup.evaluate(i,now=1000)['reason'],'ACTIVE_WORK_NOT_RECONCILED')
 def test_browser_owner_requires_no_active_job_or_udd_lock(self):
  i=self.inc(component_id='browser.cluster-a-owner'); i['reconciliation']['udd_lock_held']=True
  self.assertEqual(self.sup.evaluate(i,now=1000)['reason'],'BROWSER_OWNERSHIP_ACTIVE')
 def test_recurrence_after_l1_success_escalates(self):
  self.ledger.append({'ts':900,'fingerprint':'fp-abc','level':'L1','phase':'RESULT','success':True})
  d=self.sup.evaluate(self.inc(),now=1000); self.assertEqual(d['decision'],'ESCALATE'); self.assertEqual(d['reason'],'RECURRENT_AFTER_L1_SUCCESS')
 def test_l1_attempt_budget_is_durable_and_bounded(self):
  for ts in (900,950): self.ledger.append({'ts':ts,'fingerprint':'fp-abc','level':'L1','phase':'ATTEMPT'})
  d=self.sup.evaluate(self.inc(),now=1000); self.assertEqual(d['reason'],'L1_ATTEMPT_BUDGET_EXHAUSTED')
 def test_execute_uses_exact_systemd_argv_and_verifies(self):
  calls=[]
  def run(argv):
   calls.append(argv); return (0,'active\n','') if argv[:2]==['systemctl','is-active'] else (0,'','')
  i=self.inc(); d=self.sup.evaluate(i,now=1000); r=self.sup.execute(i,d,runner=run,now=1000)
  self.assertEqual(calls,[['sudo','-n','systemctl','restart','die-muxia-cluster-b.service'],['systemctl','is-active','die-muxia-cluster-b.service']]); self.assertTrue(r['mutation_performed']); self.assertFalse(r['business_work_generated'])
  events=self.ledger._load()['events']; self.assertEqual([e['phase'] for e in events],['ATTEMPT','RESULT'])
 def test_failed_verification_never_claims_recovery(self):
  def run(argv): return (0,'inactive\n','')
  i=self.inc(); d=self.sup.evaluate(i,now=1000)
  with self.assertRaisesRegex(R.SupervisorError,'E_L1_VERIFY_FAILED'): self.sup.execute(i,d,runner=run,now=1000)
 def test_l2_l3_never_execute_local_recovery(self):
  for level in ('L2','L3'): self.assertEqual(self.sup.evaluate(self.inc(level=level),now=1000)['decision'],'ESCALATE')
 def test_allowlist_excludes_legacy_hermes_and_opencode(self):
  vals=set(R.L1_SYSTEMD_ALLOWLIST.values()); self.assertNotIn('die-hermes-gateway.service',vals); self.assertNotIn('die-opencode-web.service',vals)


 def test_runtime_contract_has_no_hidden_scheduler(self):
  r=json.loads((ROOT/'company'/'company-os'/'die-h01'/'runtime'/'h01-recovery-supervisor.v1.json').read_text())
  self.assertFalse(r['authority']['supervisor_is_scheduler']); self.assertFalse(r['execution_model']['background_poll_loop']); self.assertFalse(r['execution_model']['queue_feeder']); self.assertFalse(r['execution_model']['graph_reader'])
  vals=set(r['l1_systemd_allowlist'].values()); self.assertNotIn('die-hermes-gateway.service',vals); self.assertNotIn('die-opencode-web.service',vals)
 def test_live_observation_is_sanitized_and_read_only(self):
  o=json.loads((ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-015'/'live-observation.sanitized.json').read_text())
  self.assertEqual(o['schema'],R.OBS_SCHEMA); self.assertTrue(all(v['state']=='active' for v in o['services'].values())); self.assertTrue(all(v['reachable'] for v in o['factories'].values()))
  self.assertEqual(o['factories']['cluster-a']['active_leases'],0); self.assertEqual(o['factories']['cluster-b']['active_leases'],0)
  self.assertFalse(o['safety']['cookies_read']); self.assertFalse(o['safety']['tokens_read']); self.assertFalse(o['safety']['business_work_generated'])
 def test_l0_acceptance_fixture_performs_no_mutation(self):
  base=ROOT/'company'/'company-os'/'die-h01'/'fixtures'/'h01-015'; d=json.loads((base/'l0-reobserve-decision.json').read_text()); r=json.loads((base/'l0-reobserve-result.json').read_text())
  self.assertEqual(d['decision'],'ALLOW_L0'); self.assertFalse(d['mutation_authorized']); self.assertFalse(d['scheduler_authorized']); self.assertEqual(r['status'],'PASS'); self.assertFalse(r['mutation_performed']); self.assertFalse(r['business_work_generated'])

if __name__=='__main__': unittest.main()
