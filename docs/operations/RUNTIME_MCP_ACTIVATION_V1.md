# Runtime MCP Activation v1

Status: repository activation contract; production activation is gated on
Founder merge and explicit local execution.

## Purpose

This contract turns the merged least-privilege Runtime Decision MCP into two
independently supervised, principal-pinned loopback services:

| Service | Principal | Binding | Tool surface |
| --- | --- | --- | --- |
| `DIERuntimeMCPExecutive` | `chatgpt-plus-executive` | `127.0.0.1:8791` | 18 bounded Executive tools |
| `DIERuntimeMCPDivision01` | `division-head-division01` | `127.0.0.1:8792` | 6 DIVISION-01 tools |

Ports `8787`, `8789`, and `8790` remain reserved for Architect DEV and local
infrastructure. The services bind loopback only and do not create a second
control plane or writer. Public transport, when separately authorized, is the
direct per-hostname Cloudflared contract in
`RUNTIME_MCP_EDGE_CONNECTOR_V1.md`; Aether Caddy is not in the Runtime MCP path.

## Security boundary

Runtime assets live at `C:\ProgramData\DIE\RuntimeMCP`. Every directory and
secret file disables ACL inheritance and allows FullControl only to Local
System, built-in Administrators, and the provisioning operator.

Each principal receives a separate bearer token, Founder OAuth login password,
snapshot HMAC key, and HMAC key identifier. These four values per principal are
entered twice through `Read-Host -AsSecureString` in a directly attached local
console. Existing roots, files, or services are never overwritten. A partial
initial provision or service install is rolled back.

Architect must never receive or display a real secret value. Do not paste a
token, login password, or signing key into chat, a command sent through
Architect MCP, logs, Git, a pull request, an evidence receipt, or
`LASTSTANDINGPOINT.md`. The Live verifier reads the bearer token locally only
to make three bounded calls and returns metadata, never the token.

The service command line contains paths and the pinned principal only. Secrets
are loaded by `Invoke-DIERuntimeMcp.ps1` from protected files into the child
process environment and are not embedded in Windows Service Control Manager.
Each pinned Runtime process also owns its OAuth metadata, dynamic registration,
Founder login/consent, PKCE S256 exchange, refresh flow, and MCP resource. There
is no shared authentication proxy and an OAuth token minted by one principal
cannot authenticate to the other.

## SCM supervision

`die-windows-service.py` is the repository-native SCM host. It uses Windows
Service Control Manager APIs, reports lifecycle state, and assigns the child
PowerShell/Python process tree to a Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. A stop or failure cannot leave an orphaned
Runtime MCP process. Recovery actions restart failed services after 5, 15, and
60 seconds.

The design deliberately follows the proven native service pattern already
used on the Founder VPS and does not depend on NSSM, WinSW, PM2, or Scheduled
Tasks.

Service creation uses PowerShell 5.1 `New-Service` so the complete nested-quoted
binary path reaches SCM as one `BinaryPathName` value. `sc.exe` remains limited
to failure-recovery configuration and rollback deletion. After creation the
installer reads `Win32_Service` metadata and fails closed unless startup is
`Auto` and the account is `LocalSystem`.

## Controlled execution order

Run these only after Founder merge, from an elevated local Windows PowerShell
console at `C:\DIE`.

1. Review all side-effect-free plans:

   ~~~powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Initialize-DIERuntimeMcpActivation.ps1 -Mode Plan
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Install-DIERuntimeMcpServices.ps1 -Mode Plan
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpActivation.ps1 -Mode Plan
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Set-DIERuntimeMcpCloudflareEdge.ps1 -Mode Plan
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpEdge.ps1 -Mode Plan
   ~~~

2. Founder or an explicitly delegated local operator provisions the protected
   values. Neither command may be routed through chat or Architect MCP:

   ~~~powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Initialize-DIERuntimeMcpActivation.ps1 -Mode Provision -ConfirmInteractiveProvisioning
   ~~~

3. Install the two Automatic LocalSystem services. Installation does not start
   either service:

   ~~~powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Install-DIERuntimeMcpServices.ps1 -Mode Install -ConfirmServiceInstall
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpActivation.ps1 -Mode Installed
   ~~~

4. After explicit Founder activation authorization, start both services and run
   the bounded Live verifier:

   ~~~powershell
   Start-Service DIERuntimeMCPExecutive
   Start-Service DIERuntimeMCPDivision01
   powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\runtime-mcp\Test-DIERuntimeMcpActivation.ps1 -Mode Live
   ~~~

Live PASS requires, for both identities:

- unauthenticated request rejected with HTTP 401;
- authenticated `initialize` returns `die-runtime-decision-mcp`;
- `tools/list` returns exactly 18 or 6 role-specific tools;
- read-only `context_snapshot` returns the pinned identity and scope;
- snapshot integrity is `HMAC-SHA256` with a non-empty signature.

The verifier does not start or stop services and does not submit a control
request.

## Explicit exclusions

- BrowserOS wake remains wake-only design; no BrowserOS wake is invoked.
- First Division OAuth/conversation wake remains design-only.
- P2 tunnel remains deferred post-PECAH-TELOR; no `tunnel-client init`,
  `doctor`, or `run` is allowed here.
- Aether Caddy remains a separate application component and is not a Runtime
  MCP transport dependency.
- Creator/Proxima remains outside Decision MCP and retains zero tools.
- No mission proposal, decision commit, Hermes delegation, or state mutation is
  part of the Live probe.
- M-001 remains unselected and uncommitted.

This contract may be committed and published to a draft pull request. Real
provisioning, service installation, service start, or connector registration
requires the ordered Founder merge and local authorization gates above.

## Founder-operated E2E activation receipt — 2026-08-22

After PR #15 merged, Founder provisioned eight ACL-restricted secret files,
installed and started both LocalSystem services, applied the already reviewed
direct Cloudflared routes, and registered each connector in its assigned
ChatGPT account. This was an operator action outside the Architect repository
turn.

| Lane | Account | Cloud-to-loopback proof | Tools | Snapshot | Result |
| --- | --- | --- | --- | --- | --- |
| Executive | Plus | `executive-mcp.aethers.web.id` -> `127.0.0.1:8791` | 18/18 | `SNAP-5B3863A47162B024` | PASS |
| DIVISION-01 | Free | `division01-mcp.aethers.web.id` -> `127.0.0.1:8792` | 6/6 | `SNAP-456CE0AED2BEC70F` | PASS |

Both lanes returned HTTP 401 without authentication and a fresh HMAC-signed
principal-pinned snapshot with a key ID when authenticated. Cross-lane tokens
were rejected. No raw filesystem, shell, Git, service, credential, or wake tool
appeared. The Division result is the first empirical proof in this project that
the assigned ChatGPT Free account can register and use a custom MCP connector;
it does not claim a documented universal entitlement.

The live activation exposed two repository defects that were bypassed locally
by the Founder operator and are corrected upstream by the subsequent hotfix:

1. `sc.exe create` nested quoting was mangled by PowerShell 5.1; the canonical
   installer now uses `New-Service`.
2. the Live verifier accessed `.Count` on an empty pipeline under strict mode;
   the pipeline is now array-wrapped before the count comparison.

Wake remains separate and inactive, P2 remains dormant, Creator/Proxima is
unchanged, and M-001 remains unselected at the time of this receipt.
