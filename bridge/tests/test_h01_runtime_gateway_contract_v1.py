import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H01 = ROOT / "company" / "company-os" / "die-h01"
MANIFEST = H01 / "runtime" / "h01-runtime-gateway-boundary.v1.json"
SCHEMA = H01 / "contracts" / "h01-runtime-gateway.v1.schema.json"
DOC = H01 / "DIE_H01_RUNTIME_GATEWAY_V1.md"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class H01RuntimeGatewayContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load(MANIFEST)
        cls.schema = load(SCHEMA)
        cls.doc = DOC.read_text(encoding="utf-8")

    def test_gateway_is_not_scheduler_and_mc_is_singleton(self):
        self.assertEqual(self.manifest["scheduler_authority"], "die-control/Mission Control")
        self.assertTrue(self.manifest["global_mission_control_singleton"])
        self.assertFalse(self.manifest["gateway_is_scheduler"])
        self.assertEqual(self.manifest["mission_protocol"], "mc-mission-v1")

    def test_only_three_cross_vps_business_message_types(self):
        self.assertEqual(
            self.manifest["cross_vps_messages"],
            ["WORK_DISPATCH", "WORK_CHECKPOINT", "WORK_RESULT"],
        )
        variants = self.schema["oneOf"]
        constants = {v["properties"]["message_type"]["const"] for v in variants}
        self.assertEqual(constants, {"WORK_DISPATCH", "WORK_CHECKPOINT", "WORK_RESULT"})

    def test_mission_mapping_reuses_canonical_methods(self):
        self.assertEqual(
            self.manifest["mission_mapping"],
            {
                "RECONCILE": "mission.task.get",
                "WORK_CHECKPOINT": "mission.task.checkpoint",
                "WORK_RESULT_BLOCKED": "mission.task.block",
                "WORK_RESULT_COMPLETED": "mission.task.complete",
            },
        )

    def test_auth_and_durability_fail_closed(self):
        auth = self.manifest["auth"]
        self.assertTrue(auth["encrypted_transport_required"])
        self.assertTrue(auth["peer_authentication_required"])
        self.assertTrue(auth["replay_resistance_required"])
        self.assertTrue(auth["service_credentials_host_local"])
        self.assertFalse(auth["mission_lease_capability_persisted_on_h01"])
        self.assertFalse(auth["mission_lease_capability_in_gateway_payload"])
        durable = self.manifest["durability"]
        self.assertTrue(durable["dispatch_store_before_ack"])
        self.assertTrue(durable["local_execution_journal_required"])
        self.assertTrue(durable["local_event_outbox_required"])
        self.assertTrue(durable["terminal_result_store_before_send"])
        self.assertTrue(durable["terminal_result_immutable"])
        self.assertFalse(durable["wan_loss_starts_new_execution"])
        self.assertEqual(durable["duplicate_same_dispatch_different_digest"], "E_IDEMPOTENCY_CONFLICT")

    def test_browser_cdp_filesystem_and_secrets_stay_local(self):
        local = set(self.manifest["h01_local_surfaces"])
        for required in {"brave", "cdp", "filesystem", "provider_sessions", "downloads", "artifact_bytes"}:
            self.assertIn(required, local)
        forbidden = set(self.manifest["forbidden_remote_surfaces"])
        for required in {"browser.click", "browser.type", "cdp.*", "filesystem.read", "filesystem.write", "shell.exec", "raw_artifact_bytes"}:
            self.assertIn(required, forbidden)
        forbidden_keys = {x.lower() for x in self.manifest["forbidden_persisted_keys"]}
        for required in {"leasetoken", "reviewtoken", "cookies", "authorization", "user_data_dir", "cdp_port"}:
            self.assertIn(required, forbidden_keys)

    def test_schema_has_no_browser_or_filesystem_rpc_field(self):
        for variant in self.schema["oneOf"]:
            self.assertFalse(variant["additionalProperties"])
            props = set(variant["properties"])
            self.assertFalse(props & {"operation", "browser_action", "cdp_command", "filesystem_path", "shell_command"})

    def test_normative_doc_explicitly_forbids_per_click_wan(self):
        for phrase in (
            "not a scheduler",
            "browser actions",
            "CDP ports",
            "store-before-ack",
            "E_IDEMPOTENCY_CONFLICT",
            "MUST NOT remote-drive",
            "no browser-control API",
        ):
            self.assertIn(phrase, self.doc)


if __name__ == "__main__":
    unittest.main()
