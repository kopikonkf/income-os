# LASTSTANDINGPOINT.md

Date: 2026-08-21
Project: Digital Income Empire — Company Holdings
Mode: Chief Executive Architect
Workflow stage: P3 — EXECUTIVE MCP ACTIVATION v1 / PHASE B1 TOOLING VERIFIED / PUBLICATION AUTHORIZATION PENDING
Canonical runtime: C:\DIE
Canonical repository: https://github.com/kopikonkf/income-os
Working branch: architect/executive-mcp-secure-config-v1
Base branch: main
Base/merge commit: c585f9d2fd3016b84f59ebc629ba339e4dc2a719
Phase A implementation commit: ae2a42aee309b9eee05dbf4376ef86806c967c4d
Merged PR: https://github.com/kopikonkf/income-os/pull/8
Publication status: PR #8 MERGED; PHASE B1 COMPLETE LOCALLY; NOTHING STAGED OR PUBLISHED

## Verified merge baseline

PR #7 — Executive MCP Activation Gate v1.1 is merged and closed:

https://github.com/kopikonkf/income-os/pull/7

- merged at: 2026-08-21T07:53:37Z;
- PR head: 4199f78114df531e0162748ced576dc482063419;
- merge commit: 9cfe7ff781726a887e8ce039fd7f6bde0f79b019;
- C:\DIE\main and origin/main were synchronized before the Phase A branch;
- post-merge Company Brain validator: PASS;
- post-merge regression before Phase A: 69 passed.

PR #8 — Executive MCP Activation Phase A v1 is merged and closed:

https://github.com/kopikonkf/income-os/pull/8

- merged at: 2026-08-21T11:54:04Z;
- feature head: 16b8cdb12e6c94ae85cd6c5ce10b2e40102b26fa;
- merge commit: c585f9d2fd3016b84f59ebc629ba339e4dc2a719;
- C:\DIE\main and origin/main are synchronized at the merge commit;
- post-merge full bridge regression: 76 passed;
- post-merge Phase A installed-state preflight: PASS / ready=true;
- live runtime state changes survived synchronization.

## Canonical runtime boundary

~~~text
GitHub main
  = canonical code + governed documents

C:\DIE\state
  = live append-only state + generated runtime projections

C:\ProgramData\DIE\ExecutiveMCP
  = local non-secret Executive MCP activation runtime
~~~

Runtime-owned repository paths currently preserved and excluded:

- state/EVENTS.jsonl — modified;
- state/projection/.cursor — modified;
- state/projection/BRIEFING.md — modified;
- state/projection/EVENTS.jsonl — modified;
- state/projection/WAKE.flag — currently absent/deleted by runtime;
- state/organism-test/groundtruth-20260821.txt — untracked runtime/test ground truth;
- state/DECISIONS.jsonl — unmodified.

These paths must not be staged, discarded, restored, rewritten, or included in
an architecture PR without a separate state-governance decision.

## Corrected P0–P9 standing

| Stage | Actual status | Canonical standing |
| --- | --- | --- |
| P0 — Autopsy/Salvage | COMPLETE | KEEP/MODIFY/RETIRE and salvage boundary complete. |
| P1 — Company Brain | COMPLETE | Constitution, identities, registry, agency contract, and validator merged in PR #2. |
| P2 — Architect MCP | FUNCTIONALLY COMPLETE | Live C:\DIE inspection/write/test/Git cycle works; security-hardening debt remains. |
| P3 — Plus Line 1/2 | CODE + GATE COMPLETE; PHASE A MERGED; PHASE B1 VERIFIED LOCALLY; ACTIVATION STILL BLOCKED | Executive Line 1/2 and Activation Gate v1.1 are merged. Official tunnel-client is installed. Secure-config tooling is verified but unpublished; no tunnel/profile/secret/process/registration exists. |
| P4 — Division Line 1/2 | TEMPLATE FOUNDATION ONLY | Keep inactive until one real division and scoped projection exist. |
| P5 — State Layer | COMPLETE v1 | Signed bounded snapshots, typed evidence, replay-safe commit, and State Manager boundary merged in PR #3. |
| P6 — Decision Gateway | COMPLETE v1 | Stateless validation/router and Hermes-ready route merged in PR #4. |
| P7 — Hermes/Worker/Proxima | PARTIAL EXISTING | Hermes integration waits until Executive MCP activation is verified. Proxima remains Worker ↔ Web Chat AI only. |
| P8 — Dashboard | BLOCKED BY DESIGN | Start only after one real division and one economic loop are alive. |
| P9 — Genome/Bootstrap/etc. | DEFERRED | Classify after the current decision/execution loop is operational. |

## Phase A authorization executed

Founder authorized Executive MCP Activation Phase A bootstrap only, with these
hard boundaries:

- versioned Windows scripts, runbook, and tests;
- latest official tunnel-client download and fixed-path installation;
- non-secret runtime/config/log directories with restrictive ACLs;
- dry-run, tests, and unauthenticated outbound/local preflight;
- no secrets, credentials, tunnel IDs, profile initialization, tunnel mutation,
  MCP start/deploy/exposure/registration, Windows service, or scheduled task;
- no commit, push, or PR without separate publication authorization.

All boundaries were preserved.

## Versioned Phase A implementation

Merged through PR #8 from architect/executive-mcp-activation-v1:

- ops/windows/executive-mcp/Install-DIEExecutiveMcpPhaseA.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpPhaseA.ps1
- docs/operations/EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md
- bridge/tests/test_executive_activation_bootstrap_v1.py
- LASTSTANDINGPOINT.md — updated canonical handoff

Installer properties:

- default mode is Plan;
- Apply uses the fixed root C:\ProgramData\DIE\ExecutiveMCP only;
- release discovery is restricted to the official openai/tunnel-client GitHub
  release API and official release URLs;
- archive SHA-256 must match official SHA256SUMS.txt;
- reported version must match the release tag;
- tunnel-client help quickstart must succeed;
- only the verified executable and non-secret install manifest persist;
- transient bootstrap files are removed;
- no activation command exists in the Phase A scripts.

## Installed Phase A runtime

Official source:

- repository: https://github.com/openai/tunnel-client
- release: v0.0.12
- release URL: https://github.com/openai/tunnel-client/releases/tag/v0.0.12
- asset: tunnel-client-v0.0.12-windows-amd64.zip
- published: 2026-08-20T05:04:29Z

Installation:

- root: C:\ProgramData\DIE\ExecutiveMCP
- binary: C:\ProgramData\DIE\ExecutiveMCP\bin\tunnel-client.exe
- evidence manifest:
  C:\ProgramData\DIE\ExecutiveMCP\bin\tunnel-client.install.json
- config directory: empty;
- logs directory: empty;
- runtime directory: empty after bootstrap cleanup;
- ACL inheritance: disabled on root, bin, config, logs, and runtime;
- ACL principals: Local System, built-in Administrators, invoking Windows
  identity.

Verification evidence:

- official/downloaded archive SHA-256:
  2a2804933924e38a502d62b61f0266cb80d56d65744f4c29876b2bf9c1544356
- installed binary SHA-256:
  6649169733686805ca16cccd91774594d0c017fd729c37ad4ce1cd18323d9ae8
- reported version:
  0.0.12+881c9a8fed7cccbe6607cd419863bbca506b8215
- version/release match: PASS;
- help quickstart exit code: 0;
- help-output digest recorded in the non-secret install manifest;
- Authenticode observation: NotSigned;
- trust basis used: exact official GitHub release URL + official checksum manifest
  + matching version + successful quickstart help.

## Verification result

Dry-run:

~~~text
schema=die.executive.mcp.activation.phase-a.v1
mode=Plan
release=v0.0.12
writes_performed=false
all safety flags=false
~~~

Pre-install preflight:

~~~text
ready=true
Windows AMD64=true
Line 1 bootstrap present=true
Line 2 bootstrap present=true
Python present=true
tunnel-client process absent=true
api.openai.com:443 reachable=true
~~~

Repository regression:

~~~text
Phase A targeted tests: 7 passed
Full bridge regression: 76 passed
git diff --check: PASS
~~~

Installed-state preflight:

~~~text
schema=die.executive.mcp.activation.phase-a.preflight.v1
mode=Installed
ready=true
failed_checks=[]
fixed directories present=true
all directory ACL checks=true
binary hash matches manifest=true
version matches release=true
quickstart help matches manifest=true
bootstrap workspace clean=true
tunnel-client process absent=true
api.openai.com:443 reachable=true
~~~

Post-bootstrap negative proof:

- tunnel profiles initialized: FALSE;
- OpenAI tunnels created or modified: FALSE;
- credentials requested or read: FALSE;
- MCP services started/deployed/exposed/registered: FALSE;
- Windows service created: FALSE;
- scheduled task created: FALSE;
- related tunnel-client process running: FALSE;
- temporary release archive/checksum/extraction artifacts retained: FALSE.

## Activation standing

The fail-closed activation checker was intentionally not rerun because Phase A
must not inspect runtime secret prerequisites.

Current canonical fact:

- tunnel-client binary is physically installed and verified at the fixed path;
- it is not added to PATH and not configured as an activation environment value;
- no runtime Platform API key or HMAC material was requested, read, generated, or
  provisioned;
- no Line 1 or Line 2 tunnel ID was requested, read, stored, or initialized;
- no profile, doctor run, tunnel process, MCP process, ChatGPT registration, or
  tool call was performed.

Therefore P3 runtime activation remains blocked by design.

## Published Phase A manifest

Exact repository files merged through PR #8:

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_activation_bootstrap_v1.py
- docs/operations/EXECUTIVE_MCP_ACTIVATION_PHASE_A_V1.md
- ops/windows/executive-mcp/Install-DIEExecutiveMcpPhaseA.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpPhaseA.ps1

Explicit publication exclusions:

- state/EVENTS.jsonl
- state/DECISIONS.jsonl
- all state/projection artifacts
- all state/organism-test artifacts
- C:\ProgramData runtime installation and evidence manifest
- secrets, credentials, tunnel IDs
- temporary files and cache artifacts

Implementation commit ae2a42aee309b9eee05dbf4376ef86806c967c4d was merged through
PR #8 at c585f9d2fd3016b84f59ebc629ba339e4dc2a719. No runtime state
path or excluded artifact was staged or committed.

## Phase B1 recommended boundary

Official OpenAI documentation confirms that real activation requires a tunnel_id,
a runtime API key, a reachable private MCP server, the correct organization and
workspace association, profile initialization, doctor validation, then a running
tunnel-client before ChatGPT discovery.

Canonical reference:

https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

Installed tunnel-client v0.0.12 help also confirms that the control-plane key can
be referenced through an environment variable or an ACL-protected file. Phase B1
will build only the reusable secure-config tooling and lane wrappers. It will not
receive, create, store, or validate any real secret or tunnel ID.

Phase B1 code-only target:

- plan-first Windows secure-config bootstrap;
- fixed ProgramData secret/config path contract with restrictive ACL rules;
- separate Line 1 and Line 2 wrapper contracts;
- file-reference support for the tunnel runtime key;
- process-scoped HMAC injection contract for Line 2 only;
- redaction, zero-secret-output, and no-environment-dump tests;
- dry-run and static validation only;
- no profile initialization, doctor, run, service, scheduled task, deployment,
  exposure, or ChatGPT registration.

## Phase B1 authorization executed

~~~text
AUTHORIZED: execute Executive MCP Activation Phase B1 secure-config tooling only.
Implement versioned Windows secure-config and isolated lane wrapper scripts,
runbook, and tests on architect/executive-mcp-secure-config-v1.
Use only fixed C:\ProgramData\DIE\ExecutiveMCP paths, restrictive ACL contracts,
and file-based secret references supported by the installed tunnel-client.
Run dry-run validation and repository tests only.

Exclude state/EVENTS.jsonl, state/DECISIONS.jsonl,
all state/projection and state/organism-test runtime artifacts,
the C:\ProgramData runtime installation, all real secrets, credentials,
tunnel IDs, temporary files, and cache artifacts.
Do not request, read, generate, or provision any real API key or HMAC material.
Do not create or modify any OpenAI tunnel.
Do not initialize tunnel profiles.
Do not run tunnel-client doctor or tunnel-client run.
Do not start, deploy, expose, or register either MCP service.
Do not create a Windows service or scheduled task.
Do not commit, push, or create a PR until separate publication authorization.
~~~

Phase B1 tooling is now verified locally but remains unstaged and unpublished.
B2 still requires the Founder to enter two tunnel IDs and runtime secret material
locally on the VPS through an interactive no-echo channel after separate B2
authorization. No secret or tunnel ID may be pasted into chat or committed to Git.

## Phase B1 implementation and verification

Implemented locally on `architect/executive-mcp-secure-config-v1`:

- `ops/windows/executive-mcp/New-DIEExecutiveMcpSecureConfigPlan.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine1Tunnel.ps1`
- `ops/windows/executive-mcp/Invoke-DIEExecutiveLine2Tunnel.ps1`
- `ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureConfig.ps1`
- `docs/operations/EXECUTIVE_MCP_SECURE_CONFIG_V1.md`
- `bridge/tests/test_executive_secure_config_v1.py`
- `LASTSTANDINGPOINT.md`

Implemented contracts:

- plan-only secure-config compiler with no Apply mode and no ProgramData access;
- fixed, lane-separated config, secret, log, PID, health, and profile paths;
- lane-specific control-plane key references using the installed client's
  `file:C:\ProgramData\...` syntax;
- protected ACL contract limited to Local System, built-in Administrators, and
  the future local activation operator;
- Line 1 strips inherited HMAC and fallback API-key variables without reading
  them;
- Line 2 validates protected files, injects HMAC material process-locally only in
  a future separately authorized Run, and clears it in `finally`;
- both wrappers default to Plan and bind health/admin endpoints to distinct
  loopback addresses;
- remote admin UI, raw HTTP logging, environment enumeration, detached process,
  Windows service, and scheduled-task paths are absent.

Verification:

~~~text
Secure-config dry-run: PASS
Checks: 29/29
Failed checks: none
ProgramData accessed by validation: false
Secret values returned: false
Targeted Phase B1 tests: 9 passed
Full bridge regression: 85 passed
git diff --check: PASS
Staged paths: 0
~~~

Negative proof:

- no real API key, HMAC value, key ID, or tunnel ID was requested, read,
  generated, provisioned, or printed;
- no ProgramData directory, profile, or secret file was created or modified;
- no tunnel profile was initialized;
- no tunnel-client doctor or run command was executed;
- no MCP service, tunnel, Windows service, scheduled task, deployment, exposure,
  or ChatGPT registration was created;
- no commit, push, or pull request was performed;
- all runtime-owned state/projection/organism-test paths remain excluded and
  untouched by the architecture work.

Exact prospective publication manifest:

- LASTSTANDINGPOINT.md
- bridge/tests/test_executive_secure_config_v1.py
- docs/operations/EXECUTIVE_MCP_SECURE_CONFIG_V1.md
- ops/windows/executive-mcp/Invoke-DIEExecutiveLine1Tunnel.ps1
- ops/windows/executive-mcp/Invoke-DIEExecutiveLine2Tunnel.ps1
- ops/windows/executive-mcp/New-DIEExecutiveMcpSecureConfigPlan.ps1
- ops/windows/executive-mcp/Test-DIEExecutiveMcpSecureConfig.ps1

## Next controlled action

Await separate publication authorization for the exact seven-file Phase B1
manifest above. Do not stage, commit, push, or open a PR before that authorization.
Phase B2 activation and all external Platform/ChatGPT mutations remain prohibited.

## Operating doctrine

Build > Run > Verify > Refactor > Extend

Do not restart the repository.
Do not build the dashboard yet.
Do not activate Division runtime yet.
Do not merge Line 2 mutation into Line 1.
Do not reuse Architect DEV trust for runtime cognition.
Do not expose raw paths, credentials, tunnel IDs, or DEV capability.
Do not stage, discard, or rewrite live state/projection/organism artifacts.
Do not write synthetic decisions to live canonical state.
Ship executable artifacts, not architecture theater.
First real money remains the organism fitness signal.
