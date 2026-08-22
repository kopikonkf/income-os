"""Least-privilege Runtime Decision MCP for Executive and Division cognition.

This is a loopback transport over the existing semantic projection, P5 state
request, P6 Decision Gateway, and DIE State Manager writer. It is not a second
control plane and exposes no filesystem, shell, Git, test, service, credential,
or arbitrary state-write primitive.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hmac
import json
import os
import pathlib
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

from . import authority, config, decision_gateway, mcp_server, state_request

SERVER_NAME = "die-runtime-decision-mcp"
SERVER_VERSION = "1.0.0"
HTTP_PATH = "/mcp"
LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
MAX_REQUEST_BYTES = 262_144
PROJECT_ROOT = pathlib.Path(r"C:\DIE")
AETHER_HOME = pathlib.Path(
    r"C:\Users\aethers\AppData\Local\hermes\profiles\income-operator"
)
WORKSPACE_ROOTS = (
    PROJECT_ROOT / "workspaces",
    PROJECT_ROOT / "STATE",
)
RUNTIME_FORBIDDEN = re.compile(
    r"(?i)\b(select|union|drop)\b|\b(exec|eval)\b|"
    r"\.\.[\\/]|\bbearer\s+\S+|\bsk-[A-Za-z0-9_-]+"
)

Writer = Callable[[dict[str, Any]], dict[str, Any]]

EXECUTIVE_PROJECTION_TOOLS = frozenset(
    {
        "system_health",
        "system_state",
        "active_missions",
        "mission_get",
        "workers",
        "scheduled_jobs",
        "capabilities",
        "recent_events",
        "search_sessions",
        "session_get",
        "briefing_get",
    }
)
EXECUTIVE_READ_TOOLS = EXECUTIVE_PROJECTION_TOOLS | {"context_snapshot"}
DIVISION_READ_TOOLS = frozenset({"context_snapshot"})
CONTROL_CAPABILITIES = {
    "propose_mission": "mission_proposal",
    "pause_mission": "bounded_decision",
    "resume_mission": "bounded_decision",
    "request_audit": "audit_request",
    "challenge": "bounded_decision",
    "escalate": "escalation",
}
COMMON_REQUIRED = {
    "request_id",
    "source_snapshot",
    "reason",
    "evidence_refs",
}
COMMON_OPTIONAL = {"assumptions"}
CONTROL_FIELDS = {
    "propose_mission": {
        "required": {"mission_id", "goal", "buyer_path", "kill_criteria"},
        "optional": set(),
    },
    "pause_mission": {"required": {"mission_id"}, "optional": set()},
    "resume_mission": {"required": {"mission_id"}, "optional": set()},
    "request_audit": {"required": {"target_ref"}, "optional": set()},
    "challenge": {"required": {"target_ref", "claim"}, "optional": set()},
    "escalate": {
        "required": {"target_ref", "escalation_target"},
        "optional": set(),
    },
}
_RUNTIME_RATE = mcp_server.RateLimit()


class RuntimeMcpError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _identity(principal_id: str, registry_path: str | pathlib.Path | None) -> dict[str, Any]:
    registry = authority.load_registry(registry_path)
    identity = next(
        (
            row
            for row in registry.get("identities", [])
            if isinstance(row, dict) and row.get("id") == principal_id
        ),
        None,
    )
    if identity is None:
        raise RuntimeMcpError(
            "E_UNAUTHORIZED_PRINCIPAL",
            "runtime principal is not registered",
        )
    if identity.get("runtime") is not True or identity.get("template") is True:
        raise RuntimeMcpError(
            "E_UNAUTHORIZED_PRINCIPAL",
            "runtime MCP requires a concrete runtime identity",
        )
    if identity.get("architect_dev_access") != "deny":
        raise RuntimeMcpError(
            "E_DEV_PRIVILEGE_DENIED",
            "runtime principal must deny Architect DEV access",
        )
    forbidden = set(
        registry.get("security", {}).get("runtime_forbidden_capabilities", [])
    )
    capabilities = {
        item for item in identity.get("capabilities", []) if isinstance(item, str)
    }
    if capabilities & forbidden or identity.get("inherits_identity_ids"):
        raise RuntimeMcpError(
            "E_DEV_PRIVILEGE_DENIED",
            "runtime principal contains inherited or DEV-reserved capability",
        )
    return identity


def _read_tools(identity: dict[str, Any]) -> frozenset[str]:
    if identity.get("kind") == "executive_strategic_intelligence":
        return EXECUTIVE_READ_TOOLS
    if identity.get("kind") == "division_decision_engine":
        return DIVISION_READ_TOOLS
    return frozenset()


def _control_tools(identity: dict[str, Any]) -> frozenset[str]:
    capabilities = set(identity.get("capabilities", []))
    return frozenset(
        tool
        for tool, capability in CONTROL_CAPABILITIES.items()
        if capability in capabilities
    )


def _evidence_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "evidence_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "kind": {"type": "string", "minLength": 1, "maxLength": 64},
                "ref": {"type": "string", "minLength": 1, "maxLength": 512},
                "claim": {"type": "string", "minLength": 1, "maxLength": 2000},
                "trust": {"type": "string", "enum": ["VERIFIED", "ASSUMED", "DEGRADED"]},
                "observed_at": {"type": "string", "minLength": 20, "maxLength": 40},
            },
            "required": ["evidence_id", "kind", "ref", "claim", "trust", "observed_at"],
            "additionalProperties": False,
        },
        "maxItems": 50,
    }


def _control_schema(name: str) -> dict[str, Any]:
    props: dict[str, Any] = {
        "request_id": {"type": "string", "pattern": r"^REQ-[A-Z0-9][A-Z0-9-]{2,63}$"},
        "source_snapshot": {"type": "object"},
        "reason": {"type": "string", "minLength": 1, "maxLength": 4000},
        "evidence_refs": _evidence_schema(),
        "assumptions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 1000},
            "maxItems": 20,
        },
    }
    for field in CONTROL_FIELDS[name]["required"]:
        if field == "mission_id":
            props[field] = {"type": "string", "pattern": r"^M-[0-9]{3,6}$"}
        elif field == "kill_criteria":
            props[field] = {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 1000},
                "minItems": 1,
                "maxItems": 20,
            }
        elif field == "escalation_target":
            props[field] = {
                "type": "string",
                "enum": ["chatgpt-plus-executive", "founder"],
            }
        else:
            props[field] = {"type": "string", "minLength": 1, "maxLength": 2000}
    required = sorted(COMMON_REQUIRED | CONTROL_FIELDS[name]["required"])
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


def _tool_definition(name: str) -> dict[str, Any]:
    if name == "context_snapshot":
        schema = {
            "type": "object",
            "properties": {
                "since_seq": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        }
        read_only = True
    elif name in mcp_server.TOOLS:
        schema = mcp_server._schema(name)
        read_only = True
    else:
        schema = _control_schema(name)
        read_only = False
    return {
        "name": name,
        "description": (
            f"Read bounded semantic DIE surface {name}."
            if read_only
            else f"Submit a governed {name} request for State Manager commit and Hermes acceptance."
        ),
        "inputSchema": schema,
        "annotations": {
            "title": name.replace("_", " ").title(),
            "readOnlyHint": read_only,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


def tool_definitions(
    principal_id: str,
    registry_path: str | pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    identity = _identity(principal_id, registry_path)
    names = sorted(_read_tools(identity) | _control_tools(identity))
    return [_tool_definition(name) for name in names]


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "isError": True,
        "content": [{"type": "text", "text": f"{code}: {message}"}],
    }


def _tool_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "isError": result.get("status") != "committed",
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
    }


def _reject_raw(value: Any) -> None:
    if isinstance(value, str):
        if RUNTIME_FORBIDDEN.search(value) or state_request.RAW_ACCESS.search(value):
            raise RuntimeMcpError(
                "E_NO_RAW_ACCESS",
                "request contains raw-access, traversal, executable, or credential-shaped content",
            )
    elif isinstance(value, list):
        for item in value:
            _reject_raw(item)
    elif isinstance(value, dict):
        for item in value.values():
            _reject_raw(item)


def _validate_control(name: str, arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "control arguments must be an object")
    spec = CONTROL_FIELDS[name]
    allowed = COMMON_REQUIRED | COMMON_OPTIONAL | spec["required"] | spec["optional"]
    missing = (COMMON_REQUIRED | spec["required"]) - set(arguments)
    unknown = set(arguments) - allowed
    if missing or unknown:
        raise RuntimeMcpError(
            "E_MCP_INPUT_INVALID",
            "control request has missing or unknown fields",
        )
    encoded = json.dumps(arguments, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        raise RuntimeMcpError("E_TOO_LARGE", "control request exceeds 262144 bytes")
    request_id = arguments.get("request_id")
    if not isinstance(request_id, str) or not state_request.REQUEST_ID.fullmatch(request_id):
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "request_id format is invalid")
    if not isinstance(arguments.get("source_snapshot"), dict):
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "source_snapshot must be an object")
    if not isinstance(arguments.get("evidence_refs"), list):
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "evidence_refs must be an array")
    assumptions = arguments.get("assumptions", [])
    if not isinstance(assumptions, list) or any(not isinstance(item, str) for item in assumptions):
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "assumptions must be an array of strings")
    for field in spec["required"] | {"reason"}:
        value = arguments.get(field)
        if field == "kill_criteria":
            if not isinstance(value, list) or not value or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise RuntimeMcpError(
                    "E_MCP_INPUT_INVALID",
                    "kill_criteria must contain at least one non-empty criterion",
                )
        elif not isinstance(value, str) or not value.strip():
            raise RuntimeMcpError("E_MCP_INPUT_INVALID", f"{field} must be a non-empty string")
    if "mission_id" in arguments and mcp_server.validate(
        "mission_get", {"mission_id": arguments["mission_id"]}
    ) is not None:
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "mission_id format is invalid")
    if name == "escalate" and arguments["escalation_target"] not in {
        "chatgpt-plus-executive",
        "founder",
    }:
        raise RuntimeMcpError("E_MCP_INPUT_INVALID", "escalation_target is invalid")
    _reject_raw(arguments)
    return arguments


def _choice(name: str, arguments: dict[str, Any]) -> str:
    if name == "propose_mission":
        return f"Propose {arguments['mission_id']}: {arguments['goal']}"
    if name in {"pause_mission", "resume_mission"}:
        verb = "Pause" if name == "pause_mission" else "Resume"
        return f"{verb} {arguments['mission_id']}"
    if name == "request_audit":
        return f"Request audit of {arguments['target_ref']}"
    if name == "challenge":
        return f"Challenge {arguments['target_ref']}: {arguments['claim']}"
    return f"Escalate {arguments['target_ref']} to {arguments['escalation_target']}"


def _submit_control(
    name: str,
    arguments: Any,
    *,
    principal_id: str,
    identity: dict[str, Any],
    writer: Writer | None,
    now: dt.datetime | None,
    registry_path: str | pathlib.Path | None,
) -> dict[str, Any]:
    args = _validate_control(name, arguments)
    capability = CONTROL_CAPABILITIES[name]
    if capability not in set(identity.get("capabilities", [])):
        return decision_gateway.rejected_result(
            "E_FORBIDDEN_ACTION",
            "runtime principal lacks the required bounded capability",
            args["request_id"],
        )
    decision: dict[str, Any] = {
        "decision_class": name,
        "choice": _choice(name, args),
        "reason": args["reason"].strip(),
        "alternatives_rejected": [],
        "control_action": name,
    }
    for field in CONTROL_FIELDS[name]["required"] | CONTROL_FIELDS[name]["optional"]:
        decision[field] = args[field]
    if identity.get("division_id"):
        decision["division_id"] = identity["division_id"]
    request = {
        "schema_version": state_request.SCHEMA_VERSION,
        "request_id": args["request_id"],
        "principal_id": principal_id,
        "scope": identity["scope"],
        "action": "state.decision.submit",
        "object_type": "DECISION",
        "object": decision,
        "source_snapshot": args["source_snapshot"],
        "evidence_refs": args["evidence_refs"],
        "assumptions": args.get("assumptions", []),
    }
    try:
        normalized = state_request.validate_and_normalize(
            request,
            now=now,
            registry_path=registry_path,
        )
    except (state_request.StateRequestError, authority.AuthorizationError) as exc:
        return decision_gateway.rejected_result(
            getattr(exc, "code", "E_REQUEST_INVALID"),
            getattr(exc, "message", str(exc)),
            args["request_id"],
        )
    return decision_gateway.process(
        normalized,
        writer=writer,
        now=now,
        registry_path=registry_path,
    )


def call_tool(
    name: Any,
    arguments: Any,
    *,
    principal_id: str,
    writer: Writer | None,
    now: dt.datetime | None = None,
    registry_path: str | pathlib.Path | None = None,
    rate_limit: mcp_server.RateLimit | None = None,
) -> dict[str, Any]:
    try:
        identity = _identity(principal_id, registry_path)
        reads = _read_tools(identity)
        controls = _control_tools(identity)
        if name in reads:
            supplied = arguments or {}
            if not isinstance(supplied, dict):
                return _error("E_NO_RAW_ACCESS", "arguments must be an object")
            if name == "context_snapshot":
                if set(supplied) - {"since_seq", "limit"}:
                    return _error("E_NO_RAW_ACCESS", "principal and scope are server-pinned")
                supplied = dict(supplied)
                supplied["principal_id"] = principal_id
                supplied["scope"] = identity["scope"]
            return mcp_server.call_tool(name, supplied)
        if name in controls:
            limiter = rate_limit or _RUNTIME_RATE
            if not limiter.allow():
                return _error("E_RATE_LIMIT", "> 60 runtime requests / hour")
            return _tool_result(
                _submit_control(
                    name,
                    arguments,
                    principal_id=principal_id,
                    identity=identity,
                    writer=writer,
                    now=now,
                    registry_path=registry_path,
                )
            )
        return _error("E_NO_RAW_ACCESS", "tool is not available to this runtime principal")
    except RuntimeMcpError as exc:
        return _error(exc.code, exc.message)


def handle(
    message: Any,
    *,
    principal_id: str,
    writer: Writer | None,
    registry_path: str | pathlib.Path | None = None,
    rate_limit: mcp_server.RateLimit | None = None,
) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
    method = message.get("method")
    ident = message.get("id")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": "invalid params"}}
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        identity = _identity(principal_id, registry_path)
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    f"Runtime principal {principal_id} ({identity['scope']}) is server-pinned. "
                    f"Operational control plane: {config.OPERATIONAL_CONTROL_PLANE}; "
                    f"canonical writer: {config.CANONICAL_WRITER}. No raw or DEV access."
                ),
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {"tools": tool_definitions(principal_id, registry_path)},
        }
    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": ident,
            "result": call_tool(
                params.get("name"),
                params.get("arguments") or {},
                principal_id=principal_id,
                writer=writer,
                registry_path=registry_path,
                rate_limit=rate_limit,
            ),
        }
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "method not found"}}


def _runtime_token() -> str:
    token = os.environ.get("DIE_MCP_TOKEN") or os.environ.get("OPERATOR_TOKEN")
    if not token or len(token.encode("utf-8")) < 32:
        raise RuntimeMcpError(
            "E_RUNTIME_TOKEN_REQUIRED",
            "DIE_MCP_TOKEN or OPERATOR_TOKEN must contain at least 32 bytes",
        )
    return token


def serve_http(
    *,
    principal_id: str,
    writer: Writer | None,
    port: int = DEFAULT_PORT,
    registry_path: str | pathlib.Path | None = None,
) -> int:
    token = _runtime_token()
    limiter = mcp_server.RateLimit()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path != HTTP_PATH:
                self.send_error(404)
                return
            supplied = self.headers.get("Authorization", "")
            expected = "Bearer " + token
            if not hmac.compare_digest(supplied, expected):
                self.send_error(401)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self.send_error(413)
                return
            try:
                message = json.loads(self.rfile.read(length).decode("utf-8"))
                response = handle(
                    message,
                    principal_id=principal_id,
                    writer=writer,
                    registry_path=registry_path,
                    rate_limit=limiter,
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            if response is None:
                self.send_response(204)
                self.end_headers()
                return
            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    _identity(principal_id, registry_path)
    server = HTTPServer((LOOPBACK_HOST, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog=SERVER_NAME)
    parser.add_argument("--principal-id", default=os.environ.get("DIE_RUNTIME_PRINCIPAL_ID"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if not args.principal_id:
        print("E_UNAUTHORIZED_PRINCIPAL: --principal-id is required", file=sys.stderr)
        return 2
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "bin"))
    import die_event  # type: ignore  # noqa: E402

    try:
        return serve_http(
            principal_id=args.principal_id,
            writer=die_event.commit_normalized_decision,
            port=args.port,
        )
    except RuntimeMcpError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
