import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "cognition_work_card.py"
spec = importlib.util.spec_from_file_location("cognition_work_card", P)
mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)


class CognitionWorkCardTests(unittest.TestCase):
    def card(self, role="KNOWLEDGE_RESEARCHER"):
        return {
            "schema_version": mod.CARD_SCHEMA,
            "work_card_id": "H03-WC-0001",
            "holding_id": "H03",
            "task_id": "H03-RSCH-002",
            "role": role,
            "queue": "research",
            "idempotency_key": "h03-rsch-0001",
            "input_artifacts": [{"artifact_id":"RP-PLAN-1","kind":"research_plan","ref":"artifact://research-plan/1","sha256":None}],
            "output_contract": {"artifact_kind":"research_packet","schema_version":"die.h03.research-packet.v1"},
            "capability_requirements": mod.standard_web_ai_capabilities(),
            "terminal_policy": {"max_attempts":3,"retryable_failures":["RATE_LIMITED","PROVIDER_UNAVAILABLE"]}
        }

    def test_standard_worker_needs_web_ai_not_mcp_shell_or_fs(self):
        card = mod.validate_work_card(self.card())
        self.assertEqual(card["capability_requirements"], {"web_ai":True,"mcp":False,"shell":False,"local_filesystem":False})

    def test_all_logical_roles_are_valid(self):
        for role in mod.ROLES:
            mod.validate_work_card(self.card(role))

    def test_success_requires_durable_output_artifact(self):
        card = self.card()
        result = {"schema_version":mod.RESULT_SCHEMA,"work_card_id":card["work_card_id"],"attempt":1,"status":"SUCCEEDED","output_artifacts":[],"worker_observation":{"provider_id":"qwen"}}
        with self.assertRaisesRegex(ValueError, "SUCCESS_REQUIRES_ARTIFACT"):
            mod.validate_worker_result(card, result)
        result["output_artifacts"] = [{"artifact_id":"RP-1","kind":"research_packet","ref":"artifact://research/1","sha256":None}]
        mod.validate_worker_result(card, result)

    def test_failure_cannot_handoff_output(self):
        card = self.card()
        result = {"schema_version":mod.RESULT_SCHEMA,"work_card_id":card["work_card_id"],"attempt":1,"status":"FAILED_RETRYABLE","output_artifacts":[{"artifact_id":"X","kind":"research_packet","ref":"artifact://x","sha256":None}],"worker_observation":{}}
        with self.assertRaisesRegex(ValueError, "FAILURE_MUST_NOT_HANDOFF_OUTPUT"):
            mod.validate_worker_result(card, result)

    def test_secret_material_rejected(self):
        card = self.card(); card["input_artifacts"][0]["cookies"] = "secret"
        with self.assertRaisesRegex(ValueError, "WORKER_SECRET_MATERIAL_FORBIDDEN"):
            mod.validate_work_card(card)
