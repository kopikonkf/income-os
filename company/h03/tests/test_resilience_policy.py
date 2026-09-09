import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'resilience_policy.py'
spec=importlib.util.spec_from_file_location('resilience_policy',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class ResiliencePolicyTests(unittest.TestCase):
    def test_backpressure_is_visible_at_queue_limit(self):
        p=mod.default_policy(queue_limit=10)
        self.assertEqual(mod.backpressure_action(queue_depth=10,policy=p)['action'],'PAUSE_NEW_DISPATCH')
        self.assertEqual(mod.backpressure_action(queue_depth=9,policy=p)['action'],'ACCEPT_DISPATCH')
    def test_rate_limit_with_alternative_falls_back_and_circuit_breaks(self):
        d=mod.decide_failure(failure_code='RATE_LIMITED',attempt=1,max_attempts=3,alternative_slots=1,policy=mod.default_policy())
        self.assertEqual(d['action'],'FALLBACK_ALTERNATE_WORKER'); self.assertTrue(d['circuit_break'])
    def test_auth_without_alternative_waits_for_capability_recovery(self):
        d=mod.decide_failure(failure_code='AUTH_REQUIRED',attempt=1,max_attempts=3,alternative_slots=0,policy=mod.default_policy())
        self.assertEqual(d['action'],'WAIT_CAPABILITY_RECOVERY'); self.assertTrue(d['circuit_break'])
    def test_retry_is_bounded_by_max_attempts(self):
        d=mod.decide_failure(failure_code='TIMEOUT',attempt=3,max_attempts=3,alternative_slots=2,policy=mod.default_policy())
        self.assertEqual(d['action'],'FAIL_TERMINAL'); self.assertFalse(d['retryable'])
    def test_policy_rejection_is_terminal(self):
        d=mod.decide_failure(failure_code='POLICY_REJECTED',attempt=1,max_attempts=3,alternative_slots=5,policy=mod.default_policy())
        self.assertEqual(d['action'],'FAIL_TERMINAL'); self.assertEqual(d['failure_class'],'POLICY')
