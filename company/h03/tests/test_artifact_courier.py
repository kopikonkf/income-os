import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company" / "h03" / "lib"

spec = importlib.util.spec_from_file_location("artifact_courier_test", LIB / "artifact_courier.py")
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class ArtifactCourierTests(unittest.TestCase):
    def test_commit_resolve_and_sha_verification(self):
        with tempfile.TemporaryDirectory() as td:
            courier = mod.ArtifactCourier(td)
            ref = courier.commit_payload(
                run_id="LIVE-ORG-001",
                artifact_id="WC-A-OUT",
                kind="problem_seed_batch",
                declared_schema="die.h03.problem-seed-batch.v1",
                producer_work_card_id="WC-A",
                payload={"seeds": [{"problem": "example"}]},
            )
            self.assertEqual(courier.resolve(ref)["seeds"][0]["problem"], "example")
            self.assertEqual(len(ref["sha256"]), 64)
            tampered = dict(ref, sha256="0" * 64)
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SHA256_MISMATCH"):
                courier.resolve(tampered)

    def test_idempotent_same_artifact_and_conflict_on_different_payload(self):
        with tempfile.TemporaryDirectory() as td:
            courier = mod.ArtifactCourier(td)
            kw = dict(run_id="R1", artifact_id="A1", kind="packet", declared_schema="packet.v1", producer_work_card_id="WC1")
            one = courier.commit_payload(payload={"x": 1}, **kw)
            two = courier.commit_payload(payload={"x": 1}, **kw)
            self.assertEqual(one, two)
            with self.assertRaisesRegex(ValueError, "ARTIFACT_ID_CONFLICT"):
                courier.commit_payload(payload={"x": 2}, **kw)

    def test_existing_ref_is_restart_safe_and_kind_checked(self):
        with tempfile.TemporaryDirectory() as td:
            courier = mod.ArtifactCourier(td)
            committed = courier.commit_payload(
                run_id="R-EXIST", artifact_id="A-EXIST", kind="packet", declared_schema="packet.v1",
                producer_work_card_id="WC-EXIST", payload={"x":1},
            )
            recovered = courier.existing_ref(run_id="R-EXIST", artifact_id="A-EXIST", kind="packet")
            self.assertEqual(recovered, committed)
            with self.assertRaisesRegex(ValueError,"ARTIFACT_KIND_MISMATCH"):
                courier.existing_ref(run_id="R-EXIST", artifact_id="A-EXIST", kind="wrong")

    def test_secret_material_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            courier = mod.ArtifactCourier(td)
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SECRET_MATERIAL_FORBIDDEN"):
                courier.commit_payload(
                    run_id="R1", artifact_id="A1", kind="packet", declared_schema="packet.v1",
                    producer_work_card_id="WC1", payload={"credentials": {"value": "never"}},
                )

    def test_queue_state_is_durable_json(self):
        with tempfile.TemporaryDirectory() as td:
            courier = mod.ArtifactCourier(td)
            state = courier.create_or_load_queue("RUN-1")
            self.assertEqual(state["batch_id"], "RUN-1")
            state["fan_in_groups"].append({"group_id": "G1", "child_work_card_ids": [], "target_work_card_id": "X", "max_children": 1})
            courier.save_queue("RUN-1", state)
            reloaded = courier.create_or_load_queue("RUN-1")
            self.assertEqual(reloaded["fan_in_groups"][0]["group_id"], "G1")


if __name__ == "__main__":
    unittest.main()
