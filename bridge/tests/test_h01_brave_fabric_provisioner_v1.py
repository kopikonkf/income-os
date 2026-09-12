from __future__ import annotations
import hashlib, json, re, unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'company/company-os/die-h01'
SRC=H/'engineering/brave_fabric_provision.py'
TPL=H/'fixtures/h01-023/profile-preferences-template.json'
RECEIPT=H/'receipts/H01-023-safe-provisioner.receipt.json'

class BraveFabricProvisionerTests(unittest.TestCase):
    def test_task_done_and_dependency(self):
        g=json.loads((H/'die-h01-task-graph.v1.json').read_text()); by={x['id']:x for x in g['tasks']}
        self.assertEqual(by['H01-022']['status'],'DONE')
        self.assertEqual(by['H01-023']['status'],'DONE')
        self.assertEqual(by['H01-023']['depends_on'],['H01-022'])

    def test_source_has_deterministic_20x5_mapping(self):
        s=SRC.read_text()
        self.assertIn('for n in range(1,101)',s)
        self.assertIn('shard=(n-1)//5+1',s)
        self.assertIn('slot=(n-1)%5+1',s)
        self.assertIn("'profiles_per_udd':5",s)
        self.assertIn("'profile_count':100",s)
        self.assertIn("'max_active_per_udd':1",s)

    def test_no_secret_store_clone_surface(self):
        s=SRC.read_text().lower(); t=TPL.read_text().lower()
        forbidden_source=['copytree','shutil','rsync','cookies','cookies-journal','login data','session storage','sessions','indexeddb','local storage','webstorage','service worker','gcm store','sync data']
        for x in forbidden_source: self.assertNotIn(x,s)
        forbidden_template=['cookie','token','session','login data','indexeddb','local storage','webstorage','service worker']
        for x in forbidden_template: self.assertNotIn(x,t)

    def test_template_is_only_stateless_ui_preferences(self):
        d=json.loads(TPL.read_text())
        self.assertEqual(set(d),{'bookmark_bar','brave','ntp','translate'})
        self.assertFalse(d['brave']['brave_search']['show-ntp-search'])
        self.assertFalse(d['brave']['new_tab_page']['show_background_image'])
        self.assertFalse(d['translate']['enabled'])

    def test_receipt_proves_live_parity_and_counts(self):
        r=json.loads(RECEIPT.read_text())
        self.assertEqual(r['result'],'PASS')
        self.assertEqual(r['live_validation']['status'],'PASS')
        self.assertEqual(r['live_validation']['udd_count'],20)
        self.assertEqual(r['live_validation']['profile_count'],100)
        self.assertEqual(r['live_validation']['errors'],[])
        self.assertEqual(r['source_parity']['repo_sha256'],r['source_parity']['host_sha256'])
        self.assertEqual(r['template_parity']['repo_sha256'],r['template_parity']['host_sha256'])
        self.assertTrue(r['safety']['cookies_or_tokens_read'] is False)
        self.assertTrue(r['safety']['session_bytes_read'] is False)

if __name__=='__main__': unittest.main()
