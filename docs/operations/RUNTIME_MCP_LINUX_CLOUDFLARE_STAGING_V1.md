# Runtime MCP Linux Cloudflare Staging v1

## Scope

`MCP-LNX-002` attaches the already-created Cloudflare tunnel `linux-mcp` to the isolated Executive and Division01 staging MCP services. It does not alter the Windows tunnel `aethers`, existing `*.aethers.web.id` endpoints, browser/CDP wake lines, or the active MX-062 source/runtime.

## Ingress allowlist

```text
executive-mcp.aethers.biz.id  -> http://127.0.0.1:8891
division01-mcp.aethers.biz.id -> http://127.0.0.1:8892
all other host/path traffic    -> http_status:404
```

No Architect MCP, CDP port, browser profile, wake endpoint, or legacy Windows hostname is permitted in this tunnel config.

## Credential boundary

Tunnel authentication uses `cloudflared --token-file`. The persistent source token lives at `/etc/die/staging/cloudflare/linux-mcp.token`, root-owned mode `0600`. systemd `LoadCredential=` presents a private ephemeral credential file to the unprivileged `die-cloudflared` service; the token is absent from `ExecStart`, config YAML, journal output, repository, and receipts.

The installer never creates or prints the token. Token provisioning is an operator/DEV deployment step performed through a secret-preserving pipe.

## Lifecycle

The installer validates the clean source checkout, token metadata, ingress YAML, forbidden-route absence, and systemd unit, then leaves the tunnel **stopped and disabled**. Activation is explicit. `MCP-LNX-002` is accepted only after the connector is active, both public `/health` endpoints resolve to the correct principal/tool count/read-only policy, unknown host/path handling remains bounded, and Windows tunnel health is unchanged.

Authenticated OAuth/tool/context parity is deferred to `MCP-LNX-003`.
