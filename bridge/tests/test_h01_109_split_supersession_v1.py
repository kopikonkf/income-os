import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GRAPH=ROOT/'company/company-os/die-h01/die-h01-task-graph.v1.json'
class H01109Split(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by={x['id']:x for x in json.loads(GRAPH.read_text())['tasks']}
    def test_technical_preflight_is_the_only_new_architect_frontier(self):
        self.assertEqual(self.by['H01-109A']['status'],'READY')
        self.assertEqual(self.by['H01-109A']['authority'],'ARCHITECT')
        self.assertEqual(self.by['H01-109A']['depends_on'],['H01-135','H01-136'])
    def test_real_upload_is_explicit_founder_gate(self):
        self.assertEqual(self.by['H01-109B']['status'],'BLOCKED')
        self.assertEqual(self.by['H01-109B']['authority'],'FOUNDER_REQUIRED')
        self.assertEqual(self.by['H01-109B']['depends_on'],['H01-109A'])
        self.assertIn('Founder-only gate',self.by['H01-109B']['founder_policy'])
    def test_legacy_109_is_umbrella_not_mixed_authority_executor(self):
        self.assertEqual(self.by['H01-109']['status'],'BLOCKED')
        self.assertEqual(self.by['H01-109']['depends_on'],['H01-109A','H01-109B'])
        self.assertIn('SPLIT:',self.by['H01-109']['result'])
    def test_old_10_and_100_runs_are_retired_without_acceptance_claim(self):
        for tid in ('H01-110','H01-111'):
            self.assertEqual(self.by[tid]['status'],'DEFERRED')
            self.assertIn('SUPERSEDED:',self.by[tid]['result'])
        self.assertIn('H01-108',self.by['H01-110']['result'])
        self.assertIn('H01-108',self.by['H01-111']['result'])
    def test_downstream_preserves_h01_108_and_real_upload_gates(self):
        self.assertEqual(self.by['H01-112']['depends_on'],['H01-108','H01-109','H01-029'])
        self.assertEqual(self.by['H01-123']['depends_on'],['H01-108','H01-109','H01-121','H01-122'])
        self.assertIn('H01-109',self.by['H01-200']['depends_on'])
if __name__=='__main__': unittest.main()
