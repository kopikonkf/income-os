# Executive MCP Secret Provisioning Tooling v1

Status: Phase B2B1 repository tooling only; no provisioning executed
Branch: architect/executive-mcp-secret-provisioning-v1
Runtime root: C:\ProgramData\DIE\ExecutiveMCP
Canonical repository: C:\DIE

## Purpose

B2B1 adds a reviewable, fail-closed Windows workflow for the future local
provisioning of Executive MCP secret files. The implementation is code-only in
this phase. Plan and repository tests are the only authorized executions.

Actual Provision mode is reserved for the Founder, or an explicitly delegated
local VPS operator, in a directly attached PowerShell console after a separate
exact execution authorization. Real values must never pass through ChatGPT,
Architect MCP, shell command arguments, environment variables, Git, logs, test
fixtures, clipboard transcripts, screenshots, or chat messages.

Tunnel identities and profile initialization are deliberately deferred to B2C.
B2B1 does not accept, store, validate, or request either tunnel identity.

## Versioned manifest

- ops/windows/executive-mcp/Set-DIEExecutiveMcpSecrets.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecrets.ps1
- docs/operations/EXECUTIVE_MCP_SECRET_PROVISIONING_V1.md
- bridge/tests/test_executive_secret_provisioning_v1.py
- LASTSTANDINGPOINT.md

Both scripts default to Plan. B2B1 repository validation must not invoke
Provision or Installed.

## Fixed secret-file contract

| Lane | Purpose | Fixed file |
| --- | --- | --- |
| Line 1 | Control-plane authentication | C:\ProgramData\DIE\ExecutiveMCP\secrets\line1\control-plane-api-key |
| Line 2 | Control-plane authentication | C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\control-plane-api-key |
| Line 2 | Snapshot HMAC signing | C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\snapshot-hmac-key |
| Line 2 | Snapshot HMAC key identifier | C:\ProgramData\DIE\ExecutiveMCP\secrets\line2\snapshot-hmac-key-id |

Line 1 is structurally unable to receive snapshot-signing material.

Initial provisioning is create-only. Existing secret files or any unexpected
lane entry cause a hard failure. Rotation is not implemented in v1 and must use
a separately reviewed rotation workflow.

## No-echo input and memory handling

Future Provision mode:

1. requires Windows, a directly attached interactive console, and the explicit
   ConfirmInteractiveProvisioning switch;
2. checks every parent ACL, empty lane, absent target, and absent tunnel-client
   process before displaying any secret prompt;
3. reads every value and confirmation through Read-Host -AsSecureString;
4. copies SecureString characters through an unmanaged BSTR into temporary
   character and byte arrays without creating a plaintext managed string;
5. compares confirmation bytes, validates only the minimum contract, and never
   prints a value, length, hash, prefix, suffix, or masked fragment;
6. creates each fixed target with FileMode.CreateNew and FileShare.None;
7. applies and verifies the restrictive ACL contract;
8. clears temporary character and byte arrays and zero-frees every BSTR;
9. removes only files created by the current transaction if a later write
   fails.

The script has no secret-valued command-line parameter and performs no
environment enumeration.

## ACL contract

Every secret directory and file must have inheritance disabled and only
explicit Allow FullControl rules for:

- Local System (S-1-5-18);
- built-in Administrators (S-1-5-32-544);
- the current local provisioning operator SID.

B2B1 refuses to repair an unsafe parent directory. The protected B2A skeleton
must pass first.

## Validation boundary

Plan is completely ProgramData-free.

A future Installed verification reads only filesystem metadata:

- exact file names and counts;
- file presence and byte-length bounds;
- directory and file ACLs;
- absence of profiles, logs, PID artifacts, and tunnel-client process.

Installed never opens or reads a secret file, never validates a secret value,
and never returns secret-derived hashes or fragments.

## Authorized B2B1 validation

Run only:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Set-DIEExecutiveMcpSecrets.ps1 -Mode Plan
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Test-DIEExecutiveMcpSecrets.ps1 -Mode Plan
python -m pytest bridge\tests\test_executive_secret_provisioning_v1.py -q
python -m pytest bridge\tests -q
~~~

Do not run Provision or Installed during B2B1 tooling validation.

## Future Founder-operated execution

This command is documented for a future separately authorized local console
session; it is not authorized by the B2B1 tooling phase:

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\ops\windows\executive-mcp\Set-DIEExecutiveMcpSecrets.ps1 -Mode Provision -ConfirmInteractiveProvisioning
~~~

After successful local provisioning, the Founder may run the metadata-only
Installed validator. Neither command may be run through chat or Architect MCP.

## Explicit B2B1 prohibitions

B2B1 tooling validation does not:

- request, read, generate, provision, rotate, or validate any real secret;
- request, read, store, or validate a tunnel identity;
- create or modify a tunnel profile;
- invoke tunnel-client doctor or tunnel-client run;
- start, deploy, expose, or register either MCP service;
- create or modify an OpenAI tunnel;
- create a Windows service or scheduled task;
- modify the Phase A binary or evidence manifest;
- touch live state, projection, or organism-test artifacts;
- commit, push, or create a pull request without separate publication
  authorization.

## Next boundaries

- B2B2: separately authorized Founder-operated local secret provisioning and
  metadata-only Installed verification.
- B2C: separately authorized two-lane tunnel-profile initialization and doctor
  validation, without persistent run.
- B2D: Line 1 activation and ChatGPT registration.
- B2E: Line 2 activation only after Line 1 evidence is healthy.
