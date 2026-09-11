import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "company" / "h03" / "lib"

cspec = importlib.util.spec_from_file_location("cognition_work_card_runner_dep", LIB / "cognition_work_card.py")
cardmod = importlib.util.module_from_spec(cspec); assert cspec.loader; cspec.loader.exec_module(cardmod)

aspec = importlib.util.spec_from_file_location("artifact_courier_runner_dep", LIB / "artifact_courier.py")
artifactmod = importlib.util.module_from_spec(aspec); assert aspec.loader; aspec.loader.exec_module(artifactmod)

rspec = importlib.util.spec_from_file_location("live_work_card_runner_test", LIB / "live_work_card_runner.py")
mod = importlib.util.module_from_spec(rspec); assert rspec.loader; rspec.loader.exec_module(mod)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.dispatch_calls = []
        self.events = []

    def dispatch(self, **kwargs):
        self.dispatch_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected dispatch")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def emit(self, event):
        self.events.append(event)
        return {"ok": True}


def card(role="MARKET_RESEARCHER", work_card_id="H03-WC-RT008-A", max_attempts=3, inputs=None):
    return {
        "schema_version": cardmod.CARD_SCHEMA,
        "work_card_id": work_card_id,
        "holding_id": "H03",
        "task_id": "H03-RT-008",
        "role": role,
        "queue": "live-cognition",
        "idempotency_key": f"idem-{work_card_id}-0001",
        "input_artifacts": inputs or [],
        "output_contract": {"artifact_kind": "research_packet", "schema_version": "die.h03.research-packet.v1"},
        "capability_requirements": cardmod.standard_web_ai_capabilities(),
        "terminal_policy": {"max_attempts": max_attempts, "retryable_failures": ["OUTPUT_SCHEMA_INVALID", "PROVIDER_FAILURE"]},
    }


def success_response(payload='{"finding":"validated"}', provider="qwen"):
    return {
        "ok": True,
        "route": {"provider_id": provider, "pool_id": "H03-KNOWLEDGE-A"},
        "response_text": payload,
        "effective_model": "Qwen3.8-Max" if provider == "qwen" else "ACCOUNT_DEFAULT_UNVERIFIED",
        "effective_mode": "Thinking" if provider == "qwen" else "Default",
        "attempts": [{"provider_id": provider, "ok": True}],
    }


class LiveWorkCardRunnerTests(unittest.TestCase):
    def test_success_commits_artifact_queue_and_telemetry(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            client = FakeClient([success_response()])
            runner = mod.LiveWorkCardRunner(courier, client)
            c = card()
            result = runner.run(run_id="LIVE-ORG-001", card=c, instruction="Return one research finding.")
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(len(client.dispatch_calls), 1)
            payload = courier.resolve(result["output_artifacts"][0])
            self.assertEqual(payload["finding"], "validated")
            state = courier.create_or_load_queue("LIVE-ORG-001")
            self.assertEqual(state["jobs"][c["work_card_id"]]["state"], "SUCCEEDED")
            states = [e["state"] for e in client.events]
            self.assertIn("OUTPUT_RECEIVED", states)
            self.assertIn("ARTIFACT_COMMITTED", states)
            self.assertEqual(states[-1], "SUCCEEDED")

    def test_replay_uses_durable_result_without_dispatching_again(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            c = card()
            first_client = FakeClient([success_response()])
            mod.LiveWorkCardRunner(courier, first_client).run(run_id="RUN-R", card=c, instruction="Do it.")
            second_client = FakeClient([])
            result = mod.LiveWorkCardRunner(courier, second_client).run(run_id="RUN-R", card=c, instruction="Do it.")
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(second_client.dispatch_calls, [])
            self.assertEqual(second_client.events[-1]["recovery"], "RESULT_RECEIPT_REPLAY")

    def test_restart_after_result_receipt_commit_does_not_duplicate_web_ai_call(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            c = card()
            calls = FakeClient([success_response()])

            def crash(stage, _result):
                if stage == "AFTER_RESULT_RECEIPT_COMMIT":
                    raise SystemExit("simulated process death")

            with self.assertRaises(SystemExit):
                mod.LiveWorkCardRunner(courier, calls, fault_hook=crash).run(run_id="RUN-CRASH", card=c, instruction="Do it.")
            self.assertEqual(len(calls.dispatch_calls), 1)
            restarted = FakeClient([])
            result = mod.LiveWorkCardRunner(courier, restarted).run(run_id="RUN-CRASH", card=c, instruction="Do it.")
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(restarted.dispatch_calls, [])
            state = courier.create_or_load_queue("RUN-CRASH")
            self.assertEqual(state["jobs"][c["work_card_id"]]["state"], "SUCCEEDED")

    def test_parser_extracts_last_json_object_from_thinking_or_prose(self):
        payload = mod.parse_json_worker_output('Thinking notes before output.\n```json\n{"draft":1}\n```\nFinal answer: {"status":"ok","items":[1,2]}')
        self.assertEqual(payload,{"status":"ok","items":[1,2]})

    def test_preferred_provider_is_forwarded_to_bridge_client(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            client = FakeClient([success_response()])
            c = card()
            mod.LiveWorkCardRunner(courier, client).run(run_id="RUN-PREF", card=c, instruction="Discover sources.", preferred_provider="copilot")
            self.assertEqual(client.dispatch_calls[0]["preferred_provider"],"copilot")

    def test_invalid_json_retries_bounded_then_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            client = FakeClient([success_response("not-json"), success_response('{"finding":"retry-pass"}', provider="gemini")])
            c = card(max_attempts=2)
            result = mod.LiveWorkCardRunner(courier, client).run(run_id="RUN-RETRY", card=c, instruction="Return JSON.")
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(result["attempt"], 2)
            self.assertEqual(len(client.dispatch_calls), 2)
            payload = courier.resolve(result["output_artifacts"][0])
            self.assertEqual(payload["finding"], "retry-pass")

    def test_semantic_validator_retries_before_artifact_commit(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            client = FakeClient([success_response('{"status":"bad"}'), success_response('{"status":"good"}', provider="gemini")])
            c = card(max_attempts=2)

            def validate(payload):
                if payload.get("status") != "good":
                    raise ValueError("SEMANTIC_OUTPUT_INVALID")
                return payload

            result = mod.LiveWorkCardRunner(courier, client).run(
                run_id="RUN-SEMANTIC", card=c, instruction="Return governed JSON.", payload_validator=validate
            )
            self.assertEqual(result["attempt"], 2)
            self.assertEqual(len(client.dispatch_calls), 2)
            self.assertEqual(courier.resolve(result["output_artifacts"][0])["status"], "good")

    def test_input_artifact_is_expanded_into_next_worker_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            upstream = courier.commit_payload(
                run_id="RUN-FANIN", artifact_id="UP-A", kind="problem_seed_batch",
                declared_schema="die.h03.problem-seed-batch.v1", producer_work_card_id="WC-UP",
                payload={"seeds": [{"problem_seed_id": "PS-1", "pain": "repeated admin work"}]},
            )
            client = FakeClient([success_response()])
            c = card(inputs=[upstream])
            mod.LiveWorkCardRunner(courier, client).run(run_id="RUN-FANIN", card=c, instruction="Evaluate demand.")
            prompt = client.dispatch_calls[0]["prompt"]
            self.assertIn("PS-1", prompt)
            self.assertIn("repeated admin work", prompt)
            self.assertIn("artifact://h03/RUN-FANIN/UP-A", prompt)

    def test_reviewer_role_maps_to_independent_reviewer_bridge_role(self):
        with tempfile.TemporaryDirectory() as td:
            courier = artifactmod.ArtifactCourier(td)
            client = FakeClient([success_response(provider="chatgpt")])
            c = card(role="REVIEWER", work_card_id="H03-WC-REVIEW")
            mod.LiveWorkCardRunner(courier, client).run(run_id="RUN-REV", card=c, instruction="Review.", dominant_producer_provider="claude")
            self.assertEqual(client.dispatch_calls[0]["role"], "INDEPENDENT_REVIEWER")
            self.assertEqual(client.dispatch_calls[0]["dominant_producer_provider"], "claude")


if __name__ == "__main__":
    unittest.main()
