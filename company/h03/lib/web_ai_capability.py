from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

REQUEST_SCHEMA = "die.h03.web-ai.text-capability-request.v1"
RESPONSE_SCHEMA = "die.h03.web-ai.text-capability-response.v1"
_ALLOWED_ROLES = {"CURATOR", "PRODUCER"}
_FORBIDDEN_KEYS = {"cookie", "cookies", "token", "tokens", "access_token", "refresh_token", "authorization", "browser_profile", "profile_path", "oauth", "session_bytes", "session_key", "credential", "credentials"}


def _walk_forbidden(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in _FORBIDDEN_KEYS:
                raise ValueError(f"SESSION_OR_CREDENTIAL_MATERIAL_FORBIDDEN:{path}.{k}")
            _walk_forbidden(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk_forbidden(v, f"{path}[{i}]")


def validate_capability_request(req: dict[str, Any]) -> None:
    if req.get("schema_version") != REQUEST_SCHEMA or req.get("holding_id") != "H03":
        raise ValueError("CAPABILITY_SCHEMA_INVALID")
    if req.get("role") not in _ALLOWED_ROLES:
        raise ValueError("CAPABILITY_ROLE_INVALID")
    for field in ("request_id", "task_id", "model_route", "prompt"):
        if not isinstance(req.get(field), str) or not req[field].strip():
            raise ValueError(f"CAPABILITY_FIELD_REQUIRED:{field}")
    if req.get("output_mode", "TEXT") not in {"TEXT", "JSON"}:
        raise ValueError("OUTPUT_MODE_INVALID")
    _walk_forbidden(req)


def build_openai_payload(req: dict[str, Any]) -> dict[str, Any]:
    validate_capability_request(req)
    role_instruction = (
        "Act as H03 curator. Analyze, compare, classify, critique, or propose. Do not claim model output is evidence or canonical truth."
        if req["role"] == "CURATOR"
        else "Act as H03 semantic producer. Produce requested draft content only. Do not invent source provenance, rights, sales, costs, or canonical truth."
    )
    context = req.get("context") or {}
    user_text = req["prompt"]
    if context:
        user_text += "\n\n[H03 governed context]\n" + json.dumps(context, ensure_ascii=False, sort_keys=True)
    return {
        "model": req["model_route"],
        "stream": False,
        "messages": [
            {"role":"system","content":role_instruction},
            {"role":"user","content":user_text},
        ],
    }


def normalize_openai_response(req: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    choices = raw.get("choices") or []
    if not choices:
        raise ValueError("WEB_AI_RESPONSE_CHOICES_MISSING")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("WEB_AI_RESPONSE_CONTENT_INVALID")
    return {
        "schema_version": RESPONSE_SCHEMA,
        "request_id": req["request_id"],
        "holding_id": "H03",
        "role": req["role"],
        "task_id": req["task_id"],
        "model_route": req["model_route"],
        "content": content,
        "usage": raw.get("usage") or {},
        "truth_status": "UNVERIFIED_MODEL_OUTPUT",
        "canonical_truth": False,
        "session_material_persisted": False,
    }


class WebAITextClient:
    def __init__(self, endpoint: str = "http://127.0.0.1:8456", timeout_seconds: float = 120.0,
                 transport: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _http_transport(self, url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError("WEB_AI_AUTH_REQUIRED") from exc
            if exc.code == 429:
                raise RuntimeError("WEB_AI_RATE_LIMITED") from exc
            raise RuntimeError(f"WEB_AI_HTTP_ERROR:{exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("WEB_AI_UNAVAILABLE") from exc

    def complete(self, req: dict[str, Any]) -> dict[str, Any]:
        payload = build_openai_payload(req)
        tx = self.transport or self._http_transport
        raw = tx(self.endpoint.rstrip("/") + "/v1/chat/completions", payload, self.timeout_seconds)
        return normalize_openai_response(req, raw)
