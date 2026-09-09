import importlib.util, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "company" / "h03" / "lib" / "web_ai_capability.py"
spec = importlib.util.spec_from_file_location("web_ai_capability", P)
ai = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(ai)

class WebAICapabilityTests(unittest.TestCase):
    def req(self, role="CURATOR"):
        return {"schema_version":ai.REQUEST_SCHEMA,"request_id":"REQ-001","holding_id":"H03","role":role,"task_id":"H03-AI-001","model_route":"qwen/qwen3.8-max","prompt":"Summarize the bounded context.","context":{"knowledge_package_id":"KP-1"},"output_mode":"TEXT"}

    def test_curator_and_producer_normalize_to_openai_messages(self):
        for role in ("CURATOR", "PRODUCER"):
            payload = ai.build_openai_payload(self.req(role))
            self.assertEqual(payload["model"], "qwen/qwen3.8-max")
            self.assertFalse(payload["stream"])
            self.assertEqual([m["role"] for m in payload["messages"]], ["system","user"])

    def test_session_and_credential_material_rejected_recursively(self):
        for bad in ("cookies", "access_token", "browser_profile", "oauth", "credentials"):
            req = self.req(); req["context"] = {"nested": {bad: "secret-like"}}
            with self.assertRaisesRegex(ValueError, "SESSION_OR_CREDENTIAL_MATERIAL_FORBIDDEN"):
                ai.validate_capability_request(req)

    def test_client_returns_unverified_model_output_and_no_session_state(self):
        seen = {}
        def fake(url, payload, timeout):
            seen.update({"url":url,"payload":payload,"timeout":timeout})
            return {"choices":[{"message":{"role":"assistant","content":"Draft answer"}}],"usage":{"total_tokens":12}}
        client = ai.WebAITextClient(endpoint="http://127.0.0.1:8456", transport=fake)
        out = client.complete(self.req())
        self.assertTrue(seen["url"].endswith("/v1/chat/completions"))
        self.assertEqual(out["content"], "Draft answer")
        self.assertEqual(out["truth_status"], "UNVERIFIED_MODEL_OUTPUT")
        self.assertFalse(out["canonical_truth"])
        self.assertFalse(out["session_material_persisted"])

    def test_missing_choices_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "WEB_AI_RESPONSE_CHOICES_MISSING"):
            ai.normalize_openai_response(self.req(), {})

    def test_extended_h03_roles_normalize(self):
        for role in ("SEED_CURATOR","MARKET_RESEARCHER","KNOWLEDGE_RESEARCHER","SYNTHESIZER","PRODUCT_ARCHITECT","REVIEWER","GROWTH_PRODUCER"):
            payload = ai.build_openai_payload(self.req(role))
            self.assertEqual(payload["model"], "qwen/qwen3.8-max")
            self.assertIn(role, ai._ALLOWED_ROLES)
