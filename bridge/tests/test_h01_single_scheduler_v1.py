import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company'/'company-os'/'die-h01'
sys.path.insert(0,str(H01/'engineering'))
import single_scheduler_guard as G
PROOF=json.loads((H01/'runtime'/'h01-single-scheduler-proof.v1.json').read_text())
GATEWAY=json.loads((H01/'runtime'/'h01-runtime-gateway-boundary.v1.json').read_text())
SUP=json.loads((H01/'runtime'/'h01-recovery-supervisor.v1.json').read_text())

class SingleSchedulerProofTests(unittest.TestCase):
 def ev(self,p=None,g=None,s=None): return G.evaluate(copy.deepcopy(p or PROOF),copy.deepcopy(g or GATEWAY),copy.deepcopy(s or SUP))
 def test_canonical_proof_passes(self):
  r=self.ev(); self.assertEqual(r['status'],'PASS'); self.assertEqual(r['business_scheduler'],'die-control/Mission Control'); self.assertEqual(r['competing_business_schedulers'],0); self.assertEqual(r['active_duplicate_dispatch_paths'],0)
 def test_linux_enabled_business_timer_fails_closed(self):
  p=copy.deepcopy(PROOF); p['legacy_linux']['enabled_business_timers']=['die-fa124-cluster-a.timer']
  with self.assertRaisesRegex(G.GuardError,'E_LINUX_TIMER_ENABLED'): self.ev(p=p)
 def test_windows_embedded_kanban_dispatch_fails_closed(self):
  p=copy.deepcopy(PROOF); p['legacy_windows']['income_operator_kanban_dispatch_in_gateway']=True
  with self.assertRaisesRegex(G.GuardError,'E_WIN_INCOME_KANBAN_DISPATCH'): self.ev(p=p)
 def test_windows_proactive_operator_must_remain_paused(self):
  p=copy.deepcopy(PROOF); p['legacy_windows']['proactive_operator_job_status']='active'
  with self.assertRaisesRegex(G.GuardError,'E_WIN_PROACTIVE_OPERATOR'): self.ev(p=p)
 def test_live_duplicate_source_or_lease_or_attempt_fails(self):
  for key in ('active_source_node_duplicates','active_task_multi_lease','active_task_duplicate_open_owner_attempts'):
   p=copy.deepcopy(PROOF); p['control_plane']['live_db'][key]=1
   with self.subTest(key=key), self.assertRaisesRegex(G.GuardError,'E_DB_DUPLICATE'): self.ev(p=p)
 def test_historical_terminal_anomaly_without_lease_is_allowed(self):
  p=copy.deepcopy(PROOF); p['control_plane']['live_db']['historical_nonactive_anomalies']=[{'task_id':'OLD','task_status':'CANCELLED','active_lease':False}]
  self.assertEqual(self.ev(p=p)['status'],'PASS')
 def test_historical_active_or_leased_anomaly_is_rejected(self):
  for row in ({'task_status':'RUNNING','active_lease':False},{'task_status':'CANCELLED','active_lease':True}):
   p=copy.deepcopy(PROOF); p['control_plane']['live_db']['historical_nonactive_anomalies']=[row]
   with self.assertRaises(G.GuardError): self.ev(p=p)
 def test_gateway_replay_contract_regression_fails(self):
  g=copy.deepcopy(GATEWAY); g['durability']['duplicate_same_dispatch_same_digest']='START_NEW_EXECUTION'
  with self.assertRaisesRegex(G.GuardError,'E_REPLAY_SAME'): self.ev(g=g)
 def test_gateway_terminal_result_must_remain_immutable(self):
  g=copy.deepcopy(GATEWAY); g['durability']['terminal_result_immutable']=False
  with self.assertRaisesRegex(G.GuardError,'E_TERMINAL_MUTABLE'): self.ev(g=g)
 def test_supervisor_cannot_become_scheduler(self):
  s=copy.deepcopy(SUP); s['authority']['supervisor_is_scheduler']=True
  with self.assertRaisesRegex(G.GuardError,'E_SUPERVISOR_SCHEDULER'): self.ev(s=s)
 def test_graph_marks_h01_016_done_but_h01_200_stays_blocked_until_other_dependencies(self):
  graph=json.loads((H01/'die-h01-task-graph.v1.json').read_text()); by={t['id']:t for t in graph['tasks']}
  self.assertEqual(by['H01-016']['status'],'DONE'); self.assertEqual(by['H01-027']['status'],'BLOCKED'); self.assertEqual(by['H01-109']['status'],'BLOCKED'); self.assertEqual(by['H01-200']['status'],'BLOCKED')
 def test_proof_contains_no_mission_lease_capability(self):
  raw=json.dumps(PROOF); self.assertNotIn('mission_lease_token',raw)
  def values(v):
   if isinstance(v,dict):
    for x in v.values(): yield from values(x)
   elif isinstance(v,list):
    for x in v: yield from values(x)
   elif isinstance(v,str): yield v
  self.assertFalse(any(v.startswith('lt_') and len(v)>20 for v in values(PROOF)))

if __name__=='__main__': unittest.main()
