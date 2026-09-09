import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def load(name):
    p=ROOT/'company'/'h03'/'lib'/f'{name}.py'; spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
review=load('review_engine'); scale=load('scale_soak')
E=ROOT/'company'/'h03'/'evidence'/'H03-ORG-001'

class ReviewScaleTests(unittest.TestCase):
    def data(self):
        return {
            'lineage':json.loads((E/'organism-lineage.json').read_text(encoding='utf-8')),
            'seed':json.loads((E/'stages'/'03-problem-seed-batch.json').read_text(encoding='utf-8'))['candidates'][0],
            'demand':json.loads((E/'stages'/'05-demand-wtp.json').read_text(encoding='utf-8')),
            'kp':json.loads((E/'stages'/'16-knowledge-package.json').read_text(encoding='utf-8')),
            'bp':json.loads((E/'stages'/'18-product-blueprint.json').read_text(encoding='utf-8')),
            'package':json.loads((E/'stages'/'21-package-receipt.json').read_text(encoding='utf-8')),
        }
    def test_reviewer_is_standard_worker_and_separated(self):
        d=self.data(); card=review.build_reviewer_work_card(product_id=d['bp']['product_id'],package_ref='artifact://org001/package')
        self.assertEqual(card['role'],'REVIEWER'); self.assertEqual(card['capability_requirements'],{'web_ai':True,'mcp':False,'shell':False,'local_filesystem':False})
        rc=review.build_review_card(lineage=d['lineage'],problem_seed=d['seed'],demand_packet=d['demand'],knowledge_package=d['kp'],blueprint=d['bp'],package_receipt=d['package'],reviewer_provider_id='fixture-reviewer-independent',dominant_producer_provider_id='fixture-producer-a',reviewer_fixture={'decision':'PASS','decision_reasons':['Product promise stays within FTC-backed evidence and clearly states limitations.'],'evidence_confidence':'HIGH','risk_flags':[{'code':'LIVE_WORKFORCE_NOT_PROVEN','severity':'MEDIUM'}],'rights_flags':[{'code':'REFERENCE_ONLY_SOURCE','severity':'LOW'}]})
        self.assertEqual(rc['decision'],'PASS'); self.assertTrue(rc['reviewer_observation']['separated_from_dominant_producer']); self.assertFalse(rc['external_publication_authorized']); self.assertTrue(rc['founder_action_required'])
    def test_same_dominant_producer_reviewer_rejected(self):
        d=self.data()
        with self.assertRaisesRegex(ValueError,'REVIEWER_SEPARATION_REQUIRED'):
            review.build_review_card(lineage=d['lineage'],problem_seed=d['seed'],demand_packet=d['demand'],knowledge_package=d['kp'],blueprint=d['bp'],package_receipt=d['package'],reviewer_provider_id='fixture-producer-a',dominant_producer_provider_id='fixture-producer-a',reviewer_fixture={'decision':'PASS','decision_reasons':['x']})
    def test_scale_soak_capacity_sized_and_resilient(self):
        d=self.data()
        with tempfile.TemporaryDirectory() as td:
            r=scale.run_scale_soak(output_root=Path(td),knowledge_package=d['kp'],problem_seed_id=d['seed']['problem_seed_id'])
            self.assertEqual(r['capacity_basis']['safe_product_capacity'],3)
            self.assertEqual(r['product_count'],3); self.assertEqual(r['worker_job_count'],6)
            self.assertEqual(r['retry_count'],1); self.assertEqual(r['fallback_success_count'],1)
            self.assertEqual(r['terminal_failure_rate'],0); self.assertEqual(r['status'],'PASS')
            self.assertFalse(r['external_publication']); self.assertEqual(len(r['package_receipts']),3)
            self.assertEqual({p['form'] for p in r['package_receipts']},{'guide','checklist','reference_sheet'})
    def test_scale_metrics_present(self):
        d=self.data()
        with tempfile.TemporaryDirectory() as td:
            r=scale.run_scale_soak(output_root=Path(td),knowledge_package=d['kp'],problem_seed_id=d['seed']['problem_seed_id'])
            self.assertGreater(r['throughput_products_per_second'],0)
            self.assertGreaterEqual(r['queue_latency_ms']['max'],r['queue_latency_ms']['min'])
            self.assertGreater(r['resource_usage']['peak_tracemalloc_bytes'],0)
            self.assertTrue(r['provider_bottlenecks']); self.assertTrue(r['profile_bottlenecks'])
