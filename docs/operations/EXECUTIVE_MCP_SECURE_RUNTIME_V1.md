# Executive MCP Secure Runtime Skeleton v1

Status: Phase B2A local non-secret runtime skeleton
Branch: architect/executive-mcp-secure-runtime-v1
Runtime root: C:\ProgramData\DIE\ExecutiveMCP
Canonical repository: C:\DIE

## Purpose

Phase B2A creates and verifies only the empty, lane-isolated Windows directory
skeleton required by the already-merged Executive MCP secure-config contract.
It applies restrictive ACLs, but it does not create configuration files, secret
files, tunnel profiles, logs, PID files, credentials, or tunnel identities.

This phase intentionally separates filesystem preparation from secret
provisioning, tunnel initialization, process execution, and ChatGPT
registration. B2B and later phases require separate Founder authorization.

## Versioned manifest

- ops/windows/executive-mcp/Initialize-DIEExecutiveMcpSecureRuntime.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureRuntime.ps1
- docs/operations/EXECUTIVE_MCP_SECURE_RUNTIME_V1.md
- bridge/tests/test_executive_secure_runtime_v1.py
- LASTSTANDINGPOINT.md

The initializer defaults to Plan. Apply is the only mutating mode. The verifier
defaults to Plan and uses Installed only after Apply.

## Fixed directory contract

| Boundary | Line 1 | Line 2 |
| --- | --- | --- |
| Configuration | C:\ProgramData\DIE\ExecutiveMCP\config\line1 | C:\ProgramData\DIE\ExecutiveMCP\config\line2 |
| Secrets container | C:\ProgramData\DIE\ExecutiveMCP\secrets\line1 | C:\ProgramData\DIE\ExecutiveMCP\secrets\line2 |
| Logs | C:\ProgramData\DIE\ExecutiveMCP\logs\line1 | C:\ProgramData\DIE\ExecutiveMCP\logs\line2 |
| Runtime | C:\ProgramData\DIE\ExecutiveMCP\runtime\line1 | C:\ProgramData\DIE\ExecutiveMCP\runtime\line2 |

The shared secrets directory is created only as an empty protected container.
Every lane directory must remain empty at the end of B2A.

The installer binary and its Phase A evidence manifest under the bin directory
are outside the B2A write set and are neither modified nor revalidated here.

## ACL contract

The Phase A root and existing config, logs, and runtime parents must already
satisfy the restrictive ACL contract. B2A refuses Apply if they do not.

B2A creates or hardens the secrets root and eight lane directories so that:

1. ACL inheritance is disabled.
2. No inherited rule is accepted.
3. Only explicit Allow rules are accepted.
4. Every accepted rule grants FullControl.
5. The complete allowed principal set is Local System (S-1-5-18), built-in
   Administrators (S-1-5-32-544), and the current activation-operator SID.
6. No broad or unresolved principal is accepted.

## Fail-closed rules

Before mutation, Apply checks the existing roots and lane paths.

- config, secrets, logs, and runtime roots may contain only line1 and line2
  directories;
- an existing lane directory must be completely empty;
- an unexpected file, directory, reparse entry, or ACL principal stops Apply;
- no existing content is deleted, moved, overwritten, or repaired;
- Apply is idempotent only while every managed lane remains empty.

Installed verification checks the same topology, ACL contract, empty-lane
contract, and absence of a tunnel-client process. It reads filesystem metadata
only. It never reads secret or profile contents.

## Execution sequence

Run from an elevated Windows PowerShell session in C:\DIE.

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Initialize-DIEExecutiveMcpSecureRuntime.ps1 -Mode Plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpSecureRuntime.ps1 -Mode Plan
python -m pytest bridge\tests\test_executive_secure_runtime_v1.py -q
python -m pytest bridge\tests -q
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Initialize-DIEExecutiveMcpSecureRuntime.ps1 -Mode Apply
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpSecureRuntime.ps1 -Mode Installed
~~~

A second Apply may be used as an idempotency proof only while the lane
directories are still empty. Once B2B provisions any local artifact, B2A Apply
must not be rerun.

## Expected evidence

Plan must report:

- writes_performed=false;
- secret_files_created=false;
- profile_files_created=false;
- every tunnel, process, service, task, and external-mutation flag=false.

Apply must report only created, existing, and protected directory paths.
Installed must report ready=true, no failed checks, empty managed lanes,
restricted ACLs, and tunnel_client_process_absent=true.

No command output may contain a real key, HMAC value, key identifier, tunnel
identity, profile content, or credential.

## Explicit B2A exclusions

Phase B2A does not:

- request, read, generate, provision, or validate secret material;
- create any secret, profile, configuration, log, or PID file;
- initialize a tunnel profile;
- invoke tunnel-client doctor or tunnel-client run;
- start, deploy, expose, or register an MCP service;
- create or modify an OpenAI tunnel;
- create a Windows service or scheduled task;
- modify the Phase A binary or installation manifest;
- touch repository state, projection, or organism-test runtime artifacts;
- commit, push, or create a pull request without separate publication
  authorization.

## Next phase boundary

B2B is Founder-operated local provisioning through a secure, no-echo VPS-side
channel. It may create the reviewed fixed-path secret and profile prerequisites
only after separate exact authorization. No real key, HMAC material, or tunnel
identity may be pasted into chat, printed in logs or tests, or committed to Git.
