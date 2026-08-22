# Runtime MCP Edge Connector v1

Status: repository-only edge contract. No production edge, service, secret, or
connector activation is authorized by this document.

## Architecture decision

Runtime MCP uses the same transport shape proven by the standalone Architect
DEV MCP, while retaining a completely separate codebase and privilege plane:

| Public hostname | Direct Cloudflared upstream | Pinned principal | Tools |
| --- | --- | --- | --- |
| `executive-mcp.aethers.web.id` | `http://localhost:8791` | `chatgpt-plus-executive` | 18 |
| `division01-mcp.aethers.web.id` | `http://localhost:8792` | `division-head-division01` | 6 |

The existing Cloudflare Tunnel is the public edge. Each hostname routes
directly to one loopback Runtime MCP process. There is no shared Runtime MCP
endpoint and no token-based choice of upstream. A hostname occurrence that is
duplicated or points at the other lane is a hard failure.

**Aether Caddy is not in this path.** The Caddy listener at `127.0.0.1:8080`
belongs to the separate Aether application routes. DIE does not acquire a
runtime or code dependency on Aether merely because both projects use hostnames
under the Founder-owned `aethers.web.id` zone.

The Runtime MCP processes embed their own OAuth authorization server, protected
resource metadata, dynamic client registration, Founder login/consent, PKCE
S256 authorization-code exchange, refresh flow, and `/mcp` resource. This
mirrors the transport responsibility observed in `D:\mcp-architect`: OAuth is
owned by the MCP server behind Cloudflared, not by Caddy or a shared auth proxy.
Bearer and OAuth signing roots remain separate per principal because each
process loads only its own protected token.

## Hard exclusions

- Architect DEV remains isolated and retains its separate domain, process, and
  administrative tool surface. Runtime never inherits repository, Git, test,
  service-control, filesystem, shell, or credential-read tools.
- The official OpenAI `tunnel-client` P2 path remains dormant and deferred
  post-PECAH-TELOR. Nothing here touches its binary or
  `C:\ProgramData\DIE\ExecutiveMCP` skeleton.
- No OpenAI control-plane API key, OpenAI billing, paid connector transport, or
  new tunnel is required.
- BrowserOS/Division wake, Creator/Proxima, and M-001 are unchanged.
- Proxy logs, receipts, and source files may contain hostnames, principal IDs,
  ports, and tool counts, but never bearer values, HMAC keys, login passwords,
  OAuth access tokens, or Cloudflare credential contents.

## Repository artifacts

- `cloudflared-runtime-mcp-ingress.yml` is a DIE-owned two-route fragment. It
  contains no tunnel ID, credential path, secret, catch-all route, or Aether
  route.
- `Set-DIERuntimeMcpCloudflareEdge.ps1` defaults to `Plan`. `ApplyIngress` and
  `ApplyDns` are separate explicit mutation gates so a DNS operation cannot be
  inferred from a config operation.
- `Test-DIERuntimeMcpEdge.ps1` defaults to `Plan`. `Configured` is read-only and
  checks exact routes, DNS targets, Cloudflared validation, and the terminal
  `http_status:404`. `Public` performs only public health/metadata and
  unauthenticated-401 probes.

The mutation script is idempotent for already-correct routes. A duplicate or
wrong upstream fails closed. When an ingress change is actually required, the
script creates a local backup, validates the complete Cloudflared config, and
restores the backup on validation/restart failure. DNS overwrite requires a
second explicit switch. None of these mutation modes may be used merely because
their implementation exists in the repository.

## Ordered gates

Run all repository checks and review the side-effect-free output first:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Set-DIERuntimeMcpCloudflareEdge.ps1 -Mode Plan
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpEdge.ps1 -Mode Plan
~~~

The production order is fixed:

1. Founder merges the reviewed local-runtime plus edge contract.
2. Sync `C:\DIE\main`; rerun Company Brain, full bridge regression,
   `py_compile`, and every Plan mode.
3. With separate Founder authorization, provision four protected values per
   principal through the directly attached no-echo console.
4. With separate authorization, install and start the two SCM services.
5. Prove loopback HTTP 401, `initialize`, exact `tools/list`, and signed
   read-only `context_snapshot`.
6. With separate authorization, apply/verify the two direct Cloudflared routes
   and DNS records. Do not add a Caddy route.
7. Run public health, OAuth metadata, protected-resource metadata, and
   unauthenticated-401 proof.
8. Register the Executive connector and prove initialize, 18 tools, and its
   signed pinned snapshot.
9. Perform the reversible DIVISION-01 Free-account registration experiment.
10. Only after both runtime lanes have receipts may Founder select an income
    stream or M-001.

Example commands for gates 6 and 7, only after their explicit authorization:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Set-DIERuntimeMcpCloudflareEdge.ps1 -Mode ApplyIngress -ConfirmEdgeMutation
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Set-DIERuntimeMcpCloudflareEdge.ps1 -Mode ApplyDns -ConfirmEdgeMutation
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpEdge.ps1 -Mode Configured
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpEdge.ps1 -Mode Public
~~~

`ApplyIngress` can restart the existing Cloudflared service only when it has
actually written a validated config change. It does not start either Runtime
MCP service. `ApplyDns` does not read Cloudflare credential-file contents; the
already configured Cloudflared identity performs the route operation.

## Free-account empirical gate

OpenAI documentation must not be interpreted as proof that a specific Free
account can register this connector. The acceptance criterion is an empirical,
cheap, and reversible account-level test after the public proof passes:

1. In DIVISION-01, attempt to add only
   `https://division01-mcp.aethers.web.id/mcp`.
2. Complete that lane's OAuth/PKCE flow; never paste a bearer token into the
   account UI.
3. Prove `initialize`, exactly 6 tools, and a signed snapshot whose principal is
   `division-head-division01` and scope is `single_division`.
4. Confirm the Executive hostname is not registered in that account and cannot
   be reached by changing a token.
5. Remove/disable the test connector if the account refuses registration or
   the proof is incomplete.

If Free registration is blocked, stop. Record the observable failure and use
the already designed Division wake/OAuth conversation path. Do not infer a paid upgrade,
do not activate P2, and do not broaden Executive access. Any future
upgrade is a separate Founder decision.

## Current observation, not activation receipt

During the Architect audit, the existing Cloudflared config already contained
the two exact direct routes and retained a terminal 404; Cloudflared ingress
validation passed and both CNAMEs resolved to the existing tunnel. Those
entries pre-existed this repository revision and were not created, altered, or
restarted by Architect. The ports `8791` and `8792` had no listeners, so this
observation is not a public Runtime MCP proof and does not skip any gate above.
