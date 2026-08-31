"""Direct Cloudflared edge and principal-pinned OAuth contract v1."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

import pytest

from income_os_bridge import runtime_mcp_oauth, runtime_mcp_server


ROOT = pathlib.Path(__file__).resolve().parents[2]
OPS = ROOT / "ops" / "windows" / "runtime-mcp"
EDGE_SET = OPS / "Set-DIERuntimeMcpCloudflareEdge.ps1"
EDGE_TEST = OPS / "Test-DIERuntimeMcpEdge.ps1"
INGRESS = OPS / "cloudflared-runtime-mcp-ingress.yml"
RUNBOOK = ROOT / "docs" / "operations" / "RUNTIME_MCP_EDGE_CONNECTOR_V1.md"

MAPPINGS = {
    "chatgpt-plus-executive": (
        "executive-mcp.aethers.web.id",
        "http://localhost:8791",
        18,
    ),
    "division-head-division01": (
        "division01-mcp.aethers.web.id",
        "http://localhost:8792",
        6,
    ),
}


def _powershell() -> str | None:
    return shutil.which("powershell.exe") or shutil.which("powershell")


def _authority(
    principal: str = "chatgpt-plus-executive",
    secret: str = "x" * 32,
) -> runtime_mcp_oauth.OAuthAuthority:
    hostname, _, _ = MAPPINGS[principal]
    return runtime_mcp_oauth.OAuthAuthority(
        principal_id=principal,
        base_url=f"https://{hostname}",
        bearer_secret=secret,
        login_password="founder-login-password",
        static_client_id="static-client",
    )


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _authorize(
    authority: runtime_mcp_oauth.OAuthAuthority,
    *,
    client_id: str,
    verifier: str,
    redirect_uri: str = "https://chatgpt.com/aip/callback?existing=1",
) -> tuple[str, dict[str, str]]:
    request = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
        "scope": "runtime",
        "state": "state-001",
    }
    destination = authority.approve(request)
    query = parse_qs(urlsplit(destination).query)
    assert query["existing"] == ["1"]
    assert query["state"] == ["state-001"]
    return query["code"][0], request


def test_principal_pinned_metadata_and_dcr_allowlist() -> None:
    authority = _authority()
    metadata = authority.authorization_metadata()
    protected = authority.protected_resource_metadata()
    assert metadata["issuer"] == "https://executive-mcp.aethers.web.id"
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    assert protected["resource"] == "https://executive-mcp.aethers.web.id/mcp"

    registered = authority.register(
        {
            "client_name": "ChatGPT Executive",
            "redirect_uris": ["https://chatgpt.com/aip/callback"],
        }
    )
    assert registered["token_endpoint_auth_method"] == "none"
    assert registered["redirect_uris"] == ["https://chatgpt.com/aip/callback"]

    with pytest.raises(runtime_mcp_oauth.OAuthError) as error:
        authority.register({"redirect_uris": ["https://attacker.invalid/callback"]})
    assert error.value.error == "invalid_redirect_uri"
    with pytest.raises(runtime_mcp_oauth.OAuthError):
        authority.register({"redirect_uris": ["https://chatgpt.com:8443/callback"]})


def test_pkce_code_is_one_time_refreshable_and_principal_bound() -> None:
    executive = _authority(secret="e" * 32)
    registration = executive.register(
        {"redirect_uris": ["https://chatgpt.com/aip/callback?existing=1"]}
    )
    client_id = registration["client_id"]

    bad_code, bad_request = _authorize(
        executive,
        client_id=client_id,
        verifier="correct-verifier-bad-attempt",
    )
    with pytest.raises(runtime_mcp_oauth.OAuthError) as bad_pkce:
        executive.exchange(
            {
                "grant_type": "authorization_code",
                "code": bad_code,
                "client_id": client_id,
                "redirect_uri": bad_request["redirect_uri"],
                "code_verifier": "wrong-verifier",
            }
        )
    assert bad_pkce.value.error == "invalid_grant"

    verifier = "correct-verifier-success"
    code, request = _authorize(executive, client_id=client_id, verifier=verifier)
    tokens = executive.exchange(
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": request["redirect_uri"],
            "code_verifier": verifier,
        }
    )
    assert tokens["scope"] == "runtime"
    assert executive.authenticate_bearer(f"Bearer {tokens['access_token']}")
    assert executive.authenticate_bearer("Bearer " + "e" * 32)

    with pytest.raises(runtime_mcp_oauth.OAuthError) as reused:
        executive.exchange(
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "redirect_uri": request["redirect_uri"],
                "code_verifier": verifier,
            }
        )
    assert reused.value.error == "invalid_grant"

    refreshed = executive.exchange(
        {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": client_id,
        }
    )
    assert executive.authenticate_bearer(f"Bearer {refreshed['access_token']}")

    division = _authority("division-head-division01", "d" * 32)
    assert not division.authenticate_bearer(f"Bearer {tokens['access_token']}")
    assert not division.authenticate_bearer("Bearer " + "e" * 32)


def test_server_public_bindings_are_exact_and_tool_surfaces_unchanged() -> None:
    assert runtime_mcp_server.SERVER_VERSION == "1.3.0"
    assert runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS["chatgpt-plus-executive"] == 8791
    assert runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS["division-head-division01"] == 8792
    assert runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS["die-lnx-executive-001"] == 8891
    assert runtime_mcp_server.PRINCIPAL_DEFAULT_PORTS["die-lnx-division-001"] == 8892
    for principal, (hostname, _, expected_tools) in MAPPINGS.items():
        assert runtime_mcp_server.PRINCIPAL_PUBLIC_BASE_URLS[principal] == f"https://{hostname}"
        assert len(runtime_mcp_server.tool_definitions(principal)) == expected_tools


def test_http_transport_exposes_metadata_401_and_pinned_tools() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])

    environment = os.environ.copy()
    bridge_path = str(ROOT / "bridge")
    environment["PYTHONPATH"] = bridge_path + os.pathsep + environment.get("PYTHONPATH", "")
    environment["DIE_HOME"] = str(ROOT)
    environment["DIE_MCP_TOKEN"] = "t" * 32
    environment["DIE_MCP_LOGIN_PASSWORD"] = "founder-login-password"
    environment["DIE_MCP_BASE_URL"] = "https://executive-mcp.aethers.web.id"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "income_os_bridge.runtime_mcp_server",
            "--principal-id",
            "chatgpt-plus-executive",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        health: dict[str, object] | None = None
        for _ in range(50):
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else ""
                pytest.fail(f"Runtime MCP process exited early: {stderr}")
            try:
                with urllib.request.urlopen(base + "/health", timeout=1) as response:
                    health = json.load(response)
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.05)
        assert health is not None
        assert health["principal_id"] == "chatgpt-plus-executive"
        assert health["tools"] == 18

        with urllib.request.urlopen(
            base + "/.well-known/oauth-authorization-server/mcp",
            timeout=2,
        ) as response:
            metadata = json.load(response)
        assert metadata["issuer"] == "https://executive-mcp.aethers.web.id"

        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        ).encode("utf-8")
        unauthenticated = urllib.request.Request(
            base + "/mcp",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as unauth_error:
            urllib.request.urlopen(unauthenticated, timeout=2)
        assert unauth_error.value.code == 401
        assert "resource_metadata=" in unauth_error.value.headers["WWW-Authenticate"]

        authenticated = urllib.request.Request(
            base + "/mcp",
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + "t" * 32,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(authenticated, timeout=2) as response:
            tool_response = json.load(response)
        assert len(tool_response["result"]["tools"]) == 18

        discover_payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "discover-1",
                "method": "server/discover",
                "params": {
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientInfo": {"name": "test-client", "version": "1.0"},
                        "io.modelcontextprotocol/clientCapabilities": {},
                    }
                },
            }
        ).encode("utf-8")
        discover_request = urllib.request.Request(
            base + "/mcp",
            data=discover_payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + "t" * 32,
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "server/discover",
            },
        )
        with urllib.request.urlopen(discover_request, timeout=2) as response:
            discover = json.load(response)
        assert discover["result"]["resultType"] == "complete"
        assert discover["result"]["supportedVersions"] == ["2026-07-28"]
        assert discover["result"]["capabilities"] == {"tools": {}}
        assert discover["result"]["ttlMs"] == 0
        assert discover["result"]["cacheScope"] == "private"

        modern_tools_payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {
                    "_meta": {
                        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientInfo": {"name": "test-client", "version": "1.0"},
                        "io.modelcontextprotocol/clientCapabilities": {},
                    }
                },
            }
        ).encode("utf-8")
        modern_tools_request = urllib.request.Request(
            base + "/mcp",
            data=modern_tools_payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + "t" * 32,
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "tools/list",
            },
        )
        with urllib.request.urlopen(modern_tools_request, timeout=2) as response:
            modern_tools = json.load(response)
        assert modern_tools["result"]["resultType"] == "complete"
        assert modern_tools["result"]["ttlMs"] == 0
        assert modern_tools["result"]["cacheScope"] == "private"
        assert len(modern_tools["result"]["tools"]) == 18
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_edge_artifacts_lock_direct_cloudflared_without_caddy_or_p2() -> None:
    for path in (EDGE_SET, EDGE_TEST, INGRESS, RUNBOOK):
        assert path.is_file(), path
    setter = EDGE_SET.read_text(encoding="utf-8")
    verifier = EDGE_TEST.read_text(encoding="utf-8")
    ingress = INGRESS.read_text(encoding="utf-8")
    combined = setter + verifier

    assert '[ValidateSet("Plan", "ApplyIngress", "ApplyDns")]' in setter
    assert '[string]$Mode = "Plan"' in setter
    assert "[switch]$ConfirmEdgeMutation" in setter
    assert "Restart-Service" in setter
    assert 'if ($Mode -eq "ApplyIngress")' in setter
    assert 'if ($Mode -eq "Plan")' in setter
    assert '[ValidateSet("Plan", "Configured", "Public")]' in verifier
    assert "http_status:404" in combined
    assert "token_based_proxy_routing = $false" in setter
    assert "aether_caddy_dependency = $false" in combined
    assert "p2_tunnel_client_dependency = $false" in combined
    assert "openai_control_plane_api_key_required = $false" in setter
    assert "C:\\ProgramData\\DIE\\ExecutiveMCP" not in combined
    assert "tunnel-client" not in combined.lower()
    assert "AetherCaddy" not in combined
    assert "127.0.0.1:8080" not in combined

    for _, (hostname, upstream, _) in MAPPINGS.items():
        assert ingress.count(hostname) == 1
        assert ingress.count(upstream) == 1
    assert "tunnel:" not in ingress
    assert "credentials-file:" not in ingress
    assert "http_status:404" not in ingress


def test_edge_runbook_preserves_free_account_fallback_and_gate_order() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Aether Caddy is not in this path" in text
    assert "directly to one loopback Runtime MCP process" in text
    assert "Free-account registration experiment" in text
    assert "wake/OAuth conversation path" in text
    assert "Do not infer a paid upgrade" in text
    assert "M-001" in text
    assert "pre-existed this repository revision" in text
    assert "ports `8791` and `8792` had no listeners" in text


@pytest.mark.skipif(_powershell() is None, reason="Windows PowerShell is unavailable")
def test_edge_plans_are_machine_readable_and_side_effect_free() -> None:
    executable = _powershell()
    assert executable is not None
    receipts = []
    for script in (EDGE_SET, EDGE_TEST):
        completed = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Mode",
                "Plan",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        receipts.append(json.loads(completed.stdout))

    setter, verifier = receipts
    assert setter["schema_version"] == "die.runtime-mcp.edge.v1"
    assert verifier["schema_version"] == "die.runtime-mcp.edge.verification.v1"
    for receipt in receipts:
        assert receipt["mode"] == "Plan"
        assert receipt["aether_caddy_dependency"] is False
        assert receipt["p2_tunnel_client_dependency"] is False
        assert receipt["secret_values_read"] is False
        assert receipt["external_mutation_performed"] is False
