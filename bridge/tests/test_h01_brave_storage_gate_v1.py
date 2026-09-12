import json, tempfile, unittest
from pathlib import Path
from unittest import mock
import sys
ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company'/'company-os'/'die-h01'
sys.path.insert(0,str(H01/'engineering'))
import brave_storage_gate as G

class BraveStorageGateTests(unittest.TestCase):
 def binding(self,root):
  udd=root/'h01-web-s01'; prof=udd/'h01-web-p001'; prof.mkdir(parents=True)
  return {'profiles':[{'profile_id':'h01-web-p001','udd_id':'h01-web-s01','user_data_dir':str(udd),'profile_directory':'h01-web-p001'}]},udd,prof
 def test_cache_allowlist_excludes_auth_and_session_stores(self):
  self.assertIn('Cache',G.CACHE_NAMES); self.assertIn('Code Cache',G.CACHE_NAMES)
  for n in ('Cookies','Local Storage','IndexedDB','Sessions','Service Worker','Login Data','Preferences','Secure Preferences','BraveWallet'):
   self.assertIn(n,G.PROTECTED_NAMES); self.assertNotIn(n,G.CACHE_NAMES)
 def test_janitor_dry_run_does_not_delete(self):
  with tempfile.TemporaryDirectory() as td:
   m,udd,p=self.binding(Path(td)); (p/'Cache').mkdir(); (p/'Cache'/'x').write_bytes(b'x'*1024); (p/'Cookies').write_text('opaque')
   with mock.patch.object(G,'udd_process_active',return_value=False), mock.patch.object(G,'du_bytes',return_value=4096):
    r=G.janitor(m,'h01-web-p001',Path(td)/'rt',False)
   self.assertEqual(r['mode'],'DRY_RUN'); self.assertTrue((p/'Cache').exists()); self.assertTrue((p/'Cookies').exists()); self.assertFalse(r['protected_entries_touched'])
 def test_execute_deletes_cache_but_preserves_protected(self):
  with tempfile.TemporaryDirectory() as td:
   m,udd,p=self.binding(Path(td));
   for n in ('Cache','Code Cache','GPUCache'): (p/n).mkdir()
   for n in ('Cookies','Sessions','Service Worker','Preferences'): (p/n).mkdir() if ' ' in n or n in ('Sessions','Service Worker') else (p/n).write_text('opaque')
   with mock.patch.object(G,'udd_process_active',return_value=False), mock.patch.object(G,'du_bytes',return_value=4096): r=G.janitor(m,'h01-web-p001',Path(td)/'rt',True)
   self.assertFalse((p/'Cache').exists()); self.assertFalse((p/'Code Cache').exists()); self.assertFalse((p/'GPUCache').exists())
   self.assertTrue((p/'Cookies').exists()); self.assertTrue((p/'Sessions').exists()); self.assertTrue((p/'Service Worker').exists()); self.assertTrue((p/'Preferences').exists()); self.assertFalse(r['protected_entries_touched'])
 def test_active_udd_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   m,_,_=self.binding(Path(td))
   with mock.patch.object(G,'udd_process_active',return_value=True):
    with self.assertRaisesRegex(G.GateError,'E_UDD_ACTIVE'): G.janitor(m,'h01-web-p001',Path(td)/'rt',True)
 def test_held_lock_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   m,_,_=self.binding(Path(td)); rt=Path(td)/'rt'; first=G.try_lock('h01-web-s01',rt)
   try:
    with mock.patch.object(G,'udd_process_active',return_value=False):
     with self.assertRaisesRegex(G.GateError,'E_UDD_LOCKED'): G.janitor(m,'h01-web-p001',rt,True)
   finally: first.close()
 def test_measure_hard_cap_blocks_sixth(self):
  m={'profiles':[]}
  for i in range(100): m['profiles'].append({'profile_id':f'h01-web-p{i+1:03d}','udd_id':f'h01-web-s{(i//5)+1:02d}','user_data_dir':'/tmp/x','profile_directory':f'h01-web-p{i+1:03d}'})
  usage=mock.Mock(total=125*1024**3,used=40*1024**3,free=85*1024**3)
  with mock.patch.object(G.shutil,'disk_usage',return_value=usage),mock.patch.object(G,'du_bytes',return_value=8192),mock.patch.object(G,'live_h01_profiles',return_value=[f'h01-web-p{i:03d}' for i in range(1,6)]): r=G.measure(m,Path('/tmp'))
  self.assertEqual(r['live']['count'],5); self.assertFalse(r['capacity']['admit'])
 def test_capacity_can_be_satisfied_by_free_space_without_topology_change(self):
  m={'profiles':[{'profile_id':f'h01-web-p{i+1:03d}','udd_id':f'h01-web-s{(i//5)+1:02d}','user_data_dir':'/tmp/x','profile_directory':f'h01-web-p{i+1:03d}'} for i in range(100)]}
  low=mock.Mock(total=125*1024**3,used=106*1024**3,free=19*1024**3); high=mock.Mock(total=225*1024**3,used=106*1024**3,free=119*1024**3)
  common=(mock.patch.object(G,'du_bytes',return_value=8192),mock.patch.object(G,'live_h01_profiles',return_value=[]))
  with common[0],common[1],mock.patch.object(G.shutil,'disk_usage',return_value=low): a=G.measure(m,Path('/tmp'))
  with mock.patch.object(G,'du_bytes',return_value=8192),mock.patch.object(G,'live_h01_profiles',return_value=[]),mock.patch.object(G.shutil,'disk_usage',return_value=high): b=G.measure(m,Path('/tmp'))
  self.assertFalse(a['capacity']['admit']); self.assertTrue(b['capacity']['admit']); self.assertEqual(a['profiles']['count'],b['profiles']['count'],100)
 def test_forecast_floor_is_conservative_512mib(self):
  m={'profiles':[{'profile_id':f'h01-web-p{i+1:03d}','udd_id':'h01-web-s01','user_data_dir':'/tmp/x','profile_directory':f'h01-web-p{i+1:03d}'} for i in range(100)]}; usage=mock.Mock(total=125*1024**3,used=40*1024**3,free=85*1024**3)
  with mock.patch.object(G.shutil,'disk_usage',return_value=usage),mock.patch.object(G,'du_bytes',return_value=20*1024**2),mock.patch.object(G,'live_h01_profiles',return_value=[]): r=G.measure(m,Path('/tmp'))
  self.assertEqual(r['profiles']['forecast_per_additional_live_profile_bytes'],512*1024**2)
 def test_manifest_requires_exact_100_profiles(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'m.json'; p.write_text(json.dumps({'schema':'die.h01.brave-fabric.host-local.v1','profiles':[]}))
   with self.assertRaisesRegex(G.GateError,'E_PROFILE_COUNT'): G.load_manifest(p)
 def test_host_policy_constants(self):
  self.assertEqual(G.MAX_LIVE,5); self.assertEqual(G.MIN_FREE,20*1024**3); self.assertEqual(G.POPULATED_THRESHOLD,16*1024**2)

if __name__=='__main__': unittest.main()
