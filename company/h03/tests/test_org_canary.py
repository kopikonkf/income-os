import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=ROOT/'company'/'h03'/'lib'/'org_canary.py'
spec=importlib.util.spec_from_file_location('org_canary',P); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
SOURCE_ROOT=ROOT/'company'/'h03'/'evidence'/'H03-ORG-001'/'sources'

class OrganismCanaryTests(unittest.TestCase):
    def run_copy(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)/'H03-ORG-001'
        shutil.copytree(SOURCE_ROOT,root/'sources')
        result=mod.run_canary(evidence_root=root)
        return td,root,result

    def test_full_problem_to_package_canary_passes_without_live_provider_claim(self):
        td,root,r=self.run_copy()
        try:
            self.assertEqual(r['status'],'PASS')
            self.assertEqual(r['worth_making_decision'],'MAKE')
            self.assertEqual(r['product_form'],'guide')
            self.assertFalse(r['live_browser_preflight_performed'])
            self.assertFalse(r['live_web_ai_provider_call_claimed'])
            self.assertFalse(r['external_publication'])
            self.assertEqual(r['package']['status'],'LOCAL_SALE_READY_UNREVIEWED')
        finally:
            td.cleanup()

    def test_gate_order_is_materialized_before_deep_research(self):
        td,root,r=self.run_copy()
        try:
            stages=root/'stages'
            self.assertTrue((stages/'02-seed-curator-work-card.json').exists())
            self.assertTrue((stages/'05-demand-wtp.json').exists())
            self.assertTrue((stages/'06-worth-making.json').exists())
            self.assertTrue((stages/'07-research-plan.json').exists())
            self.assertTrue((stages/'08-research-dispatches.json').exists())
            worth=json.loads((stages/'06-worth-making.json').read_text(encoding='utf-8'))
            self.assertEqual(worth['decision'],'MAKE')
        finally:
            td.cleanup()

    def test_market_sources_do_not_leak_into_product_knowledge_packet(self):
        td,root,r=self.run_copy()
        try:
            kp=json.loads((root/'stages'/'16-knowledge-package.json').read_text(encoding='utf-8'))
            self.assertEqual(kp['source_packet']['source_id'],'ORG001-FTC-PEOPLESEARCH')
            self.assertNotIn('incogni.com',json.dumps(kp).lower())
            self.assertNotIn('joindeleteme.com',json.dumps(kp).lower())
        finally:
            td.cleanup()

    def test_role_fanout_uses_multiple_fixture_workers_through_normal_router(self):
        td,root,r=self.run_copy()
        try:
            self.assertEqual(r['research_provider_ids'],['fixture-market-a','fixture-knowledge-a','fixture-market-b'])
            self.assertGreaterEqual(len(set(r['producer_provider_ids'])),2)
            dispatches=json.loads((root/'stages'/'19-producer-dispatches.json').read_text(encoding='utf-8'))
            self.assertTrue(all(d['execution_mode']=='NONLIVE_ROLE_FIXTURE' for d in dispatches))
        finally:
            td.cleanup()

    def test_package_is_byte_deterministic_from_committed_source_snapshots(self):
        t1,r1,a=self.run_copy(); t2,r2,b=self.run_copy()
        try:
            self.assertEqual(a['package']['pdf_sha256'],b['package']['pdf_sha256'])
            self.assertEqual(a['package']['zip_sha256'],b['package']['zip_sha256'])
            self.assertEqual(a['package']['page_count'],2)
        finally:
            t1.cleanup(); t2.cleanup()
