# Executive MCP Secure Configuration v1

Status: Phase B1 repository tooling only
Branch: `architect/executive-mcp-secure-config-v1`
Runtime root contract: `C:\ProgramData\DIE\ExecutiveMCP`
Canonical repository: `C:\DIE`

## Purpose

Phase B1 defines a fail-closed, reviewable contract for two isolated Executive
MCP tunnel lanes. It adds no runtime configuration and performs no activation.

The official Secure MCP Tunnel guide describes an outbound-only client that
needs a tunnel identity, a runtime API key, and a reachable local MCP server.
The installed `tunnel-client` v0.0.12 help additionally supports the control
plane key as a file reference in the form `file:/path/to/secret`. B1 uses that
file-reference capability and does not place a key value in a command, profile,
environment dump, log, repository file, or test fixture.

Canonical reference:

https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

## B1 manifest

- `ops/windows/executive-mcp/New-DIEExecutiveMcpSecureConfigPlan.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine1Tunnel.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine2Tunnel.ps1`
- `ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureConfig.ps1`
- `docs/operations/EXECUTIVE_MCP_SECURE_CONFIG_V1.md`
- `bridge/tests/test_executive_secure_config_v1.py`
- `LASTSTANDINGPOINT.md`

All PowerShell entry points default to `Plan`. B1 validation invokes only
`Plan`; it never invokes a wrapper with `Run`.

## Fixed path contract

| Boundary | Line 1 | Line 2 |
| --- | --- | --- |
| Profile directory | `C:\ProgramData\DIE\ExecutiveMCP\config\line1` | `C:\ProgramData\DIE\ExecutiveMCP\config\line2` |
| Profile file | `...\executive-line1.yaml` | `...\executive-line2.yaml` |
| Secret directory | `C:\ProgramData\DIE\ExecutiveMCP\secrets\line1` | `C:\ProgramData\DIE\ExecutiveMCP\secrets\line2` |
| Control-plane key file | `...\control-plane-api-key` | `...\control-plane-api-key` |
| Tunnel-client key reference | `file:C:\ProgramData\DIE\ExecutiveMCP\secrets\line1\control-plane-api-key` | `file:C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\control-plane-api-key` |
| HMAC key file | prohibited | `...\snapshot-hmac-key` |
| HMAC key-id file | prohibited | `...\snapshot-hmac-key-id` |
| Log file | `C:\ProgramData\DIE\ExecutiveMCP\logs\line1\tunnel-client.jsonl` | `C:\ProgramData\DIE\ExecutiveMCP\logs\line2\tunnel-client.jsonl` |
| PID file | `C:\ProgramData\DIE\ExecutiveMCP\runtime\line1\tunnel-client.pid` | `C:\ProgramData\DIE\ExecutiveMCP\runtime\line2\tunnel-client.pid` |
| Health listener | `127.0.0.1:18101` | `127.0.0.1:18102` |
| MCP bootstrap | `C:\DIE\bin\die_executive_line1_mcp.py` | `C:\DIE\bin\die_executive_mcp.py` |

No tunnel identity appears in this manifest. Profile files and all secret files
are local B2 runtime artifacts and must never be committed.

## ACL contract

Every runtime directory, profile, secret, log, and PID file must satisfy all of
these rules before either future wrapper can leave Plan mode:

1. ACL inheritance is disabled.
2. No inherited access rule exists.
3. Only explicit Allow rules exist.
4. Only Local System (`S-1-5-18`), built-in Administrators
   (`S-1-5-32-544`), and the local B2 activation operator SID are allowed.
5. Broad principals such as Everyone, BUILTIN\Users, or Authenticated Users are
   forbidden.

The wrappers validate this contract and fail closed. They do not repair ACLs,
create directories, create profiles, or create secret files.

## Lane isolation

### Line 1 — observation only

The Line 1 wrapper removes inherited `DIE_SNAPSHOT_HMAC_KEY` and
`DIE_SNAPSHOT_HMAC_KEY_ID` values without reading them. It also removes
fallback API-key environment variables and supplies only the lane-specific
control-plane key file reference to `tunnel-client`.

Line 1 cannot load HMAC files and cannot inherit signing material.

### Line 2 — decision push

The Line 2 wrapper validates fixed-path ACLs before any protected file read. In a
future, separately authorized Run, it will:

1. let `tunnel-client` consume the control-plane API key through the fixed
   `file:` reference;
2. read the Line 2 HMAC key and key-id files without printing their values;
3. inject them only into the current wrapper process;
4. let only the tunnel-client process and its Line 2 MCP child inherit them;
5. clear both process-scoped variables in `finally`.

The wrapper rejects HMAC keys shorter than 32 UTF-8 bytes and rejects malformed
key identifiers. It never writes either value.

## B1 dry-run

Run from an ordinary PowerShell session in `C:\DIE`:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\New-DIEExecutiveMcpSecureConfigPlan.ps1 -Mode Plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Invoke-DIEExecutiveLine1Tunnel.ps1 -Mode Plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Invoke-DIEExecutiveLine2Tunnel.ps1 -Mode Plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpSecureConfig.ps1
python -m pytest bridge\tests\test_executive_secure_config_v1.py -q
python -m pytest bridge\tests -q
~~~

Expected properties:

- every command is read-only;
- every JSON result reports Plan or DryRun;
- no ProgramData path is created, read, or modified by B1 validation;
- no secret value or tunnel identity is requested or returned;
- no profile is initialized;
- no `tunnel-client doctor` or `tunnel-client run` command is executed;
- no MCP process, Windows service, scheduled task, tunnel, or registration is
  created.

## Future B2 boundary

B2 requires a separate Founder authorization. Only then may a local operator,
through a secure no-echo VPS-side channel:

- create the fixed directories and restrictive ACLs;
- provision lane-specific secret files;
- enter two real tunnel identities;
- initialize two distinct local profiles;
- validate profiles;
- start either tunnel lane.

No real key, HMAC material, or tunnel identity may be pasted into chat, printed
in logs, stored in test output, or committed to Git.

## Explicit B1 prohibitions

Phase B1 does not:

- access or modify `C:\ProgramData\DIE\ExecutiveMCP`;
- request, read, generate, validate, or provision real secret material;
- request, read, or persist tunnel identities;
- initialize or mutate tunnel profiles;
- invoke tunnel-client doctor or run;
- create or modify an OpenAI-hosted tunnel;
- start, deploy, expose, or register an MCP service;
- create a Windows service or scheduled task;
- stage, commit, push, or open a pull request;
- touch live state, projection, or organism-test artifacts.
