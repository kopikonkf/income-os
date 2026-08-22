"""Principal-pinned OAuth/PKCE authority for one Runtime MCP process.

This module deliberately keeps OAuth inside the same process that owns the
Runtime MCP principal.  There is no shared proxy, token-based upstream router,
or dependency on the Architect DEV/Aether planes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit


SCHEMA_VERSION = "die.runtime-mcp.oauth.v1"
ACCESS_TTL_S = 3_600
AUTH_CODE_TTL_S = 300
CLIENT_TTL_S = 31_536_000
REFRESH_TTL_S = 2_592_000
SESSION_TTL_S = 43_200
SUPPORTED_SCOPE = "runtime"


class OAuthError(ValueError):
    def __init__(self, error: str, description: str, status: int = 400):
        super().__init__(description)
        self.error = error
        self.description = description
        self.status = status


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, TypeError) as exc:
        raise OAuthError("invalid_token", "token encoding is invalid", 401) from exc


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise OAuthError(
            "invalid_server_config",
            "Runtime MCP public base URL has an invalid port",
            500,
        ) from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise OAuthError(
            "invalid_server_config",
            "Runtime MCP public base URL must be an HTTPS origin",
            500,
        )
    return f"https://{parsed.netloc}"


class OAuthAuthority:
    """Small stateless-token OAuth authority with one-time authorization codes."""

    def __init__(
        self,
        *,
        principal_id: str,
        base_url: str,
        bearer_secret: str,
        login_password: str,
        static_client_id: str,
        allowed_redirect_hosts: tuple[str, ...] = ("chatgpt.com", "openai.com"),
        clock: Any = time.time,
    ) -> None:
        if len(bearer_secret.encode("utf-8")) < 32:
            raise OAuthError(
                "invalid_server_config",
                "Runtime MCP bearer secret must contain at least 32 bytes",
                500,
            )
        if len(login_password) < 16:
            raise OAuthError(
                "invalid_server_config",
                "Runtime MCP login password must contain at least 16 characters",
                500,
            )
        if not static_client_id or len(static_client_id) > 128:
            raise OAuthError(
                "invalid_server_config",
                "Runtime MCP OAuth client identifier is invalid",
                500,
            )
        self.principal_id = principal_id
        self.base_url = normalize_base_url(base_url)
        self.raw_bearer = bearer_secret
        self.login_password = login_password
        self.static_client_id = static_client_id
        self.allowed_redirect_hosts = tuple(host.lower() for host in allowed_redirect_hosts)
        if not self.allowed_redirect_hosts:
            raise OAuthError(
                "invalid_server_config",
                "at least one OAuth redirect host must be allowlisted",
                500,
            )
        self.clock = clock
        self._key = hmac.new(
            bearer_secret.encode("utf-8"),
            f"die-runtime-oauth:{principal_id}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
        self._codes: dict[str, dict[str, Any]] = {}

    @property
    def resource(self) -> str:
        return f"{self.base_url}/mcp"

    def authorization_metadata(self) -> dict[str, Any]:
        return {
            "issuer": self.base_url,
            "authorization_endpoint": f"{self.base_url}/oauth/authorize",
            "token_endpoint": f"{self.base_url}/oauth/token",
            "registration_endpoint": f"{self.base_url}/oauth/register",
            "scopes_supported": [SUPPORTED_SCOPE],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }

    def protected_resource_metadata(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "authorization_servers": [self.base_url],
            "scopes_supported": [SUPPORTED_SCOPE],
            "bearer_methods_supported": ["header"],
        }

    def _mint(self, kind: str, payload: dict[str, Any], ttl_s: int) -> str:
        now = int(self.clock())
        envelope = {
            "v": 1,
            "kind": kind,
            "principal_id": self.principal_id,
            "iat": now,
            "exp": now + ttl_s,
            "nonce": secrets.token_urlsafe(12),
            **payload,
        }
        body = _b64encode(
            json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signature = _b64encode(hmac.new(self._key, body.encode("ascii"), hashlib.sha256).digest())
        return f"v1.{body}.{signature}"

    def _verify(self, token: str, kind: str) -> dict[str, Any]:
        try:
            version, body, supplied = token.split(".", 2)
        except ValueError as exc:
            raise OAuthError("invalid_token", "token shape is invalid", 401) from exc
        if version != "v1":
            raise OAuthError("invalid_token", "token version is invalid", 401)
        expected = _b64encode(
            hmac.new(self._key, body.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied, expected):
            raise OAuthError("invalid_token", "token signature is invalid", 401)
        try:
            payload = json.loads(_b64decode(body))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise OAuthError("invalid_token", "token payload is invalid", 401) from exc
        if (
            payload.get("kind") != kind
            or payload.get("principal_id") != self.principal_id
            or not isinstance(payload.get("exp"), int)
            or payload["exp"] < int(self.clock())
        ):
            raise OAuthError("invalid_token", "token claims are invalid or expired", 401)
        return payload

    def session_token(self) -> str:
        return self._mint("session", {"role": "founder"}, SESSION_TTL_S)

    def verify_session(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            payload = self._verify(token, "session")
        except OAuthError:
            return False
        return payload.get("role") == "founder"

    def verify_login(self, supplied: str) -> bool:
        return hmac.compare_digest(supplied, self.login_password)

    def _redirect_allowed(self, redirect_uri: str) -> bool:
        parsed = urlparse(redirect_uri)
        try:
            port = parsed.port
        except ValueError:
            return False
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or parsed.fragment
        ):
            return False
        host = parsed.hostname.lower()
        return any(host == allowed or host.endswith("." + allowed) for allowed in self.allowed_redirect_hosts)

    def _client_redirects(self, client_id: str) -> tuple[str, ...] | None:
        if client_id == self.static_client_id:
            return None
        try:
            payload = self._verify(client_id, "client")
        except OAuthError:
            raise OAuthError("invalid_client", "OAuth client is not registered", 401)
        redirects = payload.get("redirect_uris")
        if not isinstance(redirects, list) or any(not isinstance(item, str) for item in redirects):
            raise OAuthError("invalid_client", "registered redirect set is invalid", 401)
        return tuple(redirects)

    def register(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise OAuthError("invalid_client_metadata", "registration body must be an object")
        redirects = payload.get("redirect_uris")
        if (
            not isinstance(redirects, list)
            or not redirects
            or len(redirects) > 10
            or any(not isinstance(uri, str) or not self._redirect_allowed(uri) for uri in redirects)
        ):
            raise OAuthError(
                "invalid_redirect_uri",
                "all registered redirects must be allowlisted HTTPS origins",
            )
        client_id = self._mint(
            "client",
            {
                "redirect_uris": redirects,
                "client_name": str(payload.get("client_name") or "ChatGPT Runtime MCP")[:128],
            },
            CLIENT_TTL_S,
        )
        return {
            "client_id": client_id,
            "client_name": str(payload.get("client_name") or "ChatGPT Runtime MCP")[:128],
            "redirect_uris": redirects,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }

    def validate_authorization(self, params: dict[str, str]) -> dict[str, str]:
        required = ("client_id", "redirect_uri", "code_challenge", "state")
        if any(not params.get(field) for field in required):
            raise OAuthError("invalid_request", "authorization parameters are incomplete")
        if params.get("response_type", "code") != "code":
            raise OAuthError("unsupported_response_type", "only authorization code is supported")
        if params.get("code_challenge_method") != "S256":
            raise OAuthError("invalid_request", "PKCE S256 is required")
        scope = params.get("scope", SUPPORTED_SCOPE)
        if set(scope.split()) - {SUPPORTED_SCOPE}:
            raise OAuthError("invalid_scope", "only the runtime scope is supported")
        redirects = self._client_redirects(params["client_id"])
        if not self._redirect_allowed(params["redirect_uri"]):
            raise OAuthError("invalid_redirect_uri", "redirect URI host is not allowlisted")
        if redirects is not None and params["redirect_uri"] not in redirects:
            raise OAuthError("invalid_redirect_uri", "redirect URI was not registered")
        return {**params, "scope": scope}

    def approve(self, params: dict[str, str]) -> str:
        request = self.validate_authorization(params)
        code = secrets.token_urlsafe(32)
        self._codes[code] = {
            "client_id": request["client_id"],
            "redirect_uri": request["redirect_uri"],
            "code_challenge": request["code_challenge"],
            "scope": request["scope"],
            "exp": int(self.clock()) + AUTH_CODE_TTL_S,
        }
        return self._redirect_with(
            request["redirect_uri"],
            {"code": code, "state": request["state"]},
        )

    def deny(self, params: dict[str, str]) -> str:
        request = self.validate_authorization(params)
        return self._redirect_with(
            request["redirect_uri"],
            {"error": "access_denied", "state": request["state"]},
        )

    @staticmethod
    def _redirect_with(redirect_uri: str, values: dict[str, str]) -> str:
        parsed = urlsplit(redirect_uri)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query.extend(values.items())
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")
        )

    def exchange(self, form: dict[str, str]) -> dict[str, Any]:
        grant_type = form.get("grant_type")
        if grant_type == "authorization_code":
            code = form.get("code", "")
            row = self._codes.pop(code, None)
            if row is None or row["exp"] < int(self.clock()):
                raise OAuthError("invalid_grant", "authorization code is missing or expired")
            if form.get("client_id") != row["client_id"] or form.get("redirect_uri") != row["redirect_uri"]:
                raise OAuthError("invalid_grant", "authorization code binding does not match")
            verifier = form.get("code_verifier", "")
            challenge = _b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            if not verifier or not hmac.compare_digest(challenge, row["code_challenge"]):
                raise OAuthError("invalid_grant", "PKCE verification failed")
            client_id = row["client_id"]
            scope = row["scope"]
        elif grant_type == "refresh_token":
            refresh = self._verify(form.get("refresh_token", ""), "refresh")
            client_id = str(refresh.get("client_id", ""))
            if form.get("client_id") and form["client_id"] != client_id:
                raise OAuthError("invalid_grant", "refresh token client does not match")
            scope = str(refresh.get("scope", SUPPORTED_SCOPE))
        else:
            raise OAuthError("unsupported_grant_type", "grant type is not supported")

        access = self._mint(
            "access",
            {"client_id": client_id, "scope": scope, "aud": self.resource},
            ACCESS_TTL_S,
        )
        refresh_token = self._mint(
            "refresh",
            {"client_id": client_id, "scope": scope},
            REFRESH_TTL_S,
        )
        return {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": ACCESS_TTL_S,
            "refresh_token": refresh_token,
            "scope": scope,
        }

    def authenticate_bearer(self, header: str) -> bool:
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        token = header[len(prefix) :]
        if hmac.compare_digest(token, self.raw_bearer):
            return True
        try:
            payload = self._verify(token, "access")
        except OAuthError:
            return False
        return payload.get("aud") == self.resource and payload.get("scope") == SUPPORTED_SCOPE
