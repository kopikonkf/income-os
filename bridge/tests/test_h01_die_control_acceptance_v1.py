import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
H01=ROOT/'company'/'company-os'/'die-h01'
RUNTIME=json.loads((H01/'runtime'/'h01-die-control-acceptance.v1.json').read_text())
RECEIPT=json.loads((H01/'receipts'/'H01-011-die-control-acceptance.receipt.json').read_text())
GRAPH=json.loads((H01/'die-h01-task-graph.v1.json').read_text())
DOC=(H01/'DIE_H01_DIE_CONTROL_ACCEPTANCE_V1.md').read_text()

class H011DieControlAcceptanceTests(unittest.TestCase):
    def test_all_acceptance_dimensions_pass(self):
        self.assertEqual(RUNTIME['status'],'PASS')
        self.assertTrue(all(RECEIPT['dimensions'][k]=='PASS' for k in (
            'mission_control','universal_mcp','state_manager_bridge','principal_registry','durable_state','backup_recovery','network_ingress')))

    def test_mission_control_is_loopback_and_durable(self):
        mc=RUNTIME['mission_control']; ds=RUNTIME['durable_state']
        self.assertEqual(mc['listen'],'127.0.0.1:8891')
        self.assertEqual(mc['protocol'],'mc-mission-v1')
        self.assertEqual(ds['sqlite_quick_check'],'ok')
        self.assertEqual(ds['journal_mode'],'wal')
        self.assertGreaterEqual(len(ds['h01_011_checkpoints_persisted']),2)

    def test_universal_is_public_ingress_not_direct_mc_exposure(self):
        u=RUNTIME['universal_mcp']; n=RUNTIME['network_ingress']
        self.assertEqual(u['local_health_http'],200)
        self.assertEqual(u['public_health_http'],200)
        self.assertEqual(u['tool_count'],46)
        self.assertTrue(n['mission_control_loopback_only'])
        self.assertFalse(n['mission_control_direct_public_exposure'])

    def test_state_manager_sovereignty_preserved(self):
        sm=RUNTIME['state_manager_bridge']
        self.assertEqual(sm['canonical_state_writer'],'die-state-manager')
        self.assertEqual(sm['sole_physical_writer_count'],1)
        self.assertEqual(sm['unauthorized_global_store_writers'],0)
        self.assertEqual(sm['live_mission_control_forbidden_company_store_refs'],0)

    def test_registry_and_recovery_are_explicit(self):
        self.assertEqual(RUNTIME['principal_registry']['configured_principal_count'],8)
        self.assertTrue(RUNTIME['principal_registry']['deferred_surfaces_remain_explicit'])
        br=RUNTIME['backup_recovery']
        self.assertEqual(br['verified_snapshot_count'],6)
        self.assertEqual(br['all_snapshot_quick_checks'],'ok')
        self.assertEqual(br['real_windows_reboot_acceptance'],'MC-008I PASS')
        self.assertFalse(br['raw_active_wal_copy_claimed_as_backup'])

    def test_no_cutover_side_effects_authorized(self):
        a=RUNTIME['authority']
        self.assertTrue(a['founder_authorized_for_h01_011'])
        for k in ('business_scheduler_cutover_performed','legacy_services_retired','srv_die_mutated','h03_rebound','runtime_gateway_deployed'):
            self.assertFalse(a[k])
        self.assertIn('does not claim an arbitrary raw copy of the active WAL database',DOC)

    def test_graph_unlocks_only_h01_011_dependents(self):
        by={t['id']:t for t in GRAPH['tasks']}
        self.assertEqual(by['H01-011']['status'],'DONE')
        self.assertEqual(by['H01-012']['status'],'DONE')
        self.assertEqual(by['H01-013']['status'],'READY')
        self.assertEqual(by['H01-014']['status'],'READY')
        self.assertEqual(by['H01-015']['status'],'READY')

    def test_receipt_contains_no_mission_owner_capability(self):
        raw=json.dumps(RECEIPT)
        self.assertNotIn('mission_lease_token',raw)
        self.assertNotRegex(raw,r'lt_[A-Za-z0-9_-]{20,}')

if __name__=='__main__': unittest.main()
