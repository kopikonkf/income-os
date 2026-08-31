"""Least-privilege Runtime Decision MCP for Executive and Division cognition.

This is a loopback transport over the existing semantic projection, P5 state
request, P6 Decision Gateway, and DIE State Manager writer. It is not a second
control plane and exposes no filesystem, shell, Git, test, service, credential,
or arbitrary state-write primitive.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from . import (
    authority,
    config,
    decision_gateway,
    mcp_server,
    runtime_mcp_oauth,
    state_request,
)

SERVER_NAME = "die-runtime-decision-mcp"
SERVER_VERSION = "1.2.0"
HTTP_PATH = "/mcp"
LOOPBACK_HOST = "127.0.0.1"
PRINCIPAL_DEFAULT_PORTS = {
    "chatgpt-plus-executive": 8791,
    "division-head-division01": 8792,
    "die-lnx-executive-001": 8891,
    "die-lnx-division-001": 8892,
}
PRINCIPAL_PUBLIC_BASE_URLS = {
    "chatgpt-plus-executive": "https://executive-mcp.aethers.web.id",
    "division-head-division01": "https://division01-mcp.aethers.web.id",
    "die-lnx-executive-001": "https://executive-mcp.aethers.biz.id",
    "die-lnx-division-001": "https://division01-mcp.aethers.biz.id",
}
PRINCIPAL_OAUTH_CLIENT_IDS = {
    "chatgpt-plus-executive": "chatgpt-executive",
    "division-head-division01": "chatgpt-division01",
    "die-lnx-executive-001": "chatgpt-die-lnx-executive-001",
    "die-lnx-division-001": "chatgpt-die-lnx-division-001",
}
INSTANCE_EXECUTIVE_PRINCIPALS = {
    "DIE-WINDOWS": "chatgpt-plus-executive",
    "DIE-LINUX": "die-lnx-executive-001",
}
INFRASTRUCTURE_RESERVED_PORTS = frozenset({8787, 8789, 8790})
CONTROL_POLICY_ENABLED = "enabled"
CONTROL_POLICY_STAGING_READ_ONLY = "staging-read-only"
CONTROL_POLICIES = frozenset({CONTROL_POLICY_ENABLED, CONTROL_POLICY_STAGING_READ_ONLY})
MAX_REQUEST_BYTES = 262_144
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


def _executive_peer_id(identity: dict[str, Any]) -> str:
    instance_id = identity.get("company_instance_id")
    peer = INSTANCE_EXECUTIVE_PRINCIPALS.get(instance_id)
    if peer is None:
        # Compatibility for legacy registries/tests that predate instance metadata.
        return "chatgpt-plus-executive"
    return peer


def _control_schema(name: str, identity: dict[str, Any]) -> dict[str, Any]:
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
                "enum": [_executive_peer_id(identity), "founder"],
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


def _tool_definition(name: str, identity: dict[str, Any]) -> dict[str, Any]:
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
        schema = _control_schema(name, identity)
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
    return [_tool_definition(name, identity) for name in names]


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


def _validate_control(
    name: str,
    arguments: Any,
    identity: dict[str, Any],
) -> dict[str, Any]:
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
        _executive_peer_id(identity),
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
    args = _validate_control(name, arguments, identity)
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
    control_policy: str | None = None,
) -> dict[str, Any]:
    try:
        effective_control_policy = _runtime_control_policy(control_policy)
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
            if effective_control_policy != CONTROL_POLICY_ENABLED:
                return _error(
                    "E_STAGING_READ_ONLY",
                    "runtime control calls are disabled by the server-pinned staging policy",
                )
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
    control_policy: str | None = None,
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
        effective_control_policy = _runtime_control_policy(control_policy)
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
                    f"canonical writer: {config.CANONICAL_WRITER}. "
                    f"Control policy: {effective_control_policy}. No raw or DEV access."
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
                control_policy=control_policy,
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


def _runtime_login_password() -> str:
    value = os.environ.get("DIE_MCP_LOGIN_PASSWORD")
    if not value or len(value) < 16:
        raise RuntimeMcpError(
            "E_RUNTIME_LOGIN_REQUIRED",
            "DIE_MCP_LOGIN_PASSWORD must contain at least 16 characters",
        )
    return value


def _runtime_control_policy(value: str | None = None) -> str:
    raw = os.environ.get("DIE_MCP_CONTROL_POLICY", CONTROL_POLICY_ENABLED) if value is None else value
    if not isinstance(raw, str):
        raise RuntimeMcpError(
            "E_RUNTIME_CONTROL_POLICY",
            "DIE_MCP_CONTROL_POLICY must be enabled or staging-read-only",
        )
    value = raw.strip().lower()
    if value not in CONTROL_POLICIES:
        raise RuntimeMcpError(
            "E_RUNTIME_CONTROL_POLICY",
            "DIE_MCP_CONTROL_POLICY must be enabled or staging-read-only",
        )
    return value


def runtime_public_base_url(principal_id: str) -> str:
    default = PRINCIPAL_PUBLIC_BASE_URLS.get(principal_id)
    if default is None:
        raise RuntimeMcpError(
            "E_RUNTIME_BINDING_MISSING",
            "runtime principal has no registered public MCP origin",
        )
    return os.environ.get("DIE_MCP_BASE_URL", default)


def runtime_oauth_client_id(principal_id: str) -> str:
    default = PRINCIPAL_OAUTH_CLIENT_IDS.get(principal_id)
    if default is None:
        raise RuntimeMcpError(
            "E_RUNTIME_BINDING_MISSING",
            "runtime principal has no registered OAuth client identifier",
        )
    return os.environ.get("DIE_MCP_OAUTH_CLIENT_ID", default)


def runtime_port(principal_id: str, requested_port: int | None = None) -> int:
    """Resolve one non-colliding loopback binding for a pinned principal."""

    default_port = PRINCIPAL_DEFAULT_PORTS.get(principal_id)
    if default_port is None:
        raise RuntimeMcpError(
            "E_RUNTIME_BINDING_MISSING",
            "runtime principal has no registered Decision MCP binding",
        )
    port = default_port if requested_port is None else requested_port
    if not isinstance(port, int) or isinstance(port, bool) or not 1024 <= port <= 65_535:
        raise RuntimeMcpError(
            "E_RUNTIME_PORT_INVALID",
            "runtime MCP port must be an integer from 1024 through 65535",
        )
    if port in INFRASTRUCTURE_RESERVED_PORTS:
        raise RuntimeMcpError(
            "E_RUNTIME_PORT_RESERVED",
            "runtime MCP port is reserved by Architect DEV or local infrastructure",
        )
    return port


def serve_http(
    *,
    principal_id: str,
    writer: Writer | None,
    port: int,
    registry_path: str | pathlib.Path | None = None,
) -> int:
    token = _runtime_token()
    control_policy = _runtime_control_policy()
    try:
        oauth = runtime_mcp_oauth.OAuthAuthority(
            principal_id=principal_id,
            base_url=runtime_public_base_url(principal_id),
            bearer_secret=token,
            login_password=_runtime_login_password(),
            static_client_id=runtime_oauth_client_id(principal_id),
            allowed_redirect_hosts=tuple(
                item.strip()
                for item in os.environ.get(
                    "DIE_MCP_OAUTH_REDIRECT_HOSTS",
                    "chatgpt.com;openai.com",
                ).split(";")
                if item.strip()
            ),
        )
    except runtime_mcp_oauth.OAuthError as exc:
        raise RuntimeMcpError("E_RUNTIME_OAUTH_CONFIG", exc.description) from exc
    limiter = mcp_server.RateLimit()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_bytes(
            self,
            status: int,
            body: bytes,
            content_type: str,
            headers: dict[str, str] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Robots-Tag", "noindex")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: Any) -> None:
            self._send_bytes(
                status,
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _send_html(self, status: int, body: str) -> None:
            self._send_bytes(
                status,
                body.encode("utf-8"),
                "text/html; charset=utf-8",
            )

        def _redirect(self, location: str, headers: dict[str, str] | None = None) -> None:
            response_headers = {"Location": location, **(headers or {})}
            self._send_bytes(302, b"", "text/plain; charset=utf-8", response_headers)

        def _read_body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise runtime_mcp_oauth.OAuthError(
                    "invalid_request", "content length is invalid"
                ) from exc
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise runtime_mcp_oauth.OAuthError(
                    "invalid_request", "request body is empty or too large", 413
                )
            return self.rfile.read(length)

        def _read_json(self) -> Any:
            try:
                return json.loads(self._read_body().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise runtime_mcp_oauth.OAuthError(
                    "invalid_request", "JSON body is invalid"
                ) from exc

        def _read_form(self) -> dict[str, str]:
            try:
                decoded = self._read_body().decode("utf-8")
            except UnicodeDecodeError as exc:
                raise runtime_mcp_oauth.OAuthError(
                    "invalid_request", "form body is invalid"
                ) from exc
            return {
                key: values[-1]
                for key, values in parse_qs(decoded, keep_blank_values=True).items()
            }

        def _session(self) -> str | None:
            raw = self.headers.get("Cookie", "")
            cookie = SimpleCookie()
            try:
                cookie.load(raw)
            except Exception:
                return None
            morsel = cookie.get("die_runtime_session")
            return morsel.value if morsel else None

        def _login_page(self, next_path: str) -> str:
            return f"""<!doctype html><html><body>
<h2>DIE Runtime MCP Login</h2>
<p>Principal: {html.escape(principal_id)}</p>
<form method="post" action="/oauth/login">
<input name="password" type="password" autocomplete="current-password" required>
<input name="next" type="hidden" value="{html.escape(next_path, quote=True)}">
<button type="submit">Sign in</button>
</form></body></html>"""

        def _consent_page(self, params: dict[str, str]) -> str:
            hidden = "".join(
                f'<input type="hidden" name="{html.escape(key, quote=True)}" '
                f'value="{html.escape(value, quote=True)}">'
                for key, value in params.items()
            )
            return f"""<!doctype html><html><body>
<h2>Approve Runtime MCP access?</h2>
<p>Principal: {html.escape(principal_id)}<br>
Client: {html.escape(params['client_id'])}<br>
Scope: {html.escape(params['scope'])}</p>
<form method="post" action="/oauth/approve">{hidden}<button type="submit">Approve</button></form>
<form method="post" action="/oauth/deny">{hidden}<button type="submit">Deny</button></form>
</body></html>"""

        def _oauth_error(self, exc: runtime_mcp_oauth.OAuthError) -> None:
            self._send_json(
                exc.status,
                {"error": exc.error, "error_description": exc.description},
            )

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "server": SERVER_NAME,
                        "version": SERVER_VERSION,
                        "principal_id": principal_id,
                        "tools": len(tool_definitions(principal_id, registry_path)),
                        "oauth": runtime_mcp_oauth.SCHEMA_VERSION,
                        "control_policy": control_policy,
                    },
                )
                return
            if parsed.path in {
                "/.well-known/oauth-authorization-server",
                "/.well-known/oauth-authorization-server/mcp",
            }:
                self._send_json(200, oauth.authorization_metadata())
                return
            if parsed.path in {
                "/.well-known/oauth-protected-resource",
                "/.well-known/oauth-protected-resource/mcp",
            }:
                self._send_json(200, oauth.protected_resource_metadata())
                return
            if parsed.path == "/login":
                self._send_html(200, self._login_page("/health"))
                return
            if parsed.path == "/oauth/authorize":
                try:
                    params = {
                        key: values[-1]
                        for key, values in parse_qs(
                            parsed.query, keep_blank_values=True
                        ).items()
                    }
                    params = oauth.validate_authorization(params)
                    if not oauth.verify_session(self._session()):
                        self._send_html(200, self._login_page(self.path))
                        return
                    self._send_html(200, self._consent_page(params))
                except runtime_mcp_oauth.OAuthError as exc:
                    self._oauth_error(exc)
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            try:
                if parsed.path == HTTP_PATH:
                    supplied = self.headers.get("Authorization", "")
                    if not oauth.authenticate_bearer(supplied):
                        self._send_bytes(
                            401,
                            b"unauthorized",
                            "text/plain; charset=utf-8",
                            {
                                "WWW-Authenticate": (
                                    f'Bearer resource_metadata="{oauth.base_url}/'
                                    '.well-known/oauth-protected-resource/mcp"'
                                )
                            },
                        )
                        return
                    message = self._read_json()
                    response = handle(
                        message,
                        principal_id=principal_id,
                        writer=writer,
                        registry_path=registry_path,
                        rate_limit=limiter,
                        control_policy=control_policy,
                    )
                    if response is None:
                        self.send_response(204)
                        self.end_headers()
                    else:
                        self._send_json(200, response)
                    return
                if parsed.path == "/oauth/register":
                    self._send_json(201, oauth.register(self._read_json()))
                    return
                if parsed.path == "/oauth/token":
                    self._send_json(200, oauth.exchange(self._read_form()))
                    return
                if parsed.path == "/oauth/login":
                    form = self._read_form()
                    if not oauth.verify_login(form.get("password", "")):
                        raise runtime_mcp_oauth.OAuthError(
                            "access_denied", "login failed", 401
                        )
                    next_path = form.get("next", "/health")
                    if not (
                        next_path == "/health"
                        or next_path.startswith("/oauth/authorize?")
                    ):
                        next_path = "/health"
                    cookie = (
                        "die_runtime_session="
                        + oauth.session_token()
                        + "; HttpOnly; Secure; SameSite=Lax; Path=/"
                    )
                    self._redirect(next_path, {"Set-Cookie": cookie})
                    return
                if parsed.path in {"/oauth/approve", "/oauth/deny"}:
                    if not oauth.verify_session(self._session()):
                        raise runtime_mcp_oauth.OAuthError(
                            "access_denied", "Founder login is required", 401
                        )
                    form = self._read_form()
                    destination = (
                        oauth.approve(form)
                        if parsed.path == "/oauth/approve"
                        else oauth.deny(form)
                    )
                    self._redirect(destination)
                    return
                self.send_error(404)
            except runtime_mcp_oauth.OAuthError as exc:
                self._oauth_error(exc)

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
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if not args.principal_id:
        print("E_UNAUTHORIZED_PRINCIPAL: --principal-id is required", file=sys.stderr)
        return 2
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "bin"))
    import die_event  # type: ignore  # noqa: E402

    try:
        port = runtime_port(args.principal_id, args.port)
        return serve_http(
            principal_id=args.principal_id,
            writer=die_event.commit_normalized_decision,
            port=port,
        )
    except RuntimeMcpError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
