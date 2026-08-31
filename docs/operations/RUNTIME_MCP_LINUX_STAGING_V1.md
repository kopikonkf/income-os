# Runtime MCP Linux Staging v1

## Purpose

`MCP-LNX-001` creates parallel Executive and Division01 Linux staging MCP services without changing the existing Linux pre-cutover services, Windows services, Windows Cloudflare tunnel, browser/CDP wake lines, or the active MX-062 soak source.

## Bindings

| Principal | Existing Linux | Staging | Public staging origin |
| --- | ---: | ---: | --- |
| Executive | `127.0.0.1:8791` | `127.0.0.1:8891` | `https://executive-mcp.aethers.biz.id` |
| Division01 | `127.0.0.1:8792` | `127.0.0.1:8892` | `https://division01-mcp.aethers.biz.id` |

Staging source is a separate clean checkout at `/opt/die/staging/income-os`. `/srv/die` is not pulled, rebuilt, or restarted while MX-062 is active.

## Safety policy

The runtime server defaults to `DIE_MCP_CONTROL_POLICY=enabled`, preserving existing behavior. Staging units pin `DIE_MCP_CONTROL_POLICY=staging-read-only`. Tool discovery remains identical (Executive 18, Division01 6), but every control tool returns `E_STAGING_READ_ONLY` before rate-limit consumption, request normalization, State Manager invocation, or writer side effects.

Systemd additionally exposes `/var/lib/die/state` read-only and gives the staging service no writable state path. Browser profiles and CDP ports are not mounted or routed into the service.

## Installation boundary

The per-principal staging installers require a clean staging source checkout, generate dedicated root-only staging OAuth/bearer material if absent, validate the staging public origin and read-only policy, install the unit, and then **stop/disable it**. They never start the service. Explicit activation is a separate operator action after local validation. Secret values are never printed.

## Activation sequence

1. Materialize exact accepted source commit at `/opt/die/staging/income-os`.
2. Run both `install-staging.sh` scripts as root.
3. Verify `systemd-analyze verify`, source SHA, env metadata keys, port availability, and existing 8791/8792 service health.
4. Explicitly start `die-executive-runtime-mcp-staging.service` and `die-division01-runtime-mcp-staging.service`.
5. Verify loopback `/health`, unauthenticated `/mcp` = 401, tool counts 18/6, control policy `staging-read-only`, and control-call writer suppression.
6. Only `MCP-LNX-002` may attach the `linux-mcp` Cloudflare connector.

`MCP-LNX-001` carries no connector handoff, no Cloudflare activation, no browser wake, and no marketplace/production authority.
