from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'company/company-os/die-h01'
class MasterBraveBaselineTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads((H/'receipts/H01-022-master-brave-baseline.acceptance-candidate.json').read_text())
        g=json.loads((H/'die-h01-task-graph.v1.json').read_text()); self.by={x['id']:x for x in g['tasks']}
    def test_founder_gate_remains_closed(self):
        self.assertEqual(self.by['H01-022']['authority'],'FOUNDER_REQUIRED')
        self.assertEqual(self.by['H01-022']['status'],'DONE')
        self.assertTrue(self.r['founder_gate']['required'])
        self.assertTrue(self.r['founder_gate']['accepted'])
    def test_baseline_identity(self):
        self.assertEqual(self.r['baseline']['profile_id'],'h01-web-p001')
        self.assertEqual(self.r['baseline']['udd_id'],'h01-web-s01')
        self.assertEqual(self.r['baseline']['cdp'],'127.0.0.1:9201')
        self.assertEqual(self.r['baseline']['manual_authentication'],'FOUNDER_PROVIDED')
        self.assertFalse(self.r['baseline']['preauthenticate_all_profiles'])
    def test_acceptance_dimensions_pass(self):
        a=self.r['acceptance']
        for k in ('persistence','restart','loopback_cdp','single_committed_page','download_output_acquisition','provider_completion_behavior','ram_renderer_disk_telemetry'):
            self.assertEqual(a[k],'PASS')
        self.assertFalse(a['cookies_or_tokens_read']); self.assertFalse(a['session_bytes_read']); self.assertFalse(a['browser_profile_copied'])
    def test_live_runtime_clean_close(self):
        rt=self.r['runtime']; self.assertEqual(rt['status'],'PASS'); self.assertEqual(rt['page_count_after_enforcement'],1); self.assertTrue(rt['loopback_only']); self.assertTrue(rt['browser_close_sent']); self.assertTrue(rt['process_exited']); self.assertTrue(rt['cdp_closed']); self.assertTrue(rt['lock_released'])
    def test_real_web_ai_and_capacity_proofs_are_accepted(self):
        p=self.r['real_web_ai_proof']; self.assertEqual(p['h01_107_status'],'PASS'); self.assertEqual(p['provider_count'],8); self.assertEqual(p['validated_svg_count'],6)
        s=self.r['storage_capacity_proof']; self.assertEqual(s['h01_024_status'],'PASS'); self.assertTrue(s['auth_session_stores_protected']); self.assertGreater(s['free_bytes_after'],20*1024**3)
if __name__=='__main__': unittest.main()
