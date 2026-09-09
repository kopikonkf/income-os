import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "h03_economic_shadow.py"
spec = importlib.util.spec_from_file_location("h03_economic_shadow", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class H03EconomicShadowTests(unittest.TestCase):
    def resource(self, state="OBSERVED"):
        provenance = "company/h03/evidence/H03-BUILD-001.json"
        return {
            "schema_version": mod.SCHEMA,
            "observation_id": "H03-OBS-RESOURCE-001",
            "holding_id": "H03",
            "observed_at": "2026-09-09T11:20:00Z",
            "event_type": "RESOURCE_USAGE",
            "measurement_state": state,
            "economic_trace_id": "H03-ECO-TRACE-001",
            "parent_task_id": "H03-PROD-003",
            "provenance_ref": provenance,
            "evidence_refs": [provenance],
            "payload": ({"resource_class":"G0","runtime_id":"h03-local","principal_id_or_provider_id":"local-python","usage_quantity":1,"usage_unit":"build","cost_event_ref":None} if state == "OBSERVED" else None)
        }

    def test_resource_observation_maps_to_validated_not_committed(self):
        admission = mod.prepare_shadow_admission(self.resource())
        self.assertEqual(admission["status"], "validated_not_committed")
        self.assertEqual(admission["writer"], "die-state-manager")
        self.assertEqual(admission["event"]["holding_id"], "H03")
        self.assertEqual(admission["event"]["event_type"], "RESOURCE_USAGE")
        self.assertTrue(all(v is False for v in admission["authority_boundary"].values()))

    def test_unknown_measurement_is_not_coerced_to_zero(self):
        with self.assertRaisesRegex(ValueError, "UNMEASURED_NOT_ADMISSIBLE"):
            mod.prepare_shadow_admission(self.resource("UNKNOWN"))

    def test_founder_time_maps_without_commit_authority(self):
        obs = self.resource()
        obs.update({"observation_id":"H03-OBS-FOUNDER-001","event_type":"FOUNDER_TIME","payload":{"duration_minutes":7,"precision":"MEASURED","category":"FOUNDER_QC_REVIEW"}})
        admission = mod.prepare_shadow_admission(obs)
        self.assertEqual(admission["event"]["founder_time"]["duration_minutes"], 7)
        self.assertFalse(admission["authority_boundary"]["canonical_commit_authorized"])

    def test_direct_cost_requires_explicit_money(self):
        obs = self.resource()
        obs.update({"observation_id":"H03-OBS-COST-001","event_type":"COST_DIRECT_VARIABLE","payload":{"currency":"USD","amount_minor":25}})
        admission = mod.prepare_shadow_admission(obs)
        self.assertEqual(admission["event"]["money"]["amount_minor"], 25)

    def test_module_has_no_writer_surface(self):
        source = P.read_text(encoding="utf-8")
        self.assertNotIn("die_event", source)
        self.assertNotIn("ECONOMICS.jsonl", source)
        self.assertNotIn("write_text(", source)
