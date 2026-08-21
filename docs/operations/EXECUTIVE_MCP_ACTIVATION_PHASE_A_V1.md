# Executive MCP Activation — Phase A Bootstrap v1

Status: IMPLEMENTED LOCALLY; BOOTSTRAP ONLY; NOT PUBLISHED
Branch: architect/executive-mcp-activation-v1
Install root: C:\ProgramData\DIE\ExecutiveMCP
Official guide: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
Official client repository: https://github.com/openai/tunnel-client

## 1. Outcome

Phase A prepares the Windows host without activating either Executive MCP lane.

It provides:

- a fail-closed, plan-first installer;
- official latest-release discovery for Windows AMD64;
- verification against the release SHA256SUMS.txt;
- binary version and quickstart-help verification before installation;
- a non-secret install manifest with source, version, help digest, and SHA-256;
- fixed runtime directories with protected ACLs;
- an unauthenticated local/outbound preflight;
- repository tests that enforce the Phase A safety boundary.

Phase A does not create or modify a tunnel, initialize a tunnel profile, request or
read credentials, start an MCP server, expose a port, register a ChatGPT
connection, create a Windows service, or create a scheduled task.

## 2. Versioned files

| File | Purpose |
| --- | --- |
| ops/windows/executive-mcp/Install-DIEExecutiveMcpPhaseA.ps1 | Plan/apply bootstrap and official-client verification |
| ops/windows/executive-mcp/Test-DIEExecutiveMcpPhaseA.ps1 | Read-only local, ACL, binary, help, checksum, and outbound preflight |
| bridge/tests/test_executive_activation_bootstrap_v1.py | Regression and safety-boundary tests |
| docs/operations/EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md | This runbook |

The installer has one fixed destination and no path override:
C:\ProgramData\DIE\ExecutiveMCP.

## 3. Runtime layout

~~~text
C:\ProgramData\DIE\ExecutiveMCP\
  bin\
    tunnel-client.exe
    tunnel-client.install.json
  config\
  logs\
  runtime\
~~~

The config, logs, and runtime directories are intentionally empty in Phase A.
No profile, credential, tunnel ID, PID file, service definition, or scheduled-task
definition is created.

ACL inheritance is disabled on the root and each child directory. Full control is
limited to:

- Local System;
- built-in Administrators;
- the Windows identity that executes the bootstrap.

## 4. Safe execution order

Run from an elevated PowerShell prompt on the VPS.

### 4.1 Plan only

~~~powershell
Set-Location C:\DIE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Install-DIEExecutiveMcpPhaseA.ps1 -Mode Plan
~~~

Expected safety flags:

- writes_performed = false
- tunnel_profiles_initialized = false
- tunnel_created_or_modified = false
- credentials_requested_or_read = false
- mcp_services_started = false
- windows_service_or_task_created = false

### 4.2 Pre-install local/outbound preflight

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpPhaseA.ps1 -Mode Plan
~~~

The only network probe is an unauthenticated TCP connection to
api.openai.com:443. It does not send an API key or call a tunnel endpoint.

### 4.3 Apply Phase A

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Install-DIEExecutiveMcpPhaseA.ps1 -Mode Apply
~~~

The installer:

1. resolves the latest stable release from the official openai/tunnel-client
   GitHub repository;
2. selects exactly one Windows AMD64 tunnel-client archive;
3. downloads the archive and official SHA256SUMS.txt into a bounded transient
   subdirectory under the Phase A runtime path;
4. compares the archive hash with the official checksum entry;
5. extracts exactly one tunnel-client.exe;
6. verifies its reported version against the release tag;
7. verifies tunnel-client help quickstart exits successfully;
8. copies only the verified executable into bin;
9. records the source, checksums, version output, help-output digest, and
   Authenticode observation in tunnel-client.install.json;
10. removes the transient bootstrap workspace.

The release archive and checksum file are not retained.

### 4.4 Installed-state verification

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpPhaseA.ps1 -Mode Installed
~~~

This verifies the fixed paths, protected ACLs, source manifest, installed binary
hash, release version, quickstart help, clean bootstrap workspace, absence of a
running tunnel-client process, local MCP bootstrap files, Python, and outbound
TCP reachability.

### 4.5 Repository regression

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest bridge/tests -q -p no:cacheprovider
~~~

Do not run the live activation-readiness checker in Phase A. Its later-phase
contract evaluates runtime prerequisites that are intentionally absent here.

## 5. Evidence contract

The non-secret runtime evidence is:

C:\ProgramData\DIE\ExecutiveMCP\bin\tunnel-client.install.json

Required fields include:

- official repository, release URL, release tag, asset URL;
- official and downloaded archive SHA-256;
- installed executable SHA-256;
- version command/output/exit code;
- quickstart-help command, exit code, and output SHA-256;
- observed Authenticode status;
- fixed installation paths and ACL status;
- explicit false flags for tunnel/profile/service/credential operations.

The manifest must never contain credentials, tunnel IDs, configuration profiles,
environment dumps, command-line secrets, or complete help output.

## 6. Phase boundary

Phase B requires separate Founder authorization. It is the earliest phase that
may address secure runtime credential provisioning, distinct tunnel identities,
profile initialization, doctor validation, MCP process lifecycle, ChatGPT
registration, or Developer Mode tool testing.

No Phase B action is implied by a successful Phase A bootstrap.

## 7. Rollback boundary

No rollback is executed automatically. Removing or replacing the ProgramData
installation is a separate destructive operation and requires explicit
authorization after the exact target is revalidated.
