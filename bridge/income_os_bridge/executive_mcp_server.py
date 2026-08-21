"""Executive Line 2 MCP transport over the P5/P6 decision contracts."""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable

from . import authority, decision_gateway, snapshot, state_request

SERVER_NAME = "die-executive-line2"
SERVER_VERSION = "1.1.0"
SERVER_INSTRUCTIONS = (
    "Call decision_submit only after obtaining a fresh Line 1 context_snapshot "
    "and explicit user confirmation. This is an append-only canonical write. "
    "Never fabricate evidence, identity, scope, or snapshot data; rejected "
    "receipts are final unless a new valid request is prepared."
)
TOOL_NAME = "decision_submit"
PRINCIPAL_ID = "chatgpt-plus-executive"
SCOPE = "company_portfolio"
MUTATION_RATE_LIMIT = 12
MUTATION_RATE_WINDOW_S = 60 * 60

REQUIRED_ARGUMENTS = {
    "request_id",
    "source_snapshot",
    "decision",
    "evidence_refs",
}
OPTIONAL_ARGUMENTS = {"assumptions"}

Writer = Callable[[dict[str, Any]], dict[str, Any]]


class MutationRateLimit:
    """Small process-local guard; replay safety remains canonical in State Manager."""

    def __init__(
        self,
        limit: int = MUTATION_RATE_LIMIT,
        window_s: int = MUTATION_RATE_WINDOW_S,
    ):
        self.limit = limit
        self.window_s = window_s
        self.times: deque[float] = deque()

    def allow(self, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        while self.times and current - self.times[0] > self.window_s:
            self.times.popleft()
        if len(self.times) >= self.limit:
            return False
        self.times.append(current)
        return True


_RATE = MutationRateLimit()


def tool_schema() -> dict[str, Any]:
    """Return the exact business-intent schema exposed to Executive cognition."""

    evidence = {
        "type": "object",
        "properties": {
            "evidence_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "kind": {"type": "string", "minLength": 1, "maxLength": 64},
            "ref": {"type": "string", "minLength": 1, "maxLength": 512},
            "claim": {"type": "string", "minLength": 1, "maxLength": 2000},
            "trust": {
                "type": "string",
                "enum": ["VERIFIED", "ASSUMED", "DEGRADED"],
            },
            "observed_at": {"type": "string", "minLength": 20, "maxLength": 40},
        },
        "required": [
            "evidence_id",
            "kind",
            "ref",
            "claim",
            "trust",
            "observed_at",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "request_id": {
                "type": "string",
                "pattern": r"^REQ-[A-Z0-9][A-Z0-9-]{2,63}$",
            },
            "source_snapshot": {
                "type": "object",
                "description": "Fresh die.context.snapshot.v1 returned by Line 1.",
            },
            "decision": {
                "type": "object",
                "properties": {
                    "decision_class": {
                        "type": "string",
                        "pattern": r"^[A-Za-z][A-Za-z0-9_-]{1,31}$",
                    },
                    "choice": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 4000},
                    "alternatives_rejected": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 500,
                        },
                        "maxItems": 20,
                    },
                },
                "required": ["decision_class", "choice", "reason"],
                "additionalProperties": False,
            },
            "evidence_refs": {
                "type": "array",
                "items": evidence,
                "maxItems": 50,
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string", "maxLength": 1000},
                "maxItems": 20,
            },
        },
        "required": sorted(REQUIRED_ARGUMENTS),
        "additionalProperties": False,
    }


def tool_definition() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": (
            "Submit one bounded Executive decision to the DIE Decision Gateway. "
            "This is an append-only canonical mutation after P5/P6 validation; "
            "present it for user confirmation before calling."
        ),
        "inputSchema": tool_schema(),
        "annotations": {
            "title": "Submit Executive Decision",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


def _request_id(arguments: Any) -> str | None:
    if not isinstance(arguments, dict):
        return None
    value = arguments.get("request_id")
    return value if isinstance(value, str) else None


def _rejected(code: str, message: str, arguments: Any = None) -> dict[str, Any]:
    return decision_gateway.rejected_result(
        code,
        message,
        _request_id(arguments),
    )


def submit_decision(
    arguments: Any,
    *,
    writer: Writer | None,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Translate the one MCP capability into P5 normalize -> P6 commit."""

    if not isinstance(arguments, dict):
        return _rejected(
            "E_MCP_INPUT_INVALID",
            "decision_submit arguments must be an object",
            arguments,
        )
    unknown = set(arguments) - REQUIRED_ARGUMENTS - OPTIONAL_ARGUMENTS
    missing = REQUIRED_ARGUMENTS - set(arguments)
    if unknown or missing:
        return _rejected(
            "E_MCP_INPUT_INVALID",
            "decision_submit has missing or unknown arguments",
            arguments,
        )
    if (
        not isinstance(arguments.get("source_snapshot"), dict)
        or not isinstance(arguments.get("decision"), dict)
        or not isinstance(arguments.get("evidence_refs"), list)
    ):
        return _rejected(
            "E_MCP_INPUT_INVALID",
            "source_snapshot, decision, and evidence_refs have invalid types",
            arguments,
        )
    assumptions = arguments.get("assumptions", [])
    if not isinstance(assumptions, list):
        return _rejected(
            "E_MCP_INPUT_INVALID",
            "assumptions must be an array",
            arguments,
        )

    request = {
        "schema_version": state_request.SCHEMA_VERSION,
        "request_id": arguments["request_id"],
        "principal_id": PRINCIPAL_ID,
        "scope": SCOPE,
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": arguments["decision"],
        "source_snapshot": arguments["source_snapshot"],
        "evidence_refs": arguments["evidence_refs"],
        "assumptions": assumptions,
    }

    try:
        normalized = state_request.validate_and_normalize(
            request,
            now=now,
            registry_path=registry_path,
        )
    except (
        state_request.StateRequestError,
        authority.AuthorizationError,
        snapshot.SnapshotError,
    ) as exc:
        return _rejected(
            getattr(exc, "code", "E_REQUEST_INVALID"),
            getattr(exc, "message", str(exc)),
            arguments,
        )
    except Exception:
        return _rejected(
            "E_MCP_DEGRADED",
            "Executive Line 2 request normalization failed closed",
            arguments,
        )

    return decision_gateway.process(
        normalized,
        writer=writer,
        now=now,
        registry_path=registry_path,
    )


def _tool_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "isError": result.get("status") != "committed",
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False),
            }
        ],
    }


def call_tool(
    name: Any,
    arguments: Any,
    *,
    writer: Writer | None,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
    rate_limit: MutationRateLimit | None = None,
) -> dict[str, Any]:
    if name != TOOL_NAME:
        return _tool_result(
            _rejected(
                "E_MCP_TOOL_NOT_FOUND",
                "Executive Line 2 exposes only decision_submit",
                arguments,
            )
        )
    limiter = _RATE if rate_limit is None else rate_limit
    if not limiter.allow():
        return _tool_result(
            _rejected(
                "E_MCP_RATE_LIMIT",
                "Executive Line 2 mutation rate limit exceeded",
                arguments,
            )
        )
    return _tool_result(
        submit_decision(
            arguments,
            writer=writer,
            now=now,
            registry_path=registry_path,
        )
    )


def handle(
    message: Any,
    *,
    writer: Writer | None,
    now: dt.datetime | None = None,
    registry_path: str | Path | None = None,
    rate_limit: MutationRateLimit | None = None,
) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "invalid request"},
        }

    method = message.get("method")
    ident = message.get("id")
    raw_params = message.get("params")
    if raw_params is not None and not isinstance(raw_params, dict):
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "error": {"code": -32602, "message": "invalid params"},
        }
    params = raw_params or {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "instructions": SERVER_INSTRUCTIONS,
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {"tools": [tool_definition()]},
        }
    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": call_tool(
                params.get("name"),
                params.get("arguments") or {},
                writer=writer,
                now=now,
                registry_path=registry_path,
                rate_limit=rate_limit,
            ),
        }
    return {
        "jsonrpc": "2.0",
        "id": ident,
        "error": {"code": -32601, "message": "method not found"},
    }


def serve(*, writer: Writer | None) -> int:
    """Serve newline-delimited MCP JSON-RPC on stdio, serially and fail closed."""

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "parse error"},
            }
        else:
            response = handle(message, writer=writer)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0
