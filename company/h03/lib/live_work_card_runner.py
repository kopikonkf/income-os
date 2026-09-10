from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import artifact_courier
import cognition_work_card
import orchestrator_queue

MC_ROLE_MAP = {
    "SEED_CURATOR": "SEED_CURATOR",
    "MARKET_RESEARCHER": "MARKET_RESEARCHER",
    "KNOWLEDGE_RESEARCHER": "KNOWLEDGE_RESEARCHER",
    "SYNTHESIZER": "SYNTHESIZER",
    "PRODUCT_ARCHITECT": "PRODUCT_ARCHITECT",
    "PRODUCER": "PRODUCER",
    "REVIEWER": "INDEPENDENT_REVIEWER",
}


def _strip_json_fence(text: str) -> str:
    value = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else value


def parse_json_worker_output(text: str) -> Any:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("WORKER_OUTPUT_EMPTY")
    try:
        return json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise ValueError("WORKER_OUTPUT_JSON_INVALID") from exc


class MissionControlH03Client:
    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8891",
        timeout_seconds: float = 180.0,
        transport: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport or self._http_transport

    @staticmethod
    def _http_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:4000]
            except Exception:
                detail = ""
            raise RuntimeError(f"MC_HTTP_ERROR:{exc.code}:{detail}") from exc
        except URLError as exc:
            raise RuntimeError("MC_UNAVAILABLE") from exc

    def dispatch(
        self,
        *,
        role: str,
        prompt: str,
        max_routes: int = 3,
        timeout_seconds: int | None = None,
        dominant_producer_provider: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": role,
            "prompt": prompt,
            "maxRoutes": max_routes,
            "timeoutSeconds": timeout_seconds or int(self.timeout_seconds),
        }
        if dominant_producer_provider:
            payload["dominantProducerProvider"] = dominant_producer_provider
        return self.transport(self.endpoint + "/api/h03/bridge/dispatch", payload, self.timeout_seconds + 30)

    def emit(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.transport(self.endpoint + "/api/h03/runtime/event", event, 20.0)


class LiveWorkCardRunner:
    def __init__(
        self,
        courier: artifact_courier.ArtifactCourier,
        client: MissionControlH03Client,
        *,
        max_input_chars: int = 80_000,
        fault_hook: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.courier = courier
        self.client = client
        self.max_input_chars = max_input_chars
        self.fault_hook = fault_hook

    def _emit(self, *, run_id: str, card: dict[str, Any], state: str, **extra: Any) -> None:
        event = {
            "schema_version": "die.h03.runtime-event.v1",
            "holding_id": "H03",
            "run_id": run_id,
            "work_card_id": card["work_card_id"],
            "task_id": card["task_id"],
            "role": card["role"],
            "queue": card["queue"],
            "state": state,
            **extra,
        }
        try:
            self.client.emit(event)
        except Exception:
            # Telemetry must not corrupt the durable H03 work state.
            pass

    @staticmethod
    def _apply_committed_result(
        queue_state: dict[str, Any], card: dict[str, Any], result: dict[str, Any]
    ) -> None:
        job = queue_state["jobs"][card["work_card_id"]]
        if job["state"] == "SUCCEEDED":
            return
        if job["state"] == "QUEUED":
            orchestrator_queue.transition(queue_state, card["work_card_id"], "DISPATCHED")
        if job["state"] == "FAILED_RETRYABLE":
            orchestrator_queue.transition(queue_state, card["work_card_id"], "QUEUED")
            orchestrator_queue.transition(queue_state, card["work_card_id"], "DISPATCHED")
        if queue_state["jobs"][card["work_card_id"]]["state"] in {"DISPATCHED", "RUNNING"}:
            orchestrator_queue.apply_result(queue_state, card, result)
            return
        raise ValueError("WORK_CARD_RECOVERY_STATE_INVALID")

    def _recover_interrupted_job(self, queue_state: dict[str, Any], card: dict[str, Any]) -> None:
        job = queue_state["jobs"][card["work_card_id"]]
        if job["state"] in {"DISPATCHED", "RUNNING"}:
            orchestrator_queue.transition(queue_state, card["work_card_id"], "FAILED_RETRYABLE")
            if job["attempt"] >= card["terminal_policy"]["max_attempts"]:
                orchestrator_queue.transition(queue_state, card["work_card_id"], "FAILED_TERMINAL")
            else:
                orchestrator_queue.transition(queue_state, card["work_card_id"], "QUEUED")

    def _prompt(self, card: dict[str, Any], instruction: str) -> str:
        expanded = self.courier.expand_inputs(card, max_chars=self.max_input_chars)
        contract = card["output_contract"]
        return (
            f"H03 WORK CARD {card['work_card_id']}\n"
            f"ROLE: {card['role']}\n"
            f"TASK: {instruction.strip()}\n\n"
            "INPUT ARTIFACTS (durable orchestrator expansion; the browser worker has no filesystem access):\n"
            f"{expanded if expanded else '[none]'}\n\n"
            "OUTPUT CONTRACT:\n"
            f"artifact_kind={contract['artifact_kind']}\n"
            f"schema_version={contract['schema_version']}\n\n"
            "Return exactly one valid JSON value and no Markdown fence. Preserve evidence references supplied in the inputs. "
            "Do not invent credentials, browser/session material, publication, revenue, or canonical truth."
        )

    def run(
        self,
        *,
        run_id: str,
        card: dict[str, Any],
        instruction: str,
        max_routes: int = 3,
        timeout_seconds: int = 180,
        dominant_producer_provider: str | None = None,
    ) -> dict[str, Any]:
        cognition_work_card.validate_work_card(card)
        if card["role"] not in MC_ROLE_MAP:
            raise ValueError("WORK_CARD_ROLE_NOT_LIVE_BRIDGED")
        if card["capability_requirements"] != cognition_work_card.standard_web_ai_capabilities():
            raise ValueError("WORK_CARD_LIVE_CAPABILITY_BOUNDARY_INVALID")

        state = self.courier.create_or_load_queue(run_id)
        if card["work_card_id"] not in state["jobs"]:
            orchestrator_queue.enqueue(state, card)
            self.courier.save_queue(run_id, state)
            self._emit(run_id=run_id, card=card, state="QUEUED")

        committed = self.courier.load_result_receipt(run_id, card)
        if committed:
            self._apply_committed_result(state, card, committed)
            self.courier.save_queue(run_id, state)
            self._emit(
                run_id=run_id,
                card=card,
                state="SUCCEEDED",
                recovery="RESULT_RECEIPT_REPLAY",
                output_artifacts=committed["output_artifacts"],
            )
            return committed

        self._recover_interrupted_job(state, card)
        self.courier.save_queue(run_id, state)
        job = state["jobs"][card["work_card_id"]]
        if job["state"] == "FAILED_TERMINAL":
            raise RuntimeError("WORK_CARD_ATTEMPTS_EXHAUSTED")

        prompt = self._prompt(card, instruction)
        max_attempts = card["terminal_policy"]["max_attempts"]

        while state["jobs"][card["work_card_id"]]["attempt"] < max_attempts:
            job = state["jobs"][card["work_card_id"]]
            if job["state"] == "FAILED_RETRYABLE":
                orchestrator_queue.transition(state, card["work_card_id"], "QUEUED")
            if job["state"] != "QUEUED":
                raise ValueError(f"WORK_CARD_RUN_STATE_INVALID:{job['state']}")

            orchestrator_queue.transition(state, card["work_card_id"], "DISPATCHED")
            self.courier.save_queue(run_id, state)
            self._emit(run_id=run_id, card=card, state="DISPATCHED")

            orchestrator_queue.transition(state, card["work_card_id"], "RUNNING")
            self.courier.save_queue(run_id, state)
            attempt = state["jobs"][card["work_card_id"]]["attempt"]
            self._emit(run_id=run_id, card=card, state="RUNNING", attempt=attempt)

            try:
                response = self.client.dispatch(
                    role=MC_ROLE_MAP[card["role"]],
                    prompt=prompt,
                    max_routes=max_routes,
                    timeout_seconds=timeout_seconds,
                    dominant_producer_provider=dominant_producer_provider,
                )
                self._emit(
                    run_id=run_id,
                    card=card,
                    state="OUTPUT_RECEIVED",
                    attempt=attempt,
                    provider=(response.get("route") or {}).get("provider_id"),
                    effective_model=response.get("effective_model"),
                    effective_mode=response.get("effective_mode"),
                    route_attempts=response.get("attempts") or [],
                )
                if not response.get("ok"):
                    raise RuntimeError("MC_BRIDGE_DISPATCH_FAILED")
                payload = parse_json_worker_output(response.get("response_text") or "")
                artifact_id = f"{card['work_card_id']}-OUT"
                artifact_ref = self.courier.commit_payload(
                    run_id=run_id,
                    artifact_id=artifact_id,
                    kind=card["output_contract"]["artifact_kind"],
                    declared_schema=card["output_contract"]["schema_version"],
                    producer_work_card_id=card["work_card_id"],
                    payload=payload,
                )
                self._emit(
                    run_id=run_id,
                    card=card,
                    state="ARTIFACT_COMMITTED",
                    attempt=attempt,
                    artifact=artifact_ref,
                )
                result = {
                    "schema_version": cognition_work_card.RESULT_SCHEMA,
                    "work_card_id": card["work_card_id"],
                    "attempt": attempt,
                    "status": "SUCCEEDED",
                    "output_artifacts": [artifact_ref],
                    "worker_observation": {
                        "provider_id": (response.get("route") or {}).get("provider_id"),
                        "effective_model": response.get("effective_model"),
                        "effective_mode": response.get("effective_mode"),
                        "route_attempts": response.get("attempts") or [],
                    },
                }
                self.courier.save_result_receipt(run_id, card, result)
                if self.fault_hook:
                    self.fault_hook("AFTER_RESULT_RECEIPT_COMMIT", result)
                orchestrator_queue.apply_result(state, card, result)
                self.courier.save_queue(run_id, state)
                self._emit(
                    run_id=run_id,
                    card=card,
                    state="SUCCEEDED",
                    attempt=attempt,
                    output_artifacts=[artifact_ref],
                )
                return result
            except Exception as exc:
                retryable = state["jobs"][card["work_card_id"]]["attempt"] < max_attempts
                failure = {
                    "schema_version": cognition_work_card.RESULT_SCHEMA,
                    "work_card_id": card["work_card_id"],
                    "attempt": attempt,
                    "status": "FAILED_RETRYABLE" if retryable else "FAILED_TERMINAL",
                    "output_artifacts": [],
                    "worker_observation": {"error": f"{type(exc).__name__}:{exc}"[:1000]},
                }
                orchestrator_queue.apply_result(state, card, failure)
                self.courier.save_queue(run_id, state)
                self._emit(
                    run_id=run_id,
                    card=card,
                    state=failure["status"],
                    attempt=attempt,
                    error=failure["worker_observation"]["error"],
                )
                if not retryable:
                    raise RuntimeError("WORK_CARD_FAILED_TERMINAL") from exc

        raise RuntimeError("WORK_CARD_ATTEMPTS_EXHAUSTED")
