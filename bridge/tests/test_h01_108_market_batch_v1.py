from __future__ import annotations
import importlib.util,json,unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];H=ROOT/'company/company-os/die-h01'
MAN=H/'fixtures/h01-108/market-informed-100.json';EVI=H/'runtime/h01-108-market-evidence.v1.json'
class H01108Tests(unittest.TestCase):
 def setUp(self):self.m=json.loads(MAN.read_text());self.e=json.loads(EVI.read_text())
 def test_frozen_unique_100(self):
  self.assertEqual(self.m['status'],'FROZEN');self.assertEqual(len(self.m['items']),100);self.assertEqual(len({x['canonical_name'] for x in self.m['items']}),100);self.assertEqual(len({x['queue_item_id'] for x in self.m['items']}),100)
 def test_bucket_mix(self):self.assertEqual(Counter(x['bucket'] for x in self.m['items']),Counter({'EVERGREEN':60,'MOMENTUM':30,'SEASONAL_Q4':10}))
 def test_seasonal_exactly_ten(self):
  self.assertEqual([x['canonical_name'] for x in self.m['items'] if x['bucket']=='SEASONAL_Q4'],['snowman','reindeer','stocking','ornament','snowflake','sleigh','holly','mistletoe','candy cane','firework'])
 def test_provider_weights(self):self.assertEqual(Counter(x['planned_provider'] for x in self.m['items']),Counter({'gemini':24,'qwen':20,'claude':20,'chatgpt':12,'manus':12,'copilot':12}))
 def test_all_source_gates_frozen(self):
  self.assertTrue(all(x['queue_item_id'].startswith('H01-SVGQ-CAND-') and x['source_candidate_id'].startswith('CAND-') for x in self.m['items']))
  self.assertEqual(self.m['authority']['submission_authorized'],False);self.assertEqual(self.m['authority']['publication_authorized'],False)
 def test_market_evidence_is_bounded_not_demand_engine(self):
  self.assertIn('does not implement or replace H01-130..133',self.e['purpose']);self.assertTrue(all(x['url'].startswith('https://') for x in self.e['sources']))
 def test_runner_keeps_lease_token_out_of_sanitized_receipts(self):
  s=(H/'engineering/h01_108_run_one.py').read_text();self.assertIn("if k!='lease_token'",s);self.assertIn("UNKNOWN_AFTER_PROVIDER_DRIVER_ERROR",s);self.assertNotIn("dump(w/'scheduler-lease.json'",s)
 def test_task_running_after_founder_start(self):
  g=json.loads((H/'die-h01-task-graph.v1.json').read_text());by={x['id']:x for x in g['tasks']};self.assertEqual(by['H01-108']['status'],'RUNNING');self.assertTrue(all(by[d]['status']=='DONE' for d in by['H01-108']['depends_on']))
if __name__=='__main__':unittest.main()
